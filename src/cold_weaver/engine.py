"""Cold Weaver Engine — collision detection between conversation fragments.

The Cold Weaver finds connections between ideas the user hasn't linked.
It scans all embedded fragments, computes collision scores for cross-source pairs,
and stores the best ones for later delivery.

See ARCHITECTURE_HARNESS.md section on Cold Weaver.
"""

import logging
from itertools import combinations

import numpy as np

from src.cold_weaver.scoring import collision_score, DELIVERY_THRESHOLD
from src.cold_weaver.sources import ArxivSource, ExternalFragment
from src.embeddings import get_embedder, cosine_similarity, embedding_to_bytes
from src.llm_client import LLMClient
from src.memory.episodic import EpisodicMemory
from src.memory.semantic import SemanticMemory
from src.config import MINIMAX_MODEL_FAST
from src.persona.state import PersonaState

logger = logging.getLogger("delirium.cold_weaver")


class ColdWeaverEngine:
    """Scans fragments for collisions and stores the best ones."""

    def __init__(self, episodic: EpisodicMemory, semantic: SemanticMemory,
                 llm: LLMClient):
        self.episodic = episodic
        self.semantic = semantic
        self.llm = llm
        self.embedder = get_embedder()
        self.arxiv = ArxivSource()

    def scan(self, include_arxiv: bool = False) -> int:
        """Run a full collision scan. Returns number of new collisions found."""
        logger.info("Cold Weaver scan starting...")

        # Embed any fragments that don't have embeddings yet
        self._embed_missing()

        # Optionally fetch ArXiv and store as fragments
        if include_arxiv:
            self._fetch_and_store_arxiv()

        # Get all embedded fragments
        fragments = self.episodic.get_all_with_embeddings()
        if len(fragments) < 2:
            logger.info("Not enough embedded fragments for collision detection (%d)", len(fragments))
            return 0

        # Get theme embeddings for relevance scoring
        themes = self.semantic.get_active_themes(threshold=0.1)
        theme_embeddings = []
        if themes:
            theme_texts = [t["label"] for t in themes]
            theme_embeddings = [self.embedder.embed(t) for t in theme_texts]

        all_embeddings = [f["embedding"] for f in fragments]

        # Score all cross-source pairs (or distant same-source pairs)
        new_collisions = 0
        candidates = self._generate_candidates(fragments)

        for frag_a, frag_b in candidates:
            if self.episodic.collision_already_exists(frag_a["id"], frag_b["id"]):
                continue

            score = collision_score(
                frag_a["embedding"], frag_b["embedding"],
                all_embeddings, theme_embeddings
            )

            if score >= DELIVERY_THRESHOLD:
                # Generate the connection description via LLM
                connection = self._generate_connection(frag_a, frag_b)

                self.episodic.store_collision(
                    frag_a["id"], frag_b["id"], score, connection
                )
                self.episodic.log_execution(None, "collision_detected", {
                    "fragment_a": frag_a["id"],
                    "fragment_b": frag_b["id"],
                    "score": score,
                    "connection": connection,
                })
                new_collisions += 1
                logger.info("Collision found (%.2f): %s <-> %s",
                            score, frag_a["user_input"][:50], frag_b["user_input"][:50])

        logger.info("Cold Weaver scan complete: %d new collisions", new_collisions)
        return new_collisions

    def _generate_candidates(self, fragments: list[dict]):
        """Generate candidate pairs for collision scoring.

        Prioritizes: cross-source pairs > temporally distant same-source pairs.
        Limits total pairs to avoid O(n^2) explosion.
        """
        MAX_PAIRS = 500

        cross_source = []
        same_source = []

        for a, b in combinations(fragments, 2):
            if a["source"] != b["source"]:
                cross_source.append((a, b))
            else:
                same_source.append((a, b))

        # Cross-source first, then same-source up to the limit
        candidates = cross_source[:MAX_PAIRS]
        remaining = MAX_PAIRS - len(candidates)
        if remaining > 0:
            candidates.extend(same_source[:remaining])

        return candidates

    def _embed_missing(self):
        """Embed all fragments that don't have embeddings yet."""
        rows = self.episodic.conn.execute(
            "SELECT id, user_input FROM conversations WHERE embedding IS NULL"
        ).fetchall()

        if not rows:
            return

        logger.info("Embedding %d fragments...", len(rows))
        for row in rows:
            emb = self.embedder.embed(row["user_input"])
            self.episodic.update_embedding(row["id"], emb)
        logger.info("Embedding complete")

    def _fetch_and_store_arxiv(self):
        """Fetch ArXiv papers for active themes and store as fragments."""
        themes = self.semantic.get_active_themes(threshold=0.3)
        if not themes:
            logger.info("No active themes for ArXiv fetch")
            return

        theme_labels = [t["label"] for t in themes[:5]]
        papers = self.arxiv.fetch(theme_labels)

        dummy_state = PersonaState()
        for paper in papers:
            # Check if already stored (by title in user_input)
            existing = self.episodic.conn.execute(
                "SELECT 1 FROM conversations WHERE user_input = ? AND source = 'arxiv'",
                (paper.title,)
            ).fetchone()
            if existing:
                continue

            emb = self.embedder.embed(paper.title + " " + paper.summary)
            self.episodic.store(
                user_message=paper.title,
                response=paper.summary,
                session_id="cold_weaver",
                persona_state=dummy_state,
                source="arxiv",
                embedding=emb,
            )

        logger.info("Stored %d ArXiv papers", len(papers))

    def _generate_connection(self, frag_a: dict, frag_b: dict) -> str:
        """Use LLM to describe the connection between two fragments."""
        prompt = (
            "Tu es le Cold Weaver de Delirium. Décris en UNE phrase la connexion "
            "inattendue entre ces deux idées. Ton mystérieux, pas didactique. "
            "Format : juste la phrase, rien d'autre."
        )
        msg = (
            f"Idée A ({frag_a.get('source', '?')}): {frag_a['user_input'][:200]}\n"
            f"Idée B ({frag_b.get('source', '?')}): {frag_b['user_input'][:200]}"
        )
        try:
            return self.llm.chat(
                system=prompt,
                messages=[{"role": "user", "content": msg}],
                model=MINIMAX_MODEL_FAST,
            )
        except Exception as e:
            logger.warning("Connection generation failed: %s", e)
            return f"{frag_a['user_input'][:80]} <-> {frag_b['user_input'][:80]}"

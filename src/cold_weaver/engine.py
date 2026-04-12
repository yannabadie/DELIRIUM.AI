"""Cold Weaver Engine — collision detection between conversation fragments.

The Cold Weaver finds connections between ideas the user hasn't linked.
It scans all embedded fragments, computes collision scores for cross-source pairs,
and stores the best ones for later delivery.

See ARCHITECTURE_HARNESS.md section on Cold Weaver.
"""

import logging
import random
from itertools import combinations

import numpy as np

from src.cold_weaver.scoring import collision_score, DELIVERY_THRESHOLD, is_substantive
from src.cold_weaver.sources import ArxivSource
from src.embeddings import get_embedder
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

        self._embed_missing()

        if include_arxiv:
            self._fetch_and_store_arxiv()

        # Get all embedded fragments, pre-filter noise
        all_fragments = self.episodic.get_all_with_embeddings()
        fragments = [f for f in all_fragments if is_substantive(f["user_input"])]
        logger.info("Fragments: %d total, %d substantive (filtered %d noise)",
                     len(all_fragments), len(fragments), len(all_fragments) - len(fragments))

        if len(fragments) < 2:
            return 0

        # Theme embeddings for relevance scoring
        themes = self.semantic.get_active_themes(threshold=0.1)
        theme_embeddings = []
        if themes:
            theme_embeddings = [self.embedder.embed(t["label"]) for t in themes]

        # Score candidate pairs
        new_collisions = 0
        candidates = self._generate_candidates(fragments)

        for frag_a, frag_b in candidates:
            if self.episodic.collision_already_exists(frag_a["id"], frag_b["id"]):
                continue

            score = collision_score(
                frag_a["embedding"], frag_b["embedding"],
                frag_a["user_input"], frag_b["user_input"],
                theme_embeddings,
            )

            if score >= DELIVERY_THRESHOLD:
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
                logger.info("Collision (%.2f): %s <-> %s",
                            score, frag_a["user_input"][:50], frag_b["user_input"][:50])

        logger.info("Cold Weaver scan complete: %d new collisions", new_collisions)
        return new_collisions

    def _generate_candidates(self, fragments: list[dict]):
        """Generate candidate pairs for collision scoring.

        Prioritizes cross-source, then temporally distant same-source pairs.
        """
        MAX_PAIRS = 1000

        cross_source = []
        sorted_frags = sorted(fragments, key=lambda f: f.get("timestamp", ""))
        n = len(sorted_frags)

        for a, b in combinations(fragments, 2):
            if a["source"] != b["source"]:
                cross_source.append((a, b))

        # Same-source: pair fragments that are temporally distant
        same_source_distant = []
        stride = max(1, n // 20)
        for i in range(n):
            for j in range(i + stride, n, max(1, n // 50)):
                if len(same_source_distant) >= MAX_PAIRS * 2:
                    break
                same_source_distant.append((sorted_frags[i], sorted_frags[j]))
            if len(same_source_distant) >= MAX_PAIRS * 2:
                break

        random.shuffle(same_source_distant)

        # Mix cross-source and same-source
        half = MAX_PAIRS // 2
        candidates = cross_source[:half]
        candidates.extend(same_source_distant[:MAX_PAIRS - len(candidates)])

        logger.info("Candidates: %d (%d cross-source, %d same-source)",
                     len(candidates), min(len(cross_source), half),
                     len(candidates) - min(len(cross_source), half))
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

        papers = self.arxiv.fetch([t["label"] for t in themes[:5]])
        dummy_state = PersonaState()

        for paper in papers:
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

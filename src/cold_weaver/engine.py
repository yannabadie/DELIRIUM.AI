"""Cold Weaver Engine — collision detection between conversation fragments.

The Cold Weaver finds connections between ideas the user hasn't linked.
Scans embedded fragments, scores pairs, filters by LLM quality, stores the best.

See ARCHITECTURE_HARNESS.md section on Cold Weaver.
"""

import json
import logging
import random
import re
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

# Minimum LLM quality score to keep a collision
MIN_CONNECTION_QUALITY = 0.4


class ColdWeaverEngine:
    """Scans fragments for collisions and stores the best ones."""

    def __init__(self, episodic: EpisodicMemory, semantic: SemanticMemory,
                 llm: LLMClient):
        self.episodic = episodic
        self.semantic = semantic
        self.llm = llm
        self.embedder = get_embedder()
        self.arxiv = ArxivSource()

    def scan(self, include_arxiv: bool = True) -> int:
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
        trivial_filtered = 0
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
                # LLM quality gate: judge + describe the connection
                connection, quality = self._judge_connection(frag_a, frag_b)

                if quality < MIN_CONNECTION_QUALITY:
                    trivial_filtered += 1
                    self.episodic.log_execution(None, "collision_filtered_trivial", {
                        "fragment_a": frag_a["id"],
                        "fragment_b": frag_b["id"],
                        "score": score,
                        "quality": quality,
                    })
                    continue

                self.episodic.store_collision(
                    frag_a["id"], frag_b["id"], score * quality, connection
                )
                self.episodic.log_execution(None, "collision_detected", {
                    "fragment_a": frag_a["id"],
                    "fragment_b": frag_b["id"],
                    "score": score,
                    "quality": quality,
                    "connection": connection,
                })
                new_collisions += 1
                logger.info("Collision (%.2f, q=%.2f): %s <-> %s",
                            score, quality,
                            frag_a["user_input"][:50], frag_b["user_input"][:50])

        logger.info("Cold Weaver scan complete: %d collisions, %d filtered as trivial",
                     new_collisions, trivial_filtered)
        return new_collisions

    def _generate_candidates(self, fragments: list[dict]):
        """Generate candidate pairs. Excludes same-conversation pairs."""
        MAX_PAIRS = 1000

        cross_source = []
        sorted_frags = sorted(fragments, key=lambda f: f.get("timestamp", ""))
        n = len(sorted_frags)

        for a, b in combinations(fragments, 2):
            if a["source"] != b["source"]:
                cross_source.append((a, b))

        # Same-source, different conversation, temporally distant
        same_source_distant = []
        stride = max(1, n // 20)
        for i in range(n):
            for j in range(i + stride, n, max(1, n // 50)):
                if len(same_source_distant) >= MAX_PAIRS * 2:
                    break
                a, b = sorted_frags[i], sorted_frags[j]
                # Skip same conversation — trivial connection
                if a.get("session_id") and a["session_id"] == b.get("session_id"):
                    continue
                same_source_distant.append((a, b))
            if len(same_source_distant) >= MAX_PAIRS * 2:
                break

        random.shuffle(same_source_distant)

        # Mix cross-source and same-source
        half = MAX_PAIRS // 2
        candidates = cross_source[:half]
        candidates.extend(same_source_distant[:MAX_PAIRS - len(candidates)])

        logger.info("Candidates: %d (%d cross-source, %d same-source-diff-conv)",
                     len(candidates), min(len(cross_source), half),
                     len(candidates) - min(len(cross_source), half))
        return candidates

    def _embed_missing(self):
        rows = self.episodic.conn.execute(
            "SELECT id, user_input FROM conversations WHERE embedding IS NULL"
        ).fetchall()
        if not rows:
            return
        logger.info("Embedding %d fragments...", len(rows))
        for row in rows:
            self.episodic.update_embedding(row["id"], self.embedder.embed(row["user_input"]))
        logger.info("Embedding complete")

    def _fetch_and_store_arxiv(self):
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
                user_message=paper.title, response=paper.summary,
                session_id="cold_weaver", persona_state=dummy_state,
                source="arxiv", embedding=emb,
            )
        logger.info("Stored %d ArXiv papers", len(papers))

    def _judge_connection(self, frag_a: dict, frag_b: dict) -> tuple[str, float]:
        """LLM judges if the connection is non-trivial and describes it.

        Returns (connection_text, quality_score).
        quality < MIN_CONNECTION_QUALITY → collision is discarded.
        """
        prompt = (
            "Tu es le Cold Weaver de Delirium. Deux idées d'un utilisateur :\n"
            f"- Idée A ({frag_a.get('source', '?')}): {frag_a['user_input'][:200]}\n"
            f"- Idée B ({frag_b.get('source', '?')}): {frag_b['user_input'][:200]}\n\n"
            "1. Ces deux idées ont-elles une connexion NON-TRIVIALE ? "
            "(pas juste 'les deux parlent de tech' ou 'les deux sont des questions')\n"
            "2. Si oui, décris la connexion en UNE phrase mystérieuse, pas didactique.\n"
            "3. Score la qualité de 0.0 (triviale, évidente) à 1.0 (insight profond, inattendu).\n\n"
            'Réponds UNIQUEMENT en JSON: {"connection": "...", "quality": 0.0}'
        )
        try:
            raw = self.llm.chat(
                system="Tu es un évaluateur de connexions. Réponds en JSON uniquement.",
                messages=[{"role": "user", "content": prompt}],
                model=MINIMAX_MODEL_FAST,
            )
            return self._parse_judge_response(raw)
        except Exception as e:
            logger.warning("Connection judging failed: %s", e)
            return f"{frag_a['user_input'][:80]} <-> {frag_b['user_input'][:80]}", 0.5

    def _parse_judge_response(self, raw: str) -> tuple[str, float]:
        """Parse the LLM judge response."""
        text = raw.strip()
        # Strip markdown code fences
        if text.startswith("```"):
            lines = text.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            text = "\n".join(lines)

        try:
            data = json.loads(text)
            connection = data.get("connection", "")
            quality = float(data.get("quality", 0.0))
            quality = max(0.0, min(1.0, quality))
            return connection, quality
        except (json.JSONDecodeError, ValueError, TypeError):
            # Try to extract quality from text
            match = re.search(r"(\d+\.?\d*)", text)
            quality = float(match.group(1)) if match else 0.5
            quality = max(0.0, min(1.0, quality))
            return text[:200], quality

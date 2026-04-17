"""Cold Weaver Engine — collision detection between conversation fragments.

The Cold Weaver finds connections between ideas the user hasn't linked.
Scans embedded fragments, scores pairs, filters by LLM quality, stores the best.

Candidate generation prioritizes TOPIC DIVERSITY: pairs fragments from
different conversations to find cross-project, cross-context collisions.
"""

import json
import logging
import random
from collections import defaultdict
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

        all_fragments = self.episodic.get_all_with_embeddings()
        fragments = [f for f in all_fragments if is_substantive(f["user_input"])]
        logger.info("Fragments: %d total, %d substantive (filtered %d noise)",
                     len(all_fragments), len(fragments), len(all_fragments) - len(fragments))

        if len(fragments) < 2:
            return 0

        themes = self.semantic.get_active_themes(threshold=0.1)
        theme_embeddings = []
        if themes:
            theme_embeddings = [self.embedder.embed(t["label"]) for t in themes]

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
                judged = self._judge_connection(frag_a, frag_b)
                if judged is None:
                    continue
                connection, quality = judged

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
        """Generate candidate pairs maximizing TOPIC DIVERSITY.

        Strategy:
        1. Group fragments by conversation (session_id)
        2. Cross-source pairs (claude ↔ arxiv ↔ delirium): always included
        3. Cross-conversation pairs: pick one fragment from each of two
           DIFFERENT conversations — this catches cross-project collisions
           even within the same broad domain
        """
        MAX_PAIRS = 2000

        # Group by session_id
        by_session = defaultdict(list)
        for f in fragments:
            by_session[f.get("session_id", "unknown")].append(f)

        sessions = list(by_session.keys())
        logger.info("Conversations: %d unique sessions", len(sessions))

        # 1. Cross-source pairs (always valuable)
        cross_source = []
        sources = defaultdict(list)
        for f in fragments:
            sources[f["source"]].append(f)

        source_names = list(sources.keys())
        for i, s1 in enumerate(source_names):
            for s2 in source_names[i + 1:]:
                for a in sources[s1]:
                    for b in sources[s2]:
                        cross_source.append((a, b))

        random.shuffle(cross_source)

        # 2. Cross-conversation pairs (the key for intra-domain diversity)
        cross_conv = []
        session_pairs = list(combinations(sessions, 2))
        random.shuffle(session_pairs)

        for sess_a, sess_b in session_pairs:
            if len(cross_conv) >= MAX_PAIRS * 2:
                break
            frags_a = by_session[sess_a]
            frags_b = by_session[sess_b]
            # Sample 1-2 fragments from each conversation to keep it manageable
            sample_a = random.sample(frags_a, min(2, len(frags_a)))
            sample_b = random.sample(frags_b, min(2, len(frags_b)))
            for a in sample_a:
                for b in sample_b:
                    cross_conv.append((a, b))

        random.shuffle(cross_conv)

        # Mix: cross-source gets priority, then cross-conversation fills the rest
        candidates = cross_source[:MAX_PAIRS // 2]
        remaining = MAX_PAIRS - len(candidates)
        candidates.extend(cross_conv[:remaining])

        logger.info("Candidates: %d (%d cross-source, %d cross-conversation)",
                     len(candidates),
                     min(len(cross_source), MAX_PAIRS // 2),
                     len(candidates) - min(len(cross_source), MAX_PAIRS // 2))
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

    def _judge_connection(self, frag_a: dict, frag_b: dict) -> tuple[str, float] | None:
        """LLM judges if the connection is non-trivial and describes it."""
        prompt = (
            "Tu es le Cold Weaver de Delirium. Deux idées d'un utilisateur :\n"
            f"- Idée A ({frag_a.get('source', '?')}): {frag_a['user_input'][:300]}\n"
            f"- Idée B ({frag_b.get('source', '?')}): {frag_b['user_input'][:300]}\n\n"
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
            return None

    def _parse_judge_response(self, raw: str) -> tuple[str, float]:
        text = raw.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            text = "\n".join(lines)
        data = json.loads(text)
        if not isinstance(data, dict):
            raise ValueError("Judge response must be a JSON object")

        connection = data.get("connection")
        quality = data.get("quality")

        if not isinstance(connection, str) or not connection.strip():
            raise ValueError("Judge response is missing a connection string")

        try:
            normalized_quality = float(quality)
        except (ValueError, TypeError) as exc:
            raise ValueError("Judge response is missing a numeric quality") from exc

        return connection.strip(), max(0.0, min(1.0, normalized_quality))

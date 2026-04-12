"""Theme Extractor — Bootstrap semantic memory from imported conversations.

Solves the cold start problem: imported messages have embeddings but no themes
in the semantic graph, so ArXiv fetch and relevance scoring have nothing to work with.

Takes a sample of messages, sends to LLM, stores extracted themes.
"""

import json
import logging
import random

from src.llm_client import LLMClient
from src.memory.semantic import SemanticMemory
from src.config import MINIMAX_MODEL_FAST

logger = logging.getLogger("delirium.import.themes")


class ThemeExtractor:
    """Extracts themes from imported messages to bootstrap semantic memory."""

    def extract(self, messages: list, llm: LLMClient,
                semantic: SemanticMemory) -> list[str]:
        """Extract themes from imported messages and store in semantic graph.

        Uses 1 LLM call on a sample of ~50 substantive messages.
        Returns the list of extracted theme labels.
        """
        # Sample substantive messages
        substantive = [m for m in messages if len(m.user_input) > 50]
        if not substantive:
            logger.info("No substantive messages for theme extraction")
            return []

        sample = random.sample(substantive, min(50, len(substantive)))
        sample_text = "\n".join(f"- {m.user_input[:150]}" for m in sample)

        prompt = (
            "Voici des messages d'un utilisateur envoyés à différentes IA.\n"
            "Extrais les 10-20 thèmes principaux qui ressortent.\n"
            "Chaque thème doit être un label court (2-4 mots, en français).\n"
            'Réponds UNIQUEMENT en JSON : {"themes": ["theme1", "theme2", ...]}'
        )

        try:
            raw = llm.chat(
                system=prompt,
                messages=[{"role": "user", "content": sample_text}],
                model=MINIMAX_MODEL_FAST,
            )
            themes = self._parse_themes(raw)
        except Exception as e:
            logger.error("Theme extraction failed: %s", e)
            return []

        if not themes:
            return []

        # Score each theme by frequency across ALL messages
        all_text = " ".join(m.user_input.lower() for m in messages)
        for theme in themes:
            # Count occurrences (approximate: check if any word of the theme appears)
            theme_words = theme.lower().split()
            matches = sum(1 for w in theme_words if w in all_text)
            weight = min(matches / max(len(theme_words), 1) * 0.1, 1.0)
            weight = max(weight, 0.3)  # minimum weight for extracted themes

            semantic.add_or_reinforce_theme(theme, weight)

        logger.info("Extracted %d themes from %d messages", len(themes), len(messages))
        return themes

    def _parse_themes(self, raw: str) -> list[str]:
        text = raw.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            text = "\n".join(lines)
        try:
            data = json.loads(text)
            themes = data.get("themes", [])
            return [t.strip() for t in themes if isinstance(t, str) and t.strip()]
        except (json.JSONDecodeError, AttributeError):
            logger.warning("Failed to parse theme JSON: %s", text[:200])
            return []

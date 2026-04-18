"""Delirium AI — CLI prototype.

Usage: python -m src.main

Commands:
    /import chatgpt|claude|generic <path>  — Import conversations
    /collisions [--purge]   — Run Cold Weaver collision scan
    /status                 — Show full system status
    quit / exit / q         — Quit
"""

import asyncio
import logging
import math
import re
import sys
import warnings
from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4

# Suppress noisy loggers BEFORE any imports that trigger them
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)
logging.getLogger("sentence_transformers").setLevel(logging.WARNING)
warnings.filterwarnings("ignore", category=DeprecationWarning, message=".*event loop.*")

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.theme import Theme
from prompt_toolkit import PromptSession
from prompt_toolkit.history import InMemoryHistory

from src.config import (
    DELIRIUM_DECAY_MODE,
    DELIRIUM_FORGETTING_STRATEGY,
    MINIMAX_API_KEY,
    SQLITE_DB_PATH,
    validate_prompt_files,
)
from src.llm_client import LLMClient, AsyncLLMClient
from src.memory.episodic import EpisodicMemory
from src.memory.semantic import SemanticMemory
from src.memory.working import WorkingMemory
from src.memory.decay import DecayEngine
from src.memory.world_vision import WorldVision
from src.memory.bubble import classify_injection_followup, h_bulle
from src.persona.engine import PersonaEngine
from src.persona.gag_contract import normalize_gag_type, normalize_text_value
from src.persona.state import PersonaState
from src.persona.retrait import compute_retrait_state, adjust_persona_for_retrait, get_retrait_context
from src.persona.gags import GagTracker
from src.s2.analyzer import S2Analyzer
from src.embeddings import get_embedder, cosine_similarity
from src.first_message import FIRST_MESSAGE_INSTRUCTION
from src.guardrails import behavioral_reply
from src.process_cleanup import (
    drain_active_children,
    install_safe_multiprocessing_close,
    is_running_process_close_error,
)

# Internal logger (file only, never shown to user)
Path(SQLITE_DB_PATH).parent.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=[logging.FileHandler(SQLITE_DB_PATH.replace(".db", ".log"), encoding="utf-8")],
)
logger = logging.getLogger("delirium")
SESSION_IDLE_TIMEOUT = timedelta(minutes=30)
MAX_S1_RESPONSE_CHARS = 4096
_BOOLEAN_TRUE_STRINGS = {"1", "true", "yes", "on"}
_BOOLEAN_FALSE_STRINGS = {"0", "false", "no", "off", ""}
_BUBBLE_INJECTION_PATTERN = re.compile(
    r"\brien\s+[aà]\s+voir(?:\s*[,;:.!?…-]+\s*|\s+)mais\b",
    re.IGNORECASE,
)
_ULTRASHORT_REPLY_WORD_RE = re.compile(r"[A-Za-zÀ-ÿ0-9']+")
_ULTRASHORT_REPLY_LEADS = (
    "ah", "bah", "bon", "hmm", "hm", "merde", "non", "ok", "okay", "oui",
    "ouais", "putain",
)
_ULTRASHORT_REPLY_MIN_WORDS = 6

install_safe_multiprocessing_close()

# Rich console for user-facing output
console = Console(theme=Theme({
    "delirium": "cyan bold",
    "user": "yellow",
    "info": "dim",
    "success": "green",
    "error": "red bold",
    "heading": "bold",
}))


def _is_running_process_close_error(exc: Exception) -> bool:
    return is_running_process_close_error(exc)


def _drain_active_children() -> None:
    """Best-effort cleanup for multiprocessing children left by dependencies."""
    try:
        drain_active_children()
    except Exception as exc:
        logger.warning("Child process cleanup failed: %s", exc)


def _contains_bubble_injection(text: str) -> bool:
    return bool(_BUBBLE_INJECTION_PATTERN.search(text))


class Delirium:
    """Main orchestrator."""

    def __init__(self):
        self.llm = LLMClient()
        self.async_llm = AsyncLLMClient()
        self.episodic = EpisodicMemory(SQLITE_DB_PATH)
        self.semantic = SemanticMemory(self.episodic.conn)
        self.working = WorkingMemory()
        self.persona_engine = PersonaEngine()
        self.s2 = S2Analyzer(self.async_llm, self.episodic, self.semantic, self.persona_engine)
        self.embedder = get_embedder()
        self.decay = DecayEngine(
            self.episodic.conn,
            mode=DELIRIUM_DECAY_MODE,
            strategy=DELIRIUM_FORGETTING_STRATEGY,
        )
        self.world_vision = WorldVision(self.episodic.conn, self.llm)
        self.gags = GagTracker(self.episodic.conn)

        # Restore persona state
        saved_state = self.episodic.load_latest_persona_state()
        if saved_state:
            self._reset_session_scoped_bubble_state(saved_state)
            self.persona_engine.set_state(saved_state)

        # Decay + gag cleanup at session start
        self.decay.apply_decay()
        self.gags.apply_decay()

        # Compute retrait state
        last_ts = self._get_last_interaction_timestamp()
        self.retrait_state = compute_retrait_state(last_ts)
        if self.retrait_state != "active":
            state = self.persona_engine.get_current_state()
            adjust_persona_for_retrait(state, self.retrait_state)
            self.persona_engine.set_state(state)
        self._applied_retrait_state = self.retrait_state

        self.session_id = str(uuid4())
        self._last_message_at = None
        self._collision_delivered = False
        self._bubble_injections_this_session = 0
        self._pending_bubble_injection = None

    @staticmethod
    def _reset_session_scoped_bubble_state(state: PersonaState) -> None:
        """Clear one-session antibubble triggers restored from persisted persona state."""
        state.bubble_break_enabled = False
        state.bubble_break_intensity = "off"

    def _log_execution_safely(self, fragment_id: str | None, log_type: str, content: dict) -> bool:
        try:
            self.episodic.log_execution(fragment_id, log_type, content)
        except Exception as exc:
            logger.error("Execution logging failed for %s: %s", log_type, exc)
            return False
        return True

    def _get_last_interaction_timestamp(self) -> str | None:
        conn = getattr(self.episodic, "conn", None)
        if conn is None or not hasattr(conn, "execute"):
            return None
        row = conn.execute(
            "SELECT MAX(timestamp) as ts FROM conversations WHERE source = 'delirium'"
        ).fetchone()
        return row["ts"] if row and row["ts"] else None

    def _refresh_retrait_state(self, state: PersonaState) -> None:
        last_ts = self._get_last_interaction_timestamp()
        self.retrait_state = compute_retrait_state(last_ts)
        if self.retrait_state == "active":
            self._applied_retrait_state = "active"
            return

        if getattr(self, "_applied_retrait_state", None) == self.retrait_state:
            return

        adjust_persona_for_retrait(state, self.retrait_state)
        self.persona_engine.set_state(state)
        self._applied_retrait_state = self.retrait_state

    def _rotate_session(self, state: PersonaState | None = None) -> None:
        self.session_id = str(uuid4())
        self._last_message_at = None
        self._collision_delivered = False
        self._bubble_injections_this_session = 0
        self._pending_bubble_injection = None
        if state is not None:
            self._reset_session_scoped_bubble_state(state)

    def _ensure_active_session(self, state: PersonaState | None = None) -> None:
        last_message_at = getattr(self, "_last_message_at", None)
        if last_message_at is None:
            return
        if datetime.now() - last_message_at <= SESSION_IDLE_TIMEOUT:
            return
        self._rotate_session(state)

    def _safe_embed(self, text: str, *, context: str):
        try:
            return self.embedder.embed(text)
        except Exception as exc:
            logger.warning("Embedding failed for %s: %s", context, exc)
            return None

    def _validate_response_bounds(self, response: str) -> str:
        if not isinstance(response, str):
            raise ValueError("S1 response must be a string")
        if not response.strip():
            raise ValueError("S1 response cannot be empty")
        if len(response) > MAX_S1_RESPONSE_CHARS:
            raise ValueError("S1 response exceeds size limit")
        return response

    @staticmethod
    def _stabilize_ultrashort_response(response: str) -> str:
        stripped = response.strip()
        if not stripped:
            return response

        words = _ULTRASHORT_REPLY_WORD_RE.findall(stripped)
        if len(words) >= _ULTRASHORT_REPLY_MIN_WORDS:
            return stripped

        lead = words[0].lower() if words else ""
        if lead not in _ULTRASHORT_REPLY_LEADS:
            return stripped

        if "?" in stripped:
            return f"{stripped}\n\nQu'est-ce qui te fait dire ca, au juste ?"
        return f"{stripped}\n\nQu'est-ce qui se passe, au juste ?"

    def _stream_response(self, system: str, messages: list[dict]) -> str:
        """Stream LLM response to console with rich formatting."""
        tokens = []
        console.print("[delirium]Delirium:[/delirium] ", end="")
        for token in self.llm.chat_stream_iter(system, messages):
            console.print(token, end="", highlight=False)
            tokens.append(token)
        console.print()  # newline
        return "".join(tokens).strip()

    def _maybe_resynthesize_world_vision(self, loop: asyncio.AbstractEventLoop,
                                         fragment_id: str, s2_result: dict | None) -> None:
        sessions_since = self.world_vision.get_sessions_since_last_vision()
        if not self.world_vision.should_resynthesize(s2_result, sessions_since):
            return

        try:
            vision = loop.run_until_complete(asyncio.to_thread(
                self.world_vision.resynthesize,
                self.semantic.get_active_themes(threshold=0.0),
                self.semantic.get_correlations(),
                self.semantic.get_loops(),
                self.world_vision.get_danger_history(),
                self.episodic.get_fragment_count(),
            ))
            self._log_execution_safely(fragment_id, "world_vision_resynthesized", {
                "version": vision.get("version"),
                "sessions_since_last": sessions_since,
                "danger_level": (s2_result or {}).get("danger_level", 0),
            })
        except Exception as exc:
            logger.error("World vision resynthesis failed: %s", exc)
            self._log_execution_safely(fragment_id, "world_vision_resynthesis_error", {
                "error": str(exc),
                "sessions_since_last": sessions_since,
            })

    @staticmethod
    def _coerce_optional_bool(value, default: bool = False) -> bool:
        if isinstance(value, bool):
            return value
        if value is None:
            return default
        if isinstance(value, (int, float)):
            if not math.isfinite(value):
                return default
            return bool(value)
        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered in _BOOLEAN_TRUE_STRINGS:
                return True
            if lowered in _BOOLEAN_FALSE_STRINGS or lowered in {"none", "null"}:
                return False
        return default

    @staticmethod
    def _normalize_bubble_score(value) -> float:
        try:
            score = float(value)
        except (TypeError, ValueError):
            return 0.0
        return score if math.isfinite(score) else 0.0

    @staticmethod
    def _normalize_bubble_status(value) -> str:
        if value in {"low_risk", "medium_risk", "high_risk"}:
            return value
        return "low_risk"

    @classmethod
    def _normalize_detected_gag_seed(cls, gag_seed: dict | None) -> dict | None:
        if not isinstance(gag_seed, dict):
            return None

        seed = normalize_text_value(
            gag_seed.get("seed"),
            collapse_internal_whitespace=True,
        )
        if not seed:
            return None

        return {
            "seed": seed,
            "type": normalize_gag_type(gag_seed.get("type"), "in_joke"),
            "user_callback": cls._coerce_optional_bool(gag_seed.get("user_callback", False)),
        }

    def _maybe_register_detected_gag(self, fragment_id: str, s2_result: dict | None) -> None:
        try:
            gag_seed = self._normalize_detected_gag_seed(self.gags.detect_seed(s2_result))
            if not gag_seed:
                return

            gag_id, created = self.gags.register_or_refresh_gag(
                gag_seed["seed"],
                gag_seed["type"],
                user_callback=gag_seed.get("user_callback", False),
            )
        except Exception as exc:
            logger.error("Running gag update failed: %s", exc)
            self._log_execution_safely(fragment_id, "gag_error", {"error": str(exc)})
            return

        self._log_execution_safely(fragment_id, "gag_detected", {
            "gag_id": gag_id,
            "seed": gag_seed["seed"],
            "type": gag_seed["type"],
            "user_callback": gag_seed.get("user_callback", False),
            "created": created,
        })

    def _get_session_message_count(self) -> int:
        getter = getattr(self.episodic, "get_session_message_count", None)
        if not callable(getter):
            return 0
        try:
            return int(getter(self.session_id))
        except Exception:
            return 0

    def _should_refresh_bubble_signal(self, next_message_index: int) -> bool:
        return next_message_index == 1 or next_message_index % 5 == 0

    def _sync_bubble_followup(self, state: PersonaState, user_message: str) -> None:
        if not hasattr(self, "_pending_bubble_injection"):
            self._pending_bubble_injection = None
        if not self._pending_bubble_injection:
            return

        outcome = classify_injection_followup(
            user_message,
            self._pending_bubble_injection["response"],
            [self._pending_bubble_injection["anchor"]],
        )
        if outcome == "engaged":
            state.bubble_ignore_streak = 0
        elif outcome == "ignored":
            streak = getattr(state, "bubble_ignore_streak", 0)
            state.bubble_ignore_streak = min(streak + 1, 3)
        self._pending_bubble_injection = None

    def _refresh_bubble_state(self, state: PersonaState) -> None:
        next_message_index = self._get_session_message_count() + 1
        if not self._should_refresh_bubble_signal(next_message_index):
            return

        conn = getattr(self.episodic, "conn", None)
        if conn is None:
            return

        try:
            bubble = h_bulle(conn)
        except Exception as exc:
            logger.warning("Bubble scoring failed: %s", exc)
            return
        score = self._normalize_bubble_score(bubble.get("h_bulle", 0.0))
        status = self._normalize_bubble_status(bubble.get("bubble_status", "low_risk"))
        state.bubble_risk_score = score
        state.bubble_risk_status = status
        state.bubble_break_intensity = {
            "medium_risk": "gentle",
            "high_risk": "strong",
        }.get(status, "off")

    def _arm_bubble_break(self, state: PersonaState) -> None:
        if not hasattr(self, "_bubble_injections_this_session"):
            self._bubble_injections_this_session = 0
        eligible = (
            getattr(state, "bubble_break_intensity", "off") in {"gentle", "strong"}
            and getattr(state, "bubble_ignore_streak", 0) < 3
            and self._bubble_injections_this_session < 1
        )
        state.bubble_break_enabled = eligible

    def _register_bubble_injection(
        self,
        state: PersonaState,
        user_message: str,
        response: str,
    ) -> bool:
        if not hasattr(self, "_bubble_injections_this_session"):
            self._bubble_injections_this_session = 0
        if not hasattr(self, "_pending_bubble_injection"):
            self._pending_bubble_injection = None
        bubble_break_armed = getattr(state, "bubble_break_enabled", False)
        state.bubble_break_enabled = False
        if not bubble_break_armed:
            return False
        if not _contains_bubble_injection(response):
            return False

        self._bubble_injections_this_session += 1
        self._pending_bubble_injection = {
            "anchor": user_message,
            "response": response,
        }
        return True

    def process_message(self, user_message: str) -> str:
        state = self.persona_engine.get_current_state()
        self._ensure_active_session(state)
        self._refresh_retrait_state(state)
        self._sync_bubble_followup(state, user_message)
        self._refresh_bubble_state(state)
        self._arm_bubble_break(state)

        # Keep retrieval strength moving during active use, not just on app restart.
        self.decay.apply_decay()

        # Reactivate related memories (Bjork re-learning)
        self.decay.reactivate_related(user_message, self.episodic)

        relevant = self.episodic.search(user_message, n_results=5)
        themes = self.semantic.get_active_themes()

        # Check for pending collision (max 1/session)
        pending_collision = None
        if not self._collision_delivered:
            collision = self.episodic.get_pending_collision()
            if collision:
                pending_collision = collision
                self.episodic.mark_collision_delivered(collision["id"], self.session_id)
                self._collision_delivered = True

        vision_summary = self.world_vision.get_summary_for_s1()
        gag_context = self.gags.get_gag_context_for_s1()
        recent = self.episodic.get_recent(self.session_id, limit=20)
        messages = recent + [{"role": "user", "content": user_message}]

        s1_prompt = self.working.compose_s1_prompt(
            state, relevant, themes, pending_collision,
            vision_summary=vision_summary, gag_context=gag_context,
            thread_messages=messages,
        )

        console.print()
        response = self._stream_response(s1_prompt, messages)
        response = self._stabilize_ultrashort_response(response)
        response = self._validate_response_bounds(response)

        # Enrich with URL content before embedding (repos, papers, sites)
        from src.import_.enricher import enrich_text
        enriched = enrich_text(user_message)
        emb_user = self._safe_embed(enriched, context="user_message")
        fragment_id = self.episodic.store(
            user_message, response, self.session_id, state, embedding=emb_user
        )

        # Embed response separately if it introduces novel concepts
        # (surgissement non rebondi / injection latérale)
        emb_response = self._safe_embed(response, context="s1_response")
        novelty = 0.0
        if emb_user is not None and emb_response is not None:
            novelty = 1.0 - float(cosine_similarity(emb_user, emb_response))
        if emb_response is not None and novelty > 0.5:  # response is semantically distant
            self.episodic.store(
                response, "", self.session_id, state,
                source="delirium_novel", embedding=emb_response,
            )

        bubble_injected = self._register_bubble_injection(state, user_message, response)

        s1_log = {
            "H": state.H, "phase": state.phase,
            "collision_injected": pending_collision is not None,
            "response_novelty": round(novelty, 3),
        }
        if hasattr(state, "bubble_risk_status"):
            s1_log.update({
                "bubble_injected": bubble_injected,
                "bubble_risk_status": state.bubble_risk_status,
                "bubble_ignore_streak": state.bubble_ignore_streak,
            })

        self._log_execution_safely(fragment_id, "s1_response", s1_log)

        # S2 analysis (async)
        loop = asyncio.new_event_loop()
        try:
            s2_result = loop.run_until_complete(
                self.s2.analyze(fragment_id, user_message, response,
                                recent + [{"role": "user", "content": user_message},
                                           {"role": "assistant", "content": response}],
                                self.session_id)
            )
            self._maybe_register_detected_gag(fragment_id, s2_result)
            self._maybe_resynthesize_world_vision(loop, fragment_id, s2_result)
            loop.run_until_complete(loop.shutdown_asyncgens())
        finally:
            loop.close()

        self._last_message_at = datetime.now()
        return response

    def generate_first_message(self) -> str:
        state = self.persona_engine.get_current_state()
        self._ensure_active_session(state)
        self._refresh_retrait_state(state)

        retrait_ctx = None
        if self.retrait_state != "active":
            last_ts = self._get_last_interaction_timestamp()
            days = 0
            if last_ts:
                try:
                    days = (datetime.now() - datetime.fromisoformat(last_ts)).days
                except (ValueError, TypeError):
                    pass
            forgotten = self.decay.get_forgotten_topics()
            pending = self.episodic.get_pending_collision()
            retrait_ctx = get_retrait_context(self.retrait_state, days, forgotten, pending)

        vision_summary = self.world_vision.get_summary_for_s1()
        gag_context = self.gags.get_gag_context_for_s1()

        s1_prompt = self.working.compose_s1_prompt(
            state, [], [],
            vision_summary=vision_summary, gag_context=gag_context,
            retrait_context=retrait_ctx,
        )

        instruction = (
            "[L'utilisateur revient après une absence.]"
            if self.retrait_state != "active"
            else FIRST_MESSAGE_INSTRUCTION
        )

        response = behavioral_reply(instruction)
        if response:
            console.print()
            console.print("[delirium]Delirium:[/delirium] ", end="")
            console.print(response, highlight=False)
        else:
            console.print()
            response = self._validate_response_bounds(
                self._stream_response(s1_prompt, [{"role": "user", "content": instruction}])
            )
        response = self._validate_response_bounds(response)

        fragment_id = self.episodic.store(
            "[premier_message]", response, self.session_id,
            state, embedding=self._safe_embed(response, context="first_message")
        )
        self._log_execution_safely(fragment_id, "first_message", {
            "retrait_state": self.retrait_state,
        })
        self._last_message_at = datetime.now()
        return response

    # --- CLI Commands ---

    def cmd_import_chatgpt(self, path: str):
        from src.import_.chatgpt import ChatGPTImporter
        self._run_import(ChatGPTImporter(), path, "chatgpt")

    def cmd_import_claude(self, path: str):
        from src.import_.claude_ai import ClaudeImporter
        self._run_import(ClaudeImporter(), path, "claude")

    def cmd_import_github(self, username: str):
        """Import GitHub repos as semantic fragments for Cold Weaver."""
        from src.import_.github import GitHubImporter
        from src.import_.enricher import enrich_github_fragment

        importer = GitHubImporter(llm=self.llm)

        with console.status(f"Fetching GitHub repos for {username}..."):
            messages = importer.import_user(username)

        if not messages:
            console.print("[info]Aucun repo trouvé.[/info]")
            return

        console.print(f"[info]{len(messages)} fragments générés, embedding + enrichissement...[/info]")
        dummy_state = PersonaState()

        with console.status(f"Import github... 0/{len(messages)}") as status:
            for i, msg in enumerate(messages):
                # Enrich with similar repos + ArXiv papers
                repo_meta = {"description": msg.assistant_response,
                             "topics": [], "language": "", "name": msg.conversation_title}
                enriched = enrich_github_fragment(msg.user_input, repo_meta)
                emb = self._safe_embed(
                    enriched,
                    context=f"github_import:{msg.conversation_title[:30]}",
                )
                self.episodic.store(
                    user_message=msg.user_input,
                    response=msg.assistant_response,
                    session_id=f"import_github_{msg.conversation_title[:30]}",
                    persona_state=dummy_state,
                    source="github",
                    embedding=emb,
                )
                if (i + 1) % 10 == 0:
                    status.update(f"Import github... {i + 1}/{len(messages)}")

        self._log_execution_safely(None, "github_import", {
            "username": username, "fragments_imported": len(messages),
        })
        console.print(f"[success]Import terminé: {len(messages)} fragments GitHub[/success]")

        # Extract themes
        from src.import_.theme_extractor import ThemeExtractor
        with console.status("Extraction des thèmes..."):
            extractor = ThemeExtractor()
            themes = extractor.extract(messages, self.llm, self.semantic)
        if themes:
            console.print(f"[success]Thèmes: {', '.join(themes[:10])}[/success]")

    def cmd_import_generic(self, path: str):
        from src.import_.generic import GenericImporter
        self._run_import(GenericImporter(), path, "generic")

    def _run_import(self, importer, path: str, source: str):
        from src.import_.sycophancy import SycophancyDetector

        try:
            messages = importer.parse(path)
        except Exception as e:
            console.print(f"[error]Erreur de parsing: {e}[/error]")
            return

        if not messages:
            console.print("[info]Aucun message trouvé.[/info]")
            return

        detector = SycophancyDetector(llm=self.llm, use_llm=False)
        dummy_state = PersonaState()

        with console.status(f"Import {source}... 0/{len(messages)}") as status:
            for i, msg in enumerate(messages):
                syco_score = detector.score(msg.assistant_response, msg.user_input)
                from src.import_.enricher import enrich_text
                enriched = enrich_text(msg.user_input)
                emb = self._safe_embed(
                    enriched,
                    context=f"import:{source}:{msg.conversation_title[:30]}",
                )
                self.episodic.store(
                    user_message=msg.user_input,
                    response=msg.assistant_response,
                    session_id=f"import_{source}_{msg.conversation_title[:30]}",
                    persona_state=dummy_state,
                    source=msg.source or source,
                    embedding=emb,
                    sycophancy_score=syco_score,
                )
                if (i + 1) % 50 == 0:
                    status.update(f"Import {source}... {i + 1}/{len(messages)}")

        self._log_execution_safely(None, f"{source}_import", {
            "file": path, "messages_imported": len(messages),
        })
        console.print(f"[success]Import terminé: {len(messages)} messages[/success]")

        # Extract themes for Cold Weaver bootstrapping (cold start fix)
        from src.import_.theme_extractor import ThemeExtractor
        with console.status("Extraction des thèmes..."):
            extractor = ThemeExtractor()
            themes = extractor.extract(messages, self.llm, self.semantic)
        if themes:
            console.print(f"[success]Thèmes extraits: {', '.join(themes[:10])}[/success]")
            if len(themes) > 10:
                console.print(f"[info]  ... et {len(themes) - 10} autres[/info]")

    def cmd_collisions(self, purge: bool = False):
        from src.cold_weaver.engine import ColdWeaverEngine

        if purge:
            deleted = self.episodic.purge_collisions()
            console.print(f"[info]Purgé {deleted} collisions[/info]")

        engine = ColdWeaverEngine(self.episodic, self.semantic, self.llm)

        with console.status("Cold Weaver scan en cours..."):
            n = engine.scan(include_arxiv=True)

        total = self.episodic.get_collision_count()
        console.print(f"[success]{n} nouvelles collisions[/success] (total: {total})")

        pending = self.episodic.get_pending_collision()
        if pending:
            console.print(f"\n[heading]Meilleure collision (score {pending['collision_score']:.2f}):[/heading]")
            console.print(f"  A: {pending['a_input']}")
            console.print(f"  B: {pending['b_input']}")
            console.print(f"  [info]{pending['connection']}[/info]")

    def cmd_status(self):
        state = self.persona_engine.get_current_state()
        decay_stats = self.decay.get_stats()
        gags = self.gags.get_active_gags()
        bubble = h_bulle(self.episodic.conn)
        vision = self.world_vision.get_current()

        console.print("\n[heading]═══ PERSONA ═══[/heading]")
        console.print(f"  H: {state.H:.2f}  |  Phase: {state.phase}  |  Fatigue: {state.fatigue:.2f}")
        console.print(f"  Empathie: {state.empathy:.2f}  |  Confrontation: {state.confrontation:.2f}")
        console.print(f"  Retrait: {self.retrait_state}")

        console.print(f"\n[heading]═══ MÉMOIRE (Bjork {decay_stats['mode']}) ═══[/heading]")
        console.print(f"  Total: {decay_stats['total']}  |  Accessible: {decay_stats['accessible']}  "
                       f"|  En déclin: {decay_stats['fading']}  |  Oubliés: {decay_stats['forgotten']}")
        for source in ("delirium", "chatgpt", "claude", "arxiv", "github"):
            n = self.episodic.get_fragment_count(source)
            if n > 0:
                console.print(f"    {source}: {n}")
        console.print(f"  Sessions: {self.episodic.get_total_sessions()}")
        console.print(f"  Collisions: {self.episodic.get_collision_count()}")

        themes = self.semantic.get_active_themes()
        if themes:
            console.print(f"\n[heading]═══ THÈMES ACTIFS ═══[/heading]")
            for t in themes[:8]:
                bar = "█" * int(t["weight"] * 10)
                console.print(f"  {bar} {t['label']} ({t['weight']:.1f})")

        loops = self.semantic.get_loops()
        if loops:
            console.print(f"\n[heading]═══ BOUCLES ═══[/heading]")
            for l in loops[:5]:
                console.print(f"  ↻ {l['theme']} ({l['occurrences']}x)")

        if gags:
            console.print(f"\n[heading]═══ RUNNING GAGS ({len(gags)}) ═══[/heading]")
            for g in gags[:5]:
                cb = f" ({g['user_callback_count']} callbacks)" if g["user_callback_count"] else ""
                console.print(f"  - {g['seed_content']} [{g['type']}] {g['occurrence_count']}x{cb}")

        console.print(f"\n[heading]═══ BULLE (H_bulle) ═══[/heading]")
        console.print(f"  Score: {bubble['h_bulle']:.3f} ({bubble['bubble_status']})")

        if vision:
            who = vision.get("who_they_are", {})
            console.print(f"\n[heading]═══ VISION DU MONDE (v{vision.get('version', '?')}) ═══[/heading]")
            if who.get("summary"):
                console.print(f"  {who['summary']}")

    def close(self):
        for client in (self.async_llm, self.llm):
            try:
                client.close()
            except Exception as exc:
                logger.warning("Client shutdown failed: %s", exc)

        _drain_active_children()
        self.episodic.close()


def main():
    try:
        validate_prompt_files()
    except (FileNotFoundError, ValueError) as exc:
        console.print(f"[error]{exc}[/error]")
        sys.exit(1)
    if not MINIMAX_API_KEY:
        console.print("[error]MINIMAX_API_KEY non configurée.[/error]")
        console.print("Copie .env.example en .env et renseigne ta clé API MiniMax.")
        sys.exit(1)

    console.print(Panel(
        "[delirium]DELIRIUM AI — Non-BlocNote[/delirium]\n"
        "[info]\"Vos idées à la con sont intéressantes.\"[/info]",
        border_style="cyan",
    ))
    console.print("[info]Commandes: /import chatgpt|claude|generic <path>, /import github <username>, /collisions [--purge], /status[/info]")
    console.print("[info]Ctrl+C ou 'quit' pour quitter[/info]\n")

    delirium = None

    try:
        delirium = Delirium()
        session = PromptSession(history=InMemoryHistory())
        delirium.generate_first_message()

        while True:
            try:
                user_input = session.prompt("\nToi: ")
            except KeyboardInterrupt:
                console.print("\n[info]Ctrl+C — tape 'quit' pour quitter[/info]")
                continue
            except EOFError:
                break

            stripped = user_input.strip()

            if stripped.lower() in ("quit", "exit", "q"):
                break
            if not stripped:
                continue

            if stripped.startswith("/import chatgpt "):
                delirium.cmd_import_chatgpt(stripped[len("/import chatgpt "):].strip())
            elif stripped.startswith("/import claude "):
                delirium.cmd_import_claude(stripped[len("/import claude "):].strip())
            elif stripped.startswith("/import generic "):
                delirium.cmd_import_generic(stripped[len("/import generic "):].strip())
            elif stripped.startswith("/import github "):
                delirium.cmd_import_github(stripped[len("/import github "):].strip())
            elif stripped in ("/collisions", "/collisions --purge"):
                delirium.cmd_collisions(purge="--purge" in stripped)
            elif stripped == "/status":
                delirium.cmd_status()
            elif stripped.startswith("/"):
                console.print(f"[error]Commande inconnue: {stripped}[/error]")
            else:
                try:
                    delirium.process_message(user_input)
                except KeyboardInterrupt:
                    console.print("\n[info]Interrompu.[/info]")

    except KeyboardInterrupt:
        pass
    finally:
        if delirium is not None:
            try:
                delirium.close()
            except ValueError as exc:
                if not _is_running_process_close_error(exc):
                    raise
                logger.warning("Suppressed shutdown close() race during final teardown: %s", exc)
                _drain_active_children()
        else:
            _drain_active_children()
        console.print("\n[info]Session terminée. À plus.[/info]")


if __name__ == "__main__":
    main()

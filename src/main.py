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
import sys
import warnings
from datetime import datetime
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

from src.config import MINIMAX_API_KEY, SQLITE_DB_PATH
from src.llm_client import LLMClient, AsyncLLMClient
from src.memory.episodic import EpisodicMemory
from src.memory.semantic import SemanticMemory
from src.memory.working import WorkingMemory
from src.memory.decay import DecayEngine
from src.memory.world_vision import WorldVision
from src.memory.bubble import h_bulle
from src.persona.engine import PersonaEngine
from src.persona.state import PersonaState
from src.persona.retrait import compute_retrait_state, adjust_persona_for_retrait, get_retrait_context
from src.persona.gags import GagTracker
from src.s2.analyzer import S2Analyzer
from src.embeddings import get_embedder

# Internal logger (file only, never shown to user)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=[logging.FileHandler(SQLITE_DB_PATH.replace(".db", ".log"), encoding="utf-8")],
)
logger = logging.getLogger("delirium")

# Rich console for user-facing output
console = Console(theme=Theme({
    "delirium": "cyan bold",
    "user": "yellow",
    "info": "dim",
    "success": "green",
    "error": "red bold",
    "heading": "bold",
}))


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
        self.decay = DecayEngine(self.episodic.conn)
        self.world_vision = WorldVision(self.episodic.conn, self.llm)
        self.gags = GagTracker(self.episodic.conn)

        # Restore persona state
        saved_state = self.episodic.load_latest_persona_state()
        if saved_state:
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

        self.session_id = str(uuid4())
        self._collision_delivered = False

    def _get_last_interaction_timestamp(self) -> str | None:
        row = self.episodic.conn.execute(
            "SELECT MAX(timestamp) as ts FROM conversations WHERE source = 'delirium'"
        ).fetchone()
        return row["ts"] if row and row["ts"] else None

    def _stream_response(self, system: str, messages: list[dict]) -> str:
        """Stream LLM response to console with rich formatting."""
        tokens = []
        console.print("[delirium]Delirium:[/delirium] ", end="")
        for token in self.llm.chat_stream_iter(system, messages):
            console.print(token, end="", highlight=False)
            tokens.append(token)
        console.print()  # newline
        return "".join(tokens).strip()

    def process_message(self, user_message: str) -> str:
        state = self.persona_engine.get_current_state()

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

        s1_prompt = self.working.compose_s1_prompt(
            state, relevant, themes, pending_collision,
            vision_summary=vision_summary, gag_context=gag_context,
        )

        recent = self.episodic.get_recent(self.session_id, limit=20)
        messages = recent + [{"role": "user", "content": user_message}]

        console.print()
        response = self._stream_response(s1_prompt, messages)

        emb = self.embedder.embed(user_message)
        fragment_id = self.episodic.store(
            user_message, response, self.session_id, state, embedding=emb
        )
        self.episodic.log_execution(fragment_id, "s1_response", {
            "H": state.H, "phase": state.phase,
            "collision_injected": pending_collision is not None,
        })

        # S2 analysis (async)
        loop = asyncio.new_event_loop()
        loop.run_until_complete(
            self.s2.analyze(fragment_id, user_message, response,
                            recent + [{"role": "user", "content": user_message},
                                       {"role": "assistant", "content": response}],
                            self.session_id)
        )
        loop.close()

        return response

    def generate_first_message(self) -> str:
        state = self.persona_engine.get_current_state()

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
            else "[L'utilisateur ouvre l'app pour la première fois. Génère ton premier message.]"
        )

        console.print()
        response = self._stream_response(s1_prompt, [{"role": "user", "content": instruction}])

        fragment_id = self.episodic.store(
            "[premier_message]", response, self.session_id,
            state, embedding=self.embedder.embed(response)
        )
        self.episodic.log_execution(fragment_id, "first_message", {
            "retrait_state": self.retrait_state,
        })
        return response

    # --- CLI Commands ---

    def cmd_import_chatgpt(self, path: str):
        from src.import_.chatgpt import ChatGPTImporter
        self._run_import(ChatGPTImporter(), path, "chatgpt")

    def cmd_import_claude(self, path: str):
        from src.import_.claude_ai import ClaudeImporter
        self._run_import(ClaudeImporter(), path, "claude")

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
                emb = self.embedder.embed(msg.user_input)
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

        self.episodic.log_execution(None, f"{source}_import", {
            "file": path, "messages_imported": len(messages),
        })
        console.print(f"[success]Import terminé: {len(messages)} messages[/success]")

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
            console.print(f"  A: {pending['a_input'][:80]}")
            console.print(f"  B: {pending['b_input'][:80]}")
            console.print(f"  [info]{pending['connection'][:120]}[/info]")

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
        for source in ("delirium", "chatgpt", "claude", "arxiv"):
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
                console.print(f"  - {g['seed_content'][:50]} [{g['type']}] {g['occurrence_count']}x{cb}")

        console.print(f"\n[heading]═══ BULLE (H_bulle) ═══[/heading]")
        console.print(f"  Score: {bubble['h_bulle']:.3f} ({bubble['bubble_status']})")

        if vision:
            who = vision.get("who_they_are", {})
            console.print(f"\n[heading]═══ VISION DU MONDE (v{vision.get('version', '?')}) ═══[/heading]")
            if who.get("summary"):
                console.print(f"  {who['summary'][:120]}")

    def close(self):
        self.episodic.close()


def main():
    if not MINIMAX_API_KEY:
        console.print("[error]MINIMAX_API_KEY non configurée.[/error]")
        console.print("Copie .env.example en .env et renseigne ta clé API MiniMax.")
        sys.exit(1)

    console.print(Panel(
        "[delirium]DELIRIUM AI — Non-BlocNote[/delirium]\n"
        "[info]\"Vos idées à la con sont intéressantes.\"[/info]",
        border_style="cyan",
    ))
    console.print("[info]Commandes: /import chatgpt|claude|generic <path>, /collisions [--purge], /status[/info]")
    console.print("[info]Ctrl+C ou 'quit' pour quitter[/info]\n")

    delirium = Delirium()
    session = PromptSession(history=InMemoryHistory())

    try:
        delirium.generate_first_message()

        while True:
            try:
                user_input = session.prompt("\nToi: ")
            except KeyboardInterrupt:
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
            elif stripped in ("/collisions", "/collisions --purge"):
                delirium.cmd_collisions(purge="--purge" in stripped)
            elif stripped == "/status":
                delirium.cmd_status()
            elif stripped.startswith("/"):
                console.print(f"[error]Commande inconnue: {stripped}[/error]")
            else:
                delirium.process_message(user_input)

    except KeyboardInterrupt:
        pass
    finally:
        delirium.close()
        console.print("\n[info]Session terminée. À plus.[/info]")


if __name__ == "__main__":
    main()

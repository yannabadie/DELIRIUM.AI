"""Delirium AI — CLI prototype.

Usage: python -m src.main

Commands:
    /import chatgpt|claude|generic <path>  — Import conversations
    /collisions             — Run Cold Weaver collision scan
    /status                 — Show persona, memory, decay, gags, bubble status
    quit / exit / q         — Quit
"""

import asyncio
import logging
import sys
from datetime import datetime
from uuid import uuid4

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

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stderr)],
)
logger = logging.getLogger("delirium")


class Delirium:
    """Main orchestrator: LLM, memory, persona, S2, Cold Weaver, decay, gags, retrait."""

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
            logger.info("Restored persona state: H=%.2f, phase=%s",
                        saved_state.H, saved_state.phase)

        # Apply decay at session start (Bjork RS decay)
        decayed = self.decay.apply_decay()
        if decayed:
            logger.info("Decay applied to %d fragments", decayed)

        # Kill stale gags (6+ months without activation)
        self.gags.apply_decay()

        # Compute retrait state
        last_ts = self._get_last_interaction_timestamp()
        self.retrait_state = compute_retrait_state(last_ts)
        if self.retrait_state != "active":
            state = self.persona_engine.get_current_state()
            adjust_persona_for_retrait(state, self.retrait_state)
            self.persona_engine.set_state(state)
            logger.info("Retrait state: %s", self.retrait_state)

        self.session_id = str(uuid4())
        self._collision_delivered = False
        logger.info("Session %s started", self.session_id)

    def _get_last_interaction_timestamp(self) -> str | None:
        row = self.episodic.conn.execute(
            "SELECT MAX(timestamp) as ts FROM conversations WHERE source = 'delirium'"
        ).fetchone()
        return row["ts"] if row and row["ts"] else None

    def process_message(self, user_message: str) -> str:
        """Process a user message: S1 response + async S2 analysis."""
        state = self.persona_engine.get_current_state()

        # Reactivate related memories (Bjork re-learning effect)
        self.decay.reactivate_related(user_message, self.episodic)

        # Retrieve relevant memories (filtered by retrieval_weight)
        relevant = self.episodic.search(user_message, n_results=5)
        themes = self.semantic.get_active_themes()

        # Check for pending collision (max 1 per session — invariant 6)
        pending_collision = None
        if not self._collision_delivered:
            collision = self.episodic.get_pending_collision()
            if collision:
                pending_collision = collision
                self.episodic.mark_collision_delivered(collision["id"], self.session_id)
                self._collision_delivered = True
                self.episodic.log_execution(None, "collision_delivered", {
                    "collision_id": collision["id"],
                    "score": collision["collision_score"],
                })

        # Get vision summary and gag context
        vision_summary = self.world_vision.get_summary_for_s1()
        gag_context = self.gags.get_gag_context_for_s1()

        # Compose S1 prompt (full working memory)
        s1_prompt = self.working.compose_s1_prompt(
            state, relevant, themes, pending_collision,
            vision_summary=vision_summary,
            gag_context=gag_context,
        )

        # Get recent conversation for context
        recent = self.episodic.get_recent(self.session_id, limit=20)
        messages = recent + [{"role": "user", "content": user_message}]

        # S1 call (streaming)
        print("\n\033[36mDelirium:\033[0m ", end="", flush=True)
        response = self.llm.chat(system=s1_prompt, messages=messages, stream=True)

        # Embed and store
        emb = self.embedder.embed(user_message)
        fragment_id = self.episodic.store(
            user_message, response, self.session_id, state, embedding=emb
        )

        # Log S1 execution
        self.episodic.log_execution(fragment_id, "s1_response", {
            "user_message": user_message,
            "response_length": len(response),
            "H": state.H,
            "phase": state.phase,
            "collision_injected": pending_collision is not None,
        })

        # Fire S2 analysis
        asyncio.get_event_loop().run_until_complete(
            self.s2.analyze(fragment_id, user_message, response,
                            recent + [{"role": "user", "content": user_message},
                                       {"role": "assistant", "content": response}],
                            self.session_id)
        )

        return response

    def generate_first_message(self) -> str:
        """Generate Delirium's opening message."""
        state = self.persona_engine.get_current_state()

        # Build retrait context if returning after absence
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
            retrait_ctx = get_retrait_context(
                self.retrait_state, days, forgotten, pending
            )

        vision_summary = self.world_vision.get_summary_for_s1()
        gag_context = self.gags.get_gag_context_for_s1()

        s1_prompt = self.working.compose_s1_prompt(
            state, [], [],
            vision_summary=vision_summary,
            gag_context=gag_context,
            retrait_context=retrait_ctx,
        )

        instruction = (
            "[L'utilisateur revient après une absence.]"
            if self.retrait_state != "active"
            else "[L'utilisateur ouvre l'app pour la première fois. Génère ton premier message.]"
        )

        print("\n\033[36mDelirium:\033[0m ", end="", flush=True)
        response = self.llm.chat(
            system=s1_prompt,
            messages=[{"role": "user", "content": instruction}],
            stream=True,
        )

        fragment_id = self.episodic.store(
            "[premier_message]", response, self.session_id,
            state, embedding=self.embedder.embed(response)
        )
        self.episodic.log_execution(fragment_id, "first_message", {
            "response": response,
            "retrait_state": self.retrait_state,
        })
        return response

    # --- CLI Commands ---

    def cmd_import_chatgpt(self, path: str):
        """Import ChatGPT conversations from export file."""
        from src.import_.chatgpt import ChatGPTImporter
        self._run_import(ChatGPTImporter(), path, "chatgpt")

    def cmd_import_claude(self, path: str):
        """Import Claude.ai conversations from export file."""
        from src.import_.claude_ai import ClaudeImporter
        self._run_import(ClaudeImporter(), path, "claude")

    def cmd_import_generic(self, path: str):
        """Import conversations from generic JSON format."""
        from src.import_.generic import GenericImporter
        self._run_import(GenericImporter(), path, "generic")

    def _run_import(self, importer, path: str, source: str):
        """Shared import logic for all importers."""
        from src.import_.sycophancy import SycophancyDetector

        print(f"\033[2mImporting {source} from {path}...\033[0m")

        try:
            messages = importer.parse(path)
        except Exception as e:
            print(f"\033[31m  Erreur de parsing: {e}\033[0m")
            return

        print(f"\033[2m  {len(messages)} message pairs extracted\033[0m")
        if not messages:
            return

        detector = SycophancyDetector(llm=self.llm, use_llm=False)
        dummy_state = PersonaState()
        imported = 0

        for msg in messages:
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
            imported += 1

            if imported % 100 == 0:
                print(f"\033[2m  {imported}/{len(messages)} imported...\033[0m")

        self.episodic.log_execution(None, f"{source}_import", {
            "file": path,
            "messages_imported": imported,
        })
        print(f"\033[32m  Import terminé: {imported} messages\033[0m")

    def cmd_collisions(self, purge: bool = False):
        """Run a Cold Weaver collision scan."""
        from src.cold_weaver.engine import ColdWeaverEngine

        if purge:
            deleted = self.episodic.purge_collisions()
            print(f"\033[2m  Purgé {deleted} collisions\033[0m")

        engine = ColdWeaverEngine(self.episodic, self.semantic, self.llm)
        print("\033[2mCold Weaver scan en cours (ArXiv activé, filtre qualité LLM)...\033[0m")
        n = engine.scan(include_arxiv=True)
        print(f"\033[32m  {n} nouvelles collisions détectées\033[0m")

        total = self.episodic.get_collision_count()
        print(f"\033[2m  Total collisions en stock: {total}\033[0m")

        pending = self.episodic.get_pending_collision()
        if pending:
            print(f"\n\033[33m  Meilleure collision en attente (score {pending['collision_score']:.2f}):\033[0m")
            print(f"    A: {pending['a_input'][:80]}")
            print(f"    B: {pending['b_input'][:80]}")
            print(f"    Connexion: {pending['connection'][:120]}")

    def cmd_status(self):
        """Show full system status."""
        state = self.persona_engine.get_current_state()
        decay_stats = self.decay.get_stats()
        gags = self.gags.get_active_gags()
        bubble = h_bulle(self.episodic.conn)
        vision = self.world_vision.get_current()

        print("\n\033[1m═══ PERSONA ═══\033[0m")
        print(f"  H: {state.H:.2f}  |  Phase: {state.phase}  |  Fatigue: {state.fatigue:.2f}")
        print(f"  Empathie: {state.empathy:.2f}  |  Confrontation: {state.confrontation:.2f}")
        print(f"  Retrait: {self.retrait_state}")

        print(f"\n\033[1m═══ MÉMOIRE (Bjork {decay_stats['mode']}) ═══\033[0m")
        print(f"  Total: {decay_stats['total']}  |  Accessible: {decay_stats['accessible']}  "
              f"|  En déclin: {decay_stats['fading']}  |  Oubliés: {decay_stats['forgotten']}")
        for source in ("delirium", "chatgpt", "claude", "arxiv"):
            n = self.episodic.get_fragment_count(source)
            if n > 0:
                print(f"    {source}: {n}")
        print(f"  Sessions: {self.episodic.get_total_sessions()}")
        print(f"  Collisions: {self.episodic.get_collision_count()}")

        themes = self.semantic.get_active_themes()
        if themes:
            print(f"\n\033[1m═══ THÈMES ACTIFS ═══\033[0m")
            for t in themes[:8]:
                bar = "█" * int(t["weight"] * 10)
                print(f"  {bar} {t['label']} ({t['weight']:.1f})")

        loops = self.semantic.get_loops()
        if loops:
            print(f"\n\033[1m═══ BOUCLES ═══\033[0m")
            for l in loops[:5]:
                print(f"  ↻ {l['theme']} ({l['occurrences']}x)")

        if gags:
            print(f"\n\033[1m═══ RUNNING GAGS ({len(gags)}) ═══\033[0m")
            for g in gags[:5]:
                cb = f" ({g['user_callback_count']} callbacks)" if g["user_callback_count"] else ""
                print(f"  - {g['seed_content'][:50]} [{g['type']}] {g['occurrence_count']}x{cb}")

        print(f"\n\033[1m═══ BULLE (H_bulle) ═══\033[0m")
        print(f"  Score: {bubble['h_bulle']:.3f} ({bubble['bubble_status']})")
        print(f"  Narrowing: {bubble['narrowing']:.3f}  |  Certainty: {bubble['certainty_drift']:.3f}  "
              f"|  Outgroup: {bubble['outgroup_language']:.3f}")

        if vision:
            who = vision.get("who_they_are", {})
            print(f"\n\033[1m═══ VISION DU MONDE (v{vision.get('version', '?')}) ═══\033[0m")
            if who.get("summary"):
                print(f"  {who['summary'][:120]}")

    def close(self):
        self.episodic.close()


def main():
    if not MINIMAX_API_KEY:
        print("\033[31mErreur: MINIMAX_API_KEY non configurée.\033[0m")
        print("Copie .env.example en .env et renseigne ta clé API MiniMax.")
        sys.exit(1)

    print("\033[1m╔══════════════════════════════════════╗\033[0m")
    print("\033[1m║     DELIRIUM AI — Non-BlocNote       ║\033[0m")
    print("\033[1m║  \"Vos idées à la con sont            ║\033[0m")
    print("\033[1m║              intéressantes.\"          ║\033[0m")
    print("\033[1m╚══════════════════════════════════════╝\033[0m")
    print("\033[2m(Ctrl+C ou 'quit' pour quitter)\033[0m")
    print("\033[2mCommandes: /import chatgpt|claude|generic <path>, /collisions [--purge], /status\033[0m\n")

    delirium = Delirium()

    try:
        delirium.generate_first_message()

        while True:
            try:
                user_input = input("\n\033[33mToi:\033[0m ")
            except EOFError:
                break

            stripped = user_input.strip()

            if stripped.lower() in ("quit", "exit", "q"):
                break
            if not stripped:
                continue

            # CLI commands
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
                print(f"\033[31mCommande inconnue: {stripped}\033[0m")
                print("\033[2mCommandes: /import chatgpt|claude|generic <path>, /collisions [--purge], /status\033[0m")
            else:
                delirium.process_message(user_input)

    except KeyboardInterrupt:
        print("\n")
    finally:
        delirium.close()
        print("\033[2mSession terminée. À plus.\033[0m")


if __name__ == "__main__":
    main()

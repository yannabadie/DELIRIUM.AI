"""Delirium AI — CLI prototype.

Usage: python -m src.main

Commands:
    /import chatgpt <path>  — Import ChatGPT conversations
    /collisions             — Run Cold Weaver collision scan
    /status                 — Show persona and memory status
    quit / exit / q         — Quit
"""

import asyncio
import logging
import sys
from uuid import uuid4

from src.config import MINIMAX_API_KEY, SQLITE_DB_PATH
from src.llm_client import LLMClient, AsyncLLMClient
from src.memory.episodic import EpisodicMemory
from src.memory.semantic import SemanticMemory
from src.memory.working import WorkingMemory
from src.persona.engine import PersonaEngine
from src.s2.analyzer import S2Analyzer
from src.embeddings import get_embedder

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stderr)],
)
logger = logging.getLogger("delirium")


class Delirium:
    """Main orchestrator: ties together LLM, memory, persona, S2, and Cold Weaver."""

    def __init__(self):
        self.llm = LLMClient()
        self.async_llm = AsyncLLMClient()
        self.episodic = EpisodicMemory(SQLITE_DB_PATH)
        self.semantic = SemanticMemory(self.episodic.conn)
        self.working = WorkingMemory()
        self.persona_engine = PersonaEngine()
        self.s2 = S2Analyzer(self.async_llm, self.episodic, self.semantic, self.persona_engine)
        self.embedder = get_embedder()

        # Restore persona state from DB if available
        saved_state = self.episodic.load_latest_persona_state()
        if saved_state:
            self.persona_engine.set_state(saved_state)
            logger.info("Restored persona state: H=%.2f, phase=%s",
                        saved_state.H, saved_state.phase)

        self.session_id = str(uuid4())
        self._collision_delivered = False
        logger.info("Session %s started", self.session_id)

    def process_message(self, user_message: str) -> str:
        """Process a user message: S1 response + async S2 analysis."""
        state = self.persona_engine.get_current_state()

        # Retrieve relevant memories
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
                logger.info("Delivering collision %.2f", collision["collision_score"])

        # Compose S1 prompt
        s1_prompt = self.working.compose_s1_prompt(
            state, relevant, themes, pending_collision
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
        """Generate Delirium's opening message (invariant 5: neutral-light)."""
        state = self.persona_engine.get_current_state()
        s1_prompt = self.working.compose_s1_prompt(state, [], [])

        print("\n\033[36mDelirium:\033[0m ", end="", flush=True)
        response = self.llm.chat(
            system=s1_prompt,
            messages=[{"role": "user", "content": "[L'utilisateur ouvre l'app pour la première fois. Génère ton premier message.]"}],
            stream=True,
        )

        fragment_id = self.episodic.store(
            "[premier_message]", response, self.session_id,
            state, embedding=self.embedder.embed(response)
        )
        self.episodic.log_execution(fragment_id, "first_message", {"response": response})
        return response

    # --- CLI Commands ---

    def cmd_import_chatgpt(self, path: str):
        """Import ChatGPT conversations from export file."""
        from src.import_.chatgpt import ChatGPTImporter
        from src.import_.sycophancy import SycophancyDetector

        print(f"\033[2mImporting from {path}...\033[0m")

        importer = ChatGPTImporter()
        messages = importer.parse(path)
        print(f"\033[2m  {len(messages)} message pairs extracted\033[0m")

        detector = SycophancyDetector(llm=self.llm, use_llm=False)  # heuristic only for bulk
        dummy_state = PersonaState()
        imported = 0

        for msg in messages:
            syco_score = detector.score(msg.assistant_response, msg.user_input)
            emb = self.embedder.embed(msg.user_input)

            self.episodic.store(
                user_message=msg.user_input,
                response=msg.assistant_response,
                session_id=f"import_chatgpt_{msg.conversation_title[:30]}",
                persona_state=dummy_state,
                source="chatgpt",
                embedding=emb,
                sycophancy_score=syco_score,
            )
            imported += 1

            if imported % 100 == 0:
                print(f"\033[2m  {imported}/{len(messages)} imported...\033[0m")

        # Log
        self.episodic.log_execution(None, "chatgpt_import", {
            "file": path,
            "messages_imported": imported,
        })

        avg_syco = sum(
            d.score(m.assistant_response, m.user_input) for m, d in
            [(msg, detector) for msg in messages[:50]]
        ) / min(len(messages), 50) if messages else 0

        print(f"\033[32m  Import terminé: {imported} messages\033[0m")
        print(f"\033[2m  Sycophantie moyenne (heuristique, 50 premiers): {avg_syco:.2f}\033[0m")

    def cmd_collisions(self):
        """Run a Cold Weaver collision scan."""
        from src.cold_weaver.engine import ColdWeaverEngine

        engine = ColdWeaverEngine(self.episodic, self.semantic, self.llm)
        print("\033[2mCold Weaver scan en cours...\033[0m")
        n = engine.scan(include_arxiv=False)
        print(f"\033[32m  {n} nouvelles collisions détectées\033[0m")

        total = self.episodic.get_collision_count()
        print(f"\033[2m  Total collisions en stock: {total}\033[0m")

        # Show the best pending one
        pending = self.episodic.get_pending_collision()
        if pending:
            print(f"\n\033[33m  Meilleure collision en attente (score {pending['collision_score']:.2f}):\033[0m")
            print(f"    A: {pending['a_input'][:80]}")
            print(f"    B: {pending['b_input'][:80]}")
            print(f"    Connexion: {pending['connection'][:120]}")

    def cmd_status(self):
        """Show persona and memory status."""
        state = self.persona_engine.get_current_state()
        total_frags = self.episodic.get_fragment_count()
        delirium_frags = self.episodic.get_fragment_count("delirium")
        chatgpt_frags = self.episodic.get_fragment_count("chatgpt")
        arxiv_frags = self.episodic.get_fragment_count("arxiv")
        themes = self.semantic.get_active_themes()
        loops = self.semantic.get_loops()
        collisions = self.episodic.get_collision_count()
        sessions = self.episodic.get_total_sessions()

        print("\n\033[1m═══ ÉTAT DE DELIRIUM ═══\033[0m")
        print(f"  H: {state.H:.2f}  |  Phase: {state.phase}  |  Fatigue: {state.fatigue:.2f}")
        print(f"  Empathie: {state.empathy:.2f}  |  Confrontation: {state.confrontation:.2f}")
        print(f"  Défensivité détectée: {state.defensiveness_detected:.2f}")

        print(f"\n\033[1m═══ MÉMOIRE ═══\033[0m")
        print(f"  Fragments: {total_frags} total ({delirium_frags} delirium, {chatgpt_frags} chatgpt, {arxiv_frags} arxiv)")
        print(f"  Sessions: {sessions}")
        print(f"  Collisions: {collisions}")

        if themes:
            print(f"\n\033[1m═══ THÈMES ACTIFS ═══\033[0m")
            for t in themes[:8]:
                bar = "█" * int(t["weight"] * 10)
                print(f"  {bar} {t['label']} ({t['weight']:.1f})")

        if loops:
            print(f"\n\033[1m═══ BOUCLES DÉTECTÉES ═══\033[0m")
            for l in loops[:5]:
                print(f"  ↻ {l['theme']} ({l['occurrences']}x)")

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
    print("\033[2mCommandes: /import chatgpt <path>, /collisions, /status\033[0m\n")

    delirium = Delirium()

    try:
        # First message from Delirium
        delirium.generate_first_message()

        # Conversation loop
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
                path = stripped[len("/import chatgpt "):].strip()
                delirium.cmd_import_chatgpt(path)
                continue
            elif stripped == "/collisions":
                delirium.cmd_collisions()
                continue
            elif stripped == "/status":
                delirium.cmd_status()
                continue
            elif stripped.startswith("/"):
                print(f"\033[31mCommande inconnue: {stripped}\033[0m")
                print("\033[2mCommandes: /import chatgpt <path>, /collisions, /status\033[0m")
                continue

            delirium.process_message(user_input)

    except KeyboardInterrupt:
        print("\n")
    finally:
        delirium.close()
        print("\033[2mSession terminée. À plus.\033[0m")


if __name__ == "__main__":
    main()

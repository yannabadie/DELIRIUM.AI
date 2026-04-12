"""Delirium AI — CLI prototype.

Usage: python -m src.main
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

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stderr)],
)
logger = logging.getLogger("delirium")


class Delirium:
    """Main orchestrator: ties together LLM, memory, persona, and S2."""

    def __init__(self):
        self.llm = LLMClient()
        self.async_llm = AsyncLLMClient()
        self.episodic = EpisodicMemory(SQLITE_DB_PATH)
        self.semantic = SemanticMemory(self.episodic.conn)
        self.working = WorkingMemory()
        self.persona_engine = PersonaEngine()
        self.s2 = S2Analyzer(self.async_llm, self.episodic, self.semantic, self.persona_engine)

        # Restore persona state from DB if available
        saved_state = self.episodic.load_latest_persona_state()
        if saved_state:
            self.persona_engine.set_state(saved_state)
            logger.info("Restored persona state: H=%.2f, phase=%s",
                        saved_state.H, saved_state.phase)

        self.session_id = str(uuid4())
        logger.info("Session %s started", self.session_id)

    def process_message(self, user_message: str) -> str:
        """Process a user message: S1 response + async S2 analysis."""
        state = self.persona_engine.get_current_state()

        # Retrieve relevant memories
        relevant = self.episodic.search(user_message, n_results=5)
        themes = self.semantic.get_active_themes()

        # Compose S1 prompt
        s1_prompt = self.working.compose_s1_prompt(state, relevant, themes)

        # Get recent conversation for context
        recent = self.episodic.get_recent(self.session_id, limit=20)
        messages = recent + [{"role": "user", "content": user_message}]

        # S1 call (streaming)
        print("\n\033[36mDelirium:\033[0m ", end="", flush=True)
        response = self.llm.chat(system=s1_prompt, messages=messages, stream=True)

        # Store in episodic memory
        fragment_id = self.episodic.store(user_message, response, self.session_id, state)

        # Log S1 execution
        self.episodic.log_execution(fragment_id, "s1_response", {
            "user_message": user_message,
            "response_length": len(response),
            "H": state.H,
            "phase": state.phase,
        })

        # Fire S2 analysis asynchronously
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
            "[premier_message]", response, self.session_id, state
        )
        self.episodic.log_execution(fragment_id, "first_message", {"response": response})
        return response

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
    print("\033[2m(Ctrl+C ou 'quit' pour quitter)\033[0m\n")

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

            if user_input.strip().lower() in ("quit", "exit", "q"):
                break

            if not user_input.strip():
                continue

            delirium.process_message(user_input)

    except KeyboardInterrupt:
        print("\n")
    finally:
        delirium.close()
        print("\033[2mSession terminée. À plus.\033[0m")


if __name__ == "__main__":
    main()

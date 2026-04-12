"""Working Memory — Layer 1. Composes the S1 prompt with context.

See ARCHITECTURE_HARNESS.md section 3.6.
Assembles: base prompt + persona state + retrieved memories + themes.
"""

from src.config import get_s1_prompt
from src.persona.state import PersonaState


class WorkingMemory:
    """Composes the full S1 system prompt from all memory layers."""

    def compose_s1_prompt(self, persona_state: PersonaState,
                          relevant_memories: list[dict],
                          active_themes: list[dict]) -> str:
        base_prompt = get_s1_prompt()

        sections = [base_prompt]

        # Persona state injection
        sections.append(f"""
═══ TON ÉTAT ACTUEL ═══
Variable H : {persona_state.H:.2f}
Phase : {persona_state.phase}
Fatigue : {persona_state.fatigue:.2f}
Confrontation : {persona_state.confrontation:.2f}
Empathie : {persona_state.empathy:.2f}""")

        # Retrieved memories
        if relevant_memories:
            mem_lines = []
            for m in relevant_memories[:5]:
                mem_lines.append(f"- [{m.get('timestamp', '?')}] Utilisateur : {m['user_input'][:100]}")
            sections.append(
                "═══ SOUVENIRS PERTINENTS ═══\n" + "\n".join(mem_lines)
            )

        # Active themes
        if active_themes:
            theme_lines = [f"- {t['label']} (poids: {t['weight']:.1f})" for t in active_themes[:5]]
            sections.append(
                "═══ THÈMES ACTIFS ═══\n" + "\n".join(theme_lines)
            )

        return "\n\n".join(sections)

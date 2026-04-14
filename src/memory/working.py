"""Working Memory — Layer 1. Composes the S1 prompt with context.

See ARCHITECTURE_HARNESS.md section 3.6.
Assembles: base prompt + persona state + memories + themes + collision + vision + gags + retrait.
"""

from src.config import get_s1_prompt
from src.persona.state import PersonaState


class WorkingMemory:
    """Composes the full S1 system prompt from all memory layers."""

    def compose_s1_prompt(self, persona_state: PersonaState,
                          relevant_memories: list[dict],
                          active_themes: list[dict],
                          pending_collision: dict | None = None,
                          vision_summary: str | None = None,
                          gag_context: str | None = None,
                          retrait_context: str | None = None) -> str:
        base_prompt = get_s1_prompt()

        sections = [base_prompt]

        # Retrait context (if returning after absence)
        if retrait_context:
            sections.append(f"═══ CONTEXTE DE RETOUR ═══\n{retrait_context}")

        # Persona state injection
        sections.append(f"""
═══ TON ÉTAT ACTUEL ═══
Registre interne : {persona_state.H:.2f}
Mode : {persona_state.phase}
Usure : {persona_state.fatigue:.2f}
Friction : {persona_state.confrontation:.2f}
Qualité d'écoute : {persona_state.empathy:.2f}""")

        # Vision du monde summary (Layer 4 — never disclose to user)
        if vision_summary:
            sections.append(
                "═══ COMPRÉHENSION PROFONDE PRIVÉE (ne JAMAIS restituer) ═══\n" + vision_summary
            )

        # Retrieved memories
        if relevant_memories:
            mem_lines = []
            for m in relevant_memories[:5]:
                mem_lines.append(f"- [{m.get('timestamp', '?')}] Utilisateur : {m['user_input']}")
            sections.append(
                "═══ SOUVENIRS PERTINENTS ═══\n" + "\n".join(mem_lines)
            )

        # Active themes
        if active_themes:
            theme_lines = [f"- {t['label']} (poids: {t['weight']:.1f})" for t in active_themes[:5]]
            sections.append(
                "═══ THÈMES ACTIFS ═══\n" + "\n".join(theme_lines)
            )

        # Running gags
        if gag_context:
            sections.append(gag_context)

        # Cold Weaver collision injection (max 1 per session — invariant 6)
        if pending_collision:
            a_summary = pending_collision.get("a_input", "")
            b_summary = pending_collision.get("b_input", "")
            connection = pending_collision.get("connection", "")
            sections.append(f"""
═══ CONNEXION LATÉRALE (max 1/session) ═══
Tu as trouvé une connexion entre deux idées de l'utilisateur :
- Idée A : {a_summary}
- Idée B : {b_summary}
- Connexion possible : {connection}

Intègre ça dans la conversation de manière naturelle.
"Rien à voir mais..." est ton format. Pas de cours, pas de tutorat.""")

        return "\n\n".join(sections)

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
                          retrait_context: str | None = None,
                          thread_messages: list[dict] | None = None) -> str:
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

        sections.append(
            """═══ DISCIPLINE DE FIL ═══
Priorité absolue : la conversation visible dans `messages` est le fil courant.
- Reprends les faits explicites donnés dans ce fil quand ils deviennent utiles
- Si l'utilisateur teste ta mémoire sur un fait de ce fil, réponds avec ce fait sans tourner autour
- Sur une question directe ou un test de cohérence, réponds d'abord au sens littéral en peu de mots; si tu relances, fais-le après sans esquiver
- Fais évoluer le ton progressivement selon l'accumulation des tours, même si l'état interne bouge peu
- En début d'échange, une salutation simple appelle une réponse de première rencontre, pas une réponse générique
- Hors crise réelle convergente, reste en personnage quand l'utilisateur demande ce que tu es
- Dans les tours 4-5, garde un seul rappel concret du fil et evite les recapitulatifs ou explications de posture
- Si le dernier message utilisateur est bref, traite-le comme la suite du sujet deja ouvert sauf indice clair du contraire
- Quand le fil devient lourd ou conflictuel, coupe l'imagerie d'un cran et privilegie des phrases plus simples"""
        )

        thread_summary = self._build_visible_thread_summary(thread_messages)
        if thread_summary:
            sections.append(thread_summary)

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
        theme_entries = self._normalize_theme_entries(active_themes)
        if theme_entries:
            theme_lines = [f"- {entry['label']} (poids: {entry['weight']:.1f})" for entry in theme_entries]
            sections.append(
                "═══ THÈMES ACTIFS ═══\n" + "\n".join(theme_lines)
            )

        bubble_section = self._build_bubble_break_section(
            persona_state,
            active_themes,
            thread_messages,
        )
        if bubble_section:
            sections.append(bubble_section)

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

    def _build_bubble_break_section(
        self,
        persona_state: PersonaState,
        active_themes: list[dict],
        thread_messages: list[dict] | None,
    ) -> str | None:
        if not getattr(persona_state, "bubble_break_enabled", False):
            return None

        risk = getattr(persona_state, "bubble_risk_status", "low_risk")
        intensity = getattr(persona_state, "bubble_break_intensity", "off")
        ignore_streak = getattr(persona_state, "bubble_ignore_streak", 0)
        anchor = self._build_bubble_anchor(
            self._normalize_theme_entries(active_themes),
            thread_messages,
        )

        if intensity == "strong":
            move = "Crochet net"
            style = (
                "Coupe franchement la boucle avec une scene adjacente concrete, "
                "presque incongrue, puis reviens au fil sans expliquer ta manoeuvre."
            )
        else:
            move = "Crochet leger"
            style = (
                "Fais juste un pas de cote: une image ou un detail adjacent qui desserre "
                "la boucle sans casser la conversation."
            )

        return (
            "═══ INJECTION LATÉRALE ANTI-BULLE ═══\n"
            f"Risque détecté : {risk}\n"
            f"Ignores consecutifs : {ignore_streak}/3\n"
            f"{move}.\n"
            "Forme attendue : commence litteralement par \"Rien à voir mais...\"\n"
            "Regles : max 1/session, aucune mention de bulle, pas de meta, pas de lecon.\n"
            f"Angle adjacent suggere : {anchor}\n"
            f"{style}"
        )

    def _build_bubble_anchor(
        self,
        active_themes: list[dict],
        thread_messages: list[dict] | None,
    ) -> str:
        if active_themes:
            return (
                f"prends le theme '{active_themes[0]['label']}' par le cote: "
                "animal, cuisine, sport, cinema ou histoire des sciences"
            )

        if thread_messages:
            user_turns = [
                self._shorten(item.get("content", ""), limit=90)
                for item in thread_messages
                if item.get("role") == "user" and item.get("content", "").strip()
            ]
            if user_turns:
                return (
                    f"pars du motif recent '{user_turns[-1]}' et ouvre un biais lateral "
                    "concret venu d'ailleurs"
                )

        return "prends un detail concret venu d'ailleurs et fais-lui couper la trajectoire"

    def _normalize_theme_entries(self, active_themes: list[dict] | None) -> list[dict]:
        entries = []
        for theme in active_themes or []:
            if not isinstance(theme, dict):
                continue
            label = str(theme.get("label", "")).strip()
            if not label:
                continue
            weight = theme.get("weight", 0.0)
            try:
                weight = float(weight)
            except (TypeError, ValueError):
                weight = 0.0
            entries.append({"label": label, "weight": weight})
        return entries[:5]

    def _build_visible_thread_summary(self, thread_messages: list[dict] | None) -> str | None:
        if not thread_messages:
            return None

        user_turns = [
            self._shorten(item.get("content", ""))
            for item in thread_messages
            if item.get("role") == "user" and item.get("content", "").strip()
        ]
        assistant_turns = [
            self._shorten(item.get("content", ""))
            for item in thread_messages
            if item.get("role") == "assistant" and item.get("content", "").strip()
        ]
        if not user_turns:
            return None

        recent_user_turns = self._dedupe_preserve_order(user_turns[-3:])
        lines = [f"Tour utilisateur courant : {len(user_turns)}"]

        if recent_user_turns:
            lines.append("Derniers apports explicites de l'utilisateur :")
            lines.extend(f"- {turn}" for turn in recent_user_turns)

        last_assistant_angle = self._extract_last_assistant_angle(assistant_turns)
        if last_assistant_angle:
            lines.append("Dernier angle ouvert par Delirium :")
            lines.append(f"- {last_assistant_angle}")

        if self._looks_brief(user_turns[-1]):
            lines.append(
                "Le dernier message utilisateur est bref : ne repars pas de zero, "
                "continue sur le sujet et la question deja ouverts."
            )

        return "═══ FIL VISIBLE EN COURS (ne pas reciter tel quel) ═══\n" + "\n".join(lines)

    def _extract_last_assistant_angle(self, assistant_turns: list[str]) -> str | None:
        if not assistant_turns:
            return None

        last = assistant_turns[-1]
        if "?" in last:
            question = last.rsplit("?", 1)[0]
            anchor = question.split(".")[-1].strip()
            return self._shorten(anchor + "?")
        return last

    def _dedupe_preserve_order(self, items: list[str]) -> list[str]:
        seen = set()
        kept = []
        for item in items:
            if item in seen:
                continue
            kept.append(item)
            seen.add(item)
        return kept

    def _looks_brief(self, text: str) -> bool:
        return len(text.split()) <= 6 and "?" not in text

    def _shorten(self, text: str, limit: int = 140) -> str:
        compact = " ".join(text.split())
        if len(compact) <= limit:
            return compact
        return compact[: limit - 3].rstrip() + "..."

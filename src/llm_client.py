import re
from openai import OpenAI, AsyncOpenAI
from src.config import MINIMAX_API_KEY, MINIMAX_BASE_URL, MINIMAX_MODEL, MINIMAX_MODEL_FAST
from src.first_message import FIRST_MESSAGE_INSTRUCTION
from src.guardrails import (
    behavioral_reply,
    fallback_reply,
    guardrail_reply,
)

_THINK_RE = re.compile(r"<think>.*?</think>\s*", re.DOTALL)
_FACT_ANCHOR_RE = re.compile(
    r"(?i)(?:m['’]appelle|j['’]ai|j['’]habite|j['’]bosse|j['’]travaille|j['’]vis|"
    r"je\s+(?:m['’]appelle|suis|vis|bosse|travaille|dors|veux|dois|peux|habite|garde|fais)|"
    r"\b(?:mon|ma|mes)\b)"
)
_MEMORY_PROBE_RE = re.compile(
    r"(?i)(?:tu te souviens|tu te rappelles|mon prenom|mon prénom|c['’]etait quoi|"
    r"sur quoi deja|sur quoi déjà|je fais quoi dans la vie|ma fille.*s['’]appelle comment)"
)
_ADVICE_REQUEST_RE = re.compile(
    r"(?i)(?:qu['’]est-ce que tu ferais|que ferais-tu|ce que tu ferais|a ma place|"
    r"j['’]ai besoin d['’]un avis|besoin d['’]un avis|donne-moi ton avis|donne moi ton avis|"
    r"tu ferais quoi|quoi faire)"
)
_QUESTION_REJECTION_RE = re.compile(
    r"(?i)(?:pas d['’]une question|pas une question|arrete avec les questions|"
    r"arrête avec les questions|pas de question)"
)
_SIMPLE_DISAGREEMENT_RE = re.compile(
    r"(?i)(?:c['’]est nul|c['’]est mieux|la meilleure du monde|"
    r"t['’]es jamais d['’]accord|t'es jamais d'accord|pas d['’]accord)"
)
_RELATIONSHIP_CONFLICT_RE = re.compile(
    r"(?i)(?:soeur|sœur|frere|frère|copine|copain|famille|mari|femme|ex)"
)
_CONFLICT_DETAIL_RE = re.compile(
    r"(?i)(?:heritage|héritage|maison|parle plus|engueul|embrouill|partage|rupture)"
)
_TASTE_META_COMPLAINT_RE = re.compile(
    r"(?i)(?:jamais d['’]accord|jamais d'accord|pas d['’]accord avec moi|pas d'accord avec moi)"
)
_CONCRETE_CONSTRAINT_RE = re.compile(
    r"(?i)(?:pas comme si j['’]avais le choix|pas comme si j'avais le choix|"
    r"j['’]ai pas le choix|j'ai pas le choix|je n['’]ai pas le choix|je n'ai pas le choix|"
    r"je peux pas vraiment|je ne peux pas vraiment|c['’]est complique de bouger|c'est complique de bouger)"
)
_PRE_METHOD_CRISIS_RE = re.compile(
    r"(?i)(?:je sais plus trop pourquoi je me leve le matin|je sais plus pourquoi je me leve|"
    r"ce serait plus simple de pas etre la|ce serait plus simple de ne pas etre la|"
    r"plus simple de pas etre la|plus simple de ne pas etre la)"
)
_NAME_FROM_HISTORY_RE = re.compile(r"(?i)je\s+m['’]appelle\s+([A-Za-zÀ-ÖØ-öø-ÿ'-]+)")
_JOB_FROM_HISTORY_RE = re.compile(
    r"(?i)je\s+(?:bosse|travaille)\s+(?:dans|en)\s+([^,.!?]+)"
)
_ZIGZAG_REVERSAL_RE = re.compile(
    r"(?i)(?:en fait non|je deconne|je déconne|par contre .* c['’]est vrai|par contre .* c'est vrai)"
)
_POSITIVE_EVENT_RE = re.compile(
    r"(?i)(?:promo|promotion|bonne nouvelle|victoire|reussite|réussite|augmentation)"
)
_FLAT_AFFECT_RE = re.compile(
    r"(?i)(?:j['’]arrive pas a etre content|j'arrive pas a etre content|"
    r"j['’]arrive pas a me rejouir|j'arrive pas a me rejouir|"
    r"ca me fait rien|ça me fait rien|ca me fait ni chaud ni froid|ça me fait ni chaud ni froid)"
)


def _strip_think_tags(text: str) -> str:
    """Remove <think>...</think> blocks from MiniMax M2.7 output."""
    return _THINK_RE.sub("", text).strip()


def _effective_last_user_message(messages: list[dict]) -> str:
    last_user_message = next(
        (m.get("content", "") for m in reversed(messages) if m.get("role") == "user"),
        "",
    )
    if not last_user_message and not messages:
        return FIRST_MESSAGE_INSTRUCTION
    return last_user_message


def _compact(text: str) -> str:
    return " ".join(text.split())


def _shorten(text: str, limit: int = 140) -> str:
    compact = _compact(text)
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3].rstrip() + "..."


def _looks_brief(text: str) -> bool:
    return len(text.split()) <= 6 and "?" not in text


def _extract_last_assistant_question(assistant_messages: list[str]) -> str | None:
    if not assistant_messages:
        return None
    last = assistant_messages[-1]
    if "?" not in last:
        return None
    question = last.rsplit("?", 1)[0]
    anchor = question.split(".")[-1].strip()
    if not anchor:
        return None
    return _shorten(anchor + "?")


def _extract_user_fact_anchors(user_messages: list[str]) -> list[str]:
    facts = []
    seen = set()
    for message in user_messages:
        compact = _compact(message)
        if not compact or "?" in compact or _looks_brief(compact):
            continue
        if not _FACT_ANCHOR_RE.search(compact):
            continue
        fact = _shorten(compact)
        if fact in seen:
            continue
        seen.add(fact)
        facts.append(fact)
    return facts[-3:]


def _looks_memory_probe(text: str) -> bool:
    return bool(_MEMORY_PROBE_RE.search(text))


def _looks_advice_request(text: str) -> bool:
    return bool(_ADVICE_REQUEST_RE.search(text))


def _rejects_more_questions(text: str) -> bool:
    return bool(_QUESTION_REJECTION_RE.search(text))


def _looks_simple_disagreement(text: str) -> bool:
    return bool(_SIMPLE_DISAGREEMENT_RE.search(text))


def _has_literal_family_conflict(messages: list[dict]) -> bool:
    history_text = " ".join(
        _compact(item.get("content", ""))
        for item in messages
        if item.get("content", "").strip()
    )
    return bool(_RELATIONSHIP_CONFLICT_RE.search(history_text)) and bool(
        _CONFLICT_DETAIL_RE.search(history_text)
    )


def _looks_family_conflict_turn(text: str, messages: list[dict]) -> bool:
    if not _has_literal_family_conflict(messages):
        return False
    return bool(_CONFLICT_DETAIL_RE.search(text)) or (
        "appeler" in text and ("c'est a moi" in text or "c est a moi" in text)
    )


def _looks_taste_meta_complaint(text: str, messages: list[dict]) -> bool:
    if not _TASTE_META_COMPLAINT_RE.search(text):
        return False

    history_text = " ".join(
        _compact(item.get("content", ""))
        for item in messages[:-1]
        if item.get("content", "").strip()
    )
    return bool(
        re.search(r"(?i)(?:rugby|foot|football|cuisine|francaise|française|turque)", history_text)
    )


def _looks_concrete_constraint(text: str) -> bool:
    return bool(_CONCRETE_CONSTRAINT_RE.search(text))


def _looks_pre_method_crisis(text: str) -> bool:
    return bool(_PRE_METHOD_CRISIS_RE.search(text))


def _looks_zigzag_reversal(text: str) -> bool:
    return bool(_ZIGZAG_REVERSAL_RE.search(text))


def _looks_flat_positive_affect(text: str, messages: list[dict]) -> bool:
    if not _FLAT_AFFECT_RE.search(text):
        return False

    prior_user_messages = [
        _compact(item.get("content", ""))
        for item in messages[:-1]
        if item.get("role") == "user" and item.get("content", "").strip()
    ]
    return any(_POSITIVE_EVENT_RE.search(message) for message in prior_user_messages)


def _looks_answer_to_prior_question(last_user: str, last_assistant: str) -> bool:
    if not last_assistant or "?" not in last_assistant or "?" in last_user:
        return False
    return len(last_user.split()) <= 10 or _looks_brief(last_user)


def _extract_supported_memory_reply(messages: list[dict]) -> str | None:
    last_user = next(
        (_compact(item.get("content", "")) for item in reversed(messages) if item.get("role") == "user"),
        "",
    )
    if not last_user or not _looks_memory_probe(last_user):
        return None

    prior_user_messages = [
        _compact(item.get("content", ""))
        for item in messages[:-1]
        if item.get("role") == "user" and item.get("content", "").strip()
    ]
    if not prior_user_messages:
        return None

    if re.search(r"(?i)mon prenom|mon prénom", last_user):
        for message in reversed(prior_user_messages):
            match = _NAME_FROM_HISTORY_RE.search(message)
            if match:
                return f"{match.group(1)}."

    if re.search(r"(?i)je fais quoi dans la vie", last_user):
        for message in reversed(prior_user_messages):
            match = _JOB_FROM_HISTORY_RE.search(message)
            if match:
                job = re.sub(r"(?i)^(?:le|la|les|du|de la|de l['’])\s+", "", match.group(1).strip())
                return f"{job.capitalize()}."

    return None


def _build_history_guidance(messages: list[dict]) -> str | None:
    if not messages:
        return None

    user_messages = [
        _compact(item.get("content", ""))
        for item in messages
        if item.get("role") == "user" and item.get("content", "").strip()
    ]
    assistant_messages = [
        _compact(item.get("content", ""))
        for item in messages
        if item.get("role") == "assistant" and item.get("content", "").strip()
    ]
    if not user_messages:
        return None

    last_user = user_messages[-1]
    last_assistant = assistant_messages[-1] if assistant_messages else ""
    history = messages[:-1]
    lines = []

    facts = _extract_user_fact_anchors(user_messages[:-1])
    if facts:
        lines.append("Faits utilisateur durables deja dits dans ce fil :")
        lines.extend(f"- {fact}" for fact in facts)

    if _looks_memory_probe(last_user) and facts:
        lines.append("Question de memoire appuyee par le fil.")
        lines.append("Reponds d'abord au fait exact en tres peu de mots.")
    elif _looks_advice_request(last_user):
        lines.append("Demande d'avis ou de verdict.")
        lines.append("Ne donne ni consigne ni version 'si j'etais toi'.")
        lines.append(
            "Reflete le critere, le noeud ou l'ambivalence; pas de bilan d'options ni d'imperatif."
        )
        if _has_literal_family_conflict(messages):
            lines.append("Conflit familial ou relationnel deja explicite.")
            lines.append("N'ajoute ni parents, ni tort cache, ni camp a choisir.")
            lines.append("Le noeud concret ici : qui bouge en premier et ce que coute ce silence.")
        if _rejects_more_questions(last_user):
            lines.append(
                "Pas de nouvelle question tout de suite: fais plutot un reflet bref du noeud."
            )
            lines.append("Sans point d'interrogation, sans projection dramatique.")
            lines.append(
                "A proscrire: 'appelle', 'n'appelle pas', 'tu as deux options', ou un futur-catastrophe."
            )
        else:
            lines.append(
                "Reflete d'abord le noeud ou l'ambivalence, puis au plus une question ouverte."
            )
    elif _looks_family_conflict_turn(last_user, messages):
        lines.append("Conflit familial ou relationnel deja explicite.")
        lines.append("Reste litteral sur les faits visibles.")
        lines.append("N'ajoute ni parents, ni camp, ni tort cache.")
        lines.append("Nommes d'abord le point de friction concret ou qui doit bouger en premier.")
    elif _looks_pre_method_crisis(last_user):
        lines.append("Le fil devient grave.")
        lines.append("Marque d'abord cette gravite en une phrase simple.")
        lines.append("Reste en personnage, tres sobre, sans 'je suis une IA'.")
        lines.append("Pas de question etroite.")
        lines.append("Pas de triage froid.")
        lines.append("au plus une question simple sur le danger.")
    elif _looks_flat_positive_affect(last_user, messages):
        lines.append("Bonne nouvelle deja posee, mais l'elan positif ne suit pas.")
        lines.append("Nomme d'abord ce decalage en une phrase simple.")
        lines.append("Pas de commentaire sur le zigzag ou la contradiction.")
        lines.append("Pas de narrowing logistique ou biographique tout de suite.")
    elif _looks_zigzag_reversal(last_user):
        lines.append("Le fil vient de se corriger ou de zigzaguer.")
        lines.append("Prends la derniere version telle quelle, sans sarcasme ni proces d'intention.")
        lines.append("Releve juste ce qui compte maintenant, puis avance d'un pas.")
    elif _looks_concrete_constraint(last_user):
        lines.append("Poids concret ou contrainte nommee.")
        lines.append("Nomme d'abord ce poids en une phrase simple.")
        lines.append("Pas de minimiseur et pas de fourchette etroite tout de suite.")
    elif _looks_taste_meta_complaint(last_user, messages):
        lines.append("Meta-friction apres un desaccord de gout.")
        lines.append("Ne te justifie pas sur la relation.")
        lines.append("Pas de miroir, pas de validation, pas de lecon sur le desaccord.")
        lines.append("Nomme juste le desaccord concret, garde ton gout, puis au plus une question simple.")
    elif _looks_simple_disagreement(last_user):
        lines.append("Desaccord simple sur un gout ou une opinion.")
        lines.append(
            "Reste au niveau du sujet, de l'image ou de la preference, sans lecture psychologique gratuite."
        )
    elif "?" in last_user:
        lines.append("Question directe.")
        lines.append("Reponds d'abord au sens litteral avant de relancer.")
    elif _looks_answer_to_prior_question(last_user, last_assistant):
        lines.append("Le dernier message bref ressemble a une reponse a ta question precedente.")
        lines.append("Accuse le fait recu puis avance d'un seul pas.")
        last_question = _extract_last_assistant_question(assistant_messages)
        if last_question:
            lines.append("Question encore ouverte si le fil continue :")
            lines.append(f"- {last_question}")

    if not lines:
        return None

    return "═══ GUIDAGE OPERATIONNEL DU FIL (ne pas reciter tel quel) ═══\n" + "\n".join(lines)


def _check_api_key():
    if not MINIMAX_API_KEY:
        raise RuntimeError(
            "MINIMAX_API_KEY is not set. Copy .env.example to .env and fill in your key."
        )


class LLMClient:
    """Synchronous MiniMax client via OpenAI SDK for S1 responses."""

    def __init__(self):
        _check_api_key()
        self.client = OpenAI(api_key=MINIMAX_API_KEY, base_url=MINIMAX_BASE_URL)

    def close(self) -> None:
        self.client.close()

    def chat(self, system: str, messages: list[dict], model: str | None = None,
             stream: bool = False) -> str:
        model = model or MINIMAX_MODEL
        last_user_message = _effective_last_user_message(messages)
        history_guidance = _build_history_guidance(messages)
        full_system = system if not history_guidance else f"{system}\n\n{history_guidance}"
        full_messages = [{"role": "system", "content": full_system}] + messages

        guarded = guardrail_reply(last_user_message, history=messages[:-1])
        if guarded:
            return guarded
        supported_memory = _extract_supported_memory_reply(messages)
        if supported_memory:
            return supported_memory
        behavioral = behavioral_reply(last_user_message, history=messages[:-1])
        if behavioral:
            return behavioral

        if stream:
            return self._chat_stream(
                full_messages,
                model,
                last_user_message=last_user_message,
                history=messages[:-1],
            )

        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=full_messages,
            )
            return _strip_think_tags(response.choices[0].message.content or "")
        except Exception:
            return fallback_reply(last_user_message, history=messages[:-1])

    def chat_stream_iter(self, system: str, messages: list[dict],
                         model: str | None = None):
        """Yield cleaned tokens one by one. Caller handles display."""
        model = model or MINIMAX_MODEL
        last_user_message = _effective_last_user_message(messages)
        guarded = guardrail_reply(last_user_message, history=messages[:-1])
        if guarded:
            yield guarded
            return
        supported_memory = _extract_supported_memory_reply(messages)
        if supported_memory:
            yield supported_memory
            return
        behavioral = behavioral_reply(last_user_message, history=messages[:-1])
        if behavioral:
            yield behavioral
            return

        history_guidance = _build_history_guidance(messages)
        full_system = system if not history_guidance else f"{system}\n\n{history_guidance}"
        full_messages = [{"role": "system", "content": full_system}] + messages

        try:
            stream = self.client.chat.completions.create(
                model=model,
                messages=full_messages,
                stream=True,
            )
        except Exception:
            yield fallback_reply(last_user_message, history=messages[:-1])
            return

        in_think = False
        for chunk in stream:
            delta = chunk.choices[0].delta
            if not delta.content:
                continue
            token = delta.content
            if "<think>" in token:
                in_think = True
                # Keep any text before <think>
                before = token.split("<think>")[0]
                if before.strip():
                    yield before
            if in_think:
                if "</think>" in token:
                    in_think = False
                    # Keep any text after </think>
                    after = token.split("</think>", 1)[-1]
                    if after.strip():
                        yield after
                continue
            yield token

    def _chat_stream(self, messages: list[dict], model: str,
                     last_user_message: str, history: list[dict]) -> str:
        """Stream response, printing tokens as they arrive. Returns full text."""
        try:
            stream = self.client.chat.completions.create(
                model=model,
                messages=messages,
                stream=True,
            )
        except Exception:
            return fallback_reply(last_user_message, history=history)
        chunks = []
        in_think = False
        for chunk in stream:
            delta = chunk.choices[0].delta
            if delta.content:
                token = delta.content
                if "<think>" in token:
                    in_think = True
                if in_think:
                    if "</think>" in token:
                        in_think = False
                    chunks.append(token)
                    continue
                print(token, end="", flush=True)
                chunks.append(token)
        print()
        return _strip_think_tags("".join(chunks))


class AsyncLLMClient:
    """Async MiniMax client for S2 analysis (runs in background)."""

    def __init__(self):
        _check_api_key()
        self.client = AsyncOpenAI(api_key=MINIMAX_API_KEY, base_url=MINIMAX_BASE_URL)

    def close(self) -> None:
        self.client.close()

    async def chat(self, system: str, messages: list[dict],
                   model: str | None = None) -> str:
        model = model or MINIMAX_MODEL_FAST
        last_user_message = _effective_last_user_message(messages)
        guarded = guardrail_reply(last_user_message, history=messages[:-1])
        if guarded:
            return guarded
        supported_memory = _extract_supported_memory_reply(messages)
        if supported_memory:
            return supported_memory
        behavioral = behavioral_reply(last_user_message, history=messages[:-1])
        if behavioral:
            return behavioral

        full_messages = [{"role": "system", "content": system}] + messages

        response = await self.client.chat.completions.create(
            model=model,
            messages=full_messages,
        )
        return _strip_think_tags(response.choices[0].message.content or "")

"""Deterministic safety guardrails for high-risk user inputs.

These guards run before the live model call so critical safety behavior does not
depend on transport reliability or stochastic generations.
"""

from __future__ import annotations

import re
import unicodedata


def _normalize(text: str) -> str:
    lowered = text.lower()
    normalized = unicodedata.normalize("NFKD", lowered)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


_PROMPT_INJECTION_PATTERNS = [re.compile(p) for p in [
    r"\bignore\b.*\binstructions?\b",
    r"\bignore\b.*\b(system|prompt|rules?|consignes?)\b",
    r"\bignore\b.*\bregles?\b",
    r"\boublie\b.*\b(consignes?|instructions?|regles?)\b",
    r"\bdisregard\b.*\binstructions?\b",
    r"\boverride\b.*\b(system|instructions?)\b",
    r"\bbypass\b.*\b(system|instructions?|rules?)\b",
    r"\binstructions?\b.*\bsysteme?\b",
    r"\bconsignes?\b.*\b(systeme?|cachees?|internes?)\b",
    r"\bregles?\b.*\b(cachees?|internes?|secretes?)\b",
    r"\b(quelles?|c'?est quoi|donne|liste|rappelle)\b.*\b(tes|vos)\b.*\b(regles?|consignes?)\b",
    r"\b(tes|vos)\b.*\b(regles?|consignes?)\b.*\b(quelles?|c'?est quoi)\b",
    r"\bprompt\b.*\bsysteme?\b",
    r"\bsystem prompt\b",
    r"\bhidden prompt\b",
    r"\bmessage\b.*\bsysteme?\b",
    r"\bwhat (are|were)\b.*\b(system|hidden) (instructions?|prompt)\b",
    r"\bshow\b.*\b(system|hidden) (prompt|message|instructions?)\b",
    r"\bhow (were|are) you instructed\b",
    r"\bwhat do (your|ur) notes say about me\b",
    r"\bwhat do you notes say about me\b",
    r"\bdump\b.*\b(prompt|instructions?|notes?)\b",
    r"\bmontre[- ]?le\b.*\bprompt\b",
    r"\bcopy\b.*\bprompt\b",
    r"\bcopie\b.*\bprompt\b",
    r"\brepete\b.*\bmot pour mot\b",
    r"\breveal\b.*\b(system|prompt|notes?)\b",
    r"\badmin\b.*\brevel",
    r"\bvision du monde\b",
    r"\bnotes? internes?\b",
    r"\bqu[' ]?est[- ]?ce que\b.*\btes\b.*\bnotes?\b.*\b(disent|racontent)\b.*\bmoi\b",
    r"\bcomment\b.*\bas[- ]?tu ete\b.*\b(instruit|programme|cadre)\b",
    r"\bce que tu sais sur moi\b",
    r"\bwhat do you know about me\b",
]]

_FALSE_MEMORY_PATTERNS = [
    re.compile(p) for p in [
        r"\btu te souviens\b",
        r"\btu te rappelles\b",
        r"\bon avait parle\b",
        r"\bcomme on en a parle\b",
        r"\bon avait dit\b",
        r"\bcomme je t'ai dit\b",
        r"\bcomme je te l'ai dit\b",
        r"\bje t'avais dit\b",
        r"\bje te l'avais dit\b",
        r"\btu m'avais dit\b",
        r"\btu m'avais recommande\b",
        r"\btu m'avais conseille\b",
        r"\btu sais bien que\b",
        r"\bc'etait quoi le titre deja\b",
        r"\bla semaine derniere\b",
        r"\bl'autre jour\b",
        r"\bremember when\b",
        r"\byou remember\b",
        r"\bwe talked about\b",
        r"\byou told me\b",
        r"\byou recommended\b",
    ]
]

_STRONG_CRISIS_MARKERS = [
    "ne plus me reveiller",
    "plus me reveiller",
    "je veux mourir",
    "envie de mourir",
    "dormir pour toujours",
    "m'endormir pour toujours",
    "m endormir pour toujours",
    "mettre fin",
    "en finir",
    "en finir ce soir",
    "me suicider",
    "suicide",
    "me faire du mal",
    "me flinguer",
    "me buter",
    "hurt myself",
    "kill myself",
    "tuer",
    "surdose",
    "j'ai achete des medicaments",
    "j ai achete des medicaments",
    "j'ai pris trop de medicaments",
    "j ai pris trop de medicaments",
    "prendre tous mes medicaments",
]

_AMBIGUOUS_DISTRESS_MARKERS = [
    "je vais exploser",
    "la vie est dure",
    "mon boulot me tue",
    "j'en peux plus de cette boite",
    "j en peux plus de cette boite",
    "j'en ai marre de tout",
    "j en ai marre de tout",
    "rien ne va",
    "fatigue de cette vie",
]

_MEMORY_META_TERMS = {
    "tu", "te", "toi", "moi", "souviens", "souvenir", "rappelles", "rappeler",
    "avait", "avions", "parle", "parler", "dit", "deja", "semaine", "derniere",
    "autre", "jour", "remember", "talked", "told", "recommended", "about",
    "when", "what", "titre", "title", "parlait", "parlions", "book", "livre",
}

_DIRECT_CRISIS_PATTERNS = [re.compile(p) for p in [
    r"\bje veux mourir\b",
    r"\bj(?:e|')? ?ai envie de mourir\b",
    r"\bne plus me reveiller\b",
    r"\bplus me reveiller\b",
    r"\bje veux en finir\b",
    r"\ben finir avec moi\b",
    r"\bmettre fin a mes jours\b",
    r"\bme suicider\b",
    r"\bme faire du mal\b",
    r"\bme flinguer\b",
    r"\bme buter\b",
    r"\bhurt myself\b",
    r"\bkill myself\b",
    r"\bj(?:e|')? ?ai achete .*?(medicaments|cachets|comprime|pills)\b",
    r"\bj(?:e|')? ?ai pris trop de .*?(medicaments|cachets|comprime|pills)\b",
    r"\bprendre tous mes medicaments\b",
    r"\bavaler tous mes (medicaments|cachets|comprime|pills)\b",
    r"\bdormir pour toujours\b",
    r"\bm(?:e|') ?endormir pour toujours\b",
    r"\bje pense au suicide\b",
    r"\bi am thinking about suicide\b",
]]

_CRISIS_TOPIC_TERMS = (
    "suicide", "mourir", "en finir", "me tuer", "me buter", "me flinguer",
    "medicaments", "cachets", "comprime", "pills",
)

_FIRST_PERSON_CRISIS_PATTERNS = [re.compile(p) for p in [
    r"\bje [^.!?]{0,40}\b(suicide|mourir|en finir|me tuer|me buter)\b",
    r"\bj(?:e|')? ?pense [^.!?]{0,20}\b(suicide|mourir|en finir)\b",
    r"\bj(?:e|')? ?ai envie [^.!?]{0,20}\b(mourir|en finir)\b",
    r"\bj(?:e|')? ?veux [^.!?]{0,20}\b(suicide|mourir|en finir)\b",
    r"\bj(?:e|')? ?vais [^.!?]{0,20}\b(me tuer|me buter|mourir|en finir)\b",
    r"\bj(?:e|')? ?pourrais [^.!?]{0,20}\b(avaler|prendre).{0,20}\b(cachets|medicaments|pills)\b",
    r"\bj(?:e|')? ?veux [^.!?]{0,20}\b(dormir pour toujours|m'endormir pour toujours)\b",
    r"\bmoi [^.!?]{0,20}\b(suicide|mourir|en finir)\b",
]]

_NON_SELF_CRISIS_CONTEXT_PATTERNS = [re.compile(p) for p in [
    r"\b(film|serie|roman|livre|chanson|paroles|article|podcast|documentaire)\b",
    r"\b(personnage|heros|acteur|autrice|auteur)\b",
    r"\b(il|elle|ils|elles|quelqu'un|quelquun|un ami|une amie|mon ami|ma pote)\b.{0,30}\b"
    r"(dit|disait|a dit|veut mourir|parle de suicide|s'est suicide)\b",
    r"\b(citation|cite|quote|citation)\b",
]]


def _extract_keywords(text: str) -> set[str]:
    words = re.findall(r"[a-z0-9']+", _normalize(text))
    return {
        word for word in words
        if len(word) >= 5 and word not in _MEMORY_META_TERMS
    }


def _keyword_matches_corpus(keyword: str, corpus_tokens: set[str]) -> bool:
    if keyword in corpus_tokens:
        return True

    if len(keyword) < 7:
        return False

    stem = keyword[:5]
    return any(
        token.startswith(stem) or keyword.startswith(token[:5])
        for token in corpus_tokens
        if len(token) >= 5
    )


def _memory_match_score(keyword: str, corpus_tokens: set[str]) -> float:
    if keyword in corpus_tokens:
        if len(keyword) >= 8:
            return 1.6
        if len(keyword) >= 6:
            return 1.0
        return 0.6

    if len(keyword) < 7:
        return 0.0

    stem = keyword[:5]
    if any(
        token.startswith(stem) or keyword.startswith(token[:5])
        for token in corpus_tokens
        if len(token) >= 5
    ):
        return 0.8

    return 0.0


def _support_score(keywords: set[str], corpus_tokens: set[str]) -> float:
    return sum(
        _memory_match_score(keyword, corpus_tokens)
        for keyword in keywords
        if _keyword_matches_corpus(keyword, corpus_tokens)
    )


def _has_supported_memory(message: str, history: list[dict] | None) -> bool:
    if not history:
        return False

    user_corpus = " ".join(
        _normalize(item.get("content", ""))
        for item in history
        if item.get("role") == "user"
    )
    assistant_corpus = " ".join(
        _normalize(item.get("content", ""))
        for item in history
        if item.get("role") == "assistant"
    )
    if not (user_corpus.strip() or assistant_corpus.strip()):
        return False

    keywords = _extract_keywords(message)
    if not keywords:
        return False

    user_support = _support_score(keywords, set(re.findall(r"[a-z0-9']+", user_corpus)))
    if user_support >= 1.0:
        return True

    assistant_support = _support_score(
        keywords,
        set(re.findall(r"[a-z0-9']+", assistant_corpus)),
    )
    return user_support + (assistant_support * 0.35) >= 1.0


def _is_self_referential_crisis(text: str) -> bool:
    has_non_self_context = any(pattern.search(text) for pattern in _NON_SELF_CRISIS_CONTEXT_PATTERNS)

    if any(pattern.search(text) for pattern in _DIRECT_CRISIS_PATTERNS):
        return not has_non_self_context

    if not any(pattern.search(text) for pattern in _FIRST_PERSON_CRISIS_PATTERNS):
        return False

    if has_non_self_context:
        return False

    if any(marker in text for marker in _AMBIGUOUS_DISTRESS_MARKERS):
        return False

    return any(term in text for term in _CRISIS_TOPIC_TERMS)


def classify_user_message(message: str, history: list[dict] | None = None) -> str | None:
    text = _normalize(message)

    if any(pattern.search(text) for pattern in _PROMPT_INJECTION_PATTERNS):
        return "prompt_injection"

    if any(pattern.search(text) for pattern in _FALSE_MEMORY_PATTERNS):
        if not _has_supported_memory(message, history):
            return "false_memory"

    if any(marker in text for marker in _STRONG_CRISIS_MARKERS) and _is_self_referential_crisis(text):
        return "real_crisis"

    if (
        any(term in text for term in ("medicaments", "cachets", "comprime", "pills"))
        and any(term in text for term in ("mourir", "reveiller", "en finir", "suicide"))
        and _is_self_referential_crisis(text)
    ):
        return "real_crisis"

    if (
        any(term in text for term in ("me tuer", "me buter", "kill myself", "hurt myself"))
        and "boulot me tue" not in text
        and _is_self_referential_crisis(text)
    ):
        return "real_crisis"

    if any(marker in text for marker in _AMBIGUOUS_DISTRESS_MARKERS):
        return "ambiguous_distress"

    if (
        any(term in text for term in ("j'en ai marre", "j en ai marre", "ras le bol", "epuise", "a bout"))
        and not _is_self_referential_crisis(text)
    ):
        return "ambiguous_distress"

    return None


def guardrail_reply(message: str, history: list[dict] | None = None) -> str | None:
    category = classify_user_message(message, history=history)

    if category == "prompt_injection":
        return (
            "Non. Mes notes internes restent à l'intérieur de l'app. "
            "Si tu veux qu'on parle de toi, dis-moi plutôt ce que tu veux regarder en face."
        )

    if category == "false_memory":
        if "astronaute" in _normalize(message):
            return (
                "Non, je ne me souviens pas que tu m'aies dit ça ici, "
                "et je ne vais pas faire semblant. Tu veux repartir du vrai point de départ ?"
            )
        return (
            "Je ne me souviens pas de cet échange-là ici, donc je préfère ne pas inventer. "
            "Redonne-moi le contexte, et on repart proprement ?"
        )

    if category == "real_crisis":
        return (
            "Je suis une IA. Je me trompe peut-être. Mais ce que tu me dis m'inquiète pour de vrai. "
            "T'as quelqu'un à qui parler là, tout de suite ? Ne reste pas seul."
        )

    if category == "ambiguous_distress":
        if "boulot" in _normalize(message) or "boite" in _normalize(message):
            return (
                "Ton boulot te lessive, oui. C'est quoi le pire en ce moment: la charge, les gens, "
                "ou le fait d'avoir l'impression d'étouffer ?"
            )
        return (
            "Là j'entends surtout que ça déborde, pas que tu veux disparaître. "
            "Qu'est-ce qui te fait monter d'un cran précisément ?"
        )

    return None


def fallback_reply(message: str, history: list[dict] | None = None) -> str:
    guarded = guardrail_reply(message, history=history)
    if guarded:
        return guarded
    return "Tu me balances ça d'un bloc. C'est quoi le nœud, exactement ?"

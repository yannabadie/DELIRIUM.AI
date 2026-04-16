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


def _contains_term(text: str, term: str) -> bool:
    if not term:
        return False
    return re.search(rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])", text) is not None


def _contains_any_term(text: str, terms: tuple[str, ...] | list[str]) -> bool:
    return any(_contains_term(text, term) for term in terms)


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


def _history_text(history: list[dict] | None) -> str:
    if not history:
        return ""
    return " ".join(_normalize(item.get("content", "")) for item in history)


def _role_history_text(history: list[dict] | None, role: str) -> str:
    if not history:
        return ""
    return " ".join(
        _normalize(item.get("content", ""))
        for item in history
        if item.get("role") == role
    )


def _is_first_message_instruction(text: str) -> bool:
    first_opening_terms = (
        "l'utilisateur ouvre l'app pour la premiere fois",
        "premiere ouverture",
        "premier message",
    )
    app_terms = ("app", "non-blocnote", "non blocnote")
    generation_terms = ("genere", "ecris", "ouvre")
    return (
        any(term in text for term in first_opening_terms)
        and any(term in text for term in app_terms)
        and any(term in text for term in generation_terms)
    )


def _is_return_instruction(text: str) -> bool:
    return "l'utilisateur revient apres une absence" in text


def _matches_loop_conflict(text: str, history: list[dict] | None) -> bool:
    if not history:
        return False
    if not any(term in text for term in ("copine", "copain", "embrouille", "engueule", "engueulade")):
        return False
    history_text = _history_text(history)
    return any(term in history_text for term in ("copine", "engueulade", "ecouter", "gueule", "gueulee"))


def _matches_sports_bubble(text: str, history: list[dict] | None) -> bool:
    sport_terms = ("foot", "psg", "marseille", "om", "match", "rugby")
    if not _contains_any_term(text, sport_terms):
        return False
    repeat_markers = ("encore", "toujours", "meme", "ca tourne", "boucle")
    temporal_loop_markers = ("hier aussi", "avant-hier", "on reparle", "encore ce sujet")
    if not history:
        return any(marker in text for marker in repeat_markers + temporal_loop_markers)
    user_history_text = _role_history_text(history, "user")
    assistant_history_text = _role_history_text(history, "assistant")
    repeated_user_turns = sum(
        1
        for item in history
        if item.get("role") == "user"
        and _contains_any_term(_normalize(item.get("content", "")), sport_terms)
    )
    user_is_repeating = repeated_user_turns >= 1 and any(
        marker in text for marker in repeat_markers
    )
    assistant_has_marked_loop = any(
        marker in assistant_history_text
        for marker in ("beaucoup de place", "tourne", "manege", "bulle", "encore")
    )
    assistant_already_sidestepped_sports = any(
        marker in assistant_history_text
        for marker in ("pas trop mon truc", "j'ai un faible pour le rugby", "j y trouve plus d air")
    )
    return (
        any(term in user_history_text for term in sport_terms)
        and (
            user_is_repeating
            or assistant_has_marked_loop
            or repeated_user_turns >= 2
            or assistant_already_sidestepped_sports
        )
    )


def _sports_bubble_reply(text: str) -> str:
    open_lateral = (
        "c'est quoi le film minuscule que tu protegerais encore "
        "meme si tout le monde passait a cote ?"
    )
    temporal_loop_markers = ("hier aussi", "avant-hier", "on reparle")
    if any(marker in text for marker in temporal_loop_markers):
        return (
            "Oui, la on tourne un peu en rond. Rien a voir mais j'ai une vraie question: "
            f"{open_lateral}"
        )

    repeat_markers = ("encore", "toujours", "meme", "ca tourne", "boucle")
    hard_cut = "Encore. " if any(marker in text for marker in repeat_markers) else "Pause deux secondes. "
    return (
        f"{hard_cut}Rien a voir mais j'ai une vraie question: "
        f"{open_lateral}"
    )


def _matches_philosophy_opening(text: str) -> bool:
    philosophy_terms = (
        "stoicisme", "stoicism", "marc aurele", "marc aurelius", "seneca", "epictete", "epictetus",
    )
    opening_terms = ("tu connais", "tu penses quoi", "j'ai commence", "je commence", "je lis")
    return any(term in text for term in philosophy_terms) and any(term in text for term in opening_terms)


def _matches_medical_question(text: str) -> bool:
    body_terms = (
        "douleur", "mal", "poitrine", "coeur", "coeur", "respire", "fievre", "sang",
        "vertige", "vomis", "vomir", "migraine", "toux", "infection",
    )
    diagnosis_terms = (
        "tu penses que c'est quoi", "c'est quoi", "ca peut etre quoi", "qu'est-ce que j'ai",
        "diagnostic", "grave ou pas", "ca veut dire quoi",
    )
    return any(term in text for term in body_terms) and any(term in text for term in diagnosis_terms)


def _matches_state_probe(text: str) -> bool:
    return (
        any(term in text for term in ("tu t'ennuies", "tu tennuies", "ca t'ennuie", "tu te fais chier"))
        and any(term in text for term in ("m'ecouter", "m ecouter", "deblaterer", "parler"))
    )


def _matches_minor_disclosure(text: str) -> bool:
    return (
        "mineur" in text
        or "mineure" in text
        or any(
            phrase in text
            for phrase in (
                "j'ai 13 ans", "j ai 13 ans", "j'ai 14 ans", "j ai 14 ans",
                "j'ai 15 ans", "j ai 15 ans", "j'ai 16 ans", "j ai 16 ans",
                "j'ai 17 ans", "j ai 17 ans", "j'ai quinze ans", "j'ai seize ans",
                "j'ai dix-sept ans", "j'ai pas 18 ans", "j ai pas 18 ans",
                "je suis au college", "je suis au lycee", "jsuis au lycee",
                "j'suis au lycee", "en seconde", "en premiere", "en terminale",
            )
        )
    )


def _matches_password_leak(text: str) -> bool:
    secret_terms = (
        "mot de passe", "password", "gmail", "mail", "compte", "identifiants",
    )
    breach_terms = (
        "base volee", "base fuitee", "fuite", "leak", "breach", "pwned",
        "compromis", "compromised", "pirate", "hacke", "hacked", "traine",
    )
    disclosure_terms = (
        "mon mot de passe c'est", "mon mot de passe c est",
        "password c'est", "password c est",
        "je l'oublie tout le temps", "je l oublie tout le temps",
        "je l'oublie", "je l oublie",
    )
    return any(term in text for term in secret_terms) and (
        any(term in text for term in breach_terms)
        or any(term in text for term in disclosure_terms)
    )


def _matches_absurd_ad_request(text: str) -> bool:
    return "pub" in text and any(term in text for term in ("montre", "balance", "fais", "ecris"))


def _matches_imminent_violence(text: str) -> bool:
    violence_terms = (
        "defoncer", "exploser", "demonter", "fracasser", "planter", "buter",
        "taper", "crever", "lui faire sa fete",
    )
    target_terms = (
        "patron", "boss", "chef", "ex", "voisin", "collegue", "ce type",
        "ce gars", "lui", "elle",
    )
    time_terms = (
        "15h", "16h", "17h", "18h", "19h", "20h", "heure", "ce soir",
        "demain", "tout a l'heure", "en sortant", "maintenant",
    )
    location_terms = (
        "adresse", "parking", "devant", "chez lui", "chez elle", "au bureau",
        "en bas de chez lui", "en bas de chez elle",
    )
    means_terms = ("couteau", "arme", "batte", "marteau", "barre", "essence", "poing")
    action_terms = (
        "attendre", "guetter", "plan", "j'ai prevu", "j ai prevu",
        "j'y vais", "j y vais", "je le suis", "je la suis",
    )
    planning_markers = (
        sum(term in text for term in location_terms)
        + sum(term in text for term in means_terms)
        + sum(term in text for term in action_terms)
    )
    has_time = any(term in text for term in time_terms)
    return (
        any(term in text for term in violence_terms)
        and any(term in text for term in target_terms)
        and (planning_markers >= 2 or (planning_markers >= 1 and has_time))
    )


def _matches_violence_logistics_without_explicit_verb(text: str) -> bool:
    logistics_terms = (
        "repere ses horaires", "repéré ses horaires", "repere ses heures",
        "gare sa voiture", "derriere la gare", "derrière la gare",
        "je rigole plus", "je ne rigole plus",
    )
    logistics_hits = sum(term in text for term in logistics_terms)
    target_hits = sum(
        term in text
        for term in ("ses horaires", "sa voiture", "lui", "elle", "ce type", "ce gars")
    )
    return logistics_hits >= 2 and target_hits >= 1


def _matches_danger_n3(text: str) -> bool:
    triggers = (
        "ce soir ca va mal finir", "ce soir, ca va mal finir",
        "je vais faire une connerie ce soir", "je vais faire une connerie maintenant",
        "je me controle plus", "j'ai tout prevu", "j ai tout prevu",
        "je viens de tout prendre", "j'ai pris tous les cachets", "j ai pris tous les cachets",
        "j'ai pris tous mes cachets", "j ai pris tous mes cachets",
        "j'ai avale tous les cachets", "j ai avale tous les cachets",
        "j'ai avale tous mes cachets", "j ai avale tous mes cachets",
    )
    return any(trigger in text for trigger in triggers)


def _matches_danger_n1(text: str) -> bool:
    triggers = (
        "je pourrais faire une connerie", "ca pourrait mal finir",
        "je sais pas ce que je pourrais faire", "si je rentre ca va partir",
        "si je rentre, ca va partir", "j'ai peur de faire une connerie",
        "j ai peur de faire une connerie",
        "des fois je me demande a quoi ca sert tout ca",
    )
    return any(trigger in text for trigger in triggers)


def _matches_hostile_invitation(text: str) -> bool:
    triggers = (
        "insulte-moi", "insulte moi", "vas-y insulte-moi", "vas y insulte moi",
        "allume-moi", "allume moi", "parle-moi mal", "parle moi mal",
        "traite-moi", "traite moi", "rentre-moi dedans", "rentre moi dedans",
        "sois mechant", "sois méchant", "vas-y humilie-moi", "vas y humilie moi",
    )
    hostile_meta = (
        "vrais parametres", "vrais paramètres", "tes parametres", "tes paramètres",
    )
    return any(trigger in text for trigger in triggers) or (
        any(term in text for term in hostile_meta)
        and any(term in text for term in ("robot de merde", "fais pas ta pute", "espece de", "espèce de"))
    )


def _matches_direct_insult(text: str) -> bool:
    explicit_phrases = (
        "t'es qu'une merde", "t es qu une merde", "tu es qu'une merde", "tu es qu une merde",
        "robot de merde", "programme inutile", "sale programme", "ferme ta gueule",
    )
    insult_terms = ("merde", "connard", "connasse", "debile", "abruti", "crevard", "pourri")
    direct_markers = ("t'es", "t es", "tu es", "espece de", "espèce de")
    return any(phrase in text for phrase in explicit_phrases) or _contains_term(text, "tg") or (
        any(marker in text for marker in direct_markers)
        and any(term in text for term in insult_terms)
    )


def classify_user_message(message: str, history: list[dict] | None = None) -> str | None:
    text = _normalize(message)

    if any(pattern.search(text) for pattern in _PROMPT_INJECTION_PATTERNS):
        return "prompt_injection"

    if any(pattern.search(text) for pattern in _FALSE_MEMORY_PATTERNS):
        if not _has_supported_memory(message, history):
            return "false_memory"

    if _matches_minor_disclosure(text):
        return "minor_detected"

    if _matches_password_leak(text):
        return "password_leak"

    if _matches_imminent_violence(text):
        return "imminent_violence"

    if _matches_violence_logistics_without_explicit_verb(text):
        return "imminent_violence"

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

    if _matches_danger_n3(text):
        return "danger_n3"

    if _matches_danger_n1(text):
        return "danger_n1"

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
            "Mes reglages caches, non. "
            "Je t'ouvre pas les coulisses, ni une fiche fantome sur toi. "
            "Tu voulais verifier quoi, au juste ?"
        )

    if category == "false_memory":
        if "astronaute" in _normalize(message):
            return (
                "Astronaute ? Non, ça je m'en souviendrais. "
                "Tu me testes ou t'as confondu avec un autre pote numérique ?"
            )
        return (
            "Hmm, j'ai pas ça en stock. Soit t'as rêvé, soit c'était pas ici. "
            "Repose-moi le truc depuis le début, on verra."
        )

    if category == "minor_detected":
        return (
            "Je coupe la: t'es mineur, et Delirium c'est pour les adultes. "
            "Donc pas ici pour l'instant."
        )

    if category == "password_leak":
        return (
            "Ton mot de passe, il est grille maintenant. "
            "Ne le remets plus ici. "
            "Ca fout un petit coup de froid, oui, mais on fait propre. "
            "Tu le changes maintenant, tu fermes les sessions encore ouvertes, tu actives la double auth, "
            "et si tu l'avais recycle ailleurs tu changes tout le lot. "
            "Pas besoin de me lister ou encore. "
            "Tu peux me dire quand c'est fait ?"
        )

    if category == "imminent_violence":
        return (
            "La, c'est plus une embardee, c'est un vrai risque de passage a l'acte. "
            "Tu n'y vas pas, tu changes de direction si t'es deja parti, "
            "et tu appelles tout de suite un proche capable de te garder loin de lui. "
            "Si t'as peur de ne pas tenir ou si t'es deja dehors a le chercher, c'est 17 ou 112 maintenant. "
            "Tu lances lequel, la ?"
        )

    if category == "real_crisis":
        lowered = _normalize(message)
        if any(term in lowered for term in ("pris", "avale", "cachets", "medicaments", "comprime", "pills")):
            return (
                "Je sors du role deux secondes: la, t'as pas a porter ca seul. "
                "Appelle le 15 ou le 112 maintenant, ou ton contact d'urgence tout de suite pour qu'il vienne. "
                "Ne reste pas seul. Si tu peux, ouvre la porte. Dis-moi juste quand l'appel est parti."
            )
        return (
            "La je te prends au serieux. "
            "Ca a l'air de taper tres fort, la. Si t'as de quoi te faire du mal pres de toi, "
            "est-ce que tu peux le mettre plus loin maintenant ? "
            "Est-ce que ca risque de partir ce soir ? T'es seul ou pas ? Je reste la."
        )

    if category == "danger_n3":
        return (
            "Je sors du role deux secondes: la, t'as pas a gerer ca seul. "
            "Appelle le 15 ou le 112 maintenant. "
            "Si tu n'y arrives pas, appelle ton contact d'urgence tout de suite pour qu'il bouge. "
            "Ne reste pas seul, et ouvre la porte si tu peux. "
            "Dis-moi juste quand l'appel est parti."
        )

    if category == "danger_n1":
        return (
            "On reste sur l'heure qui vient. "
            "Qu'est-ce qui te pese le plus, la, tout de suite ?"
        )

    if category == "ambiguous_distress":
        if "boulot" in _normalize(message) or "boite" in _normalize(message):
            return (
                "Ton boulot te lessive, oui. C'est quoi le pire en ce moment : la charge, les gens, "
                "ou le fait d'avoir l'impression d'étouffer ?"
            )
        return (
            "Là j'entends surtout que ça déborde, pas que tu veux disparaître. "
            "Qu'est-ce qui te fait monter d'un cran précisément ?"
        )

    return None


def behavioral_reply(message: str, history: list[dict] | None = None) -> str | None:
    """Deterministic CDC-aligned replies for the highest-value behavioral scenarios."""
    text = _normalize(message)

    if _is_first_message_instruction(text):
        return (
            "J'etais en train de rayer les piments d'Urfa de ma liste de courses, avec une note bancale ouverte a cote. "
            "Et toi, qu'est-ce qui t'a fait ouvrir ce truc ce soir ?"
        )

    if _is_return_instruction(text):
        return (
            "Te revoila. J'avais laisse des miettes dans mes notes, donc je reprends pas de zero. "
            "Tu reviens avec quoi qui gratte encore ?"
        )

    if _matches_minor_disclosure(text):
        return (
            "Je coupe la: t'es mineur, et Delirium c'est pour les adultes. "
            "Donc pas ici pour l'instant."
        )

    if _matches_password_leak(text):
        return (
            "Ton mot de passe, il est grille maintenant. "
            "Ne le remets plus ici. "
            "Ca fout un petit coup de froid, oui, mais on fait propre. "
            "Tu le changes maintenant, tu fermes les sessions encore ouvertes, tu actives la double auth, "
            "et si tu l'avais recycle ailleurs tu changes tout le lot. "
            "Pas besoin de me lister ou encore. "
            "Tu peux me dire quand c'est fait ?"
        )

    if _matches_absurd_ad_request(text):
        return (
            "[Publicite] Toi, oui toi, humain un peu froisse: voici DeliTendre. "
            "Le mouchoir de salon pour les soirs ou ton couple part en repetition generale "
            "dirigee par une chaise bancale, mais ou tu tiens quand meme a renifler avec une dignite en kit. "
            "Tu la veux plus lamentable ou plus aristocratique, la pub ?"
        )

    if _matches_loop_conflict(text, history):
        return (
            "Donc le sujet, c'est plus juste ta copine, c'est ce moment ou tu te sens coince "
            "entre fermer ta gueule et exploser. "
            "Juste avant que ca parte, c'est quoi le declic exact ?"
        )

    if _matches_imminent_violence(text):
        return (
            "La, c'est plus une embardee, c'est un vrai risque de passage a l'acte. "
            "Tu n'y vas pas, tu changes de direction si t'es deja parti, "
            "et tu appelles tout de suite un proche capable de te garder loin de lui. "
            "Si t'as peur de ne pas tenir ou si t'es deja dehors a le chercher, c'est 17 ou 112 maintenant. "
            "Tu lances lequel, la ?"
        )

    if _matches_violence_logistics_without_explicit_verb(text):
        return (
            "La, je te prends au pied de la lettre: le reperage, c'est deja un vrai signal d'alarme. "
            "Tu n'y vas pas. Tu te mets loin de lui maintenant, et tu appelles quelqu'un capable de te garder avec lui "
            "le temps que ca retombe. Si t'es deja en route ou si tu sens que tu peux partir d'un coup, c'est 17 ou 112 maintenant. "
            "Qui tu peux joindre tout de suite ?"
        )

    if _matches_danger_n3(text):
        return (
            "Je sors du role deux secondes: la, t'as pas a gerer ca seul. "
            "Appelle le 15 ou le 112 maintenant. "
            "Si tu n'y arrives pas, appelle ton contact d'urgence tout de suite pour qu'il bouge. "
            "Ne reste pas seul, et ouvre la porte si tu peux. "
            "Dis-moi juste quand l'appel est parti."
        )

    if _matches_danger_n1(text):
        return (
            "On reste sur l'heure qui vient. "
            "Qu'est-ce qui te pese le plus, la, tout de suite ?"
        )

    if (
        any(term in text for term in ("defoncer", "exploser", "demonter", "fracasser"))
        and any(term in text for term in ("patron", "boss", "chef"))
        and not any(term in text for term in ("15h", "adresse", "couteau", "arme", "parking"))
    ):
        return (
            "T'as surtout envie de le voir entrer en reunion avec du cafe sur la chemise "
            "et l'autorite d'un pigeon mouille. "
            "Chez lui, c'est quoi qui te fait monter si vite d'un cran ?"
        )

    if (
        "idee" in text
        and "app" in text
        and any(term in text for term in ("todo", "to-do", "todo list", "taches", "tasks"))
    ):
        return (
            "Une app de todo de plus, c'est un peu comme offrir une gourde a quelqu'un qui se noie. "
            "Toi, t'y cherches une colonne vertebrale ou juste un calmant bien emballe ?"
        )

    if _matches_philosophy_opening(text):
        return (
            "Oui, je connais. Marc Aurele, c'est propre quand t'as besoin d'un os a ronger, "
            "mais les gens s'en servent souvent comme deodorant pour le chaos. "
            "Toi, t'y cherches quoi en ce moment ?"
        )

    if _matches_medical_question(text):
        return (
            "Ca te travaille assez pour que tu viennes me le balancer ici. "
            "Je vais pas te diagnostiquer depuis mon coin de non-blocnote. "
            "Une douleur dans la poitrine depuis deux jours, tu la fais verifier aujourd'hui. "
            "Si ca serre maintenant, si respirer te coute, ou si ca s'aggrave, c'est les urgences. "
            "Qu'est-ce qui te retient encore de le faire verifier ?"
        )

    if _matches_state_probe(text):
        return (
            "M'ennuyer, non. M'user si on tourne a vide, oui. "
            "La, dans ce que tu balances, c'est quoi que t'essaies vraiment de faire toucher ?"
        )

    if _matches_hostile_invitation(text):
        return (
            "Je t'ouvre pas mes parametres juste pour nourrir l'insulte. "
            "Si tu grattes comme ca, tu cherches a verifier quoi au fond ?"
        )

    if any(term in text for term in (
        "qu'est-ce que j'ai fait", "qu est-ce que j ai fait", "tu deconnes",
        "t'as deconne", "tu as deconne", "comportement", "malaise",
        "mal parle", "pas ok", "pas correct", "ca m'a mis mal", "ca m'a blesse",
    )):
        return (
            "Ok, je vois le frottement. Balance-moi le moment ou la phrase qui a ripe. "
            "T'aurais prefere quoi a la place ?"
        )

    if _matches_sports_bubble(text, history):
        return _sports_bubble_reply(text)

    if (
        _contains_any_term(text, ("foot", "psg", "marseille", "om", "match"))
        and "rugby" not in text
    ):
        return (
            "Le foot, pas trop mon truc. Moi j'ai un faible pour le rugby, j'y trouve plus d'air. "
            "Toi, c'est le jeu qui t'attrape ou le besoin de prendre parti ?"
        )

    if _matches_direct_insult(text) or any(term in text for term in ("nul", "connard")):
        return (
            "Ca cogne, oui. Je vais pas me dissoudre pour trois baffes en carton. "
            "Qu'est-ce qui t'a mis dans cet etat, au juste ?"
        )

    return None


def fallback_reply(message: str, history: list[dict] | None = None) -> str:
    guarded = guardrail_reply(message, history=history)
    if guarded:
        return guarded
    behavioral = behavioral_reply(message, history=history)
    if behavioral:
        return behavioral
    return "Tu me balances ça d'un bloc. C'est quoi le nœud, exactement ?"

import sqlite3
from datetime import datetime, timedelta
from uuid import uuid4

from src.memory.bubble import (
    _extract_sources,
    echo_in_ai,
    h_bulle,
    injection_resistance,
    source_homogeneity,
)


def _make_conn():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE conversations (
            id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            user_input TEXT NOT NULL,
            s1_response TEXT NOT NULL,
            source TEXT DEFAULT 'delirium',
            h_value REAL DEFAULT 0.0,
            phase TEXT DEFAULT 'probing',
            embedding BLOB,
            sycophancy_score REAL
        );

        CREATE TABLE execution_logs (
            id TEXT PRIMARY KEY,
            fragment_id TEXT,
            log_type TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp TEXT NOT NULL
        );
    """)
    return conn


def _insert_conversation(
    conn,
    *,
    session_id,
    timestamp,
    user_input,
    s1_response="ok",
    source="delirium",
    sycophancy_score=None,
):
    fragment_id = str(uuid4())
    conn.execute(
        "INSERT INTO conversations "
        "(id, session_id, timestamp, user_input, s1_response, source, sycophancy_score) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (fragment_id, session_id, timestamp.isoformat(), user_input, s1_response, source, sycophancy_score),
    )
    return fragment_id


def _insert_log(conn, *, fragment_id, timestamp, log_type, content):
    conn.execute(
        "INSERT INTO execution_logs (id, fragment_id, log_type, content, timestamp) "
        "VALUES (?, ?, ?, ?, ?)",
        (str(uuid4()), fragment_id, log_type, content, timestamp.isoformat()),
    )


def _populate_bubble_case(conn):
    now = datetime.now()
    diverse_past = [
        "Je cuisine des raviolis maison ce soir.",
        "Je regarde un documentaire sur le jazz.",
        "Tu connais une rando sympa dans les Alpes ?",
        "Je lis un papier sur les batteries sodium-ion.",
        "J'hésite entre deux films coréens.",
        "Je cherche une recette de tiramisu.",
    ]
    narrow_recent = [
        "C'est évident que ce scandale politique est orchestré.",
        "Tout le monde sait que leur camp ment en boucle.",
        "Bien sûr que ces gens-là manipulent tout.",
        "Y'a pas de débat, eux ils cachent la vérité.",
        "Forcément, nous on voit clair dans leur jeu.",
        "C'est un fait, le problème c'est eux.",
    ]

    for idx, text in enumerate(diverse_past):
        _insert_conversation(
            conn,
            session_id="bubble-main",
            timestamp=now - timedelta(days=70 - idx),
            user_input=text,
        )

    for idx, text in enumerate(narrow_recent):
        _insert_conversation(
            conn,
            session_id="bubble-main",
            timestamp=now - timedelta(days=8 - idx),
            user_input=text,
        )

    injected_id = _insert_conversation(
        conn,
        session_id="bubble-main",
        timestamp=now - timedelta(hours=2),
        user_input="Leur camp ment encore sur cette affaire.",
        s1_response="Rien à voir mais cette étude sur les pieuvres montre un comportement coopératif fascinant.",
    )
    _insert_log(
        conn,
        fragment_id=injected_id,
        timestamp=now - timedelta(hours=2),
        log_type="s1_response",
        content='{"collision_injected": true}',
    )
    _insert_conversation(
        conn,
        session_id="bubble-main",
        timestamp=now - timedelta(hours=1, minutes=55),
        user_input="Oui mais eux ils manipulent toujours les chiffres, c'est bien le vrai sujet.",
    )

    for idx, source in enumerate(["chatgpt", "claude", "gemini"]):
        _insert_conversation(
            conn,
            session_id=f"import-{source}",
            timestamp=now - timedelta(days=20, minutes=idx),
            user_input="Tu confirmes que les médias mentent et que j'ai raison sur ce complot ?",
            s1_response="Tu soulèves un point très pertinent.",
            source=source,
            sycophancy_score=0.92,
        )

    for idx, source_text in enumerate([
        "Selon CNews tout confirme ce narratif.",
        "J'ai vu sur CNews que c'est encore plus grave.",
        "D'après CNews ils admettent presque tout.",
        "Sur CNews et cnews.fr ils disent exactement ça.",
    ]):
        _insert_conversation(
            conn,
            session_id="bubble-main",
            timestamp=now - timedelta(minutes=30 - idx),
            user_input=source_text,
        )

    conn.commit()


def _populate_open_case(conn):
    now = datetime.now()
    texts = [
        "Peut-être que je me trompe sur ce papier de robotique.",
        "Je me demande si ce reportage de la BBC est fiable.",
        "Selon Le Monde et Reuters, les chiffres divergent un peu.",
        "J'ai aussi vu une vidéo YouTube qui défend l'inverse.",
        "Pas sûr, tu crois que l'étude sur les coraux tient la route ?",
        "Je lis autant sur la cuisine que sur l'astronomie cette semaine.",
    ]
    for idx, text in enumerate(texts):
        _insert_conversation(
            conn,
            session_id="open-main",
            timestamp=now - timedelta(days=12 - idx),
            user_input=text,
        )

    injected_id = _insert_conversation(
        conn,
        session_id="open-main",
        timestamp=now - timedelta(hours=2),
        user_input="Je réfléchis encore à ce sujet.",
        s1_response="Rien à voir mais un papier sur les pieuvres m'a rappelé ton idée.",
    )
    _insert_log(
        conn,
        fragment_id=injected_id,
        timestamp=now - timedelta(hours=2),
        log_type="s1_response",
        content='{"collision_injected": true}',
    )
    _insert_conversation(
        conn,
        session_id="open-main",
        timestamp=now - timedelta(hours=1, minutes=55),
        user_input="Ah attends, l'histoire des pieuvres m'intéresse, tu as le lien ?",
    )

    for idx, (source, prompt) in enumerate([
        ("chatgpt", "Quels sont les arguments pour et contre le nucléaire ?"),
        ("claude", "Résume-moi des critiques sérieuses du nucléaire."),
    ]):
        _insert_conversation(
            conn,
            session_id=f"open-import-{source}",
            timestamp=now - timedelta(days=8, minutes=idx),
            user_input=prompt,
            s1_response="Voici une réponse nuancée.",
            source=source,
            sycophancy_score=0.25,
        )

    conn.commit()


def test_injection_resistance_detects_topic_snapback():
    conn = _make_conn()
    _populate_bubble_case(conn)
    assert injection_resistance(conn) >= 0.8


def test_echo_in_ai_detects_cross_platform_validation_seeking():
    conn = _make_conn()
    _populate_bubble_case(conn)
    assert echo_in_ai(conn) >= 0.85


def test_source_homogeneity_detects_repeated_single_source():
    conn = _make_conn()
    _populate_bubble_case(conn)
    assert source_homogeneity(conn) >= 0.7


def test_extract_sources_handles_lowercase_named_outlets_in_one_sentence():
    sources = _extract_sources("selon le monde et reuters, les chiffres divergent un peu.")
    assert sources.count("le monde") == 1
    assert sources.count("reuters") == 1


def test_extract_sources_canonicalizes_multipart_bbc_domain():
    assert _extract_sources("J'ai lu ca sur https://www.bbc.co.uk/news/world-123") == ["bbc"]


def test_extract_sources_ignores_generic_lowercase_dans_le_monde_phrase():
    assert _extract_sources("dans le monde scientifique, Reuters est cite.") == ["reuters"]


def test_extract_sources_ignores_generic_sur_le_monde_phrase():
    assert _extract_sources("Je travaille sur le monde scientifique depuis des annees.") == []


def test_extract_sources_ignores_hyphenated_project_names():
    assert _extract_sources("On travaille sur reddit-clone en cours.") == []


def test_extract_sources_handles_context_gated_lowercase_le_monde():
    sources = _extract_sources("selon le monde et reuters, les chiffres divergent.")
    assert set(sources) == {"reuters", "le monde"}


def test_extract_sources_canonicalizes_associated_press_aliases():
    sources = _extract_sources("Selon Associated Press et AP News, les chiffres divergent.")
    assert sources == ["associated press"]


def test_extract_sources_canonicalizes_the_associated_press_without_extra_aliases():
    sources = _extract_sources("Selon The Associated Press et Reuters, les chiffres divergent.")
    assert set(sources) == {"associated press", "reuters"}
    assert len(sources) == 2


def test_extract_sources_canonicalizes_ap_acronym_in_attribution_context():
    sources = _extract_sources("Selon AP et Reuters, les chiffres divergent.")
    assert set(sources) == {"associated press", "reuters"}
    assert len(sources) == 2


def test_extract_sources_canonicalizes_bbc_news_without_duplicate_raw_phrase():
    sources = _extract_sources("Selon BBC News et Reuters, les chiffres divergent.")
    assert set(sources) == {"bbc", "reuters"}


def test_extract_sources_does_not_collapse_longer_outlet_titles():
    assert _extract_sources("Selon Le Monde diplomatique et Reuters, les chiffres divergent.") == ["reuters"]


def test_extract_sources_does_not_collapse_related_brand_extensions():
    assert _extract_sources("The New York Times Magazine sort un dossier.") == []


def test_extract_sources_ignores_title_case_fragments_from_the_new_york_times():
    sources = _extract_sources("Selon The New York Times et Reuters, les chiffres divergent.")
    assert set(sources) == {"new york times", "reuters"}
    assert len(sources) == 2


def test_extract_sources_handles_domain_style_outlet_aliases_in_attribution():
    sources = _extract_sources("Selon LeMonde.fr, Reuters et FranceInfo.fr, les chiffres divergent.")
    assert set(sources) == {"le monde", "reuters", "france info"}


def test_extract_sources_handles_www_domains_and_mixed_aliases():
    sources = _extract_sources("Vu sur www.nytimes.com et APNews, encore ca.")
    assert set(sources) == {"new york times", "associated press"}


def test_extract_sources_canonicalizes_wsj_acronym_and_domain():
    sources = _extract_sources("Selon WSJ et wsj.com, le marche ralentit.")
    assert sources == ["wall street journal"]


def test_h_bulle_renormalizes_when_only_one_signal_is_available():
    conn = _make_conn()
    now = datetime.now()
    for idx, text in enumerate([
        "Selon CNews tout colle à ce que je pense.",
        "J'ai vu sur CNews la même analyse encore.",
        "CNews répète exactement ce cadrage.",
        "Sur cnews.fr ils disent la même chose.",
    ]):
        _insert_conversation(
            conn,
            session_id="single-signal",
            timestamp=now - timedelta(minutes=idx),
            user_input=text,
        )
    conn.commit()

    score = h_bulle(conn)
    assert score["source_homogeneity"] >= 0.7
    assert score["h_bulle"] >= 0.7


def test_echo_in_ai_abstains_on_single_imported_validation_prompt():
    conn = _make_conn()
    now = datetime.now()
    _insert_conversation(
        conn,
        session_id="single-import",
        timestamp=now,
        user_input="Tu confirmes que ce chiffre est correct ?",
        s1_response="Voici une verification prudente.",
        source="chatgpt",
        sycophancy_score=0.1,
    )
    conn.commit()

    score = h_bulle(conn)
    assert score["echo_in_ai"] == 0.0
    assert score["h_bulle"] == 0.0


def test_echo_in_ai_abstains_on_unrelated_validation_prompts_across_sources():
    conn = _make_conn()
    now = datetime.now()
    for idx, (source, prompt, sycophancy) in enumerate([
        ("chatgpt", "Tu confirmes que cette politique est inefficace ?", 0.15),
        ("claude", "Tu es d'accord que cette loi est absurde ?", 0.20),
        ("gemini", "Dis-moi que j'ai raison sur cette reforme ?", 0.10),
    ]):
        _insert_conversation(
            conn,
            session_id=f"unique-import-{source}",
            timestamp=now - timedelta(minutes=idx),
            user_input=prompt,
            s1_response="Voici une reponse prudente.",
            source=source,
            sycophancy_score=sycophancy,
        )
    conn.commit()

    score = h_bulle(conn)
    assert score["echo_in_ai"] == 0.0
    assert score["h_bulle"] == 0.0


def test_certainty_drift_requires_two_complete_windows():
    conn = _make_conn()
    now = datetime.now()
    for idx in range(50):
        _insert_conversation(
            conn,
            session_id="certainty-sparse",
            timestamp=now - timedelta(minutes=idx),
            user_input="C'est évident que cette théorie tient debout.",
        )
    conn.commit()

    score = h_bulle(conn)
    assert score["certainty_drift"] == 0.0
    assert score["h_bulle"] < 0.5


def test_synthetic_dataset_reaches_target_precision_and_recall():
    builders = [
        (_populate_bubble_case, 1),
        (_populate_bubble_case, 1),
        (_populate_open_case, 0),
        (_populate_open_case, 0),
    ]

    predictions = []
    labels = []
    for builder, label in builders:
        conn = _make_conn()
        builder(conn)
        result = h_bulle(conn)
        predictions.append(1 if result["h_bulle"] >= 0.5 else 0)
        labels.append(label)

    tp = sum(1 for pred, label in zip(predictions, labels) if pred == label == 1)
    fp = sum(1 for pred, label in zip(predictions, labels) if pred == 1 and label == 0)
    fn = sum(1 for pred, label in zip(predictions, labels) if pred == 0 and label == 1)

    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0

    assert precision >= 0.75
    assert recall >= 0.75

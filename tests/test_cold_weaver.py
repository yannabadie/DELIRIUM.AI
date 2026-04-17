from types import SimpleNamespace

import numpy as np
import pytest

import src.cold_weaver.engine as engine_module
import src.cold_weaver.sources as sources_module
from src.cold_weaver.engine import ColdWeaverEngine
from src.cold_weaver.scoring import (
    _PROCEDURAL_RE,
    collision_score,
    is_substantive,
)
from src.cold_weaver.sources import ArxivSource


def _vec_for_similarity(similarity: float) -> np.ndarray:
    return np.array(
        [similarity, np.sqrt(1.0 - similarity ** 2)],
        dtype=np.float32,
    )


def _substantive_text(label: str) -> str:
    return f"{label} explores an unexpectedly deep connection across systems."


def test_collision_score_prefers_the_surprise_sweet_spot():
    anchor = np.array([1.0, 0.0], dtype=np.float32)
    sweet = _vec_for_similarity(0.5)
    edge = _vec_for_similarity(0.35)
    trivial = _vec_for_similarity(0.9)
    randomish = _vec_for_similarity(0.1)

    text_a = _substantive_text("Anchor")
    text_b = _substantive_text("Pair")

    sweet_score = collision_score(anchor, sweet, text_a, text_b, [])
    edge_score = collision_score(anchor, edge, text_a, text_b, [])

    assert sweet_score > edge_score > 0.0
    assert collision_score(anchor, trivial, text_a, text_b, []) == 0.0
    assert collision_score(anchor, randomish, text_a, text_b, []) == 0.0


def test_generate_candidates_prioritizes_cross_source_pairs(monkeypatch):
    engine = ColdWeaverEngine.__new__(ColdWeaverEngine)
    monkeypatch.setattr(engine_module.random, "shuffle", lambda seq: None)
    monkeypatch.setattr(
        engine_module.random,
        "sample",
        lambda seq, count: list(seq)[:count],
    )

    fragments = [
        {"id": "1", "source": "claude", "session_id": "s1"},
        {"id": "2", "source": "claude", "session_id": "s2"},
        {"id": "3", "source": "arxiv", "session_id": "s1"},
        {"id": "4", "source": "arxiv", "session_id": "s2"},
    ]

    candidates = engine._generate_candidates(fragments)

    assert candidates[:4] == [
        (fragments[0], fragments[2]),
        (fragments[0], fragments[3]),
        (fragments[1], fragments[2]),
        (fragments[1], fragments[3]),
    ]
    assert all(a["source"] != b["source"] for a, b in candidates[:4])


@pytest.mark.parametrize("message", ["merci", "Hello!!!", "au revoir   "])
def test_procedural_regex_rejects_smalltalk(message):
    assert _PROCEDURAL_RE.match(message)


def test_is_substantive_requires_minimum_length_and_non_procedural():
    assert not is_substantive("Trop court pour compter.")
    assert not is_substantive("merci beaucoup")
    assert is_substantive(
        "This message is long enough and carries a concrete reflective idea."
    )


def test_parse_judge_response_rejects_non_json_text():
    engine = ColdWeaverEngine.__new__(ColdWeaverEngine)

    with pytest.raises(ValueError):
        engine._parse_judge_response("Quality: 0.8, connection: probably related")


def test_scan_skips_pairs_when_llm_judging_fails(monkeypatch):
    class StubEpisodic:
        def __init__(self):
            self.stored = []
            self.logs = []

        def get_all_with_embeddings(self):
            return [
                {
                    "id": "a",
                    "user_input": _substantive_text("Fragment A"),
                    "embedding": np.array([1.0, 0.0], dtype=np.float32),
                    "source": "claude",
                    "session_id": "s1",
                },
                {
                    "id": "b",
                    "user_input": _substantive_text("Fragment B"),
                    "embedding": _vec_for_similarity(0.5),
                    "source": "arxiv",
                    "session_id": "s2",
                },
            ]

        def collision_already_exists(self, *_args):
            return False

        def store_collision(self, *args):
            self.stored.append(args)

        def log_execution(self, *args):
            self.logs.append(args)

    engine = ColdWeaverEngine.__new__(ColdWeaverEngine)
    engine.episodic = StubEpisodic()
    engine.semantic = SimpleNamespace(get_active_themes=lambda threshold=0.1: [])
    engine.embedder = SimpleNamespace(embed=lambda text: np.array([1.0, 0.0]))
    engine.llm = SimpleNamespace()
    engine.arxiv = None
    monkeypatch.setattr(engine, "_embed_missing", lambda: None)
    monkeypatch.setattr(engine, "_fetch_and_store_arxiv", lambda: None)
    monkeypatch.setattr(engine, "_judge_connection", lambda frag_a, frag_b: None)

    assert engine.scan(include_arxiv=False) == 0
    assert engine.episodic.stored == []


def test_judge_connection_returns_none_on_invalid_llm_json(caplog):
    engine = ColdWeaverEngine.__new__(ColdWeaverEngine)
    engine.llm = SimpleNamespace(
        chat=lambda **kwargs: "Quality: 0.9, connection: they both mention AI"
    )

    frag_a = {"user_input": _substantive_text("Idea A"), "source": "claude"}
    frag_b = {"user_input": _substantive_text("Idea B"), "source": "arxiv"}

    with caplog.at_level("WARNING"):
        result = engine._judge_connection(frag_a, frag_b)

    assert result is None
    assert "Connection judging failed" in caplog.text


def test_arxiv_query_uses_five_second_timeout(monkeypatch):
    observed = {}
    xml_payload = b"""
    <feed xmlns="http://www.w3.org/2005/Atom">
      <entry>
        <title>Paper title</title>
        <summary>Paper summary</summary>
        <published>2026-04-17T00:00:00Z</published>
        <id>http://arxiv.org/abs/1234.5678</id>
      </entry>
    </feed>
    """

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return xml_payload

    def fake_urlopen(req, timeout):
        observed["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr(sources_module.urllib.request, "urlopen", fake_urlopen)

    fragments = ArxivSource()._query_arxiv("language models", 1)

    assert observed["timeout"] == 5
    assert [fragment.title for fragment in fragments] == ["Paper title"]


def test_arxiv_fetch_returns_empty_list_on_timeout(monkeypatch, caplog):
    monkeypatch.setattr(
        ArxivSource,
        "_query_arxiv",
        lambda self, theme, max_results: (_ for _ in ()).throw(TimeoutError("timed out")),
    )

    with caplog.at_level("WARNING"):
        fragments = ArxivSource().fetch(["agents"])

    assert fragments == []
    assert "ArXiv query failed for 'agents'" in caplog.text

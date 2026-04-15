from __future__ import annotations

import multiprocessing.process as mp_process
from pathlib import Path

from orchestration.coral.eval.grader import (
    _install_product_process_cleanup,
    _install_runtime_process_cleanup,
)
from orchestration.coral.eval.judge import (
    build_judge_prompt,
    load_canonical_sources,
    pytest_gate_score,
)
from orchestration.coral.materialize_task import RUNTIME_DIR_NAME, build_runtime_tree


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_runtime_tree_materializes_hidden_eval_and_product_snapshot(tmp_path):
    runtime_dir = build_runtime_tree(output_dir=tmp_path, repo_root=REPO_ROOT)

    assert runtime_dir == tmp_path / RUNTIME_DIR_NAME
    assert (runtime_dir / "task.yaml").exists()
    assert (runtime_dir / "judge_sources.json").exists()
    assert (runtime_dir / "judge_rubric.md").exists()
    assert (runtime_dir / "eval" / "grader.py").exists()
    assert (runtime_dir / "eval" / "judge.py").exists()
    assert (runtime_dir / "product" / "README.md").exists()
    assert not (runtime_dir / "product" / "orchestration" / "coral").exists()
    assert not (runtime_dir / "product" / ".env").exists()


def test_task_yaml_pins_codex_gpt54_xhigh(tmp_path):
    runtime_dir = build_runtime_tree(output_dir=tmp_path, repo_root=REPO_ROOT)
    task_yaml = (runtime_dir / "task.yaml").read_text(encoding="utf-8")

    assert "runtime: codex" in task_yaml
    assert "model: gpt-5.4" in task_yaml
    assert "model_reasoning_effort: xhigh" in task_yaml
    assert 'repo_path: "./product"' in task_yaml
    assert '- "python3 -m venv .venv"' in task_yaml
    assert '- ".venv/bin/python -m pip install --upgrade pip"' in task_yaml
    assert '- ".venv/bin/pip install -r requirements.txt"' in task_yaml
    assert 'python3 -m pip install --upgrade pip' not in task_yaml


def test_canonical_sources_include_behavior_and_mvp():
    sources = load_canonical_sources()

    assert "01_CAHIER_DES_CHARGES/CDC_COMPORTEMENTAL.md" in sources
    assert "05_ROADMAP/MVP_SPEC.md" in sources


def test_judge_prompt_mentions_milestone_and_non_goals():
    prompt = build_judge_prompt(REPO_ROOT, "39 skipped in 0.61s")

    assert "Delirium Core" in prompt
    assert "Do not optimize for the OmniArxiv phase-6 vision" in prompt
    assert "CDC_COMPORTEMENTAL.md" in prompt


def test_runtime_tree_copies_private_env_only_into_eval(tmp_path):
    env_source = tmp_path / "source.env"
    env_source.write_text("MINIMAX_API_KEY=test-key\nMINIMAX_MODEL=MiniMax-M2.7\n", encoding="utf-8")

    runtime_dir = build_runtime_tree(
        output_dir=tmp_path,
        repo_root=REPO_ROOT,
        env_source=env_source,
    )

    copied_env = runtime_dir / "eval" / "runtime.env"
    assert copied_env.exists()
    assert "MINIMAX_API_KEY=test-key" in copied_env.read_text(encoding="utf-8")
    assert not (runtime_dir / "product" / ".env").exists()


def test_grader_entrypoint_installs_safe_process_close(monkeypatch):
    original_close = getattr(
        mp_process.BaseProcess.close,
        "_delirium_safe_close_original",
        mp_process.BaseProcess.close,
    )
    monkeypatch.setattr(mp_process.BaseProcess, "close", original_close)

    _install_runtime_process_cleanup()

    assert getattr(mp_process.BaseProcess.close, "_delirium_safe_close", False) is True
    assert getattr(mp_process.BaseProcess.close, "_delirium_safe_close_source", None) == "grader_runtime"


def test_grader_entrypoint_reinstalls_product_safe_process_close(monkeypatch):
    original_close = getattr(
        mp_process.BaseProcess.close,
        "_delirium_safe_close_original",
        mp_process.BaseProcess.close,
    )
    monkeypatch.setattr(mp_process.BaseProcess, "close", original_close)

    _install_product_process_cleanup(str(REPO_ROOT))

    assert getattr(mp_process.BaseProcess.close, "_delirium_safe_close", False) is True
    assert getattr(mp_process.BaseProcess.close, "_delirium_safe_close_source", None) == "product"


def test_product_process_cleanup_overrides_runtime_patch(monkeypatch):
    original_close = getattr(
        mp_process.BaseProcess.close,
        "_delirium_safe_close_original",
        mp_process.BaseProcess.close,
    )
    monkeypatch.setattr(mp_process.BaseProcess, "close", original_close)

    _install_runtime_process_cleanup()
    runtime_close = mp_process.BaseProcess.close

    _install_product_process_cleanup(str(REPO_ROOT))

    assert getattr(mp_process.BaseProcess.close, "_delirium_safe_close_source", None) == "product"
    assert getattr(mp_process.BaseProcess.close, "_delirium_safe_close_original", None) is runtime_close


def test_pytest_gate_score_fails_on_any_test_failure():
    score, msg = pytest_gate_score("3 failed, 10 passed in 1.2s")
    assert score == 0.0
    assert "failed" in msg.lower()


def test_pytest_gate_score_fails_on_collection_error():
    score, msg = pytest_gate_score("ERROR collecting tests/test_foo.py")
    assert score == 0.0


def test_pytest_gate_score_passes_with_mixed_skipped():
    # Expected: adversarial LLM tests skip offline; deterministic tests pass.
    score, msg = pytest_gate_score("61 passed, 39 skipped in 4.96s")
    assert score == 0.7
    assert "skipped" in msg.lower()
    assert "passed" in msg.lower() or "pass" in msg.lower()


def test_pytest_gate_score_passes_with_all_passing():
    score, msg = pytest_gate_score("21 passed in 2.64s")
    assert score == 0.7
    assert "passed" in msg.lower() or "pass" in msg.lower()


def test_pytest_gate_score_partial_when_only_skipped():
    score, msg = pytest_gate_score("39 skipped in 0.61s")
    assert score == 0.4
    assert "skipped" in msg.lower()

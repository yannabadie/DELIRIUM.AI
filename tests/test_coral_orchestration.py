from __future__ import annotations

from pathlib import Path

from orchestration.coral.eval.judge import build_judge_prompt, load_canonical_sources
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


def test_task_yaml_pins_codex_gpt54_xhigh(tmp_path):
    runtime_dir = build_runtime_tree(output_dir=tmp_path, repo_root=REPO_ROOT)
    task_yaml = (runtime_dir / "task.yaml").read_text(encoding="utf-8")

    assert "runtime: codex" in task_yaml
    assert "model: gpt-5.4" in task_yaml
    assert "model_reasoning_effort: xhigh" in task_yaml
    assert 'repo_path: "./product"' in task_yaml


def test_canonical_sources_include_behavior_and_mvp():
    sources = load_canonical_sources()

    assert "01_CAHIER_DES_CHARGES/CDC_COMPORTEMENTAL.md" in sources
    assert "05_ROADMAP/MVP_SPEC.md" in sources


def test_judge_prompt_mentions_milestone_and_non_goals():
    prompt = build_judge_prompt(REPO_ROOT, "39 skipped in 0.61s")

    assert "Delirium Core" in prompt
    assert "Do not optimize for the OmniArxiv phase-6 vision" in prompt
    assert "CDC_COMPORTEMENTAL.md" in prompt

# Coral Orchestration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a self-contained Coral orchestration pack to `DELIRIUM.AI` that can materialize a private Coral task workspace, run Codex agents as `gpt-5.4` with `xhigh`, and evaluate productization progress with deterministic checks plus an LLM judge.

**Architecture:** Keep upstream Coral unchanged. Store orchestration assets in this repository, then materialize a runtime workspace outside the repository so Coral agents only see the product code under evaluation and never the visible grader assets. Use the existing `pytest` suite as the deterministic gate and a Delirium-specific judge layer driven by canonical product documents.

**Tech Stack:** Python 3.11+, PowerShell, Bash, WSL2 Ubuntu, Coral task YAML, Codex CLI, pytest, JSON.

---

### Task 1: Add orchestration pack skeleton

**Files:**
- Create: `orchestration/coral/README.md`
- Create: `orchestration/coral/task.template.yaml`
- Create: `orchestration/coral/materialize_task.py`
- Create: `orchestration/coral/judge_rubric.md`
- Create: `orchestration/coral/judge_sources.json`

- [ ] **Step 1: Write the failing test**

```python
from pathlib import Path


def test_orchestration_assets_exist():
    root = Path(__file__).resolve().parents[1]
    assert (root / "orchestration" / "coral" / "task.template.yaml").exists()
    assert (root / "orchestration" / "coral" / "materialize_task.py").exists()
    assert (root / "orchestration" / "coral" / "judge_rubric.md").exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_coral_orchestration.py::test_orchestration_assets_exist -v`
Expected: FAIL because orchestration files do not exist yet.

- [ ] **Step 3: Write minimal implementation**

```python
# materialize_task.py
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / ".runtime" / "coral-task"


def main() -> int:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

```yaml
# task.template.yaml
task:
  name: delirium-ai
  description: |
    Productize DELIRIUM.AI toward a local-first, testable Delirium Core.
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_coral_orchestration.py::test_orchestration_assets_exist -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add orchestration/coral tests/test_coral_orchestration.py
git commit -m "feat: add coral orchestration skeleton"
```

### Task 2: Materialize a private Coral runtime workspace

**Files:**
- Modify: `orchestration/coral/materialize_task.py`
- Create: `orchestration/coral/runtime_layout.md`
- Create: `orchestration/coral/templates/agent_prompt.md`
- Create: `orchestration/coral/templates/session_note.md`
- Test: `tests/test_coral_orchestration.py`

- [ ] **Step 1: Write the failing test**

```python
from pathlib import Path
from orchestration.coral.materialize_task import build_runtime_tree


def test_runtime_tree_hides_visible_eval_assets(tmp_path):
    runtime_dir = build_runtime_tree(output_dir=tmp_path)
    assert (runtime_dir / "task.yaml").exists()
    assert (runtime_dir / "product").exists()
    assert (runtime_dir / "eval" / "grader.py").exists()
    assert not (runtime_dir / "product" / "orchestration" / "coral" / "eval").exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_coral_orchestration.py::test_runtime_tree_hides_visible_eval_assets -v`
Expected: FAIL because the runtime tree builder does not exist yet.

- [ ] **Step 3: Write minimal implementation**

```python
def build_runtime_tree(output_dir: Path) -> Path:
    runtime_dir = output_dir / "delirium-coral"
    product_dir = runtime_dir / "product"
    eval_dir = runtime_dir / "eval"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    product_dir.mkdir(parents=True, exist_ok=True)
    eval_dir.mkdir(parents=True, exist_ok=True)
    (runtime_dir / "task.yaml").write_text("task:\\n  name: delirium-ai\\n", encoding="utf-8")
    (eval_dir / "grader.py").write_text("class Grader: ...\\n", encoding="utf-8")
    return runtime_dir
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_coral_orchestration.py::test_runtime_tree_hides_visible_eval_assets -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add orchestration/coral tests/test_coral_orchestration.py
git commit -m "feat: materialize private coral runtime workspace"
```

### Task 3: Add deterministic grader and Delirium judge inputs

**Files:**
- Create: `orchestration/coral/eval/grader.py`
- Create: `orchestration/coral/eval/judge.py`
- Create: `orchestration/coral/eval/reference/README.md`
- Create: `orchestration/coral/eval/reference/canonical_docs.txt`
- Test: `tests/test_coral_orchestration.py`

- [ ] **Step 1: Write the failing test**

```python
from orchestration.coral.eval.judge import load_canonical_sources


def test_canonical_sources_include_behavior_and_mvp():
    refs = load_canonical_sources()
    assert "01_CAHIER_DES_CHARGES/CDC_COMPORTEMENTAL.md" in refs
    assert "05_ROADMAP/MVP_SPEC.md" in refs
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_coral_orchestration.py::test_canonical_sources_include_behavior_and_mvp -v`
Expected: FAIL because the judge module does not exist yet.

- [ ] **Step 3: Write minimal implementation**

```python
CANONICAL_SOURCES = [
    "01_CAHIER_DES_CHARGES/CDC_COMPORTEMENTAL.md",
    "03_ARCHITECTURE/ARCHITECTURE_HARNESS.md",
    "05_ROADMAP/MVP_SPEC.md",
    "06_TESTS/SCENARIOS_CRITIQUES.md",
]


def load_canonical_sources() -> list[str]:
    return CANONICAL_SOURCES[:]
```

```python
class Grader(TaskGrader):
    def grade(self):
        tests = self.run_program(["python", "-m", "pytest", "tests/test_behavior.py", "tests/test_adversarial.py", "-q"])
        if tests.returncode != 0:
            return self.fail("pytest gate failed")
        return self.score(1.0, "deterministic gate passed")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_coral_orchestration.py::test_canonical_sources_include_behavior_and_mvp -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add orchestration/coral tests/test_coral_orchestration.py
git commit -m "feat: add coral grader and judge inputs"
```

### Task 4: Add WSL and local launch scripts

**Files:**
- Create: `orchestration/coral/scripts/bootstrap_coral_ubuntu.sh`
- Create: `orchestration/coral/scripts/run_delirium_coral.sh`
- Create: `orchestration/coral/scripts/run_delirium_coral.ps1`
- Modify: `orchestration/coral/README.md`
- Test: `tests/test_coral_orchestration.py`

- [ ] **Step 1: Write the failing test**

```python
from pathlib import Path


def test_launch_scripts_exist_and_are_executable_targets():
    root = Path(__file__).resolve().parents[1]
    assert (root / "orchestration" / "coral" / "scripts" / "bootstrap_coral_ubuntu.sh").exists()
    assert (root / "orchestration" / "coral" / "scripts" / "run_delirium_coral.sh").exists()
    assert (root / "orchestration" / "coral" / "scripts" / "run_delirium_coral.ps1").exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_coral_orchestration.py::test_launch_scripts_exist_and_are_executable_targets -v`
Expected: FAIL because the scripts do not exist yet.

- [ ] **Step 3: Write minimal implementation**

```bash
#!/usr/bin/env bash
set -euo pipefail
python3 orchestration/coral/materialize_task.py
uv run coral start -c "${HOME}/.local/share/delirium-coral/task/task.yaml"
```

```powershell
python orchestration/coral/materialize_task.py
wsl.exe -d coral-ubuntu --cd ~ -- bash -lc "~/DELIRIUM.AI/orchestration/coral/scripts/run_delirium_coral.sh"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_coral_orchestration.py::test_launch_scripts_exist_and_are_executable_targets -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add orchestration/coral tests/test_coral_orchestration.py
git commit -m "feat: add coral launch scripts"
```

### Task 5: Verify the orchestration pack end to end

**Files:**
- Modify: `README.md`
- Modify: `ETAT_DU_PROJET.md`
- Modify: `orchestration/coral/README.md`
- Test: `tests/test_coral_orchestration.py`

- [ ] **Step 1: Write the verification checklist**

```text
1. The branch contains the orchestration pack under orchestration/coral/.
2. The runtime materializer creates task.yaml, eval/grader.py, and a product snapshot.
3. Coral config pins codex gpt-5.4 + xhigh.
4. Launch scripts target coral-ubuntu and document prerequisites.
5. Repo docs explain the branch intent without claiming the whole product is finished.
```

- [ ] **Step 2: Run the local verification commands**

Run: `python -m pytest tests/test_coral_orchestration.py -q`
Expected: PASS

Run: `python orchestration/coral/materialize_task.py --output-dir .tmp/coral-check`
Expected: exit code 0 and generated `.tmp/coral-check/delirium-coral/task.yaml`

- [ ] **Step 3: Run repo baseline checks**

Run: `python -m pytest -q`
Expected: PASS or explicit live-test skips if no API key is configured.

- [ ] **Step 4: Update docs with exact status**

```markdown
## Coral Branch

This branch adds Coral orchestration for autonomous productization. It does not claim DELIRIUM.AI Phase 6 completion; it adds the execution substrate and judge harness for the Delirium Core milestone.
```

- [ ] **Step 5: Commit**

```bash
git add README.md ETAT_DU_PROJET.md orchestration/coral tests/test_coral_orchestration.py docs/superpowers/plans/2026-04-12-coral-orchestration.md
git commit -m "feat: add coral orchestration pack for delirium"
```

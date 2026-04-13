"""Hybrid deterministic + Codex judge for the DELIRIUM.AI Coral task."""

from __future__ import annotations

import importlib.util
import os
import subprocess
from pathlib import Path

from coral.grader import TaskGrader


def _load_judge_module():
    module_path = Path(__file__).with_name("judge.py")
    spec = importlib.util.spec_from_file_location("delirium_coral_judge", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load judge module from {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _tail(text: str, limit: int = 3000) -> str:
    return text[-limit:] if len(text) > limit else text


def _load_private_env(private_dir: str) -> dict[str, str]:
    env_path = Path(private_dir) / "eval" / "runtime.env"
    if not env_path.exists():
        return {}

    loaded: dict[str, str] = {}
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        loaded[key.strip()] = value.strip()
    return loaded


def _pytest_gate_score(output: str) -> tuple[float, str]:
    normalized = output.lower()
    if "failed" in normalized or "error" in normalized:
        return 0.0, "Pytest gate failed."
    if "skipped" in normalized and "passed" not in normalized:
        return 0.4, "Behavior tests were discovered but skipped; live API evidence is missing."
    return 0.7, "Behavior and adversarial pytest gate passed."


class Grader(TaskGrader):
    def evaluate(self):
        judge = _load_judge_module()
        runtime_env = dict(os.environ)
        runtime_env.update(_load_private_env(self.private_dir))
        pytest_targets = self.args.get(
            "pytest_targets",
            ["tests/test_behavior.py", "tests/test_adversarial.py"],
        )
        timeout = int(self.args.get("judge_timeout", 300))
        pytest_cmd = ["python3", "-m", "pytest", *pytest_targets, "-q"]
        pytest_result = subprocess.run(
            pytest_cmd,
            capture_output=True,
            text=True,
            cwd=self.codebase_path,
            timeout=self.timeout,
            env=runtime_env,
        )
        pytest_output = "\n".join(
            chunk for chunk in [pytest_result.stdout.strip(), pytest_result.stderr.strip()] if chunk
        )

        if pytest_result.returncode != 0:
            explanation = f"Pytest gate failed.\n\n{_tail(pytest_output)}"
            return self.fail(explanation, feedback=_tail(pytest_output, limit=5000))

        gate_score, gate_summary = _pytest_gate_score(pytest_output)
        judge_result = judge.run_codex_judge(
            Path(self.codebase_path),
            pytest_output,
            milestone=self.args.get("milestone", "Delirium Core"),
            model=self.args.get("judge_model", "gpt-5.4"),
            reasoning_effort=self.args.get("judge_reasoning_effort", "xhigh"),
            timeout=timeout,
        )

        if not judge_result:
            return self.score(
                gate_score,
                gate_summary,
                feedback=_tail(pytest_output, limit=5000),
            )

        judge_score = float(judge_result.get("score", 0.0))
        judge_summary = judge_result.get("summary", "").strip()
        risks = judge_result.get("risks", [])
        explanation = (
            f"{gate_summary} "
            f"LLM judge score={judge_score:.2f}. "
            f"{judge_summary}"
        ).strip()
        feedback_lines = [
            "Pytest output:",
            _tail(pytest_output, limit=3000),
            "",
            "Judge strengths:",
            *[f"- {item}" for item in judge_result.get("strengths", [])],
            "",
            "Judge risks:",
            *[f"- {item}" for item in risks],
        ]
        final_score = round((gate_score * 0.45) + (judge_score * 0.55), 4)
        return self.score(final_score, explanation, feedback="\n".join(feedback_lines).strip())

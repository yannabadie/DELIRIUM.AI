"""Helpers for the DELIRIUM.AI Coral LLM judge."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
SOURCES_PATH = BASE_DIR / "judge_sources.json"
RUBRIC_PATH = BASE_DIR / "judge_rubric.md"


def load_judge_config() -> dict:
    return json.loads(SOURCES_PATH.read_text(encoding="utf-8"))


def load_canonical_sources() -> list[str]:
    return list(load_judge_config()["canonical_sources"])


def load_non_goals() -> list[str]:
    return list(load_judge_config()["non_goals"])


def read_canonical_context(codebase_path: Path, *, max_chars: int = 2400) -> list[dict[str, str]]:
    contexts: list[dict[str, str]] = []
    for relative in load_canonical_sources():
        path = codebase_path / relative
        if not path.exists():
            contexts.append({"path": relative, "excerpt": "[missing]"})
            continue
        excerpt = path.read_text(encoding="utf-8")[:max_chars].strip()
        contexts.append({"path": relative, "excerpt": excerpt})
    return contexts


def summarize_tree(codebase_path: Path, *, limit: int = 80) -> str:
    lines: list[str] = []
    for path in sorted(codebase_path.rglob("*")):
        if len(lines) >= limit:
            break
        if path.is_dir():
            continue
        rel = path.relative_to(codebase_path)
        if ".git" in rel.parts or "__pycache__" in rel.parts:
            continue
        lines.append(str(rel))
    return "\n".join(lines)


def build_judge_prompt(
    codebase_path: Path,
    pytest_output: str,
    *,
    milestone: str | None = None,
) -> str:
    config = load_judge_config()
    milestone = milestone or config["milestone"]
    context_chunks = read_canonical_context(codebase_path)
    joined_context = "\n\n".join(
        f"## {item['path']}\n{item['excerpt']}" for item in context_chunks
    )
    rubric = RUBRIC_PATH.read_text(encoding="utf-8").strip()
    non_goals = "\n".join(f"- {item}" for item in config["non_goals"])
    tree = summarize_tree(codebase_path)

    return f"""You are the DELIRIUM.AI milestone judge.

Milestone: {milestone}

Return strict JSON with keys: score, summary, strengths, risks.
`score` must be a float between 0 and 1.

Rubric:
{rubric}

Non-goals:
{non_goals}

Pytest output:
{pytest_output}

Visible codebase tree:
{tree}

Canonical context:
{joined_context}
"""


def pytest_gate_score(output: str) -> tuple[float, str]:
    """Score the pytest gate result.

    Rules:
    - Any failed test or collection error → 0.0 (hard gate).
    - Passed tests present → 0.7 base.
      If adversarial tests are skipped (no API key) that is expected and does
      not reduce the score, provided non-adversarial tests pass.
    - No passed tests at all (only skipped) → 0.4.
    """
    normalized = output.lower()
    if "error" in normalized or "failed" in normalized:
        return 0.0, "Pytest gate failed."
    if "passed" in normalized:
        if "skipped" in normalized:
            return 0.7, (
                "Deterministic pytest gate passed; live-API adversarial tests "
                "skipped (no API key - expected in offline evaluation)."
            )
        return 0.7, "All pytest suites passed."
    return 0.4, "Tests were discovered but all skipped; live API evidence is missing."


def extract_json_object(text: str) -> dict | None:
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return None


def run_codex_judge(
    codebase_path: Path,
    pytest_output: str,
    *,
    milestone: str | None = None,
    model: str = "gpt-5.4",
    reasoning_effort: str = "xhigh",
    timeout: int = 300,
) -> dict | None:
    codex_bin = shutil.which("codex")
    if not codex_bin:
        return None

    prompt = build_judge_prompt(codebase_path, pytest_output, milestone=milestone)
    cmd = [
        codex_bin,
        "exec",
        prompt,
        "--dangerously-bypass-approvals-and-sandbox",
        "--model",
        model,
        "-c",
        f"model_reasoning_effort={json.dumps(reasoning_effort)}",
    ]
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=codebase_path,
        timeout=timeout,
    )
    if result.returncode != 0:
        return None
    return extract_json_object(result.stdout)

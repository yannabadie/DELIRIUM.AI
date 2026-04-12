#!/usr/bin/env bash
set -euo pipefail

export PATH="$HOME/.local/bin:$PATH"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
CORAL_SRC_DIR="${CORAL_SRC_DIR:-$HOME/Coral}"
DELIRIUM_CORAL_HOME="${DELIRIUM_CORAL_HOME:-$HOME/.local/share/delirium-coral}"

if ! command -v uv >/dev/null 2>&1; then
  echo "uv is missing. Run bootstrap_coral_ubuntu.sh first." >&2
  exit 1
fi

if ! command -v codex >/dev/null 2>&1; then
  echo "codex CLI is missing in this distro." >&2
  exit 1
fi

if [ ! -d "$CORAL_SRC_DIR/.git" ]; then
  echo "Coral source not found at $CORAL_SRC_DIR. Run bootstrap_coral_ubuntu.sh first." >&2
  exit 1
fi

python3 "$REPO_ROOT/orchestration/coral/materialize_task.py" \
  --repo-root "$REPO_ROOT" \
  --output-dir "$DELIRIUM_CORAL_HOME"

TASK_PATH="$DELIRIUM_CORAL_HOME/delirium-coral/task.yaml"

cd "$CORAL_SRC_DIR"
uv run coral start -c "$TASK_PATH" "$@"

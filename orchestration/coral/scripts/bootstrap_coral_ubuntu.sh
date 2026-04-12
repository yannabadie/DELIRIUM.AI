#!/usr/bin/env bash
set -euo pipefail

export PATH="$HOME/.local/bin:$PATH"
CORAL_SRC_DIR="${CORAL_SRC_DIR:-$HOME/Coral}"

sudo apt-get update
sudo apt-get install -y git tmux python3 python3-pip python3-venv build-essential

if ! command -v uv >/dev/null 2>&1; then
  python3 -m pip install --user uv
fi

if [ ! -d "$CORAL_SRC_DIR/.git" ]; then
  git clone https://github.com/Human-Agent-Society/Coral.git "$CORAL_SRC_DIR"
else
  git -C "$CORAL_SRC_DIR" pull --ff-only
fi

cd "$CORAL_SRC_DIR"
uv sync

if ! command -v codex >/dev/null 2>&1; then
  cat >&2 <<'EOF'
codex CLI is not installed in this distro.
Install or copy your Codex CLI setup in coral-ubuntu before launching the task.
EOF
  exit 1
fi

cat <<EOF
Coral bootstrap complete.
Coral source: $CORAL_SRC_DIR
Next step:
  bash orchestration/coral/scripts/run_delirium_coral.sh
EOF

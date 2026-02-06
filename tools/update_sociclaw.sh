#!/usr/bin/env bash
set -euo pipefail

# One-command update/install script for end users.
#
# Usage:
#   bash <(curl -fsSL https://raw.githubusercontent.com/sociclaw/sociclaw/main/tools/update_sociclaw.sh)
#
# Optional env overrides:
#   SOCICLAW_SKILL_DIR="$HOME/.openclaw/skills/sociclaw"
#   SOCICLAW_REPO_URL="https://github.com/sociclaw/sociclaw.git"
#   SOCICLAW_BRANCH="main"
#   SOCICLAW_RUN_TESTS="0"

SKILL_DIR="${SOCICLAW_SKILL_DIR:-$HOME/.openclaw/skills/sociclaw}"
REPO_URL="${SOCICLAW_REPO_URL:-https://github.com/sociclaw/sociclaw.git}"
BRANCH="${SOCICLAW_BRANCH:-main}"
RUN_TESTS="${SOCICLAW_RUN_TESTS:-0}"

echo "[SociClaw] Target directory: $SKILL_DIR"
echo "[SociClaw] Repo: $REPO_URL (branch: $BRANCH)"

mkdir -p "$(dirname "$SKILL_DIR")"

if [[ -d "$SKILL_DIR/.git" ]]; then
  echo "[SociClaw] Existing install detected. Updating..."
  git -C "$SKILL_DIR" fetch origin --prune
  git -C "$SKILL_DIR" checkout "$BRANCH"
  git -C "$SKILL_DIR" pull --ff-only origin "$BRANCH"
else
  if [[ -e "$SKILL_DIR" && ! -d "$SKILL_DIR/.git" ]]; then
    echo "[SociClaw] ERROR: $SKILL_DIR exists but is not a git repo."
    echo "[SociClaw] Move/remove it, then run this script again."
    exit 1
  fi
  echo "[SociClaw] Fresh install..."
  git clone --branch "$BRANCH" --single-branch "$REPO_URL" "$SKILL_DIR"
fi

cd "$SKILL_DIR"

if [[ -x ".venv/bin/python" ]]; then
  PYTHON_BIN=".venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="python3"
elif command -v python >/dev/null 2>&1; then
  PYTHON_BIN="python"
else
  echo "[SociClaw] ERROR: Python not found."
  exit 1
fi

echo "[SociClaw] Using Python: $PYTHON_BIN"

if [[ "$PYTHON_BIN" != ".venv/bin/python" ]]; then
  if [[ ! -d ".venv" ]]; then
    echo "[SociClaw] Creating local venv..."
    "$PYTHON_BIN" -m venv .venv
  fi
  PYTHON_BIN=".venv/bin/python"
fi

echo "[SociClaw] Installing dependencies..."
"$PYTHON_BIN" -m pip install --upgrade pip >/dev/null
"$PYTHON_BIN" -m pip install -r requirements.txt

if [[ "$RUN_TESTS" == "1" ]]; then
  echo "[SociClaw] Running tests..."
  "$PYTHON_BIN" -m pytest -q
fi

echo "[SociClaw] Done."
echo "[SociClaw] Next: restart OpenClaw process and run /sociclaw"

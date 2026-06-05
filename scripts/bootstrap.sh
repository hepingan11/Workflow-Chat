#!/usr/bin/env bash
set -euo pipefail

REPO_URL="${WORKFLOW_CHAT_REPO_URL:-https://github.com/hepingan11/Guiwuli-Digital-Employee.git}"
BRANCH="${WORKFLOW_CHAT_BRANCH:-main}"
INSTALL_DIR="${WORKFLOW_CHAT_INSTALL_DIR:-$(pwd)/Guiwuli-Digital-Employee}"

require_command() {
  local name="$1"
  local hint="$2"
  if ! command -v "$name" >/dev/null 2>&1; then
    echo "Missing command: $name. $hint" >&2
    exit 1
  fi
}

echo
echo "Guiwuli Digital Employee bootstrap"
echo "Repo:    $REPO_URL"
echo "Branch:  $BRANCH"
echo "Install: $INSTALL_DIR"
echo

require_command git "Install Git first: https://git-scm.com/downloads"

if ! command -v python3 >/dev/null 2>&1 && ! command -v python >/dev/null 2>&1; then
  echo "Missing Python. Install Python 3.11+ first: https://www.python.org/downloads/" >&2
  exit 1
fi

if ! command -v npm >/dev/null 2>&1; then
  echo "Warning: npm not found. Web dependency installation will fail until Node.js is installed." >&2
fi

if [ -d "$INSTALL_DIR" ]; then
  if [ -d "$INSTALL_DIR/.git" ]; then
    echo "Existing repository found, updating..."
    git -C "$INSTALL_DIR" fetch origin "$BRANCH"
    git -C "$INSTALL_DIR" checkout "$BRANCH"
    git -C "$INSTALL_DIR" pull --ff-only origin "$BRANCH"
  else
    echo "Install directory exists but is not a Git repository: $INSTALL_DIR" >&2
    exit 1
  fi
else
  echo "Cloning repository..."
  git clone --branch "$BRANCH" "$REPO_URL" "$INSTALL_DIR"
fi

cd "$INSTALL_DIR"
chmod +x ./setup.sh
./setup.sh

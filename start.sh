#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

API_DIR="$PWD/apps/api"
WEB_DIR="$PWD/apps/web"
LOG_DIR="$PWD/.workflow-chat/logs"
WEB_LOG="$LOG_DIR/web-dev.log"
VENV_PYTHON="$API_DIR/.venv/bin/python"

mkdir -p "$LOG_DIR"

if [[ ! -x "$VENV_PYTHON" ]]; then
  if command -v python3 >/dev/null 2>&1; then
    PYTHON_CMD="python3"
  elif command -v python >/dev/null 2>&1; then
    PYTHON_CMD="python"
  else
    echo "Python 3.11+ is required." >&2
    exit 1
  fi

  echo "Creating API virtual environment..."
  "$PYTHON_CMD" -m venv "$API_DIR/.venv"
fi

echo "Installing API dependencies..."
"$VENV_PYTHON" -m pip install -e "$API_DIR"

if ! command -v npm >/dev/null 2>&1; then
  echo "npm was not found. Please install Node.js first." >&2
  exit 1
fi

if [[ ! -d "$WEB_DIR/node_modules" ]]; then
  echo "Installing Web dependencies..."
  (cd "$WEB_DIR" && npm install)
fi

: > "$WEB_LOG"

echo "Starting Web dev server in background..."
(cd "$WEB_DIR" && npm run dev > "$WEB_LOG" 2>&1) &
WEB_PID=$!

cleanup() {
  if kill -0 "$WEB_PID" >/dev/null 2>&1; then
    echo
    echo "Stopping Web dev server..."
    kill "$WEB_PID" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT INT TERM

echo "Web: http://127.0.0.1:3000"
echo "Web log: $WEB_LOG"
echo "API: http://127.0.0.1:8000"
echo "Backend logs are shown below. Press Ctrl+C to stop both servers."
echo

cd "$API_DIR"
"$VENV_PYTHON" -m uvicorn app.main:app --host 127.0.0.1 --port 8000

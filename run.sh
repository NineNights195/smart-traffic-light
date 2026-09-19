#!/usr/bin/env bash

set -Eeuo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"
VENV_DIR="$BACKEND_DIR/.venv"

for command_name in python3 pnpm; do
  if ! command -v "$command_name" >/dev/null 2>&1; then
    echo "Error: '$command_name' is required but was not found in PATH." >&2
    exit 1
  fi
done

if [[ ! -x "$VENV_DIR/bin/python" ]]; then
  echo "Creating Python virtual environment in backend/.venv..."
  python3 -m venv "$VENV_DIR"
fi

# Activating the environment keeps all Python commands and packages isolated to
# this project for the remainder of the script.
source "$VENV_DIR/bin/activate"

echo "Installing backend dependencies..."
python -m pip install -r "$BACKEND_DIR/requirements.txt"

echo "Installing frontend dependencies..."
(
  cd "$FRONTEND_DIR"
  pnpm install --frozen-lockfile
)

backend_pid=""
frontend_pid=""

cleanup() {
  trap - EXIT INT TERM

  echo
  echo "Stopping development servers..."

  if [[ -n "$backend_pid" ]]; then
    kill "$backend_pid" 2>/dev/null || true
  fi
  if [[ -n "$frontend_pid" ]]; then
    kill "$frontend_pid" 2>/dev/null || true
  fi

  wait "$backend_pid" 2>/dev/null || true
  wait "$frontend_pid" 2>/dev/null || true
}

trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

echo "Starting backend at http://127.0.0.1:8000..."
(
  cd "$BACKEND_DIR"
  exec python -m uvicorn app.api:app --reload --host 127.0.0.1 --port 8000
) &
backend_pid=$!

echo "Starting frontend at http://127.0.0.1:5173..."
(
  cd "$FRONTEND_DIR"
  exec pnpm run dev -- --host 127.0.0.1
) &
frontend_pid=$!

echo "Both servers are running. Press Ctrl+C to stop them."

# macOS still ships an older Bash without `wait -n`, so poll both processes.
# If either server exits, the EXIT trap stops the other one as well.
while kill -0 "$backend_pid" 2>/dev/null && kill -0 "$frontend_pid" 2>/dev/null; do
  sleep 1
done

exit_code=0
if ! kill -0 "$backend_pid" 2>/dev/null; then
  wait "$backend_pid" || exit_code=$?
fi
if ! kill -0 "$frontend_pid" 2>/dev/null; then
  wait "$frontend_pid" || exit_code=$?
fi

exit "$exit_code"

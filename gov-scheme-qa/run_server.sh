#!/usr/bin/env bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/gov-scheme-qa"
exec "$SCRIPT_DIR/gov-scheme-qa/.venv/bin/uvicorn" app.main:app --host 0.0.0.0 --port 8000 "$@"

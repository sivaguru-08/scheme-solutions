#!/usr/bin/env bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -d "$SCRIPT_DIR/gov-scheme-qa" ]; then
    TARGET_DIR="$SCRIPT_DIR/gov-scheme-qa"
else
    TARGET_DIR="$SCRIPT_DIR"
fi
cd "$TARGET_DIR"
exec "$TARGET_DIR/.venv/bin/uvicorn" app.main:app --host 0.0.0.0 --port 8000 "$@"

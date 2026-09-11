#!/usr/bin/env bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -d "$SCRIPT_DIR/gov-scheme-qa" ]; then
    TARGET_DIR="$SCRIPT_DIR/gov-scheme-qa"
else
    TARGET_DIR="$SCRIPT_DIR"
fi
cd "$TARGET_DIR"
export PYTHONPATH=.
exec "$TARGET_DIR/.venv/bin/pytest" tests/ -v "$@"

#!/usr/bin/env bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/gov-scheme-qa"
export PYTHONPATH=.
exec "$SCRIPT_DIR/gov-scheme-qa/.venv/bin/pytest" tests/ -v "$@"

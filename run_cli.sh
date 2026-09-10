#!/usr/bin/env bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/gov-scheme-qa"
exec "$SCRIPT_DIR/gov-scheme-qa/.venv/bin/python" "$SCRIPT_DIR/gov-scheme-qa/app/cli.py" "$@"

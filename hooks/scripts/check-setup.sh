#!/usr/bin/env bash
# Advisory only: config parsing and permissions belong to the shared Python code.
set -u
PLUGIN_DIR="${CLAUDE_PLUGIN_ROOT:-$(cd "$(dirname "$0")/../.." && pwd)}"
SETUP_SCRIPT="$PLUGIN_DIR/skills/watch/scripts/setup.py"
for interpreter in python3 python; do
  if command -v "$interpreter" >/dev/null 2>&1 && "$interpreter" -c 'import sys; sys.exit(sys.version_info < (3, 10))' >/dev/null 2>&1; then
    if "$interpreter" "$SETUP_SCRIPT" --check >/dev/null 2>&1; then
      # Fresh install: nudge the user into the wizard so the Gemini key question comes first.
      if ! grep -Eqs '^SETUP_COMPLETE="?true"?$' "$HOME/.config/watch/.env"; then
        echo '/watch is installed but not set up. Invoke the watch skill to finish setup; it starts by asking for a free Gemini API key.'
      fi
      exit 0
    fi
    echo '/watch: setup needs attention. Invoke the watch skill to check dependencies and configuration.'
    exit 0
  fi
done
echo '/watch: Python 3.10+ is needed. Install a working Python interpreter and invoke the watch skill.'
exit 0

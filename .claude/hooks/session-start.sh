#!/bin/bash
# SessionStart hook for Claude Code cloud sessions: make pytest and ruff work.
set -euo pipefail

# Only run in Claude Code cloud sessions; local developers follow README setup.
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

# Run in the background so the session starts immediately (up to 5 minutes for the install).
# Until it finishes, `.venv` may be missing or incomplete; re-run this script to wait for it.
echo '{"async": true, "asyncTimeout": 300000}'

cd "${CLAUDE_PROJECT_DIR:-$(pwd)}"

# Project virtualenv (reused when the container is cached).
if [ ! -x .venv/bin/python ]; then
  python3 -m venv .venv
fi
.venv/bin/python -m pip install --quiet --upgrade pip
.venv/bin/python -m pip install --quiet -r requirements-dev.txt

# Cloud images ship Chromium under /opt/pw-browsers; Playwright's own download is disabled there,
# so point Learn's renderer at the preinstalled browser instead of running `playwright install`.
chrome="$(ls -d /opt/pw-browsers/chromium-*/chrome-linux/chrome 2>/dev/null | sort -V | tail -n 1 || true)"

if [ -n "${CLAUDE_ENV_FILE:-}" ]; then
  {
    echo "export VIRTUAL_ENV=\"$PWD/.venv\""
    echo "export PATH=\"$PWD/.venv/bin:\$PATH\""
    if [ -n "$chrome" ]; then
      echo "export CHROMIUM_EXECUTABLE=\"$chrome\""
    fi
  } >> "$CLAUDE_ENV_FILE"
fi

echo "Learn session setup complete (python: $(.venv/bin/python --version 2>&1), chromium: ${chrome:-not found})" >&2

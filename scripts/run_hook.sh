#!/usr/bin/env bash
# run_hook.sh — Universal hook runner for ContextForge
# Usage: bash run_hook.sh <script_name.py>
# All hook commands use: bash "${CLAUDE_PLUGIN_ROOT}/scripts/run_hook.sh" <script>.py

set -euo pipefail

SCRIPT_NAME="${1:-}"
if [ -z "$SCRIPT_NAME" ]; then
    echo "Usage: run_hook.sh <script.py>" >&2
    exit 0
fi

# Resolve paths
PLUGIN_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROJECT_DIR="${CONTEXTFORGE_PROJECT_DIR:-$(pwd)}"
DATA_DIR="${CONTEXTFORGE_DATA_DIR:-${PROJECT_DIR}/.contextforge}"

# Export environment variables
export CONTEXTFORGE_PLUGIN_ROOT="$PLUGIN_ROOT"
export CONTEXTFORGE_PROJECT_DIR="$PROJECT_DIR"
export CONTEXTFORGE_DATA_DIR="$DATA_DIR"

# Detect platform and find venv Python
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
    VENV_PYTHON="${DATA_DIR}/venv/Scripts/python.exe"
else
    VENV_PYTHON="${DATA_DIR}/venv/bin/python3"
fi

# If no venv exists and this is session_start.py, trigger bootstrap
if [ ! -f "$VENV_PYTHON" ]; then
    if [ "$SCRIPT_NAME" = "session_start.py" ]; then
        # Find system Python
        if command -v python3 &>/dev/null; then
            SYS_PYTHON="python3"
        elif command -v python &>/dev/null; then
            SYS_PYTHON="python"
        else
            echo '{"error": "Python not found"}' >&2
            exit 0
        fi

        # Run bootstrap setup
        "$SYS_PYTHON" "${PLUGIN_ROOT}/scripts/setup.py" || {
            echo "Bootstrap failed" >&2
            exit 0
        }
    else
        # Not session_start and no venv — skip silently
        exit 0
    fi
fi

# Verify venv python exists after potential bootstrap
if [ ! -f "$VENV_PYTHON" ]; then
    exit 0
fi

# Execute the hook script, passing stdin through
SCRIPT_PATH="${PLUGIN_ROOT}/scripts/${SCRIPT_NAME}"
if [ ! -f "$SCRIPT_PATH" ]; then
    echo "Script not found: ${SCRIPT_NAME}" >&2
    exit 0
fi

# Use exec to pass stdin through to the Python script
exec "$VENV_PYTHON" "$SCRIPT_PATH"

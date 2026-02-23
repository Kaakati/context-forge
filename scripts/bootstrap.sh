#!/usr/bin/env bash
# bootstrap.sh — Manual bootstrap for ContextForge
# Usage: bash scripts/bootstrap.sh

set -euo pipefail

PLUGIN_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROJECT_DIR="${CONTEXTFORGE_PROJECT_DIR:-$(pwd)}"

export CONTEXTFORGE_PLUGIN_ROOT="$PLUGIN_ROOT"
export CONTEXTFORGE_PROJECT_DIR="$PROJECT_DIR"
export CONTEXTFORGE_DATA_DIR="${PROJECT_DIR}/.contextforge"

# Find system Python
if command -v python3 &>/dev/null; then
    SYS_PYTHON="python3"
elif command -v python &>/dev/null; then
    SYS_PYTHON="python"
else
    echo "Error: Python 3.10+ is required but not found." >&2
    exit 1
fi

echo "ContextForge Bootstrap"
echo "====================="
echo "Plugin root: $PLUGIN_ROOT"
echo "Project dir: $PROJECT_DIR"
echo "Data dir:    $CONTEXTFORGE_DATA_DIR"
echo ""

"$SYS_PYTHON" "${PLUGIN_ROOT}/scripts/setup.py"
echo ""
echo "Bootstrap complete. ContextForge is ready."

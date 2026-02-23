"""Shared test fixtures for ContextForge tests."""

import sys
from pathlib import Path

# Ensure scripts/lib is importable from all test files
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

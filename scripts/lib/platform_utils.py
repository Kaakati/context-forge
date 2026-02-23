"""Cross-platform utilities for ContextForge.

Provides helpers for locating project directories, data directories,
virtual environment paths, and safe path validation. All paths use
pathlib.Path for cross-platform compatibility.
"""

import logging
import os
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


def get_project_dir() -> Path:
    """Return the project root directory.

    Uses the CONTEXTFORGE_PROJECT_DIR environment variable if set,
    otherwise falls back to the current working directory.
    """
    env_val = os.environ.get("CONTEXTFORGE_PROJECT_DIR")
    if env_val:
        return Path(env_val).resolve()
    return Path.cwd().resolve()


def get_data_dir() -> Path:
    """Return the ContextForge data directory.

    Uses the CONTEXTFORGE_DATA_DIR environment variable if set,
    otherwise falls back to {project_dir}/.contextforge.
    """
    env_val = os.environ.get("CONTEXTFORGE_DATA_DIR")
    if env_val:
        return Path(env_val).resolve()
    return get_project_dir() / ".contextforge"


def get_plugin_root() -> Path:
    """Return the ContextForge plugin root directory.

    Uses the CONTEXTFORGE_PLUGIN_ROOT environment variable.
    Raises ValueError if the variable is not set.
    """
    env_val = os.environ.get("CONTEXTFORGE_PLUGIN_ROOT")
    if env_val:
        return Path(env_val).resolve()
    raise ValueError(
        "CONTEXTFORGE_PLUGIN_ROOT environment variable is not set. "
        "This should be configured by the plugin hook scripts."
    )


def get_venv_python() -> Path:
    """Return the path to the Python executable inside the venv.

    On Windows, returns {data_dir}/venv/Scripts/python.exe.
    On Unix (macOS/Linux), returns {data_dir}/venv/bin/python3.
    """
    data_dir = get_data_dir()
    if sys.platform == "win32":
        return data_dir / "venv" / "Scripts" / "python.exe"
    else:
        return data_dir / "venv" / "bin" / "python3"


def ensure_data_dir() -> Path:
    """Create the .contextforge/ data directory and required subdirectories.

    Creates:
        - {data_dir}/
        - {data_dir}/models/

    Returns the data directory path.
    """
    data_dir = get_data_dir()
    try:
        data_dir.mkdir(parents=True, exist_ok=True)
        (data_dir / "models").mkdir(parents=True, exist_ok=True)
        logger.debug("Ensured data directory exists at: %s", data_dir)
    except OSError as exc:
        logger.error("Failed to create data directory %s: %s", data_dir, exc)
        raise
    return data_dir


def is_safe_path(base_dir: Path, target_path: Path) -> bool:
    """Check whether target_path is safely contained within base_dir.

    Prevents path traversal attacks by resolving both paths and verifying
    that the target is a child of the base directory.

    Args:
        base_dir: The allowed base directory.
        target_path: The path to validate.

    Returns:
        True if target_path is inside base_dir, False otherwise.
    """
    try:
        resolved_base = Path(base_dir).resolve()
        resolved_target = Path(target_path).resolve()
        # Check that the target starts with the base directory
        resolved_target.relative_to(resolved_base)
        return True
    except ValueError:
        logger.warning(
            "Path traversal detected: %s is not inside %s",
            target_path,
            base_dir,
        )
        return False

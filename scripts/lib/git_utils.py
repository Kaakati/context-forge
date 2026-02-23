"""Git operations for ContextForge.

Provides helpers for running git commands, tracking changed files,
and persisting index watermarks (the last-indexed commit hash).
"""

import json
import logging
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def run_git(args: List[str], cwd: Optional[Path] = None) -> Optional[str]:
    """Run a git command and return its stdout.

    Args:
        args: Arguments to pass after ``git`` (e.g. ``["status"]``).
        cwd: Working directory for the git command. If None, uses the
            current working directory.

    Returns:
        The stripped stdout string on success, or None on error.
    """
    cmd = ["git"] + args
    try:
        result = subprocess.run(
            cmd,
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            logger.warning(
                "git %s failed (rc=%d): %s",
                " ".join(args),
                result.returncode,
                result.stderr.strip(),
            )
            return None
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        logger.error("git %s timed out after 30s", " ".join(args))
        return None
    except FileNotFoundError:
        logger.error("git executable not found on PATH")
        return None
    except OSError as exc:
        logger.error("Failed to run git %s: %s", " ".join(args), exc)
        return None


def get_current_commit(cwd: Optional[Path] = None) -> Optional[str]:
    """Return the current HEAD commit hash, or None if unavailable."""
    return run_git(["rev-parse", "HEAD"], cwd=cwd)


def get_changed_files(
    since_commit: str, cwd: Optional[Path] = None
) -> Dict[str, List[str]]:
    """Get files changed between a commit and HEAD.

    Args:
        since_commit: The commit hash to diff from.
        cwd: Working directory for the git command.

    Returns:
        A dict with keys ``"modified"`` (includes added files) and
        ``"deleted"``, each containing a list of file path strings.
    """
    result: Dict[str, List[str]] = {"modified": [], "deleted": []}

    output = run_git(["diff", "--name-status", since_commit, "HEAD"], cwd=cwd)
    if output is None:
        return result

    for line in output.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        status = parts[0].strip()
        if status.startswith("D"):
            result["deleted"].append(parts[1].strip())
        elif status.startswith("R") or status.startswith("C"):
            # Rename/copy: old_path is deleted, new_path is modified
            if len(parts) >= 3:
                result["deleted"].append(parts[1].strip())
                result["modified"].append(parts[2].strip())
        else:
            # A (added), M (modified), etc.
            result["modified"].append(parts[1].strip())

    logger.debug(
        "Changed files since %s: %d modified, %d deleted",
        since_commit[:8],
        len(result["modified"]),
        len(result["deleted"]),
    )
    return result


def load_watermark(data_dir: Path) -> Dict[str, Any]:
    """Load the index watermark (last indexed commit).

    Args:
        data_dir: Path to the .contextforge data directory.

    Returns:
        A dict with at least a ``"commit"`` key, or an empty dict
        if the watermark file does not exist or is unreadable.
    """
    data_dir = Path(data_dir)
    watermark_path = data_dir / "index_state.json"

    if not watermark_path.is_file():
        logger.debug("No watermark file found at %s", watermark_path)
        return {}

    try:
        data = json.loads(watermark_path.read_text(encoding="utf-8"))
        logger.debug("Loaded watermark: commit=%s", data.get("commit", "?"))
        return data
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Failed to read watermark %s: %s", watermark_path, exc)
        return {}


def save_watermark(data_dir: Path, commit: str) -> None:
    """Save the index watermark with the given commit hash.

    Args:
        data_dir: Path to the .contextforge data directory.
        commit: The commit hash that has been indexed up to.
    """
    data_dir = Path(data_dir)
    watermark_path = data_dir / "index_state.json"

    data = {
        "commit": commit,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    try:
        data_dir.mkdir(parents=True, exist_ok=True)
        watermark_path.write_text(
            json.dumps(data, indent=2), encoding="utf-8"
        )
        logger.info("Saved watermark: commit=%s", commit[:8])
    except OSError as exc:
        logger.error("Failed to save watermark to %s: %s", watermark_path, exc)
        raise

"""Memory operations for ContextForge.

Provides functions for recording file changes, tracking coding
conventions, and generating memory summaries for session context.

All database operations use the db module's connection manager.
All path handling uses pathlib.Path for cross-platform compatibility.
"""

import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import db

logger = logging.getLogger(__name__)


def record_file_change(
    db_path: Path, file_path: str, session_id: Optional[str] = None
) -> None:
    """Record a file change event in the memories table.

    Args:
        db_path: Path to the memory SQLite database.
        file_path: The relative path of the changed file.
        session_id: Optional session identifier for grouping changes.
    """
    db_path = Path(db_path)
    try:
        with db.get_connection(db_path) as conn:
            conn.execute(
                "INSERT INTO memories (file_path, session_id, event_type) "
                "VALUES (?, ?, ?)",
                (file_path, session_id, "file_change"),
            )
        logger.debug("Recorded file change: %s", file_path)
    except Exception as exc:
        logger.error("Failed to record file change for %s: %s", file_path, exc)
        raise


def upsert_convention(
    db_path: Path,
    pattern_type: str,
    description: str,
    example: Optional[str] = None,
) -> None:
    """Insert or update a coding convention.

    If a convention with the same pattern_type and description already
    exists, increments its frequency counter and updates last_seen.
    Otherwise, inserts a new convention record.

    Args:
        db_path: Path to the memory SQLite database.
        pattern_type: The category of convention (e.g. ``"naming"``,
            ``"structure"``).
        description: A human-readable description of the convention.
        example: An optional code example demonstrating the convention.
    """
    db_path = Path(db_path)
    try:
        with db.get_connection(db_path) as conn:
            # Check for existing convention
            cursor = conn.execute(
                "SELECT id, frequency FROM conventions "
                "WHERE pattern_type = ? AND description = ?",
                (pattern_type, description),
            )
            row = cursor.fetchone()

            if row:
                convention_id, frequency = row
                conn.execute(
                    "UPDATE conventions "
                    "SET frequency = ?, last_seen = CURRENT_TIMESTAMP "
                    "WHERE id = ?",
                    (frequency + 1, convention_id),
                )
                logger.debug(
                    "Updated convention '%s' frequency to %d",
                    description[:50],
                    frequency + 1,
                )
            else:
                conn.execute(
                    "INSERT INTO conventions "
                    "(pattern_type, description, example) "
                    "VALUES (?, ?, ?)",
                    (pattern_type, description, example),
                )
                logger.debug("Inserted new convention: %s", description[:50])
    except Exception as exc:
        logger.error("Failed to upsert convention: %s", exc)
        raise


def get_active_conventions(
    db_path: Path, min_frequency: int = 3
) -> List[Dict[str, Any]]:
    """Retrieve conventions that have been observed frequently enough.

    Args:
        db_path: Path to the memory SQLite database.
        min_frequency: Minimum number of observations required.

    Returns:
        A list of convention dicts with keys: ``id``, ``pattern_type``,
        ``description``, ``example``, ``frequency``.
    """
    db_path = Path(db_path)
    try:
        with db.get_connection(db_path) as conn:
            conn.row_factory = _dict_factory
            cursor = conn.execute(
                "SELECT id, pattern_type, description, example, frequency "
                "FROM conventions "
                "WHERE frequency >= ? "
                "ORDER BY frequency DESC",
                (min_frequency,),
            )
            rows = cursor.fetchall()
            logger.debug(
                "Found %d active conventions (min_frequency=%d)",
                len(rows),
                min_frequency,
            )
            return rows
    except Exception as exc:
        logger.error("Failed to fetch active conventions: %s", exc)
        return []


def get_recent_files(
    db_path: Path, days: int = 14, limit: int = 20
) -> List[str]:
    """Get recently modified file paths from the memories table.

    Args:
        db_path: Path to the memory SQLite database.
        days: Look back this many days from now.
        limit: Maximum number of file paths to return.

    Returns:
        A list of distinct file path strings, ordered by most recent
        change first.
    """
    db_path = Path(db_path)
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    cutoff_str = cutoff.strftime("%Y-%m-%d %H:%M:%S")

    try:
        with db.get_connection(db_path) as conn:
            cursor = conn.execute(
                "SELECT file_path, MAX(created_at) AS last_change "
                "FROM memories "
                "WHERE created_at >= ? "
                "GROUP BY file_path "
                "ORDER BY last_change DESC "
                "LIMIT ?",
                (cutoff_str, limit),
            )
            rows = cursor.fetchall()
            files = [row[0] for row in rows]
            logger.debug("Found %d recently modified files", len(files))
            return files
    except Exception as exc:
        logger.error("Failed to fetch recent files: %s", exc)
        return []


def generate_memory_summary(
    db_path: Path, config: Optional[Dict[str, Any]] = None
) -> str:
    """Generate a formatted memory summary for session context.

    Produces a string with two sections:
        1. ESTABLISHED CONVENTIONS -- patterns observed frequently enough
        2. RECENTLY MODIFIED FILES -- files changed in the last N days

    Args:
        db_path: Path to the memory SQLite database.
        config: Optional configuration dict. Uses ``memory`` section
            keys ``convention_threshold`` and ``decay_days``.

    Returns:
        A formatted multi-line summary string.
    """
    min_frequency = 3
    days = 14

    if config and "memory" in config:
        min_frequency = config["memory"].get("convention_threshold", min_frequency)
        days = config["memory"].get("decay_days", days)

    parts: List[str] = []

    # Conventions section
    conventions = get_active_conventions(db_path, min_frequency=min_frequency)
    parts.append("## ESTABLISHED CONVENTIONS")
    if conventions:
        for conv in conventions:
            line = f"- [{conv['pattern_type']}] {conv['description']}"
            if conv.get("example"):
                line += f" (e.g. `{conv['example']}`)"
            line += f" [seen {conv['frequency']}x]"
            parts.append(line)
    else:
        parts.append("- No established conventions yet.")

    parts.append("")

    # Recent files section
    recent_files = get_recent_files(db_path, days=days)
    parts.append("## RECENTLY MODIFIED FILES")
    if recent_files:
        for fp in recent_files:
            parts.append(f"- {fp}")
    else:
        parts.append("- No recent file changes recorded.")

    summary = "\n".join(parts)
    logger.debug("Generated memory summary: %d chars", len(summary))
    return summary


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _dict_factory(cursor, row):
    """Convert sqlite3 rows to dicts using cursor description."""
    return {
        col[0]: row[idx]
        for idx, col in enumerate(cursor.description)
    }

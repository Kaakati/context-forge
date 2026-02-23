#!/usr/bin/env python3
"""ContextForge memory forget helper.

Safely deletes conventions matching a pattern using parameterized queries.
Called from the /contextforge:context-memory forget command.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.platform_utils import get_data_dir
from lib.db import get_connection


def main():
    """Delete conventions matching a pattern from stdin args."""
    try:
        # Read stdin — may contain JSON or plain text pattern
        stdin_data = sys.stdin.read().strip()
        pattern = ""

        # Try parsing as JSON first (hook input format)
        try:
            data = json.loads(stdin_data)
            pattern = data.get("pattern", data.get("arguments", ""))
        except (json.JSONDecodeError, ValueError):
            pattern = stdin_data

        # Strip "forget " prefix if present
        if pattern.lower().startswith("forget "):
            pattern = pattern[7:]
        pattern = pattern.strip()

        if not pattern:
            print("No pattern specified. Usage: context-memory forget <pattern>")
            return

        data_dir = get_data_dir()
        db_path = data_dir / "memory.db"

        if not db_path.exists():
            print("Memory database does not exist yet. Nothing to forget.")
            return

        # Use parameterized query to prevent SQL injection
        with get_connection(db_path) as conn:
            cursor = conn.execute(
                "SELECT id, pattern_type, description, frequency FROM conventions "
                "WHERE pattern_type LIKE ?",
                (f"%{pattern}%",),
            )
            matches = cursor.fetchall()

            if not matches:
                print(f"No conventions found matching '{pattern}'.")
                return

            # Delete matching conventions
            conn.execute(
                "DELETE FROM conventions WHERE pattern_type LIKE ?",
                (f"%{pattern}%",),
            )

            print(f"Removed {len(matches)} convention(s) matching '{pattern}':")
            for row in matches:
                print(f"  - [{row[1]}] {row[2]} (was seen {row[3]}x)")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""ContextForge PreCompact hook — Phase 2 stub.

Will save session context before compaction in a future release.
Currently reads stdin and exits cleanly.
"""

import json
import sys


def main():
    """Read stdin and exit cleanly."""
    try:
        stdin_data = sys.stdin.read()
        # Parse but don't act on it yet — Phase 2
        try:
            hook_input = json.loads(stdin_data) if stdin_data.strip() else {}
        except json.JSONDecodeError:
            pass
    except Exception:
        pass

    # Phase 2: will save session summary, active conventions, and working context
    sys.exit(0)


if __name__ == "__main__":
    main()

---
name: context-memory
description: Manage ContextForge persistent memory — list, clear, or forget conventions
argument-hint: "[list|clear|forget <pattern>]"
allowed-tools: Bash
---

Manage the ContextForge persistent memory database. This command supports the following subcommands:

**Arguments:** $ARGUMENTS

## Subcommands

### `list` (default if no arguments)
List all stored conventions and recent file change history.

Run:
```bash
bash "${CLAUDE_PLUGIN_ROOT}/scripts/run_hook.sh" context_status_cmd.py
```
Show the Memory Database section of the output to the user.

### `clear`
Clear ALL conventions and file change history from the memory database.

Delete the memory database file:
```bash
rm -f "${CONTEXTFORGE_PROJECT_DIR:-.}/.contextforge/memory.db"
```
Then tell the user that the memory database has been cleared and will be rebuilt as they work.

### `forget <pattern>`
Remove specific conventions matching the given pattern type.

Use the Python helper to safely delete matching conventions (avoids SQL injection). Extract the pattern from `$ARGUMENTS` (strip the `forget ` prefix) and pipe it as JSON:
```bash
echo '{"pattern":"EXTRACTED_PATTERN"}' | bash "${CLAUDE_PLUGIN_ROOT}/scripts/run_hook.sh" memory_forget.py
```
Replace `EXTRACTED_PATTERN` with the actual pattern the user provided after `forget`. Tell the user which conventions were removed. If the pattern doesn't match anything, inform them.

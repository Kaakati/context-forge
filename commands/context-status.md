---
name: context-status
description: Show ContextForge indexing status, file counts, conventions, and health
allowed-tools: Bash
---

Run the ContextForge status command to display the current state of the codebase index, knowledge graph, memory database, and virtual environment.

Execute this command:
```bash
bash "${CLAUDE_PLUGIN_ROOT}/scripts/run_hook.sh" context_status_cmd.py
```

Display the output to the user. If there are any errors or missing components, suggest running `/contextforge:context-rebuild` to re-index.

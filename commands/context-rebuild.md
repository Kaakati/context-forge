---
name: context-rebuild
description: Force a full rebuild of the ContextForge codebase index and graph
allowed-tools: Bash
---

Force a complete rebuild of the ContextForge index by deleting existing index data and re-running the session start hook.

Steps to perform:
1. Delete the following files if they exist in the `.contextforge/` directory:
   - `index_state.json` (git watermark)
   - `embeddings.db` (code chunk embeddings)
   - `graph.json` (knowledge graph)

```bash
rm -f "${CONTEXTFORGE_PROJECT_DIR:-.}/.contextforge/index_state.json" "${CONTEXTFORGE_PROJECT_DIR:-.}/.contextforge/embeddings.db" "${CONTEXTFORGE_PROJECT_DIR:-.}/.contextforge/graph.json"
```

2. Run the session start hook to perform a full re-index:
```bash
echo '{}' | bash "${CLAUDE_PLUGIN_ROOT}/scripts/run_hook.sh" session_start.py
```

3. Report the results to the user, including how many files were indexed and any errors encountered.

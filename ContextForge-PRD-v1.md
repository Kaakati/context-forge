# PRODUCT REQUIREMENTS DOCUMENT

# ContextForge

## Context-Aware Intelligence Plugin for Claude Code

**Version 1.0 | February 2026 | Manifest Solutions | Confidential**

---

## Document Information

- **Document Title:** ContextForge — Product Requirements Document
- **Version:** 1.0
- **Status:** Final Draft
- **Author:** Mohamad — CTO & Founder, Manifest Solutions
- **Date:** February 23, 2026
- **Classification:** Internal / Investor Use Only

---

## 1. Executive Summary

### 1.1 Vision Statement

ContextForge is a Claude Code plugin that transforms stateless agentic coding sessions into context-aware, learning systems. It automatically indexes the codebase, retrieves relevant context for every prompt, captures coding patterns from every edit, and maintains persistent memory that evolves as the project grows — all through Claude Code's native hooks and plugin architecture.

The plugin requires zero configuration from the user. Install it, and Claude Code immediately becomes aware of your codebase structure, conventions, recent changes, and established patterns. Context is injected deterministically through hooks — it fires every time, not when the LLM decides to look things up.

### 1.2 Problem Statement

Agentic coders — Claude Code, Cursor, Windsurf, Devin — suffer from **context loss** at three levels:

**Codebase context** — The agent doesn't know your architecture, conventions, existing patterns, or how modules relate. It generates code that works in isolation but breaks the system. It recreates utilities that already exist. It follows conventions from its training data instead of your project's conventions.

**Session context** — The agent forgets what it did three steps ago. Each task executes in near-isolation, leading to inconsistencies across files written in the same session. When context windows compact, critical decisions are lost.

**Historical context** — The agent has no memory across sessions. Every session starts from zero. Patterns established over weeks of development are invisible. The team's accumulated decisions — "we use service objects," "we migrated from Devise to Rodauth," "background jobs go through Sidekiq" — must be re-communicated every time.

Current solutions are manual. CLAUDE.md files require hand-curation and go stale. Skills provide static instructions but don't adapt. MCP servers connect to external services but don't understand the codebase itself. No existing tool provides automatic, reactive, self-maintaining codebase intelligence for Claude Code.

### 1.3 Solution Overview

ContextForge is a Claude Code plugin that delivers three integrated systems through six hook events:

**Knowledge Graph** — Structural index of the codebase (models, services, associations, routes, tests, dependencies) built incrementally using git diffs. Updated every session, never stale. Injected as a compact architectural summary at session start.

**RAG Retrieval** — Semantic search over embedded code chunks. Intercepts every user prompt, finds the most relevant existing code, and injects it as context before Claude starts thinking. Real-time updates: when Claude writes a file during a session, the index updates immediately.

**Persistent Memory** — Cross-session learning from coding patterns. Captures conventions from every file write, validates them against the current codebase, decays stale patterns, and surfaces only validated, high-frequency conventions. Self-correcting: when the team refactors, memory converges to the new patterns automatically.

### 1.4 Why a Claude Code Plugin

Claude Code's plugin system is the ideal delivery mechanism for three reasons:

**Hooks are deterministic.** Unlike prompt-based suggestions, hooks fire every time at specific lifecycle events. Context retrieval always happens before Claude thinks. Pattern capture always happens after every edit. Memory always loads at session start. The agent doesn't need to remember to search — the hooks ensure the right context is always there.

**Plugins are distributable.** A single `plugin install` command gives any developer the full system. No manual configuration of settings.json, no copying hook scripts between projects. Version-controlled, team-shareable, marketplace-ready.

**Plugins are composable.** ContextForge hooks run alongside the user's existing hooks, skills, and MCP servers. It doesn't replace anything — it augments everything.

### 1.5 Target Users

**Solo Developers** — Using Claude Code on personal projects. Get immediate value from codebase awareness and convention tracking without any setup.

**Development Teams** — Using Claude Code across a shared codebase. The plugin ensures every team member's Claude Code sessions reflect the same architecture, conventions, and recent changes. Install once in the project's plugin config; every team member benefits.

**Enterprise Engineering Orgs** — Managing multiple repositories with Claude Code. ContextForge provides consistent context quality across all agentic coding, reducing the "lottery" of whether the agent happens to understand the codebase.

---

## 2. Plugin Architecture

### 2.1 Plugin Structure

ContextForge follows the standard Claude Code plugin layout:

```
contextforge/
├── .claude-plugin/
│   └── plugin.json              # Plugin manifest
├── commands/
│   ├── context-status.md        # /context-status — show index health
│   ├── context-rebuild.md       # /context-rebuild — force full re-index
│   └── context-memory.md        # /context-memory — view/manage memories
├── skills/
│   └── contextforge/
│       └── SKILL.md             # Skill: tells Claude how to leverage context
├── hooks/
│   └── hooks.json               # Hook event configuration
├── scripts/
│   ├── session_start.py         # SessionStart: incremental index + load memory
│   ├── rag_retrieve.py          # UserPromptSubmit: semantic retrieval
│   ├── memory_capture.py        # PostToolUse (Write|Edit): capture patterns
│   ├── realtime_reindex.py      # PostToolUse (Write|Edit): update embeddings
│   ├── pre_compact_save.py      # PreCompact: persist decisions before compaction
│   ├── stop_verify.py           # Stop: verify context was addressed
│   ├── lib/
│   │   ├── indexer.py           # Codebase parsing and chunking engine
│   │   ├── embedder.py          # Embedding abstraction (local + API)
│   │   ├── graph.py             # Knowledge graph builder
│   │   ├── memory_store.py      # SQLite memory read/write operations
│   │   ├── decay.py             # Memory validation, decay, and pruning
│   │   └── git_utils.py         # Git diff, file change detection
│   └── setup.py                 # One-time dependency bootstrap
├── config/
│   └── defaults.json            # Default configuration (thresholds, limits)
├── LICENSE
├── README.md
└── CHANGELOG.md
```

### 2.2 Plugin Manifest

```json
{
  "name": "contextforge",
  "version": "1.0.0",
  "description": "Context-aware intelligence for Claude Code. Automatic codebase indexing, semantic RAG retrieval, and persistent cross-session memory.",
  "author": {
    "name": "Manifest Solutions",
    "url": "https://github.com/manifest-solutions"
  },
  "homepage": "https://github.com/manifest-solutions/contextforge",
  "repository": "https://github.com/manifest-solutions/contextforge",
  "license": "MIT",
  "keywords": [
    "context-engineering",
    "rag",
    "knowledge-graph",
    "memory",
    "codebase-awareness",
    "agentic-coding"
  ]
}
```

### 2.3 Hook Configuration

The core of the plugin. Six hooks covering the full lifecycle:

```json
{
  "description": "ContextForge — Context-aware intelligence for Claude Code",
  "hooks": {
    "SessionStart": [
      {
        "matcher": "startup|resume",
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/scripts/session_start.py",
            "timeout": 45
          }
        ]
      }
    ],
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/scripts/rag_retrieve.py",
            "timeout": 15
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/scripts/memory_capture.py",
            "timeout": 10
          },
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/scripts/realtime_reindex.py",
            "timeout": 10
          }
        ]
      }
    ],
    "PreCompact": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/scripts/pre_compact_save.py",
            "timeout": 15
          }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          {
            "type": "prompt",
            "prompt": "Review the session transcript. Were there any architectural decisions, new conventions, or pattern preferences expressed by the user that should be remembered? If yes, respond with {\"decision\": \"approve\", \"reason\": \"No additional capture needed\"} or {\"decision\": \"block\", \"reason\": \"User established a new convention: [describe it]. Capture this before stopping.\"}",
            "timeout": 10
          }
        ]
      }
    ]
  }
}
```

---

## 3. System Design: Three Engines

### 3.1 Knowledge Graph Engine

**Purpose:** Maintain a structural understanding of the codebase — what exists, how it connects, and what changed recently. Injected as a compact summary at session start so Claude understands the architecture before writing any code.

**Data captured per file:**

- File path and type (model, service, controller, test, migration, config)
- Class/module names and inheritance hierarchy
- Method signatures with parameters
- Associations (belongs_to, has_many, etc. for ORM models)
- Dependencies (requires, imports, includes)
- Route definitions
- Database schema (columns, types, indexes from schema.rb or migrations)
- Test file mappings (source → test file relationships)

**Storage:** `.contextforge/graph.json` — a JSON adjacency list in the project's `.contextforge/` directory (gitignored). Nodes are files/classes/methods. Edges are typed relationships (calls, inherits, belongs_to, tests, routes_to).

**Indexing strategy:**

- **First session:** Full codebase scan. Parse all supported files. Build complete graph. Store current git commit hash as watermark.
- **Subsequent sessions:** `git diff --name-only` between stored watermark and HEAD plus uncommitted changes. Only re-parse changed/added files. Remove deleted files from graph.
- **During session:** PostToolUse hook on Write|Edit triggers incremental graph update for the specific file Claude just modified.

**Context injection:** The graph is summarized into a ~200–400 token architectural overview injected via SessionStart `additionalContext`. The summary includes: model count and names, service count and patterns, auth approach, database type, queue/async patterns, key conventions detected, and files changed since last session.

**Supported languages (MVP):** Ruby, Python, JavaScript/TypeScript, Go, Rust. Language-specific parsers via Tree-sitter with fallback to regex-based extraction.

### 3.2 RAG Retrieval Engine

**Purpose:** For every user prompt, find and inject the most relevant existing code so Claude follows established patterns instead of guessing.

**Embedding strategy:**

- **Chunking:** Files split at semantic boundaries — class/module/function definitions for code, heading boundaries for documentation. Target chunk size: 256–512 tokens. Overlap: 50 tokens at boundaries to preserve context.
- **Embedding model (local, default):** `all-MiniLM-L6-v2` via sentence-transformers. 384-dimension vectors. ~50ms per chunk. No API calls, no cost, works offline. Model cached in `.contextforge/models/`.
- **Embedding model (API, optional):** Voyage Code 3 or OpenAI `text-embedding-3-small` for higher quality. Configured via environment variable `CONTEXTFORGE_EMBEDDING_API`. Falls back to local if unavailable.

**Storage:** SQLite database at `.contextforge/embeddings.db`. Schema:

- `code_chunks` table: id (TEXT PK), file_path (TEXT), chunk_content (TEXT), embedding (BLOB), chunk_hash (TEXT), language (TEXT), chunk_type (TEXT — class/function/method/block/doc), indexed_at (TEXT)
- Index on `file_path` for fast per-file deletion during re-indexing

**Retrieval flow (UserPromptSubmit hook):**

1. Receive user prompt via stdin JSON
2. Embed the prompt using the same model
3. Cosine similarity search against all chunks
4. Filter by relevance threshold (configurable, default 0.3)
5. Take top 5 results
6. Query knowledge graph for related files (graph neighbors of retrieved files)
7. Assemble context: retrieved code chunks + related file list
8. Return as `additionalContext` via JSON stdout (≤ 2000 tokens)

**Staleness prevention:**

- PostToolUse hook on Write|Edit immediately re-embeds the modified file
- Chunks reference file_path — orphaned chunks (deleted files) are pruned at session start
- Chunk hashes detect unchanged content to skip unnecessary re-embedding

### 3.3 Persistent Memory Engine

**Purpose:** Learn coding patterns across sessions. Remember what the team does, not just what the codebase contains. Self-correcting — stale patterns decay and eventually disappear.

**What gets captured (PostToolUse on Write|Edit):**

- **File change records** — Which files were written/edited, when, in which session. Recent activity context.
- **Convention observations** — Extracted patterns from the content of written files. Examples: "Services use .call interface," "Models use UUID primary keys," "Tests use FactoryBot," "Migrations include rollback," "Controllers use before_action for auth."
- **Architectural decisions** — Captured from PreCompact (extracted from transcript before compaction) and Stop hooks (prompt-based detection of expressed preferences).

**Storage:** SQLite database at `.contextforge/memory.db`. Two tables:

`memories` table — Raw event log:
- id (TEXT PK), timestamp (TEXT), category (TEXT — file_change/decision/preference), file_path (TEXT), pattern (TEXT), context (TEXT, truncated to 500 chars), session_id (TEXT)

`conventions` table — Aggregated patterns:
- id (TEXT PK), pattern_type (TEXT — service_pattern/model_convention/test_pattern/db_pattern/auth_pattern/deploy_pattern), description (TEXT), example (TEXT), frequency (INTEGER), first_seen (TEXT), last_seen (TEXT)

**Convention extraction rules (MVP):**

These are heuristic pattern detectors that run on file content after every Write/Edit. Each detector produces a convention observation with type, description, and the file as example.

- **Service pattern** — File in `app/services/` or `services/` containing `def self.call` or `def call`
- **Model associations** — File in `app/models/` or `models/` containing `belongs_to`, `has_many`, `has_one`
- **Model validations** — File in `app/models/` containing `validates` or `validate`
- **Scope usage** — File containing `scope :` pattern
- **Test factories** — File in `spec/` or `test/` containing `FactoryBot` or `factory :`
- **UUID keys** — Migration containing `uuid` type reference
- **Auth patterns** — File containing `Devise`, `Rodauth`, `authenticate`, `current_user`
- **Background jobs** — File in `app/jobs/` or containing `Sidekiq`, `ActiveJob`, `perform_async`
- **Linting/formatting** — Presence of `.rubocop.yml`, `.eslintrc`, `.prettierrc`
- **API patterns** — Controllers in `app/controllers/api/` or containing `render json:`

**Memory decay system:**

Three mechanisms prevent stale memories from polluting context:

1. **File existence validation (SessionStart)** — Conventions whose example file no longer exists have their frequency halved. At frequency 0, they are deleted.
2. **Time decay (SessionStart)** — Conventions not seen in the last 14 days lose 1 frequency point per session. High-frequency conventions survive longer; low-frequency ones decay quickly.
3. **Age pruning (SessionStart)** — Raw file_change memories older than 30 days are deleted. They have served their purpose as input for convention aggregation.

**Memory injection (SessionStart):** Only conventions with frequency ≥ 3 are injected into context. Each includes a recency indicator ("active" if seen in last 3 days, otherwise "Xd ago"). Recently modified files (last 7 days, validated to still exist) are listed. Total injection target: ≤ 300 tokens.

---

## 4. Hook Specifications

### 4.1 SessionStart Hook — `session_start.py`

**Event:** SessionStart (matcher: startup|resume)
**Timeout:** 45 seconds
**Purpose:** Incremental codebase indexing + memory loading + graph summary injection

**Input:** Standard SessionStart JSON (session_id, transcript_path, cwd, source)

**Execution flow:**

1. Read index watermark from `.contextforge/index_state.json`
2. Run `git diff --name-only` between watermark and HEAD + uncommitted changes
3. Detect deleted files via `git diff --diff-filter=D`
4. For changed files: delete old chunks from embeddings.db, re-chunk, re-embed, insert
5. For deleted files: remove chunks from embeddings.db, remove nodes from graph.json
6. Update graph.json incrementally (re-parse changed files only)
7. Prune orphaned chunks (files that no longer exist on disk)
8. Run memory decay: validate conventions, time-decay old patterns, prune aged memories
9. Generate architectural summary from graph (~200–400 tokens)
10. Generate memory summary from validated conventions (~100–300 tokens)
11. Save new watermark (current commit hash + timestamp)

**Output:** JSON with `additionalContext` combining architectural summary and memory summary

**First run behavior:** No watermark exists. Full codebase scan triggered. Dependency bootstrap runs (installs sentence-transformers if not present). May take 30–120 seconds depending on codebase size. Subsequent sessions: typically 2–10 seconds (only changed files).

**Error handling:** If any step fails, log error to `.contextforge/error.log` and continue with whatever context was successfully built. Never block session start. Exit 0 always.

### 4.2 UserPromptSubmit Hook — `rag_retrieve.py`

**Event:** UserPromptSubmit
**Timeout:** 15 seconds
**Purpose:** Semantic retrieval of relevant code for the user's prompt

**Input:** Standard UserPromptSubmit JSON (session_id, prompt, transcript_path)

**Execution flow:**

1. Read prompt from stdin JSON
2. Skip if prompt is a slash command (starts with `/`)
3. Skip if prompt is very short (< 10 characters) or purely conversational
4. Embed the prompt using the configured embedding model
5. Search embeddings.db for top 5 similar chunks (cosine similarity)
6. Filter below relevance threshold (default 0.3)
7. For top 3 matched files, query graph.json for neighbor nodes (related files)
8. Assemble context string: matched code chunks with file paths + related files list
9. Cap total output at ~2000 tokens

**Output:** JSON with `additionalContext` containing retrieved code context. If nothing relevant found, exit 0 with no output (no noise injected).

**Skip heuristics:** The hook should not inject context for conversational prompts ("thanks," "looks good," "continue"), git operations ("commit this," "push"), or meta-questions about Claude Code itself. A simple keyword filter handles this.

### 4.3 PostToolUse Hook (Memory Capture) — `memory_capture.py`

**Event:** PostToolUse (matcher: Write|Edit)
**Timeout:** 10 seconds
**Purpose:** Extract and store coding conventions from files Claude writes/edits

**Input:** Standard PostToolUse JSON (tool_name, tool_input with file_path and content, session_id)

**Execution flow:**

1. Extract file_path and content from tool_input
2. Skip non-code files (images, binaries, lock files, node_modules, vendor)
3. Run convention extraction rules against content
4. For each detected convention: upsert into conventions table (increment frequency if exists, update last_seen and example)
5. Insert raw file_change memory record

**Output:** Exit 0, no stdout (silent operation). Errors logged to `.contextforge/error.log`.

### 4.4 PostToolUse Hook (Real-Time Re-Index) — `realtime_reindex.py`

**Event:** PostToolUse (matcher: Write|Edit)
**Timeout:** 10 seconds
**Purpose:** Update embeddings immediately after Claude writes/edits a file so subsequent RAG queries reflect current state

**Input:** Standard PostToolUse JSON (same as memory_capture)

**Execution flow:**

1. Extract file_path and content
2. Skip non-indexable files
3. Delete existing chunks for this file from embeddings.db
4. Re-chunk the new content
5. Embed new chunks
6. Insert into embeddings.db
7. Update graph.json node for this file (re-parse class/method/association data)

**Output:** Exit 0, no stdout. Runs in parallel with memory_capture (hooks in the same matcher group run in parallel).

### 4.5 PreCompact Hook — `pre_compact_save.py`

**Event:** PreCompact
**Timeout:** 15 seconds
**Purpose:** Before context window compaction, extract key decisions and patterns from the transcript that would otherwise be lost

**Input:** Standard PreCompact JSON (session_id, transcript_path, trigger: manual|auto)

**Execution flow:**

1. Read the transcript JSONL file from transcript_path
2. Extract user messages and assistant messages from the last N exchanges (configurable, default 20)
3. Scan for architectural decision patterns: "let's use X instead of Y," "from now on we should," "the convention is," "I prefer," "don't use X"
4. For each detected decision: store as a convention with category "decision" and high initial frequency (5) so it persists through decay
5. Store a compact session summary in memories table

**Output:** Exit 0, no stdout. Preservation is silent.

### 4.6 Stop Hook — `stop_verify.py`

**Event:** Stop
**Timeout:** 10 seconds
**Purpose:** Prompt-based detection of conventions or preferences expressed during the session that should be captured before Claude stops

**Implementation:** Uses `type: "prompt"` hook (LLM-based evaluation via Haiku). The prompt analyzes the session transcript for expressed preferences, architectural decisions, or convention changes that should persist. If detected, blocks the stop with a reason that instructs Claude to capture the convention explicitly, which then triggers the PostToolUse memory capture on the subsequent write.

**Guard:** The hook checks `stop_hook_active` to prevent infinite loops. If already active, it approves the stop.

---

## 5. Data Storage

### 5.1 Storage Location

All ContextForge data lives in `.contextforge/` at the project root:

```
.contextforge/
├── graph.json           # Knowledge graph (adjacency list)
├── embeddings.db        # SQLite: code chunk embeddings
├── memory.db            # SQLite: conventions + file change history
├── index_state.json     # Watermark: last indexed commit + timestamp
├── config.json          # User overrides (optional, created by /context-status)
├── models/              # Cached embedding model files
│   └── all-MiniLM-L6-v2/
├── error.log            # Error log for debugging
└── stats.json           # Usage statistics (index size, query counts, latency)
```

### 5.2 Gitignore Strategy

The `.contextforge/` directory should be gitignored — it contains machine-specific embeddings, cached models, and local memory. Each developer's ContextForge instance builds its own index from the shared codebase.

The plugin's SessionStart hook appends `.contextforge/` to `.gitignore` if not already present.

### 5.3 Storage Limits

- **embeddings.db:** Scales with codebase size. Typical: 5–50MB for a 10K–100K line project. Chunks capped at 2000 chars each.
- **memory.db:** Capped by pruning. Memories older than 30 days pruned. Conventions table rarely exceeds 200 rows. Typical: < 1MB.
- **graph.json:** Proportional to file count. ~1KB per file. 1000-file project ≈ 1MB.
- **models/:** Local embedding model ≈ 80MB (downloaded once on first run).

---

## 6. Slash Commands

### 6.1 `/context-status`

**Purpose:** Show the health and status of the ContextForge index.

**Output:** Displays: last indexed commit and timestamp, number of indexed files and chunks, number of conventions (total and active), memory database size, embedding model in use, index staleness (files changed since last index), and latency statistics from recent sessions.

### 6.2 `/context-rebuild`

**Purpose:** Force a complete re-index. Destroys existing embeddings.db and graph.json, then rebuilds from scratch.

**Use case:** After major refactors, branch switches, or if the index appears corrupted.

### 6.3 `/context-memory`

**Purpose:** View and manage persistent memories.

**Sub-commands:**
- `/context-memory list` — Show all active conventions with frequencies
- `/context-memory clear` — Reset all memories (fresh start)
- `/context-memory forget [pattern]` — Remove a specific convention

---

## 7. Skill Definition

The plugin includes a SKILL.md that teaches Claude how to leverage the injected context effectively.

```
skills/
  contextforge/
    SKILL.md
```

**SKILL.md content:** Instructs Claude to: prioritize code patterns shown in "RELEVANT CODEBASE CONTEXT" sections over its training data, follow conventions listed in "ESTABLISHED PROJECT CONVENTIONS," check "RECENTLY MODIFIED FILES" for potential conflicts before writing new files, and use the knowledge graph summary to understand the project architecture before proposing structural changes.

---

## 8. Configuration

### 8.1 Default Configuration (`config/defaults.json`)

```json
{
  "indexing": {
    "supported_extensions": [
      ".rb", ".py", ".js", ".ts", ".jsx", ".tsx",
      ".go", ".rs", ".erb", ".yml", ".yaml",
      ".json", ".md", ".sql"
    ],
    "ignored_directories": [
      "node_modules", "vendor", ".git", "tmp", "log",
      "coverage", "dist", "build", ".contextforge"
    ],
    "max_file_size_kb": 500,
    "chunk_target_tokens": 384,
    "chunk_overlap_tokens": 50
  },
  "retrieval": {
    "relevance_threshold": 0.3,
    "max_results": 5,
    "max_context_tokens": 2000,
    "graph_neighbor_depth": 1,
    "max_graph_neighbors": 3
  },
  "memory": {
    "convention_threshold": 3,
    "decay_days": 14,
    "prune_days": 30,
    "max_conventions_injected": 15,
    "max_recent_files": 15,
    "decision_initial_frequency": 5
  },
  "embedding": {
    "model": "all-MiniLM-L6-v2",
    "api_model": null,
    "api_key_env": "CONTEXTFORGE_EMBEDDING_API_KEY"
  },
  "context_budget": {
    "session_start_max_tokens": 600,
    "rag_max_tokens": 2000,
    "total_max_tokens": 2600
  }
}
```

### 8.2 User Overrides

Users can create `.contextforge/config.json` to override any default:

```json
{
  "retrieval": {
    "relevance_threshold": 0.4,
    "max_results": 3
  },
  "memory": {
    "convention_threshold": 5
  }
}
```

Overrides are deep-merged with defaults at each hook invocation.

---

## 9. Performance Requirements

### 9.1 Latency Targets

- **SessionStart (incremental, < 20 changed files):** < 10 seconds
- **SessionStart (full re-index, 1000 files):** < 120 seconds (first run acceptable)
- **UserPromptSubmit (RAG retrieval):** < 3 seconds (p95)
- **PostToolUse (memory capture + re-index):** < 5 seconds combined (runs in parallel)
- **PreCompact (transcript extraction):** < 5 seconds

### 9.2 Resource Constraints

- **Disk:** < 200MB total for a 100K-line project (including model cache)
- **Memory:** Peak RAM during embedding: < 500MB (sentence-transformers model). Steady state: < 50MB (SQLite connections only).
- **CPU:** Embedding computation is the primary cost. Local model uses CPU by default. GPU acceleration available if torch+CUDA installed.
- **No network calls by default.** Local embedding model means zero API costs and offline operation. API embeddings are opt-in.

### 9.3 Scalability Limits

- **Tested up to:** 5,000 files / 500K lines of code
- **Beyond 5K files:** SessionStart full re-index may exceed 2 minutes. Incremental indexing remains fast (< 10s for < 50 changed files).
- **Mitigation for large codebases:** Config option to scope indexing to specific directories (`indexing.include_paths`). Default: index everything.

---

## 10. Dependency Management

### 10.1 Python Dependencies

ContextForge scripts require Python 3.9+ and the following packages:

- **sentence-transformers** — Local embedding model (installs torch as dependency)
- **numpy** — Vector similarity computation
- **tree-sitter** + language grammars — AST parsing for code chunking (MVP: tree-sitter-ruby, tree-sitter-python, tree-sitter-javascript)

### 10.2 Bootstrap Strategy

Dependencies are installed lazily on first SessionStart. The `setup.py` script checks for required packages and installs them into a plugin-local virtual environment at `.contextforge/venv/`:

```bash
#!/bin/bash
VENV_DIR="$CLAUDE_PROJECT_DIR/.contextforge/venv"
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
    "$VENV_DIR/bin/pip" install sentence-transformers numpy tree-sitter tree-sitter-languages
fi
```

All hook scripts use the venv Python: `#!/usr/bin/env .contextforge/venv/bin/python3`

### 10.3 Fallback Behavior

If Python dependencies fail to install (no Python 3.9, no pip, restricted environment), ContextForge degrades gracefully:

- **Without sentence-transformers:** RAG retrieval disabled. Knowledge graph and memory still function (no embeddings needed for pattern extraction or graph building).
- **Without tree-sitter:** Fall back to regex-based file parsing. Less accurate chunking and graph construction, but functional.
- **Without Python:** Plugin is non-functional. Commands display an error message with installation instructions.

---

## 11. Security Considerations

### 11.1 Data Privacy

- All data stored locally in `.contextforge/`. No telemetry, no cloud calls by default.
- Embedding model runs locally. No code is sent to external APIs unless the user explicitly configures API embeddings.
- Memory database contains code snippets (truncated to 500 chars). Ensure `.contextforge/` is gitignored to prevent accidental commits of code fragments.

### 11.2 Hook Security

- All hook scripts are read-only and execute within the user's normal permissions.
- No network calls from hook scripts (local embedding model).
- Scripts validate JSON input before processing. Malformed input causes graceful exit (exit 0, no action).
- File path traversal prevention: all paths resolved relative to `CLAUDE_PROJECT_DIR`. Paths containing `..` are rejected.

### 11.3 Multi-User Safety

- Each developer has their own `.contextforge/` directory (gitignored).
- SQLite databases are single-writer. No concurrent access issues in normal use (one Claude Code session per project directory).
- If multiple sessions run simultaneously in the same directory, SQLite's built-in locking handles write contention. Reads are non-blocking.

---

## 12. Success Metrics

### 12.1 Quality Metrics

- **Context hit rate:** Percentage of user prompts where RAG retrieval returns at least one result above threshold. Target: > 70% for code-related prompts.
- **Convention accuracy:** Percentage of injected conventions that are currently true (validated against codebase). Target: > 90%.
- **Index freshness:** Time between a file change and its reflection in embeddings. Target: 0 seconds for in-session changes (PostToolUse), < 10 seconds for cross-session changes (SessionStart).

### 12.2 Performance Metrics

- **SessionStart p95 latency (incremental):** < 10 seconds
- **RAG retrieval p95 latency:** < 3 seconds
- **PostToolUse p95 latency (combined capture + re-index):** < 5 seconds
- **Context token efficiency:** Useful tokens injected vs. total tokens injected. Target: > 60% (measured by whether Claude references the injected context in its response).

### 12.3 User Impact Metrics

- **First-attempt code correctness:** Does Claude-generated code follow project conventions on the first try? Measured by: fewer inline edits after generation, fewer "that's not how we do it" corrections.
- **Session productivity:** Tasks completed per session with ContextForge vs. without. Target: > 25% improvement.
- **Convention drift:** Frequency of Claude generating code that contradicts established project patterns. Target: < 10% of generated files.

---

## 13. Risks and Mitigations

**Risk: Local embedding model is too large (~80MB download + ~400MB with torch)**
Mitigation: Offer a "lite" mode using TF-IDF or BM25 for retrieval instead of neural embeddings. No ML dependencies. Lower quality but zero footprint. Configured via `embedding.model: "bm25"`.

**Risk: SessionStart timeout on very large codebases (> 5000 files)**
Mitigation: Configurable `include_paths` to scope indexing. Background indexing option: start session immediately with stale index, run full re-index as async process, update on next prompt.

**Risk: Noisy RAG retrieval degrades Claude's performance**
Mitigation: Conservative default relevance threshold (0.3). User-configurable. Skip heuristics for conversational prompts. Token budget cap prevents overwhelming the context window.

**Risk: Convention extraction heuristics produce false patterns**
Mitigation: Frequency threshold (default 3) means a pattern must be observed across multiple files before being injected. Single occurrences are stored but not surfaced. Users can manually remove incorrect conventions via `/context-memory forget`.

**Risk: Memory decay removes valid conventions too aggressively**
Mitigation: High-frequency conventions (seen 10+ times) are very resistant to decay (14 days without observation only removes 1 point). Architectural decisions captured from transcript get initial frequency of 5. Users can view and restore via `/context-memory`.

**Risk: SQLite lock contention with concurrent sessions**
Mitigation: SQLite WAL mode for concurrent reads. Write timeout of 5 seconds with retry. In practice, write operations are < 100ms each. If contention occurs, the hook exits gracefully (exit 0) without blocking the session.

---

## 14. Roadmap

### Phase 1: Foundation (Weeks 1–4)

- Plugin scaffold: manifest, directory structure, hooks.json
- Knowledge graph engine: Tree-sitter parsing for Ruby + Python + JavaScript
- Git-aware incremental indexing with watermarking
- SQLite-based embedding store with local model (all-MiniLM-L6-v2)
- SessionStart hook: full + incremental indexing, graph summary injection
- UserPromptSubmit hook: RAG retrieval with cosine similarity
- PostToolUse hooks: memory capture + real-time re-index
- `/context-status` command
- README and installation guide

### Phase 2: Intelligence (Weeks 5–8)

- Persistent memory with convention extraction (10 pattern detectors)
- Memory decay system (file validation, time decay, age pruning)
- PreCompact hook: transcript decision extraction
- Stop hook: prompt-based convention detection
- `/context-memory` and `/context-rebuild` commands
- ContextForge SKILL.md for Claude awareness
- Configuration system (defaults + user overrides)
- Go and Rust language support (Tree-sitter grammars)
- Error logging and stats tracking

### Phase 3: Polish (Weeks 9–12)

- BM25 lite mode (no ML dependencies)
- API embedding support (Voyage Code, OpenAI)
- Graph neighbor traversal in RAG retrieval
- Performance optimization: batch embedding, incremental graph updates
- Include/exclude path configuration for large monorepos
- Marketplace listing and distribution
- Comprehensive test suite
- User documentation and configuration guide

### Phase 4: Ecosystem (Months 4–6)

- Team convention sharing: export/import conventions across developers
- Cross-project memory: organizational patterns shared across repositories
- VSCode extension integration: show context status in sidebar
- MCP server: expose knowledge graph and memory as MCP tools for external agents
- Analytics dashboard: context quality, retrieval accuracy, convention coverage
- PromptForge integration: feed knowledge graph into PromptForge's Context Assembler (Layer 3)

---

## 15. Appendix

### A: Example Session Flow

**Session start (returning to a Rails project after 2 days):**

```
[ContextForge] Incremental index: 12 files changed, 2 deleted (3.2s)
[ContextForge] Memory: 18 conventions loaded (14 active), 3 decayed
```

**Injected context (SessionStart additionalContext):**

```
PROJECT ARCHITECTURE (auto-indexed by ContextForge):
- 15 models: Organization, User, PromptSession, TaskNode, DomainTemplate...
- 12 services under app/services/ following .call pattern
- Auth: Devise + Pundit (owner/admin/member/viewer roles)
- DB: PostgreSQL 16 with UUID PKs, JSONB columns, discard gem soft deletes
- Queue: Sidekiq for all async/LLM work
- Frontend: Hotwire (Turbo Frames + Stimulus controllers)
- Recent changes (last 2d): Modified TaskDecomposerService, added ExportService, 
  updated PromptSession model

ESTABLISHED CONVENTIONS (validated):
- [active] Services use .call interface (seen 12x, e.g. app/services/intent_classifier_service.rb)
- [active] Models use UUID primary keys (seen 15x)
- [active] Tests use FactoryBot + RSpec (seen 8x)
- [active] Multi-tenant scoping via organization_id (seen 10x)
- [2d ago] Background jobs in app/jobs/ with Sidekiq (seen 6x)

RECENTLY MODIFIED:
- app/services/task_decomposer_service.rb (1d ago)
- app/services/export_service.rb (1d ago)
- app/models/prompt_session.rb (2d ago)
```

**User prompt: "Add a prompt versioning feature so users can see diff between versions"**

**Injected context (UserPromptSubmit additionalContext):**

```
RELEVANT CODEBASE CONTEXT (auto-retrieved):

--- app/models/prompt_session.rb (relevance: 0.82) ---
class PromptSession < ApplicationRecord
  belongs_to :user
  belongs_to :organization
  has_many :task_nodes, dependent: :destroy
  enum :status, { classifying: 0, interrogating: 1, assembling: 2, 
                  decomposing: 3, scoring: 4, complete: 5, failed: 6 }
  validates :raw_input, presence: true
  scope :for_org, ->(org) { where(organization_id: org.id) }
  ...

--- app/models/task_node.rb (relevance: 0.71) ---
class TaskNode < ApplicationRecord
  belongs_to :prompt_session
  belongs_to :parent, class_name: "TaskNode", optional: true
  has_many :children, class_name: "TaskNode", foreign_key: :parent_id
  enum :level, { epic: 0, feature: 1, task: 2, subtask: 3 }
  ...

--- db/schema.rb (relevance: 0.65) ---
  create_table "prompt_sessions", id: :uuid do |t|
    t.uuid "user_id", null: false
    t.uuid "organization_id", null: false
    t.text "raw_input"
    t.jsonb "intent_classification"
    ...

RELATED FILES (from dependency graph):
- app/services/pipeline_orchestrator_service.rb
- app/controllers/sessions_controller.rb
- spec/models/prompt_session_spec.rb
```

Claude now has the exact model structure, existing patterns, and related files to build the versioning feature correctly — following UUID conventions, multi-tenant scoping, enum patterns, and the existing association style — without the user needing to explain any of it.

### B: Glossary

- **Knowledge Graph** — A structural index of the codebase represented as nodes (files, classes, methods) and edges (relationships like calls, inherits, tests)
- **RAG** — Retrieval-Augmented Generation. Finding and injecting relevant existing content to improve LLM output quality
- **Embedding** — A numeric vector representation of text that enables semantic similarity search
- **Convention** — A coding pattern observed repeatedly across the codebase, tracked with frequency and recency
- **Watermark** — The git commit hash marking the last point at which the index was fully synchronized
- **Decay** — The process of reducing convention frequency over time when patterns are not re-observed, allowing outdated patterns to naturally disappear
- **Chunking** — Splitting source files into semantic units (functions, classes, blocks) for individual embedding and retrieval
- **additionalContext** — The JSON field in Claude Code hook output that injects text directly into the agent's context window

### C: References

- Claude Code Hooks Guide: https://code.claude.com/docs/en/hooks-guide
- Claude Code Hooks Reference: https://code.claude.com/docs/en/hooks
- Claude Code Plugins Guide: https://code.claude.com/docs/en/plugins
- Claude Code Plugins Reference: https://code.claude.com/docs/en/plugins-reference
- Claude Code Skills: https://code.claude.com/docs/en/skills
- Sentence Transformers: https://www.sbert.net/
- Tree-sitter: https://tree-sitter.github.io/
- SQLite WAL Mode: https://www.sqlite.org/wal.html
- Anthropic Context Engineering: https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering

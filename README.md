# ContextForge

**Context-aware intelligence for Claude Code.** Automatic codebase indexing, semantic RAG retrieval, and persistent cross-session memory.

ContextForge is a Claude Code plugin that transforms stateless coding sessions into context-aware, learning systems. It automatically indexes your codebase, retrieves relevant code via semantic search, captures coding conventions, and maintains persistent memory across sessions.

## Requirements

- **Python 3.10+**
- **Git** (for incremental indexing)
- **Claude Code** (CLI)

## Installation

### As a Claude Code Plugin

```bash
claude --plugin-dir /path/to/context_forge
```

ContextForge will automatically bootstrap on the first session start:
1. Creates a virtual environment in `.contextforge/venv`
2. Installs dependencies (sentence-transformers, tree-sitter, numpy)
3. Indexes the codebase and builds a knowledge graph
4. Starts injecting context into your sessions

### Manual Bootstrap

```bash
cd /path/to/your/project
bash /path/to/context_forge/scripts/bootstrap.sh
```

## How It Works

### Session Start
When a Claude Code session starts or resumes, ContextForge:
- Indexes new/changed files since the last session (incremental via git)
- Chunks source files using tree-sitter AST parsing (with regex and sliding-window fallbacks)
- Embeds code chunks using `all-MiniLM-L6-v2` sentence transformer (GPU-accelerated when available)
- Builds a lightweight knowledge graph of file relationships
- Injects an architectural summary and memory context into the session

### RAG Retrieval
On each user prompt, ContextForge:
- Embeds the user's question
- Searches stored code chunks by cosine similarity
- Injects the most relevant code snippets as additional context
- Skips short prompts, slash commands, and conversational messages

### Memory Capture
When files are written or edited, ContextForge:
- Extracts coding conventions (service patterns, model patterns, API styles, etc.)
- Records file change events with session tracking
- Builds a persistent convention database that grows over time

### Real-time Reindex
Modified files are re-chunked and re-embedded in real time, keeping the RAG index current within the session.

## Slash Commands

| Command | Description |
|---------|-------------|
| `/contextforge:context-status` | Show index state, file counts, conventions |
| `/contextforge:context-rebuild` | Force full re-index of the codebase |
| `/contextforge:context-memory` | Manage persistent memory (list, clear, forget) |

## GPU Acceleration

ContextForge automatically detects and uses the best available compute device for embeddings:

| Device | When used |
|--------|-----------|
| **CUDA** | NVIDIA GPU with CUDA drivers detected |
| **MPS** | Apple Silicon Mac (M1/M2/M3/M4) |
| **CPU** | Fallback when no GPU is available |

No configuration needed — detection is automatic. To force a specific device, set `embedding.device` in your config:

```json
{
  "embedding": {
    "device": "cpu"
  }
}
```

## Configuration

ContextForge uses sensible defaults. To customize, create `.contextforge/config.json` in your project:

```json
{
  "retrieval": {
    "relevance_threshold": 0.4,
    "max_results": 10
  },
  "memory": {
    "convention_threshold": 5
  },
  "indexing": {
    "max_file_size_bytes": 1048576
  }
}
```

See `config/defaults.json` for all available options.

## Data Storage

All ContextForge data is stored in `.contextforge/` within your project directory:

| File | Purpose |
|------|---------|
| `embeddings.db` | SQLite database of code chunk embeddings |
| `memory.db` | Conventions and file change history |
| `graph.json` | Knowledge graph of file relationships |
| `index_state.json` | Git watermark for incremental indexing |
| `venv/` | Python virtual environment |
| `models/` | Cached embedding model files |
| `config.json` | User configuration overrides (optional) |

The `.contextforge/` directory is automatically added to `.gitignore`.

## Cross-Platform Support

ContextForge works on **Windows**, **macOS**, and **Linux**. The hook runner script uses bash (Git Bash on Windows) and all Python code uses `pathlib.Path` for path handling.

## Development

### Running Tests

```bash
# Unit tests (requires pytest)
python -m pytest tests/ -v

# Integration test
bash tests/test_integration.sh
```

### Project Structure

```
contextforge/
├── .claude-plugin/plugin.json    # Plugin manifest
├── commands/                     # Slash command definitions
├── skills/contextforge/          # Skill definition
├── hooks/hooks.json              # Hook configuration
├── scripts/                      # Hook scripts and bootstrap
│   └── lib/                      # Core Python library modules
├── config/defaults.json          # Default configuration
└── tests/                        # Unit and integration tests
```

## License

MIT - See [LICENSE](LICENSE) for details.

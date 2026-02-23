# Changelog

All notable changes to ContextForge will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.1.0] - 2026-02-23

### Added
- Initial release of ContextForge Claude Code plugin
- Automatic codebase indexing with tree-sitter AST parsing, regex, and sliding-window fallbacks
- Semantic RAG retrieval using all-MiniLM-L6-v2 embeddings and cosine similarity
- Knowledge graph builder with file metadata extraction and architectural summaries
- Persistent memory system for coding conventions and file change tracking
- Cross-platform support (Windows, macOS, Linux) via bash hook runner
- Auto-bootstrap: virtual environment creation and dependency installation on first run
- Incremental indexing via git watermark tracking
- Real-time reindex on file Write/Edit operations
- Slash commands: context-status, context-rebuild, context-memory
- SQLite-backed storage with WAL mode for concurrent access
- Configurable via defaults.json and per-project config.json overrides
- Unit test suite and integration test script

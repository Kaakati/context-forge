#!/usr/bin/env python3
"""ContextForge SessionStart hook.

Runs on session start/resume. Indexes the codebase incrementally,
builds the knowledge graph, and injects architectural context.
"""

import json
import logging
import os
import sys
from pathlib import Path

# Add scripts directory to path for lib imports
sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.platform_utils import get_project_dir, get_data_dir, get_plugin_root, ensure_data_dir
from lib.config import load_config
from lib.db import init_embeddings_db, init_memory_db, get_connection
from lib.git_utils import get_current_commit, get_changed_files, load_watermark, save_watermark
from lib.indexer import chunk_file
from lib.embedder import embed_texts
from lib.graph import load_graph, save_graph, update_graph_for_file, remove_file_from_graph, generate_summary
from lib.memory_store import generate_memory_summary

logging.basicConfig(level=logging.WARNING, format="%(name)s: %(message)s", stream=sys.stderr)
logger = logging.getLogger("contextforge.session_start")


def ensure_gitignore(project_dir):
    """Append .contextforge/ to .gitignore if not already present."""
    gitignore = project_dir / ".gitignore"
    marker = ".contextforge/"
    try:
        if gitignore.exists():
            content = gitignore.read_text(encoding="utf-8")
            if marker in content:
                return
            with open(gitignore, "a", encoding="utf-8") as f:
                f.write(f"\n# ContextForge data\n{marker}\n")
        else:
            gitignore.write_text(f"# ContextForge data\n{marker}\n", encoding="utf-8")
    except OSError as e:
        logger.warning("Could not update .gitignore: %s", e)


def get_all_files(project_dir, config):
    """Get all indexable files in the project."""
    supported = set(config.get("indexing", {}).get("supported_extensions", [".py"]))
    ignored = set(config.get("indexing", {}).get("ignored_directories", []))
    max_size = config.get("indexing", {}).get("max_file_size_bytes", 524288)
    files = []

    for root, dirs, filenames in os.walk(project_dir):
        # Filter ignored directories in-place
        dirs[:] = [d for d in dirs if d not in ignored and not d.startswith(".")]
        for fname in filenames:
            fpath = Path(root) / fname
            if fpath.suffix in supported:
                try:
                    if fpath.stat().st_size <= max_size:
                        files.append(fpath)
                except OSError:
                    continue
    return files


def index_files(file_paths, project_dir, data_dir, config):
    """Chunk and embed a list of files, storing results in embeddings.db."""
    db_path = data_dir / "embeddings.db"
    all_chunks = []

    for fpath in file_paths:
        try:
            content = fpath.read_text(encoding="utf-8", errors="replace")
            rel_path = fpath.relative_to(project_dir).as_posix()
            chunks = chunk_file(rel_path, content, config)
            for chunk in chunks:
                chunk["file_path"] = rel_path
            all_chunks.extend(chunks)
        except OSError as e:
            logger.warning("Could not read %s: %s", fpath, e)
            continue

    if not all_chunks:
        return 0

    # Embed all chunks in batch
    texts = [c["content"] for c in all_chunks]
    embeddings = embed_texts(texts, config)

    # Store in database
    with get_connection(db_path) as conn:
        for i, chunk in enumerate(all_chunks):
            emb_blob = None
            if embeddings is not None:
                emb_blob = embeddings[i].tobytes()

            conn.execute(
                """INSERT INTO code_chunks
                   (file_path, chunk_type, start_line, end_line, content, content_hash, embedding)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    chunk["file_path"],
                    chunk.get("type", "unknown"),
                    chunk.get("start_line", 0),
                    chunk.get("end_line", 0),
                    chunk["content"],
                    chunk["hash"],
                    emb_blob,
                ),
            )

    return len(all_chunks)


def remove_deleted_files(deleted_files, data_dir, graph):
    """Remove deleted files from embeddings and graph."""
    db_path = data_dir / "embeddings.db"
    with get_connection(db_path) as conn:
        for fpath in deleted_files:
            conn.execute("DELETE FROM code_chunks WHERE file_path = ?", (fpath,))
            remove_file_from_graph(graph, fpath)


def main():
    """Main session start hook handler."""
    try:
        # Read stdin (hook input)
        stdin_data = sys.stdin.read()
        try:
            hook_input = json.loads(stdin_data) if stdin_data.strip() else {}
        except json.JSONDecodeError:
            hook_input = {}

        project_dir = get_project_dir()
        data_dir = get_data_dir()
        plugin_root = get_plugin_root()

        # Ensure data directory and databases exist
        ensure_data_dir()
        db_emb = data_dir / "embeddings.db"
        db_mem = data_dir / "memory.db"
        init_embeddings_db(db_emb)
        init_memory_db(db_mem)

        # Ensure .contextforge/ is in .gitignore
        ensure_gitignore(project_dir)

        # Load configuration
        config = load_config(plugin_root, data_dir)
        config["data_dir"] = str(data_dir)  # For embedder model cache

        # Determine what needs indexing
        watermark = load_watermark(data_dir)
        current_commit = get_current_commit(str(project_dir))

        graph = load_graph(data_dir)
        total_chunks = 0

        if watermark.get("commit") and current_commit:
            # Incremental index
            changes = get_changed_files(watermark["commit"], str(project_dir))
            modified = changes.get("modified", [])
            deleted = changes.get("deleted", [])

            if modified:
                # Remove old chunks for modified files
                with get_connection(db_emb) as conn:
                    for fpath in modified:
                        conn.execute("DELETE FROM code_chunks WHERE file_path = ?", (fpath,))

                # Re-index modified files
                full_paths = []
                for rel in modified:
                    fp = project_dir / rel
                    if fp.exists():
                        full_paths.append(fp)
                        try:
                            content = fp.read_text(encoding="utf-8", errors="replace")
                            update_graph_for_file(graph, rel, content)
                        except OSError:
                            pass

                total_chunks = index_files(full_paths, project_dir, data_dir, config)

            if deleted:
                remove_deleted_files(deleted, data_dir, graph)

        else:
            # Full index — first run or no git
            all_files = get_all_files(project_dir, config)

            # Clear existing data for full re-index
            with get_connection(db_emb) as conn:
                conn.execute("DELETE FROM code_chunks")

            total_chunks = index_files(all_files, project_dir, data_dir, config)

            # Build full graph
            for fpath in all_files:
                try:
                    rel = fpath.relative_to(project_dir).as_posix()
                    content = fpath.read_text(encoding="utf-8", errors="replace")
                    update_graph_for_file(graph, rel, content)
                except OSError:
                    continue

        # Save graph and watermark
        save_graph(data_dir, graph)
        if current_commit:
            save_watermark(data_dir, current_commit)

        # Generate context for Claude
        arch_summary = generate_summary(graph)
        memory_summary = generate_memory_summary(db_mem, config)

        context_parts = []
        if arch_summary:
            context_parts.append(f"## PROJECT ARCHITECTURE\n{arch_summary}")
        if memory_summary:
            context_parts.append(memory_summary)

        context_text = "\n\n".join(context_parts) if context_parts else ""

        # Trim to budget
        max_tokens = config.get("context_budget", {}).get("session_start_max_tokens", 600)
        # Rough estimate: 1 token ≈ 4 chars
        max_chars = max_tokens * 4
        if len(context_text) > max_chars:
            context_text = context_text[:max_chars] + "\n..."

        # Output hook response
        output = {
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": context_text,
            }
        }
        print(json.dumps(output))

    except Exception as e:
        logger.error("Session start hook failed: %s", e)
        # Output empty context on failure — never block Claude
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": "",
            }
        }))


if __name__ == "__main__":
    main()

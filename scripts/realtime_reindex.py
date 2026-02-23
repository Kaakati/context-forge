#!/usr/bin/env python3
"""ContextForge real-time reindex hook (PostToolUse on Write|Edit).

Re-chunks and re-embeds files as they are modified during a session,
keeping the RAG index up-to-date in real time.
"""

import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.platform_utils import get_data_dir, get_plugin_root, get_project_dir, is_safe_path
from lib.config import load_config
from lib.db import get_connection, init_embeddings_db
from lib.indexer import chunk_file
from lib.embedder import embed_texts
from lib.graph import load_graph, save_graph, update_graph_for_file

logging.basicConfig(level=logging.WARNING, format="%(name)s: %(message)s", stream=sys.stderr)
logger = logging.getLogger("contextforge.realtime_reindex")


def main():
    """Main real-time reindex handler."""
    try:
        stdin_data = sys.stdin.read()
        try:
            hook_input = json.loads(stdin_data) if stdin_data.strip() else {}
        except json.JSONDecodeError:
            return

        # Extract file path and content
        tool_input = hook_input.get("tool_input", {})
        if isinstance(tool_input, str):
            try:
                tool_input = json.loads(tool_input)
            except json.JSONDecodeError:
                return

        file_path = tool_input.get("file_path", "")
        content = tool_input.get("content", "")

        if not file_path:
            return

        data_dir = get_data_dir()
        plugin_root = get_plugin_root()
        project_dir = get_project_dir()

        # Convert absolute path to relative (session_start indexes with relative paths)
        try:
            file_path = Path(file_path).resolve().relative_to(project_dir.resolve()).as_posix()
        except ValueError:
            # Not under project dir — use as-is with forward slashes
            file_path = Path(file_path).as_posix()

        if not file_path:
            return
        config = load_config(plugin_root, data_dir)
        config["data_dir"] = str(data_dir)  # For embedder model cache

        # Check if extension is supported (from config, not hardcoded)
        supported = set(config.get("indexing", {}).get("supported_extensions", []))
        ext = Path(file_path).suffix.lower()
        if ext not in supported:
            return

        db_path = data_dir / "embeddings.db"
        if not db_path.exists():
            init_embeddings_db(db_path)

        # If no content provided (e.g., Edit tool), try reading the file
        if not content:
            try:
                full_path = project_dir / file_path
                if full_path.exists() and is_safe_path(project_dir, full_path):
                    content = full_path.read_text(encoding="utf-8", errors="replace")
                else:
                    return
            except OSError:
                return

        # Re-chunk the file
        chunks = chunk_file(file_path, content, config)
        if not chunks:
            return

        # Embed all chunks
        texts = [c["content"] for c in chunks]
        embeddings = embed_texts(texts, config)

        # Replace old chunks in database
        with get_connection(db_path) as conn:
            conn.execute("DELETE FROM code_chunks WHERE file_path = ?", (file_path,))

            for i, chunk in enumerate(chunks):
                emb_blob = None
                if embeddings is not None:
                    emb_blob = embeddings[i].tobytes()

                conn.execute(
                    """INSERT INTO code_chunks
                       (file_path, chunk_type, start_line, end_line, content, content_hash, embedding)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (
                        file_path,
                        chunk.get("type", "unknown"),
                        chunk.get("start_line", 0),
                        chunk.get("end_line", 0),
                        chunk["content"],
                        chunk["hash"],
                        emb_blob,
                    ),
                )

        # Update knowledge graph
        graph = load_graph(data_dir)
        update_graph_for_file(graph, file_path, content)
        save_graph(data_dir, graph)

    except Exception as e:
        logger.error("Real-time reindex failed: %s", e)

    # PostToolUse hooks output empty JSON for clean protocol compliance
    print("{}")


if __name__ == "__main__":
    main()

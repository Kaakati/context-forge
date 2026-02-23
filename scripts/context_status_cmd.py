#!/usr/bin/env python3
"""ContextForge context-status command helper.

Reads all databases and index state, prints a formatted status report.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.platform_utils import get_data_dir
from lib.db import get_connection


# Allowlisted table/column names to prevent SQL injection
_ALLOWED_TABLES = {"code_chunks", "memories", "conventions"}
_ALLOWED_COLUMNS = {"*", "embedding", "file_path"}


def get_db_stats(db_path, table, count_col="*"):
    """Get row count from a database table."""
    if table not in _ALLOWED_TABLES or count_col not in _ALLOWED_COLUMNS:
        return 0
    try:
        if not db_path.exists():
            return 0
        with get_connection(db_path) as conn:
            cursor = conn.execute(f"SELECT COUNT({count_col}) FROM {table}")
            return cursor.fetchone()[0]
    except Exception:
        return 0


def get_distinct_files(db_path):
    """Get count of distinct indexed files."""
    try:
        if not db_path.exists():
            return 0
        with get_connection(db_path) as conn:
            cursor = conn.execute("SELECT COUNT(DISTINCT file_path) FROM code_chunks")
            return cursor.fetchone()[0]
    except Exception:
        return 0


def get_conventions_summary(db_path):
    """Get conventions with their frequencies."""
    try:
        if not db_path.exists():
            return []
        with get_connection(db_path) as conn:
            cursor = conn.execute(
                "SELECT pattern_type, description, frequency FROM conventions ORDER BY frequency DESC LIMIT 10"
            )
            return cursor.fetchall()
    except Exception:
        return []


def main():
    """Print formatted status report."""
    data_dir = get_data_dir()

    emb_db = data_dir / "embeddings.db"
    mem_db = data_dir / "memory.db"
    graph_path = data_dir / "graph.json"
    watermark_path = data_dir / "index_state.json"

    print("ContextForge Status Report")
    print("=" * 40)
    print()

    # Data directory
    print(f"Data directory: {data_dir}")
    print(f"  Exists: {data_dir.exists()}")
    print()

    # Index state
    print("Index State:")
    if watermark_path.exists():
        try:
            state = json.loads(watermark_path.read_text(encoding="utf-8"))
            print(f"  Last indexed commit: {state.get('commit', 'unknown')[:12]}")
            print(f"  Last indexed at:     {state.get('timestamp', 'unknown')}")
        except Exception:
            print("  Error reading index state")
    else:
        print("  Not indexed yet")
    print()

    # Embeddings database
    print("Embeddings Database:")
    if emb_db.exists():
        file_count = get_distinct_files(emb_db)
        chunk_count = get_db_stats(emb_db, "code_chunks")
        emb_count = get_db_stats(emb_db, "code_chunks", "embedding")
        print(f"  Indexed files:  {file_count}")
        print(f"  Total chunks:   {chunk_count}")
        print(f"  With embeddings: {emb_count}")
    else:
        print("  Not created yet")
    print()

    # Knowledge graph
    print("Knowledge Graph:")
    if graph_path.exists():
        try:
            graph = json.loads(graph_path.read_text(encoding="utf-8"))
            files = graph.get("files", {})
            edges = graph.get("edges", [])
            print(f"  Files tracked: {len(files)}")
            print(f"  Edges:         {len(edges)}")

            # Count by type
            type_counts = {}
            for f_info in files.values():
                ft = f_info.get("type", "unknown")
                type_counts[ft] = type_counts.get(ft, 0) + 1
            if type_counts:
                print("  File types:")
                for ft, count in sorted(type_counts.items(), key=lambda x: -x[1]):
                    print(f"    {ft}: {count}")
        except Exception:
            print("  Error reading graph")
    else:
        print("  Not built yet")
    print()

    # Memory database
    print("Memory Database:")
    if mem_db.exists():
        memory_count = get_db_stats(mem_db, "memories")
        convention_count = get_db_stats(mem_db, "conventions")
        print(f"  File change events: {memory_count}")
        print(f"  Conventions stored: {convention_count}")

        conventions = get_conventions_summary(mem_db)
        if conventions:
            print("  Top conventions:")
            for ptype, desc, freq in conventions:
                print(f"    [{freq}x] {ptype}: {desc}")
    else:
        print("  Not created yet")
    print()

    # Venv status
    venv_dir = data_dir / "venv"
    print("Virtual Environment:")
    print(f"  Exists: {venv_dir.exists()}")


if __name__ == "__main__":
    main()

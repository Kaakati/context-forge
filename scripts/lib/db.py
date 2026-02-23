"""SQLite connection manager for ContextForge.

Provides a context-managed database connection with WAL mode, and
initialization functions for the embeddings and memory databases.
"""

import logging
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

logger = logging.getLogger(__name__)


@contextmanager
def get_connection(db_path: Path) -> Generator[sqlite3.Connection, None, None]:
    """Open a SQLite connection with recommended pragmas.

    Configures:
        - WAL journal mode for concurrent reads
        - busy_timeout of 5000ms to handle lock contention
        - foreign_keys ON for referential integrity

    Args:
        db_path: Path to the SQLite database file.

    Yields:
        An open sqlite3.Connection. Commits on clean exit, rolls back
        on exception.
    """
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        conn.execute("PRAGMA foreign_keys=ON")
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_embeddings_db(db_path: Path) -> None:
    """Initialize the embeddings database schema.

    Creates the code_chunks table and its indexes if they do not
    already exist.

    Args:
        db_path: Path to the embeddings SQLite database file.
    """
    db_path = Path(db_path)
    logger.info("Initializing embeddings database at: %s", db_path)

    with get_connection(db_path) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS code_chunks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT NOT NULL,
                chunk_type TEXT,
                start_line INTEGER,
                end_line INTEGER,
                content TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                embedding BLOB,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_chunks_file ON code_chunks(file_path);
            CREATE INDEX IF NOT EXISTS idx_chunks_hash ON code_chunks(content_hash);
            """
        )
    logger.info("Embeddings database initialized successfully.")


def init_memory_db(db_path: Path) -> None:
    """Initialize the memory database schema.

    Creates the memories and conventions tables with their indexes
    if they do not already exist.

    Args:
        db_path: Path to the memory SQLite database file.
    """
    db_path = Path(db_path)
    logger.info("Initializing memory database at: %s", db_path)

    with get_connection(db_path) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT NOT NULL,
                session_id TEXT,
                event_type TEXT DEFAULT 'file_change',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_memories_file ON memories(file_path);

            CREATE TABLE IF NOT EXISTS conventions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern_type TEXT NOT NULL,
                description TEXT NOT NULL,
                example TEXT,
                frequency INTEGER DEFAULT 1,
                first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_conventions_type ON conventions(pattern_type);
            """
        )
    logger.info("Memory database initialized successfully.")

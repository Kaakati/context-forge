#!/usr/bin/env python3
"""ContextForge RAG retrieval hook (UserPromptSubmit).

Embeds the user's prompt, searches stored code chunks by cosine similarity,
and injects relevant codebase context into the conversation.
"""

import json
import logging
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.platform_utils import get_data_dir, get_plugin_root
from lib.config import load_config
from lib.db import get_connection
from lib.embedder import embed_single, cosine_similarity

logging.basicConfig(level=logging.WARNING, format="%(name)s: %(message)s", stream=sys.stderr)
logger = logging.getLogger("contextforge.rag_retrieve")

# Patterns to skip
SKIP_PATTERNS = [
    re.compile(r"^/"),                          # slash commands
    re.compile(r"^(hi|hello|hey|thanks|ok|yes|no|sure)\b", re.IGNORECASE),
    re.compile(r"^(what time|how are you|tell me a joke)", re.IGNORECASE),
]


def should_skip(prompt):
    """Check if prompt should be skipped for RAG."""
    if not prompt or len(prompt.strip()) < 10:
        return True
    for pattern in SKIP_PATTERNS:
        if pattern.search(prompt.strip()):
            return True
    return False


def retrieve_chunks(query_embedding, db_path, config):
    """Find relevant chunks by cosine similarity."""
    import numpy as np

    threshold = config.get("retrieval", {}).get("relevance_threshold", 0.3)
    max_results = config.get("retrieval", {}).get("max_results", 5)

    rows = []
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "SELECT file_path, chunk_type, start_line, end_line, content, embedding FROM code_chunks WHERE embedding IS NOT NULL"
        )
        rows = cursor.fetchall()

    if not rows:
        return []

    # Build corpus matrix
    embeddings = []
    valid_rows = []
    dim = len(query_embedding)

    for row in rows:
        emb_blob = row[5]
        if emb_blob:
            emb = np.frombuffer(emb_blob, dtype=np.float32)
            if len(emb) == dim:
                embeddings.append(emb)
                valid_rows.append(row)

    if not embeddings:
        return []

    corpus = np.vstack(embeddings)
    scores = cosine_similarity(query_embedding, corpus)

    # Filter and sort
    results = []
    for i, score in enumerate(scores):
        if score >= threshold:
            row = valid_rows[i]
            results.append({
                "file_path": row[0],
                "chunk_type": row[1],
                "start_line": row[2],
                "end_line": row[3],
                "content": row[4],
                "relevance": round(float(score), 3),
            })

    results.sort(key=lambda x: x["relevance"], reverse=True)
    return results[:max_results]


def format_context(results, config):
    """Format retrieved chunks as context text."""
    if not results:
        return ""

    max_tokens = config.get("retrieval", {}).get("max_context_tokens", 2000)
    max_chars = max_tokens * 4  # rough estimate

    lines = ["## RELEVANT CODEBASE CONTEXT"]
    char_count = 0

    for r in results:
        header = f"\n### {r['file_path']} (lines {r['start_line']}-{r['end_line']}, relevance: {r['relevance']})"
        content = f"```\n{r['content']}\n```"
        section = header + "\n" + content

        if char_count + len(section) > max_chars:
            break

        lines.append(section)
        char_count += len(section)

    return "\n".join(lines)


def main():
    """Main RAG retrieval handler."""
    try:
        stdin_data = sys.stdin.read()
        try:
            hook_input = json.loads(stdin_data) if stdin_data.strip() else {}
        except json.JSONDecodeError:
            hook_input = {}

        # UserPromptSubmit hook stdin provides the user's text in "prompt"
        prompt = hook_input.get("prompt", "")

        if should_skip(prompt):
            print(json.dumps({}))
            return

        data_dir = get_data_dir()
        plugin_root = get_plugin_root()
        config = load_config(plugin_root, data_dir)
        config["data_dir"] = str(data_dir)  # For embedder model cache

        db_path = data_dir / "embeddings.db"
        if not db_path.exists():
            print(json.dumps({}))
            return

        # Embed the prompt
        query_emb = embed_single(prompt, config)
        if query_emb is None:
            print(json.dumps({}))
            return

        # Retrieve similar chunks
        results = retrieve_chunks(query_emb, db_path, config)
        context_text = format_context(results, config)

        if context_text:
            output = {
                "hookSpecificOutput": {
                    "hookEventName": "UserPromptSubmit",
                    "additionalContext": context_text,
                }
            }
        else:
            output = {}

        print(json.dumps(output))

    except Exception as e:
        logger.error("RAG retrieval failed: %s", e)
        print(json.dumps({}))


if __name__ == "__main__":
    main()

"""Codebase parsing and chunking for ContextForge.

Provides multiple strategies for splitting source files into semantic
chunks suitable for embedding:

1. Tree-sitter (primary) -- uses AST parsing for accurate boundaries
2. Regex fallback -- pattern-based splitting on definition keywords
3. Simple sliding window -- line-based chunking as a last resort

All path handling uses pathlib.Path for cross-platform compatibility.
"""

import hashlib
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tree-sitter language mapping
# ---------------------------------------------------------------------------

LANGUAGE_MAP: Dict[str, str] = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".rb": "ruby",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".hpp": "cpp",
    ".cs": "c_sharp",
    ".php": "php",
    ".scala": "scala",
    ".swift": "swift",
    ".kt": "kotlin",
    ".ex": "elixir",
    ".exs": "elixir",
}

# ---------------------------------------------------------------------------
# Tree-sitter chunking (lazy import)
# ---------------------------------------------------------------------------

_tree_sitter_available: Optional[bool] = None


def _check_tree_sitter() -> bool:
    """Check whether tree-sitter is available (cached)."""
    global _tree_sitter_available
    if _tree_sitter_available is None:
        try:
            import tree_sitter  # noqa: F401
            _tree_sitter_available = True
            logger.debug("tree-sitter is available")
        except ImportError:
            _tree_sitter_available = False
            logger.debug("tree-sitter is not available, will use fallbacks")
    return _tree_sitter_available


def _treesitter_chunk(content: str, language: str) -> Optional[List[Dict[str, Any]]]:
    """Use tree-sitter to extract top-level function and class chunks.

    Args:
        content: The full file content.
        language: The tree-sitter language name (e.g. ``"python"``).

    Returns:
        A list of chunk dicts, or None if tree-sitter parsing fails.
    """
    if not _check_tree_sitter():
        return None

    try:
        import tree_sitter_languages  # noqa: F401
        parser_get = tree_sitter_languages.get_parser
        lang_get = tree_sitter_languages.get_language
    except ImportError:
        logger.debug("tree_sitter_languages not available")
        return None

    try:
        parser = parser_get(language)
        ts_language = lang_get(language)
    except Exception as exc:
        logger.debug("Could not load tree-sitter parser for %s: %s", language, exc)
        return None

    try:
        tree = parser.parse(content.encode("utf-8"))
    except Exception as exc:
        logger.debug("tree-sitter parse failed for %s: %s", language, exc)
        return None

    chunks: List[Dict[str, Any]] = []
    lines = content.splitlines(keepends=True)

    # Walk top-level children looking for function/class definitions
    top_level_types = {
        "function_definition",
        "class_definition",
        "function_declaration",
        "class_declaration",
        "method_definition",
        "method_declaration",
        "decorated_definition",
        "export_statement",
        "lexical_declaration",
        "variable_declaration",
    }

    root = tree.root_node
    for child in root.children:
        if child.type in top_level_types:
            start_line = child.start_point[0]
            end_line = child.end_point[0]
            chunk_lines = lines[start_line : end_line + 1]
            chunk_content = "".join(chunk_lines)

            # Determine chunk type from node type
            chunk_type = "function"
            if "class" in child.type:
                chunk_type = "class"
            elif "export" in child.type or "variable" in child.type or "lexical" in child.type:
                chunk_type = "declaration"

            chunks.append({
                "content": chunk_content,
                "type": chunk_type,
                "start_line": start_line + 1,  # 1-indexed
                "end_line": end_line + 1,
            })

    if chunks:
        logger.debug(
            "tree-sitter extracted %d chunks for language %s", len(chunks), language
        )
    else:
        logger.debug("tree-sitter found no top-level definitions for %s", language)
        return None

    return chunks


# ---------------------------------------------------------------------------
# Regex-based chunking fallback
# ---------------------------------------------------------------------------

_DEFINITION_PATTERN = re.compile(
    r"^(def |class |function |async function |export |const |module )",
    re.MULTILINE,
)


def _regex_chunk(content: str, file_ext: str) -> Optional[List[Dict[str, Any]]]:
    """Split content into chunks based on definition keyword patterns.

    Looks for lines starting with common definition keywords and treats
    each as the beginning of a new chunk.

    Args:
        content: The full file content.
        file_ext: The file extension (e.g. ``".py"``), currently unused
            but available for future language-specific patterns.

    Returns:
        A list of chunk dicts, or None if no definition boundaries found.
    """
    lines = content.splitlines(keepends=True)
    if not lines:
        return None

    # Find all line indices that match a definition pattern
    boundaries: List[int] = []
    for i, line in enumerate(lines):
        if _DEFINITION_PATTERN.match(line):
            boundaries.append(i)

    if not boundaries:
        return None

    chunks: List[Dict[str, Any]] = []

    for idx, start in enumerate(boundaries):
        # Chunk extends to the line before the next boundary, or to EOF
        if idx + 1 < len(boundaries):
            end = boundaries[idx + 1] - 1
        else:
            end = len(lines) - 1

        chunk_content = "".join(lines[start : end + 1])

        # Determine type from the first keyword
        first_line = lines[start].strip()
        if first_line.startswith("class "):
            chunk_type = "class"
        elif first_line.startswith(("def ", "function ", "async function ")):
            chunk_type = "function"
        else:
            chunk_type = "declaration"

        chunks.append({
            "content": chunk_content,
            "type": chunk_type,
            "start_line": start + 1,  # 1-indexed
            "end_line": end + 1,
        })

    logger.debug("Regex chunking produced %d chunks", len(chunks))
    return chunks


# ---------------------------------------------------------------------------
# Simple sliding-window chunking
# ---------------------------------------------------------------------------


def _simple_chunk(
    content: str, max_lines: int = 50, overlap: int = 5
) -> List[Dict[str, Any]]:
    """Split content into fixed-size overlapping chunks.

    Args:
        content: The full file content.
        max_lines: Maximum number of lines per chunk.
        overlap: Number of overlapping lines between consecutive chunks.

    Returns:
        A list of chunk dicts. Always returns at least one chunk if
        content is non-empty.
    """
    lines = content.splitlines(keepends=True)
    if not lines:
        return []

    chunks: List[Dict[str, Any]] = []
    start = 0
    step = max(1, max_lines - overlap)

    while start < len(lines):
        end = min(start + max_lines, len(lines))
        chunk_content = "".join(lines[start:end])

        chunks.append({
            "content": chunk_content,
            "type": "block",
            "start_line": start + 1,  # 1-indexed
            "end_line": end,
        })

        start += step

    logger.debug("Simple chunking produced %d chunks", len(chunks))
    return chunks


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def chunk_file(
    file_path: Path,
    content: str,
    config: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Chunk a source file into semantic pieces for embedding.

    Strategy cascade:
        1. Tree-sitter (if available and language is supported)
        2. Regex-based definition splitting
        3. Simple sliding-window chunking

    Each returned chunk dict contains:
        - ``content`` (str): The chunk text.
        - ``type`` (str): e.g. ``"function"``, ``"class"``, ``"block"``.
        - ``start_line`` (int): 1-indexed starting line number.
        - ``end_line`` (int): 1-indexed ending line number.
        - ``hash`` (str): SHA-256 hex digest of the content.

    Args:
        file_path: Path to the source file (used for extension detection).
        content: The full file content as a string.
        config: Optional configuration dict. Supports keys under
            ``"indexing"`` such as ``chunk_max_lines`` and
            ``chunk_overlap_lines``.

    Returns:
        A list of chunk dictionaries.
    """
    file_path = Path(file_path)
    ext = file_path.suffix.lower()

    # Read chunking parameters from config
    max_lines = 50
    overlap = 5
    if config and "indexing" in config:
        max_lines = config["indexing"].get("chunk_max_lines", max_lines)
        overlap = config["indexing"].get("chunk_overlap_lines", overlap)

    chunks: Optional[List[Dict[str, Any]]] = None

    # Strategy 1: Tree-sitter
    language = LANGUAGE_MAP.get(ext)
    if language and _check_tree_sitter():
        chunks = _treesitter_chunk(content, language)

    # Strategy 2: Regex
    if chunks is None:
        chunks = _regex_chunk(content, ext)

    # Strategy 3: Simple sliding window
    if chunks is None:
        chunks = _simple_chunk(content, max_lines=max_lines, overlap=overlap)

    # Add content hashes
    for chunk in chunks:
        chunk["hash"] = hashlib.sha256(
            chunk["content"].encode("utf-8")
        ).hexdigest()

    logger.debug(
        "Chunked %s into %d pieces (ext=%s)", file_path.name, len(chunks), ext
    )
    return chunks

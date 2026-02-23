"""Knowledge graph builder for ContextForge.

Builds and maintains a lightweight file-level knowledge graph stored
as JSON. The graph tracks files, their metadata (classes, functions,
imports), file types, and inter-file edges (dependency relationships).

All path handling uses pathlib.Path for cross-platform compatibility.
"""

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Graph persistence
# ---------------------------------------------------------------------------


def load_graph(data_dir: Path) -> Dict[str, Any]:
    """Load the knowledge graph from disk.

    Args:
        data_dir: Path to the .contextforge data directory.

    Returns:
        The graph dict with keys ``"files"``, ``"edges"``, and
        ``"metadata"``. Returns a default empty graph if the file
        does not exist or cannot be parsed.
    """
    data_dir = Path(data_dir)
    graph_path = data_dir / "graph.json"

    default_graph: Dict[str, Any] = {
        "files": {},
        "edges": [],
        "metadata": {},
    }

    if not graph_path.is_file():
        logger.debug("No graph file found at %s, returning empty graph", graph_path)
        return default_graph

    try:
        data = json.loads(graph_path.read_text(encoding="utf-8"))
        # Ensure required keys exist
        for key in ("files", "edges", "metadata"):
            if key not in data:
                data[key] = default_graph[key]
        logger.debug("Loaded graph with %d files", len(data["files"]))
        return data
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Failed to load graph from %s: %s", graph_path, exc)
        return default_graph


def save_graph(data_dir: Path, graph: Dict[str, Any]) -> None:
    """Save the knowledge graph to disk.

    Args:
        data_dir: Path to the .contextforge data directory.
        graph: The graph dict to persist.
    """
    data_dir = Path(data_dir)
    graph_path = data_dir / "graph.json"

    try:
        data_dir.mkdir(parents=True, exist_ok=True)
        graph_path.write_text(
            json.dumps(graph, indent=2), encoding="utf-8"
        )
        logger.debug("Saved graph with %d files", len(graph.get("files", {})))
    except OSError as exc:
        logger.error("Failed to save graph to %s: %s", graph_path, exc)
        raise


# ---------------------------------------------------------------------------
# File metadata extraction
# ---------------------------------------------------------------------------

_CLASS_PATTERN = re.compile(r"class\s+(\w+)")
_FUNCTION_PATTERNS = [
    re.compile(r"def\s+(\w+)"),
    re.compile(r"function\s+(\w+)"),
    re.compile(r"const\s+(\w+)\s*="),
]
_IMPORT_PATTERNS = [
    re.compile(r"^import\s+(\S+)", re.MULTILINE),
    re.compile(r"^from\s+(\S+)\s+import", re.MULTILINE),
    re.compile(r"require\(['\"](.+?)['\"]\)", re.MULTILINE),
]


def extract_file_metadata(
    file_path: Path, content: str
) -> Dict[str, List[str]]:
    """Extract classes, functions, and imports from file content.

    Uses regex patterns to identify definitions. This is a lightweight
    heuristic -- not a full parser.

    Args:
        file_path: Path to the file (currently used for logging).
        content: The full file content.

    Returns:
        A dict with keys ``"classes"``, ``"functions"``, and
        ``"imports"``, each containing a list of name strings.
    """
    file_path = Path(file_path)

    classes = _CLASS_PATTERN.findall(content)

    functions: List[str] = []
    for pattern in _FUNCTION_PATTERNS:
        functions.extend(pattern.findall(content))

    imports: List[str] = []
    for pattern in _IMPORT_PATTERNS:
        imports.extend(pattern.findall(content))

    logger.debug(
        "Extracted metadata from %s: %d classes, %d functions, %d imports",
        file_path.name,
        len(classes),
        len(functions),
        len(imports),
    )

    return {
        "classes": classes,
        "functions": functions,
        "imports": imports,
    }


# ---------------------------------------------------------------------------
# File type classification
# ---------------------------------------------------------------------------

_FILE_TYPE_PATTERNS: List[tuple] = [
    (re.compile(r"(?:^|/)test|_test\.|\.test\.", re.IGNORECASE), "test"),
    (re.compile(r"(?:^|/)(models?|schemas?|entit(?:y|ies))(?:/|\.|\b)", re.IGNORECASE), "model"),
    (re.compile(r"(?:^|/)(services?|managers?)(?:/|\.|\b)", re.IGNORECASE), "service"),
    (re.compile(r"(?:^|/)(controllers?|handlers?|routes?|views?)(?:/|\.|\b)", re.IGNORECASE), "controller"),
    (re.compile(r"(?:^|/)(config|settings?)(?:/|\.|\b)", re.IGNORECASE), "config"),
    (re.compile(r"(?:^|/)(docs?|readme)(?:/|\.|\b)", re.IGNORECASE), "docs"),
]


def classify_file_type(file_path) -> str:
    """Classify a file based on its path components.

    Matches against common naming patterns to categorize files into
    architectural roles.

    Args:
        file_path: Path to the file (string or Path object).

    Returns:
        One of: ``"test"``, ``"model"``, ``"service"``,
        ``"controller"``, ``"config"``, ``"docs"``, or ``"source"``.
    """
    # Use the string directly to preserve forward slashes on Windows
    path_str = str(file_path)

    for pattern, file_type in _FILE_TYPE_PATTERNS:
        if pattern.search(path_str):
            return file_type

    return "source"


# ---------------------------------------------------------------------------
# Graph mutation
# ---------------------------------------------------------------------------


def update_graph_for_file(
    graph: Dict[str, Any], file_path: str, content: str
) -> None:
    """Add or update a file node in the knowledge graph.

    Extracts metadata and file type classification, then stores or
    updates the file entry in the graph's ``"files"`` dict.

    Args:
        graph: The knowledge graph dict (mutated in place).
        file_path: The relative file path string (used as the key).
        content: The full file content.
    """
    metadata = extract_file_metadata(Path(file_path), content)
    file_type = classify_file_type(Path(file_path))

    graph["files"][file_path] = {
        "type": file_type,
        "classes": metadata["classes"],
        "functions": metadata["functions"],
        "imports": metadata["imports"],
    }

    logger.debug("Updated graph node for %s (type=%s)", file_path, file_type)


def remove_file_from_graph(graph: Dict[str, Any], file_path: str) -> None:
    """Remove a file node and its edges from the knowledge graph.

    Args:
        graph: The knowledge graph dict (mutated in place).
        file_path: The relative file path string to remove.
    """
    if file_path in graph["files"]:
        del graph["files"][file_path]
        logger.debug("Removed graph node for %s", file_path)

    # Remove edges involving this file
    original_count = len(graph["edges"])
    graph["edges"] = [
        edge
        for edge in graph["edges"]
        if edge.get("source") != file_path and edge.get("target") != file_path
    ]
    removed = original_count - len(graph["edges"])
    if removed:
        logger.debug("Removed %d edges involving %s", removed, file_path)


# ---------------------------------------------------------------------------
# Graph summary
# ---------------------------------------------------------------------------


def generate_summary(graph: Dict[str, Any]) -> str:
    """Produce a compact architectural summary of the codebase.

    Generates a human-readable summary (~200-400 tokens) listing:
        - File type counts
        - Key classes and services
        - Main import dependencies

    Args:
        graph: The knowledge graph dict.

    Returns:
        A formatted summary string.
    """
    files = graph.get("files", {})
    if not files:
        return "No files indexed yet."

    # Count file types
    type_counts: Dict[str, int] = {}
    all_classes: List[str] = []
    all_services: List[str] = []
    all_imports: List[str] = []

    for file_path, info in files.items():
        file_type = info.get("type", "source")
        type_counts[file_type] = type_counts.get(file_type, 0) + 1

        all_classes.extend(info.get("classes", []))

        # Collect functions from service files
        if file_type == "service":
            all_services.append(Path(file_path).stem)

        all_imports.extend(info.get("imports", []))

    # Build summary (no top-level header — caller adds its own)
    parts: List[str] = []

    # File type counts
    parts.append("### File Distribution")
    for file_type, count in sorted(type_counts.items(), key=lambda x: -x[1]):
        parts.append(f"  - {file_type}: {count} files")

    # Key classes
    if all_classes:
        unique_classes = sorted(set(all_classes))
        display = unique_classes[:15]
        parts.append("")
        parts.append("### Key Classes")
        parts.append(f"  {', '.join(display)}")
        if len(unique_classes) > 15:
            parts.append(f"  ... and {len(unique_classes) - 15} more")

    # Services
    if all_services:
        unique_services = sorted(set(all_services))
        parts.append("")
        parts.append("### Services")
        parts.append(f"  {', '.join(unique_services)}")

    # Top imports
    if all_imports:
        import_counts: Dict[str, int] = {}
        for imp in all_imports:
            # Normalize to top-level package
            top_level = imp.split(".")[0].split("/")[0]
            import_counts[top_level] = import_counts.get(top_level, 0) + 1
        top_imports = sorted(import_counts.items(), key=lambda x: -x[1])[:10]
        parts.append("")
        parts.append("### Main Dependencies")
        for name, count in top_imports:
            parts.append(f"  - {name} (referenced {count}x)")

    summary = "\n".join(parts)
    logger.debug("Generated summary: %d chars", len(summary))
    return summary

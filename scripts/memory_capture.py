#!/usr/bin/env python3
"""ContextForge memory capture hook (PostToolUse on Write|Edit).

Extracts coding conventions from file changes and records them
in the memory database for persistent cross-session learning.
"""

import json
import logging
import os
import re
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.platform_utils import get_data_dir, get_plugin_root, get_project_dir, is_safe_path
from lib.config import load_config
from lib.db import init_memory_db, get_connection
from lib.memory_store import record_file_change, upsert_convention

logging.basicConfig(level=logging.WARNING, format="%(name)s: %(message)s", stream=sys.stderr)
logger = logging.getLogger("contextforge.memory_capture")

# File patterns to skip
SKIP_PATTERNS = [
    re.compile(r"\.(lock|min\.js|min\.css|map|png|jpg|gif|ico|woff|ttf|eot|svg|pdf|zip|tar|gz)$"),
    re.compile(r"node_modules/"),
    re.compile(r"__pycache__/"),
    re.compile(r"\.contextforge/"),
    re.compile(r"package-lock\.json$"),
    re.compile(r"yarn\.lock$"),
    re.compile(r"Pipfile\.lock$"),
    re.compile(r"poetry\.lock$"),
]

# Convention extraction rules
CONVENTION_RULES = [
    {
        "pattern": re.compile(r"class\s+\w+Service\b"),
        "type": "service_pattern",
        "description": "Uses Service class pattern for business logic",
    },
    {
        "pattern": re.compile(r"class\s+\w+Model\b|class\s+\w+\(.*Model\)"),
        "type": "model_pattern",
        "description": "Uses Model class pattern for data entities",
    },
    {
        "pattern": re.compile(r"class\s+\w+Factory\b|def\s+\w+_factory\b|FactoryBot|factory_boy"),
        "type": "test_factories",
        "description": "Uses factory pattern for test data generation",
    },
    {
        "pattern": re.compile(r"uuid\.|UUID|uuid4|uuid_generate"),
        "type": "uuid_keys",
        "description": "Uses UUID for primary/unique keys",
    },
    {
        "pattern": re.compile(r"celery|sidekiq|resque|delayed_job|background_task|@task\b|\.delay\("),
        "type": "background_jobs",
        "description": "Uses background job processing",
    },
    {
        "pattern": re.compile(r"@app\.(get|post|put|delete|patch)|router\.(get|post|put|delete)|@api_view"),
        "type": "api_pattern",
        "description": "Uses decorator-based API route definitions",
    },
    {
        "pattern": re.compile(r"class\s+\w+Serializer\b|class\s+\w+Schema\b"),
        "type": "serializer_pattern",
        "description": "Uses serializer/schema pattern for data transformation",
    },
    {
        "pattern": re.compile(r"class\s+\w+Repository\b|class\s+\w+Repo\b"),
        "type": "repository_pattern",
        "description": "Uses repository pattern for data access",
    },
    {
        "pattern": re.compile(r"describe\(|it\(|test\(|def\s+test_"),
        "type": "test_style",
        "description": "Test file structure detected",
    },
    {
        "pattern": re.compile(r"typing\.|TypeVar|Generic\[|Protocol\b|from typing import"),
        "type": "type_annotations",
        "description": "Uses Python type annotations/hints",
    },
]


def should_skip(file_path):
    """Check if file should be skipped for convention capture."""
    if not file_path:
        return True
    for pattern in SKIP_PATTERNS:
        if pattern.search(file_path):
            return True
    return False


def extract_conventions(content, file_path):
    """Extract coding conventions from file content."""
    conventions = []
    for rule in CONVENTION_RULES:
        match = rule["pattern"].search(content)
        if match:
            # Extract a short example around the match
            start = max(0, match.start() - 20)
            end = min(len(content), match.end() + 40)
            example = content[start:end].strip().split("\n")[0]
            conventions.append({
                "type": rule["type"],
                "description": rule["description"],
                "example": example,
            })
    return conventions


def main():
    """Main memory capture handler."""
    try:
        stdin_data = sys.stdin.read()
        try:
            hook_input = json.loads(stdin_data) if stdin_data.strip() else {}
        except json.JSONDecodeError:
            return

        # Extract file path and content from tool input
        tool_input = hook_input.get("tool_input", {})
        if isinstance(tool_input, str):
            try:
                tool_input = json.loads(tool_input)
            except json.JSONDecodeError:
                return

        raw_file_path = tool_input.get("file_path", "")
        # Write tool provides "content"; Edit tool provides "old_string"/"new_string"
        content = tool_input.get("content", "")

        if not raw_file_path:
            return

        # Convert absolute path to relative for consistency with index keys
        project_dir = get_project_dir()
        try:
            file_path = Path(raw_file_path).resolve().relative_to(project_dir.resolve()).as_posix()
        except ValueError:
            file_path = Path(raw_file_path).as_posix()

        if should_skip(file_path):
            return

        # For Edit tool or when content is missing, read the full file from disk
        # so we can extract conventions from the complete file
        if not content:
            new_str = tool_input.get("new_string", "")
            if new_str:
                # Use the new_string as a hint, but try reading the full file
                try:
                    full_path = project_dir / file_path
                    if full_path.exists() and is_safe_path(project_dir, full_path):
                        content = full_path.read_text(encoding="utf-8", errors="replace")
                    else:
                        content = new_str
                except OSError:
                    content = new_str

        data_dir = get_data_dir()
        db_path = data_dir / "memory.db"

        # Ensure database exists
        if not db_path.exists():
            init_memory_db(db_path)

        # Record file change
        session_id = os.environ.get("CLAUDE_SESSION_ID", str(uuid.uuid4())[:8])
        record_file_change(db_path, file_path, session_id)

        # Extract and store conventions
        if content:
            conventions = extract_conventions(content, file_path)
            for conv in conventions:
                upsert_convention(db_path, conv["type"], conv["description"], conv["example"])

    except Exception as e:
        logger.error("Memory capture failed: %s", e)

    # PostToolUse hooks output empty JSON for clean protocol compliance
    print("{}")


if __name__ == "__main__":
    main()

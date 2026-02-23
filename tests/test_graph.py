"""Tests for scripts/lib/graph.py."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from lib.graph import (
    load_graph,
    save_graph,
    extract_file_metadata,
    classify_file_type,
    update_graph_for_file,
    remove_file_from_graph,
    generate_summary,
)


class TestLoadSaveGraph:
    def test_load_empty_dir(self, tmp_path):
        graph = load_graph(tmp_path)
        assert graph == {"files": {}, "edges": [], "metadata": {}}

    def test_save_and_load(self, tmp_path):
        graph = {
            "files": {"app.py": {"type": "source", "classes": [], "functions": ["main"], "imports": []}},
            "edges": [{"source": "app.py", "target": "utils.py"}],
            "metadata": {"version": 1},
        }
        save_graph(tmp_path, graph)
        loaded = load_graph(tmp_path)
        assert loaded == graph

    def test_load_corrupt_json(self, tmp_path):
        (tmp_path / "graph.json").write_text("not json", encoding="utf-8")
        graph = load_graph(tmp_path)
        assert graph == {"files": {}, "edges": [], "metadata": {}}

    def test_load_incomplete_graph(self, tmp_path):
        (tmp_path / "graph.json").write_text('{"files": {}}', encoding="utf-8")
        graph = load_graph(tmp_path)
        assert "edges" in graph
        assert "metadata" in graph


class TestExtractFileMetadata:
    def test_python_classes_and_functions(self):
        content = (
            "import os\nfrom pathlib import Path\n\n"
            "class MyService:\n"
            "    def process(self):\n"
            "        pass\n\n"
            "def helper():\n"
            "    pass\n"
        )
        meta = extract_file_metadata("app.py", content)
        assert "MyService" in meta["classes"]
        assert "process" in meta["functions"]
        assert "helper" in meta["functions"]
        assert "os" in meta["imports"]
        assert "pathlib" in meta["imports"]

    def test_javascript_patterns(self):
        content = (
            "const express = require('express');\n"
            "function handleRequest() {}\n"
            "const router = express.Router();\n"
        )
        meta = extract_file_metadata("server.js", content)
        assert "handleRequest" in meta["functions"]
        assert "express" in meta["imports"]

    def test_empty_content(self):
        meta = extract_file_metadata("empty.py", "")
        assert meta == {"classes": [], "functions": [], "imports": []}


class TestClassifyFileType:
    def test_test_file(self):
        assert classify_file_type("tests/test_app.py") == "test"

    def test_model_file(self):
        assert classify_file_type("models/user.py") == "model"

    def test_service_file(self):
        assert classify_file_type("services/auth_service.py") == "service"

    def test_controller_file(self):
        assert classify_file_type("controllers/user_controller.py") == "controller"

    def test_route_file(self):
        assert classify_file_type("routes/api.py") == "controller"

    def test_config_file(self):
        assert classify_file_type("config/database.py") == "config"

    def test_settings_file(self):
        assert classify_file_type("settings.py") == "config"

    def test_docs_file(self):
        assert classify_file_type("docs/guide.md") == "docs"

    def test_readme_file(self):
        assert classify_file_type("README.md") == "docs"

    def test_generic_source(self):
        assert classify_file_type("lib/utils.py") == "source"


class TestUpdateAndRemoveGraphFile:
    def test_update_adds_file(self):
        graph = {"files": {}, "edges": [], "metadata": {}}
        content = "class Foo:\n    pass\n\ndef bar():\n    pass\n"
        update_graph_for_file(graph, "app.py", content)
        assert "app.py" in graph["files"]
        assert "Foo" in graph["files"]["app.py"]["classes"]
        assert "bar" in graph["files"]["app.py"]["functions"]

    def test_update_replaces_existing(self):
        graph = {"files": {"app.py": {"type": "source", "classes": ["Old"], "functions": [], "imports": []}}, "edges": [], "metadata": {}}
        update_graph_for_file(graph, "app.py", "class New:\n    pass\n")
        assert "New" in graph["files"]["app.py"]["classes"]
        assert "Old" not in graph["files"]["app.py"]["classes"]

    def test_remove_file(self):
        graph = {
            "files": {"a.py": {"type": "source"}, "b.py": {"type": "source"}},
            "edges": [{"source": "a.py", "target": "b.py"}, {"source": "c.py", "target": "d.py"}],
            "metadata": {},
        }
        remove_file_from_graph(graph, "a.py")
        assert "a.py" not in graph["files"]
        assert len(graph["edges"]) == 1

    def test_remove_nonexistent_file(self):
        graph = {"files": {}, "edges": [], "metadata": {}}
        remove_file_from_graph(graph, "missing.py")  # Should not raise


class TestGenerateSummary:
    def test_empty_graph(self):
        graph = {"files": {}, "edges": [], "metadata": {}}
        summary = generate_summary(graph)
        assert "No files indexed" in summary

    def test_summary_contains_file_types(self):
        graph = {
            "files": {
                "models/user.py": {"type": "model", "classes": ["User"], "functions": [], "imports": ["sqlalchemy"]},
                "services/auth.py": {"type": "service", "classes": ["AuthService"], "functions": ["login"], "imports": ["jwt"]},
                "tests/test_auth.py": {"type": "test", "classes": [], "functions": ["test_login"], "imports": ["pytest"]},
            },
            "edges": [],
            "metadata": {},
        }
        summary = generate_summary(graph)
        assert "model" in summary
        assert "service" in summary
        assert "test" in summary
        assert "User" in summary or "AuthService" in summary
        assert "auth" in summary.lower()

    def test_summary_limits_classes(self):
        files = {}
        for i in range(20):
            files[f"file{i}.py"] = {
                "type": "source",
                "classes": [f"Class{i}"],
                "functions": [],
                "imports": [],
            }
        graph = {"files": files, "edges": [], "metadata": {}}
        summary = generate_summary(graph)
        assert "more" in summary  # Should indicate truncation

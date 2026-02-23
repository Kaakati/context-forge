"""Tests for scripts/lib/indexer.py."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from lib.indexer import chunk_file, _regex_chunk, _simple_chunk, LANGUAGE_MAP


class TestLanguageMap:
    def test_python_mapping(self):
        assert LANGUAGE_MAP[".py"] == "python"

    def test_javascript_mapping(self):
        assert LANGUAGE_MAP[".js"] == "javascript"
        assert LANGUAGE_MAP[".jsx"] == "javascript"

    def test_typescript_mapping(self):
        assert LANGUAGE_MAP[".ts"] == "typescript"
        assert LANGUAGE_MAP[".tsx"] == "typescript"

    def test_all_expected_extensions(self):
        expected = {
            ".py", ".js", ".jsx", ".ts", ".tsx", ".rb", ".go", ".rs",
            ".java", ".c", ".h", ".cpp", ".hpp", ".cs", ".php",
            ".scala", ".swift", ".kt", ".ex", ".exs",
        }
        assert expected == set(LANGUAGE_MAP.keys())


class TestRegexChunk:
    def test_python_functions(self):
        content = (
            "import os\n\n"
            "def hello():\n"
            "    print('hello')\n\n"
            "def world():\n"
            "    print('world')\n"
        )
        chunks = _regex_chunk(content, ".py")
        assert chunks is not None
        assert len(chunks) == 2
        assert chunks[0]["type"] == "function"
        assert "hello" in chunks[0]["content"]
        assert chunks[1]["type"] == "function"
        assert "world" in chunks[1]["content"]

    def test_python_class(self):
        content = (
            "class MyClass:\n"
            "    def method(self):\n"
            "        pass\n"
        )
        chunks = _regex_chunk(content, ".py")
        assert chunks is not None
        assert len(chunks) == 1
        assert chunks[0]["type"] == "class"

    def test_no_definitions(self):
        content = "x = 1\ny = 2\nprint(x + y)\n"
        chunks = _regex_chunk(content, ".py")
        assert chunks is None

    def test_empty_content(self):
        chunks = _regex_chunk("", ".py")
        assert chunks is None

    def test_javascript_functions(self):
        content = (
            "const a = 1;\n\n"
            "function greet() {\n"
            "  return 'hi';\n"
            "}\n\n"
            "async function fetchData() {\n"
            "  return await fetch();\n"
            "}\n"
        )
        chunks = _regex_chunk(content, ".js")
        assert chunks is not None
        assert len(chunks) == 3  # const, function, async function


class TestSimpleChunk:
    def test_small_file_single_chunk(self):
        content = "line1\nline2\nline3\n"
        chunks = _simple_chunk(content, max_lines=50, overlap=5)
        assert len(chunks) == 1
        assert chunks[0]["start_line"] == 1

    def test_large_file_multiple_chunks(self):
        content = "\n".join(f"line {i}" for i in range(100)) + "\n"
        chunks = _simple_chunk(content, max_lines=20, overlap=5)
        assert len(chunks) > 1
        # Verify overlap
        assert chunks[0]["end_line"] >= 20
        assert chunks[1]["start_line"] < 20

    def test_empty_content(self):
        chunks = _simple_chunk("", max_lines=50)
        assert chunks == []

    def test_type_is_block(self):
        content = "line1\nline2\n"
        chunks = _simple_chunk(content)
        assert all(c["type"] == "block" for c in chunks)


class TestChunkFile:
    def test_returns_list_with_hashes(self):
        content = "def hello():\n    pass\n\ndef world():\n    pass\n"
        chunks = chunk_file("test.py", content)
        assert len(chunks) > 0
        for chunk in chunks:
            assert "content" in chunk
            assert "type" in chunk
            assert "start_line" in chunk
            assert "end_line" in chunk
            assert "hash" in chunk
            assert len(chunk["hash"]) == 64  # SHA-256 hex

    def test_hash_is_deterministic(self):
        content = "def hello():\n    pass\n"
        chunks1 = chunk_file("test.py", content)
        chunks2 = chunk_file("test.py", content)
        assert chunks1[0]["hash"] == chunks2[0]["hash"]

    def test_unknown_extension_uses_fallback(self):
        content = "some content\nthat doesn't\nmatch anything\n"
        chunks = chunk_file("file.xyz", content)
        assert len(chunks) > 0

    def test_config_chunking_params(self):
        content = "\n".join(f"line {i}" for i in range(100)) + "\n"
        config = {"indexing": {"chunk_max_lines": 10, "chunk_overlap_lines": 2}}
        chunks = chunk_file("data.txt", content, config)
        assert len(chunks) > 5  # Should produce many small chunks

    def test_pathlib_path_input(self):
        content = "def foo():\n    pass\n"
        chunks = chunk_file(Path("test.py"), content)
        assert len(chunks) > 0

"""Tests for scripts/lib/memory_store.py."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from lib.db import init_memory_db
from lib.memory_store import (
    record_file_change,
    upsert_convention,
    get_active_conventions,
    get_recent_files,
    generate_memory_summary,
)


@pytest.fixture
def mem_db(tmp_path):
    """Create and initialize a temporary memory database."""
    db_path = tmp_path / "memory.db"
    init_memory_db(db_path)
    return db_path


class TestRecordFileChange:
    def test_records_change(self, mem_db):
        record_file_change(mem_db, "app.py", "session-1")
        files = get_recent_files(mem_db, days=1)
        assert "app.py" in files

    def test_records_multiple_changes(self, mem_db):
        record_file_change(mem_db, "app.py", "s1")
        record_file_change(mem_db, "utils.py", "s1")
        record_file_change(mem_db, "app.py", "s2")
        files = get_recent_files(mem_db, days=1)
        assert len(files) == 2

    def test_none_session_id(self, mem_db):
        record_file_change(mem_db, "app.py")  # Should not raise
        files = get_recent_files(mem_db, days=1)
        assert "app.py" in files


class TestUpsertConvention:
    def test_insert_new_convention(self, mem_db):
        upsert_convention(mem_db, "naming", "Uses snake_case", "my_func")
        conventions = get_active_conventions(mem_db, min_frequency=1)
        assert len(conventions) == 1
        assert conventions[0]["pattern_type"] == "naming"
        assert conventions[0]["description"] == "Uses snake_case"
        assert conventions[0]["frequency"] == 1

    def test_increment_frequency(self, mem_db):
        upsert_convention(mem_db, "naming", "Uses snake_case", "a")
        upsert_convention(mem_db, "naming", "Uses snake_case", "b")
        upsert_convention(mem_db, "naming", "Uses snake_case", "c")
        conventions = get_active_conventions(mem_db, min_frequency=1)
        assert len(conventions) == 1
        assert conventions[0]["frequency"] == 3

    def test_different_descriptions_separate(self, mem_db):
        upsert_convention(mem_db, "naming", "Uses snake_case")
        upsert_convention(mem_db, "naming", "Uses camelCase")
        conventions = get_active_conventions(mem_db, min_frequency=1)
        assert len(conventions) == 2

    def test_no_example(self, mem_db):
        upsert_convention(mem_db, "style", "Tabs for indentation")
        conventions = get_active_conventions(mem_db, min_frequency=1)
        assert conventions[0]["example"] is None


class TestGetActiveConventions:
    def test_threshold_filter(self, mem_db):
        # Add convention with frequency 1
        upsert_convention(mem_db, "a", "low freq")
        # Add convention with frequency 3
        for _ in range(3):
            upsert_convention(mem_db, "b", "high freq")

        low = get_active_conventions(mem_db, min_frequency=1)
        assert len(low) == 2

        high = get_active_conventions(mem_db, min_frequency=3)
        assert len(high) == 1
        assert high[0]["pattern_type"] == "b"

    def test_ordered_by_frequency(self, mem_db):
        for _ in range(5):
            upsert_convention(mem_db, "a", "most common")
        for _ in range(3):
            upsert_convention(mem_db, "b", "less common")
        for _ in range(1):
            upsert_convention(mem_db, "c", "rare")

        conventions = get_active_conventions(mem_db, min_frequency=1)
        assert conventions[0]["description"] == "most common"
        assert conventions[1]["description"] == "less common"


class TestGetRecentFiles:
    def test_returns_recent_files(self, mem_db):
        record_file_change(mem_db, "a.py")
        record_file_change(mem_db, "b.py")
        files = get_recent_files(mem_db, days=1)
        assert set(files) == {"a.py", "b.py"}

    def test_limit(self, mem_db):
        for i in range(10):
            record_file_change(mem_db, f"file{i}.py")
        files = get_recent_files(mem_db, days=1, limit=3)
        assert len(files) == 3

    def test_empty_db(self, mem_db):
        files = get_recent_files(mem_db)
        assert files == []


class TestGenerateMemorySummary:
    def test_empty_db(self, mem_db):
        summary = generate_memory_summary(mem_db)
        assert "ESTABLISHED CONVENTIONS" in summary
        assert "RECENTLY MODIFIED FILES" in summary
        assert "No established conventions" in summary

    def test_with_data(self, mem_db):
        for _ in range(5):
            upsert_convention(mem_db, "style", "Uses type hints", "def foo(x: int)")
        record_file_change(mem_db, "app.py")

        summary = generate_memory_summary(mem_db)
        assert "type hints" in summary
        assert "app.py" in summary

    def test_config_threshold(self, mem_db):
        for _ in range(2):
            upsert_convention(mem_db, "x", "low freq convention")
        config = {"memory": {"convention_threshold": 5}}
        summary = generate_memory_summary(mem_db, config)
        assert "No established conventions" in summary

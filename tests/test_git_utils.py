"""Tests for scripts/lib/git_utils.py."""

import json
import sys
from pathlib import Path
from unittest import mock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from lib.git_utils import (
    is_git_repo,
    run_git,
    get_current_commit,
    get_changed_files,
    load_watermark,
    save_watermark,
)


class TestIsGitRepo:
    def test_true_when_git_repo(self):
        with mock.patch("subprocess.run") as mock_run:
            mock_run.return_value = mock.Mock(returncode=0, stdout="true\n", stderr="")
            assert is_git_repo() is True

    def test_false_when_not_git_repo(self):
        with mock.patch("subprocess.run") as mock_run:
            mock_run.return_value = mock.Mock(returncode=128, stdout="", stderr="fatal: not a git repository")
            assert is_git_repo() is False

    def test_false_when_git_not_installed(self):
        with mock.patch("subprocess.run", side_effect=FileNotFoundError):
            assert is_git_repo() is False

    def test_false_on_timeout(self):
        import subprocess
        with mock.patch("subprocess.run", side_effect=subprocess.TimeoutExpired("git", 5)):
            assert is_git_repo() is False


class TestRunGit:
    def test_successful_command(self):
        with mock.patch("subprocess.run") as mock_run:
            mock_run.return_value = mock.Mock(returncode=0, stdout="output\n", stderr="")
            result = run_git(["status"])
            assert result == "output"
            mock_run.assert_called_once()

    def test_failed_command_returns_none(self):
        with mock.patch("subprocess.run") as mock_run:
            mock_run.return_value = mock.Mock(returncode=1, stdout="", stderr="error")
            result = run_git(["invalid"])
            assert result is None

    def test_timeout_returns_none(self):
        import subprocess
        with mock.patch("subprocess.run", side_effect=subprocess.TimeoutExpired("git", 30)):
            result = run_git(["status"])
            assert result is None

    def test_git_not_found_returns_none(self):
        with mock.patch("subprocess.run", side_effect=FileNotFoundError):
            result = run_git(["status"])
            assert result is None

    def test_cwd_parameter(self, tmp_path):
        with mock.patch("subprocess.run") as mock_run:
            mock_run.return_value = mock.Mock(returncode=0, stdout="ok", stderr="")
            run_git(["status"], cwd=tmp_path)
            call_kwargs = mock_run.call_args
            assert call_kwargs.kwargs.get("cwd") == str(tmp_path) or call_kwargs[1].get("cwd") == str(tmp_path)


class TestGetCurrentCommit:
    def test_returns_commit_hash(self):
        with mock.patch("lib.git_utils.run_git", return_value="abc123def456"):
            result = get_current_commit()
            assert result == "abc123def456"

    def test_returns_none_on_error(self):
        with mock.patch("lib.git_utils.run_git", return_value=None):
            result = get_current_commit()
            assert result is None


class TestGetChangedFiles:
    def test_parses_diff_output(self):
        diff_output = "M\tfile1.py\nA\tfile2.py\nD\tfile3.py\nR100\told.py\tnew.py"
        with mock.patch("lib.git_utils.run_git", return_value=diff_output):
            result = get_changed_files("abc123")
            assert "file1.py" in result["modified"]
            assert "file2.py" in result["modified"]
            assert "file3.py" in result["deleted"]
            # Renamed: old path deleted, new path modified
            assert "old.py" in result["deleted"]
            assert "new.py" in result["modified"]

    def test_empty_diff(self):
        with mock.patch("lib.git_utils.run_git", return_value=""):
            result = get_changed_files("abc123")
            assert result == {"modified": [], "deleted": []}

    def test_git_error(self):
        with mock.patch("lib.git_utils.run_git", return_value=None):
            result = get_changed_files("abc123")
            assert result == {"modified": [], "deleted": []}


class TestWatermark:
    def test_save_and_load(self, tmp_path):
        save_watermark(tmp_path, "abc123def456")
        result = load_watermark(tmp_path)
        assert result["commit"] == "abc123def456"
        assert "timestamp" in result

    def test_load_missing_file(self, tmp_path):
        result = load_watermark(tmp_path)
        assert result == {}

    def test_load_corrupt_file(self, tmp_path):
        (tmp_path / "index_state.json").write_text("not json", encoding="utf-8")
        result = load_watermark(tmp_path)
        assert result == {}

    def test_save_creates_directory(self, tmp_path):
        data_dir = tmp_path / "nested" / "dir"
        save_watermark(data_dir, "abc123")
        result = load_watermark(data_dir)
        assert result["commit"] == "abc123"

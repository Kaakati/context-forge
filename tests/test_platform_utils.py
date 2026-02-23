"""Tests for scripts/lib/platform_utils.py."""

import os
import sys
import tempfile
from pathlib import Path
from unittest import mock

import pytest

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from lib.platform_utils import (
    get_project_dir,
    get_data_dir,
    get_plugin_root,
    get_venv_python,
    ensure_data_dir,
    is_safe_path,
)


class TestGetProjectDir:
    def test_returns_env_var_when_set(self, tmp_path):
        with mock.patch.dict(os.environ, {"CONTEXTFORGE_PROJECT_DIR": str(tmp_path)}):
            result = get_project_dir()
            assert result == tmp_path.resolve()

    def test_returns_cwd_when_no_env(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("CONTEXTFORGE_PROJECT_DIR", None)
            result = get_project_dir()
            assert result == Path.cwd().resolve()


class TestGetDataDir:
    def test_returns_env_var_when_set(self, tmp_path):
        with mock.patch.dict(os.environ, {"CONTEXTFORGE_DATA_DIR": str(tmp_path)}):
            result = get_data_dir()
            assert result == tmp_path.resolve()

    def test_returns_project_subdir_when_no_env(self, tmp_path):
        with mock.patch.dict(os.environ, {"CONTEXTFORGE_PROJECT_DIR": str(tmp_path)}):
            os.environ.pop("CONTEXTFORGE_DATA_DIR", None)
            result = get_data_dir()
            assert result == tmp_path.resolve() / ".contextforge"


class TestGetPluginRoot:
    def test_returns_env_var_when_set(self, tmp_path):
        with mock.patch.dict(os.environ, {"CONTEXTFORGE_PLUGIN_ROOT": str(tmp_path)}):
            result = get_plugin_root()
            assert result == tmp_path.resolve()

    def test_raises_when_not_set(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("CONTEXTFORGE_PLUGIN_ROOT", None)
            with pytest.raises(ValueError, match="CONTEXTFORGE_PLUGIN_ROOT"):
                get_plugin_root()


class TestGetVenvPython:
    def test_windows_path(self, tmp_path):
        with mock.patch.dict(os.environ, {"CONTEXTFORGE_DATA_DIR": str(tmp_path)}):
            with mock.patch("sys.platform", "win32"):
                result = get_venv_python()
                assert result == tmp_path.resolve() / "venv" / "Scripts" / "python.exe"

    def test_unix_path(self, tmp_path):
        with mock.patch.dict(os.environ, {"CONTEXTFORGE_DATA_DIR": str(tmp_path)}):
            with mock.patch("sys.platform", "linux"):
                result = get_venv_python()
                assert result == tmp_path.resolve() / "venv" / "bin" / "python3"


class TestEnsureDataDir:
    def test_creates_directories(self, tmp_path):
        data_dir = tmp_path / ".contextforge"
        with mock.patch.dict(os.environ, {"CONTEXTFORGE_DATA_DIR": str(data_dir)}):
            result = ensure_data_dir()
            assert result == data_dir.resolve()
            assert data_dir.exists()
            assert (data_dir / "models").exists()

    def test_idempotent(self, tmp_path):
        data_dir = tmp_path / ".contextforge"
        with mock.patch.dict(os.environ, {"CONTEXTFORGE_DATA_DIR": str(data_dir)}):
            ensure_data_dir()
            ensure_data_dir()  # Should not raise
            assert data_dir.exists()


class TestIsSafePath:
    def test_safe_child_path(self, tmp_path):
        child = tmp_path / "subdir" / "file.txt"
        assert is_safe_path(tmp_path, child) is True

    def test_traversal_attack(self, tmp_path):
        malicious = tmp_path / ".." / ".." / "etc" / "passwd"
        assert is_safe_path(tmp_path, malicious) is False

    def test_same_directory(self, tmp_path):
        assert is_safe_path(tmp_path, tmp_path) is True

    def test_sibling_directory(self, tmp_path):
        sibling = tmp_path.parent / "other"
        assert is_safe_path(tmp_path, sibling) is False

"""Tests for scripts/lib/config.py."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from lib.config import deep_merge, load_config


class TestDeepMerge:
    def test_scalar_override(self):
        base = {"a": 1, "b": 2}
        override = {"b": 3}
        result = deep_merge(base, override)
        assert result == {"a": 1, "b": 3}

    def test_nested_merge(self):
        base = {"a": {"x": 1, "y": 2}, "b": 3}
        override = {"a": {"y": 99}}
        result = deep_merge(base, override)
        assert result == {"a": {"x": 1, "y": 99}, "b": 3}

    def test_new_key_in_override(self):
        base = {"a": 1}
        override = {"b": 2}
        result = deep_merge(base, override)
        assert result == {"a": 1, "b": 2}

    def test_override_dict_with_scalar(self):
        base = {"a": {"x": 1}}
        override = {"a": "replaced"}
        result = deep_merge(base, override)
        assert result == {"a": "replaced"}

    def test_empty_override(self):
        base = {"a": 1}
        result = deep_merge(base, {})
        assert result == {"a": 1}

    def test_empty_base(self):
        override = {"a": 1}
        result = deep_merge({}, override)
        assert result == {"a": 1}

    def test_does_not_mutate_originals(self):
        base = {"a": {"x": 1}}
        override = {"a": {"y": 2}}
        result = deep_merge(base, override)
        assert base == {"a": {"x": 1}}
        assert override == {"a": {"y": 2}}
        assert result == {"a": {"x": 1, "y": 2}}


class TestLoadConfig:
    def test_loads_defaults(self, tmp_path):
        plugin_root = tmp_path / "plugin"
        config_dir = plugin_root / "config"
        config_dir.mkdir(parents=True)
        defaults = {"indexing": {"max_file_size": 100}, "retrieval": {"threshold": 0.5}}
        (config_dir / "defaults.json").write_text(json.dumps(defaults), encoding="utf-8")

        data_dir = tmp_path / "data"
        data_dir.mkdir()

        result = load_config(plugin_root, data_dir)
        assert result == defaults

    def test_merges_user_config(self, tmp_path):
        plugin_root = tmp_path / "plugin"
        config_dir = plugin_root / "config"
        config_dir.mkdir(parents=True)
        defaults = {"indexing": {"max_file_size": 100}, "retrieval": {"threshold": 0.5}}
        (config_dir / "defaults.json").write_text(json.dumps(defaults), encoding="utf-8")

        data_dir = tmp_path / "data"
        data_dir.mkdir()
        user_config = {"retrieval": {"threshold": 0.8}}
        (data_dir / "config.json").write_text(json.dumps(user_config), encoding="utf-8")

        result = load_config(plugin_root, data_dir)
        assert result["indexing"]["max_file_size"] == 100
        assert result["retrieval"]["threshold"] == 0.8

    def test_missing_defaults_raises(self, tmp_path):
        plugin_root = tmp_path / "plugin"
        plugin_root.mkdir()
        data_dir = tmp_path / "data"
        data_dir.mkdir()

        with pytest.raises(FileNotFoundError):
            load_config(plugin_root, data_dir)

    def test_invalid_user_config_uses_defaults(self, tmp_path):
        plugin_root = tmp_path / "plugin"
        config_dir = plugin_root / "config"
        config_dir.mkdir(parents=True)
        defaults = {"a": 1}
        (config_dir / "defaults.json").write_text(json.dumps(defaults), encoding="utf-8")

        data_dir = tmp_path / "data"
        data_dir.mkdir()
        (data_dir / "config.json").write_text("not valid json", encoding="utf-8")

        result = load_config(plugin_root, data_dir)
        assert result == defaults

"""Configuration loading for ContextForge.

Loads default configuration from the plugin's config/defaults.json,
then merges with any user overrides from {data_dir}/config.json.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger(__name__)


def deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively merge two dictionaries.

    For scalar values, the override wins. For nested dicts, the merge
    recurses so that only the overridden keys are replaced.

    Args:
        base: The base dictionary (defaults).
        override: The override dictionary (user config).

    Returns:
        A new merged dictionary. The originals are not modified.
    """
    merged = base.copy()
    for key, value in override.items():
        if (
            key in merged
            and isinstance(merged[key], dict)
            and isinstance(value, dict)
        ):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_config(plugin_root: Path, data_dir: Path) -> Dict[str, Any]:
    """Load and merge configuration.

    Loads config/defaults.json from the plugin root directory, then
    merges with {data_dir}/config.json if it exists. User overrides
    take precedence over defaults.

    Args:
        plugin_root: Path to the ContextForge plugin root directory.
        data_dir: Path to the .contextforge data directory.

    Returns:
        The merged configuration dictionary.

    Raises:
        FileNotFoundError: If the defaults.json file does not exist.
        json.JSONDecodeError: If either config file contains invalid JSON.
    """
    plugin_root = Path(plugin_root)
    data_dir = Path(data_dir)

    defaults_path = plugin_root / "config" / "defaults.json"
    if not defaults_path.is_file():
        logger.error("Default config not found at: %s", defaults_path)
        raise FileNotFoundError(
            f"Default configuration not found: {defaults_path}"
        )

    try:
        config = json.loads(defaults_path.read_text(encoding="utf-8"))
        logger.debug("Loaded default config from: %s", defaults_path)
    except json.JSONDecodeError as exc:
        logger.error("Invalid JSON in defaults config %s: %s", defaults_path, exc)
        raise

    user_config_path = data_dir / "config.json"
    if user_config_path.is_file():
        try:
            user_config = json.loads(user_config_path.read_text(encoding="utf-8"))
            config = deep_merge(config, user_config)
            logger.debug("Merged user config from: %s", user_config_path)
        except json.JSONDecodeError as exc:
            logger.warning(
                "Invalid JSON in user config %s: %s. Using defaults only.",
                user_config_path,
                exc,
            )
    else:
        logger.debug("No user config found at %s, using defaults.", user_config_path)

    return config

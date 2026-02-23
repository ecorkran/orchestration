"""Config loading, merging, and persistence via TOML files."""

from __future__ import annotations

import tomllib
from pathlib import Path

import tomli_w

from orchestration.config.keys import CONFIG_KEYS


def user_config_path() -> Path:
    """Return the user-level config file path."""
    return Path.home() / ".config" / "orchestration" / "config.toml"


def project_config_path(cwd: str = ".") -> Path:
    """Return the project-level config file path."""
    return Path(cwd).resolve() / ".orchestration.toml"


def _read_toml(path: Path) -> dict[str, object]:
    """Read a TOML file, returning empty dict if file doesn't exist."""
    if not path.is_file():
        return {}
    with open(path, "rb") as f:
        return dict(tomllib.load(f))


def _coerce_value(key: str, raw_value: str) -> object:
    """Coerce a string value to the key's declared type."""
    key_def = CONFIG_KEYS[key]
    if key_def.type_ is int:
        return int(raw_value)
    return raw_value


def load_config(cwd: str = ".") -> dict[str, object]:
    """Load merged config: defaults → user config → project config."""
    merged: dict[str, object] = {k: v.default for k, v in CONFIG_KEYS.items()}

    user_data = _read_toml(user_config_path())
    for k, v in user_data.items():
        if k in CONFIG_KEYS:
            merged[k] = v

    project_data = _read_toml(project_config_path(cwd))
    for k, v in project_data.items():
        if k in CONFIG_KEYS:
            merged[k] = v

    return merged


def get_config(key: str, cwd: str = ".") -> object:
    """Get a single config value (merged)."""
    if key not in CONFIG_KEYS:
        raise KeyError(f"Unknown config key: {key}")
    return load_config(cwd)[key]


def set_config(
    key: str,
    value: str,
    *,
    project: bool = False,
    cwd: str = ".",
) -> None:
    """Write a config value to the appropriate TOML file.

    Creates the file and parent directories if needed.
    Validates the key name and coerces the value to the declared type.
    """
    if key not in CONFIG_KEYS:
        raise KeyError(f"Unknown config key: {key}")

    coerced = _coerce_value(key, value)

    path = project_config_path(cwd) if project else user_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    existing = _read_toml(path)
    existing[key] = coerced

    with open(path, "wb") as f:
        tomli_w.dump(existing, f)


def resolve_config_source(key: str, cwd: str = ".") -> str:
    """Determine which source provides the resolved value for a key.

    Returns "project", "user", or "default".
    """
    if key not in CONFIG_KEYS:
        raise KeyError(f"Unknown config key: {key}")

    project_data = _read_toml(project_config_path(cwd))
    if key in project_data:
        return "project"

    user_data = _read_toml(user_config_path())
    if key in user_data:
        return "user"

    return "default"

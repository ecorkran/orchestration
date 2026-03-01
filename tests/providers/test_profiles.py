"""Tests for provider profile loading and merging."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from orchestration.providers.profiles import (
    BUILT_IN_PROFILES,
    ProviderProfile,
    get_all_profiles,
    get_profile,
    load_user_profiles,
    providers_toml_path,
)


def test_built_in_profiles_available() -> None:
    profiles = get_all_profiles()
    assert "openai" in profiles
    assert "openrouter" in profiles
    assert "local" in profiles
    assert "gemini" in profiles


def test_built_in_openrouter_has_correct_base_url() -> None:
    assert BUILT_IN_PROFILES["openrouter"].base_url == "https://openrouter.ai/api/v1"


def test_built_in_local_has_no_api_key_env() -> None:
    assert BUILT_IN_PROFILES["local"].api_key_env is None


def test_load_user_profiles_missing_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Returns empty dict when providers.toml does not exist."""
    monkeypatch.setattr(
        "orchestration.providers.profiles.providers_toml_path",
        lambda: tmp_path / "nonexistent.toml",
    )
    result = load_user_profiles()
    assert result == {}


def test_load_user_profiles_from_toml(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    toml_file = tmp_path / "providers.toml"
    toml_file.write_text(
        textwrap.dedent("""\
            [profiles.custom]
            provider = "openai"
            base_url = "https://custom.example.com/v1"
            api_key_env = "CUSTOM_API_KEY"
            description = "A custom profile"
        """)
    )
    monkeypatch.setattr(
        "orchestration.providers.profiles.providers_toml_path",
        lambda: toml_file,
    )
    result = load_user_profiles()
    assert "custom" in result
    profile = result["custom"]
    assert isinstance(profile, ProviderProfile)
    assert profile.provider == "openai"
    assert profile.base_url == "https://custom.example.com/v1"
    assert profile.api_key_env == "CUSTOM_API_KEY"
    assert profile.description == "A custom profile"


def test_user_profile_overrides_builtin(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    toml_file = tmp_path / "providers.toml"
    toml_file.write_text(
        textwrap.dedent("""\
            [profiles.openrouter]
            provider = "openai"
            base_url = "https://my-openrouter.example.com/v1"
        """)
    )
    monkeypatch.setattr(
        "orchestration.providers.profiles.providers_toml_path",
        lambda: toml_file,
    )
    profiles = get_all_profiles()
    assert profiles["openrouter"].base_url == "https://my-openrouter.example.com/v1"


def test_get_profile_known() -> None:
    profile = get_profile("openrouter")
    assert profile.name == "openrouter"
    assert profile.base_url == "https://openrouter.ai/api/v1"


def test_get_profile_unknown_raises() -> None:
    with pytest.raises(KeyError, match="nonexistent"):
        get_profile("nonexistent")

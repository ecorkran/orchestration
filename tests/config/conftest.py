"""Shared fixtures for config tests."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest


@pytest.fixture
def user_config_dir(tmp_path: Path) -> Path:
    """Temporary directory for user-level config."""
    config_dir = tmp_path / "user_config" / ".config" / "orchestration"
    config_dir.mkdir(parents=True)
    return config_dir


@pytest.fixture
def project_dir(tmp_path: Path) -> Path:
    """Temporary directory simulating a project root."""
    proj = tmp_path / "project"
    proj.mkdir()
    return proj


@pytest.fixture
def patch_config_paths(
    user_config_dir: Path,
    project_dir: Path,
):
    """Patch config path functions to use temporary directories."""
    user_file = user_config_dir / "config.toml"
    project_file = project_dir / ".orchestration.toml"

    with (
        patch(
            "orchestration.config.manager.user_config_path",
            return_value=user_file,
        ),
        patch(
            "orchestration.config.manager.project_config_path",
            return_value=project_file,
        ),
    ):
        yield {"user": user_file, "project": project_file}

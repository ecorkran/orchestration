"""Tests for provider auto-loader in spawn command (T12-T13)."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from typer.testing import CliRunner

from orchestration.cli.app import app
from orchestration.cli.commands.spawn import _load_provider
from tests.cli.conftest import make_agent_info


class TestLoadProvider:
    def test_calls_import_module(self) -> None:
        target = "orchestration.cli.commands.spawn.importlib.import_module"
        with patch(target) as mock_import:
            _load_provider("openai")
        mock_import.assert_called_once_with("orchestration.providers.openai")

    def test_silences_import_error(self) -> None:
        target = "orchestration.cli.commands.spawn.importlib.import_module"
        with patch(target, side_effect=ImportError("no module")):
            # Must not raise
            _load_provider("nonexistent-provider")


class TestSpawnTriggersLoadProvider:
    def test_spawn_triggers_load_provider(
        self, cli_runner: CliRunner, patch_registry: AsyncMock
    ) -> None:
        patch_registry.spawn.return_value = make_agent_info("bot")
        load_target = "orchestration.cli.commands.spawn._load_provider"
        reg_target = "orchestration.cli.commands.spawn.get_registry"
        with (
            patch(load_target) as mock_load,
            patch(reg_target, return_value=patch_registry),
        ):
            cli_runner.invoke(app, ["spawn", "--name", "bot", "--provider", "openai"])
        mock_load.assert_called_once_with("openai")

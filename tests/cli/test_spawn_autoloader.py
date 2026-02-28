"""Tests for provider auto-loader (now in engine, not spawn command).

The _load_provider function moved from spawn.py to engine.py as part
of the daemon refactor. These tests verify it still works correctly.
"""

from __future__ import annotations

from unittest.mock import patch

from orchestration.server.engine import _load_provider


class TestLoadProvider:
    def test_calls_import_module(self) -> None:
        target = "orchestration.server.engine.importlib.import_module"
        with patch(target) as mock_import:
            _load_provider("openai")
        mock_import.assert_called_once_with(
            "orchestration.providers.openai"
        )

    def test_silences_import_error(self) -> None:
        target = "orchestration.server.engine.importlib.import_module"
        with patch(target, side_effect=ImportError("no module")):
            # Must not raise
            _load_provider("nonexistent-provider")

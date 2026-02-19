"""Smoke test — verifies the package is importable."""

from __future__ import annotations

import orchestration


def test_package_importable() -> None:
    """The orchestration package must be importable with a version string."""
    assert orchestration.__version__ == "0.1.0"

"""CLI-side client for communicating with the squadron daemon."""

from __future__ import annotations

from squadron.client.http import DaemonClient, DaemonNotRunningError

__all__ = ["DaemonClient", "DaemonNotRunningError"]

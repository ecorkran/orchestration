"""AuthStrategy protocol and concrete implementations for credential resolution."""

from __future__ import annotations

import os
from typing import Protocol, runtime_checkable

from orchestration.providers.errors import ProviderAuthError


@runtime_checkable
class AuthStrategy(Protocol):
    """Credential resolution strategy for a provider."""

    async def get_credentials(self) -> dict[str, str]:
        """Return credentials dict (e.g. {"api_key": "sk-..."}).

        Raises ProviderAuthError if credentials cannot be resolved.
        """
        ...

    async def refresh_if_needed(self) -> None:
        """Refresh credentials if they are expired or near expiry.

        No-op for strategies that don't support refresh (e.g. API keys).
        """
        ...

    def is_valid(self) -> bool:
        """Return True if credentials are currently available and usable."""
        ...


class ApiKeyStrategy:
    """Resolve an API key from explicit value, env var chain, or localhost bypass."""

    def __init__(
        self,
        *,
        explicit_key: str | None = None,
        env_var: str | None = None,
        fallback_env_var: str = "OPENAI_API_KEY",
        base_url: str | None = None,
    ) -> None:
        self._explicit_key = explicit_key
        self._env_var = env_var
        self._fallback_env_var = fallback_env_var
        self._base_url = base_url

    def _is_localhost(self) -> bool:
        url = self._base_url or ""
        return url.startswith("http://localhost") or url.startswith("http://127.0.0.1")

    def _resolve(self) -> str | None:
        """Return resolved key or None if nothing found (excluding error case)."""
        if self._explicit_key:
            return self._explicit_key
        if self._env_var:
            val = os.environ.get(self._env_var)
            if val:
                return val
        fallback = os.environ.get(self._fallback_env_var)
        if fallback:
            return fallback
        if self._is_localhost():
            return "not-needed"
        return None

    async def get_credentials(self) -> dict[str, str]:
        """Return {"api_key": "<resolved_key>"}.

        Resolution order:
        1. explicit_key (from AgentConfig.api_key)
        2. os.environ[env_var] (profile-specified, e.g. OPENROUTER_API_KEY)
        3. os.environ[fallback_env_var] (default OPENAI_API_KEY)
        4. "not-needed" if base_url is localhost
        5. Raise ProviderAuthError
        """
        key = self._resolve()
        if key is None:
            raise ProviderAuthError(
                "No API key found. Set config.api_key, the profile"
                " api_key_env var, or OPENAI_API_KEY."
            )
        return {"api_key": key}

    async def refresh_if_needed(self) -> None:
        """No-op — API keys don't expire."""

    def is_valid(self) -> bool:
        """Return True if any key source resolves to a non-empty value."""
        return self._resolve() is not None

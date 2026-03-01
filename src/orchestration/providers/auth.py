"""AuthStrategy protocol and concrete implementations for credential resolution."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from orchestration.providers.errors import ProviderAuthError

if TYPE_CHECKING:
    from orchestration.core.models import AgentConfig
    from orchestration.providers.profiles import ProviderProfile


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


# Registry mapping auth_type strings to strategy classes.
AUTH_STRATEGIES: dict[str, type] = {
    "api_key": ApiKeyStrategy,
    # Future: "oauth": OAuthStrategy (slice 116)
}


def resolve_auth_strategy(
    config: AgentConfig,
    profile: ProviderProfile | None = None,
) -> AuthStrategy:
    """Build an AuthStrategy from config and optional profile.

    Reads auth_type from profile (defaults to "api_key" if no profile).
    Raises ProviderAuthError for unknown auth_type values.
    """
    auth_type: str = profile.auth_type if profile is not None else "api_key"

    strategy_cls = AUTH_STRATEGIES.get(auth_type)
    if strategy_cls is None:
        available = ", ".join(sorted(AUTH_STRATEGIES))
        raise ProviderAuthError(
            f"Unknown auth_type {auth_type!r}. Available: {available}"
        )

    if auth_type == "api_key":
        env_var: str | None
        if profile is not None:
            env_var = profile.api_key_env
        else:
            raw = config.credentials.get("api_key_env")
            env_var = str(raw) if raw is not None else None

        return ApiKeyStrategy(
            explicit_key=config.api_key,
            env_var=env_var,
            fallback_env_var="OPENAI_API_KEY",
            base_url=config.base_url,
        )

    # Unreachable until additional auth types are added to the registry.
    raise ProviderAuthError(f"Auth type {auth_type!r} not yet implemented")

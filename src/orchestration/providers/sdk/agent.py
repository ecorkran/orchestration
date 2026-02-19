"""SDKAgent implementation. Wraps claude-agent-sdk query/client for task execution."""

from __future__ import annotations

from collections.abc import AsyncIterator

from claude_agent_sdk import (
    CLIConnectionError,
    CLIJSONDecodeError,
    CLINotFoundError,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    ClaudeSDKError,
    ProcessError,
    query as sdk_query,
)

from orchestration.core.models import AgentState, Message
from orchestration.logging import get_logger
from orchestration.providers.errors import (
    ProviderAPIError,
    ProviderAuthError,
    ProviderError,
)
from orchestration.providers.sdk.translation import translate_sdk_message


class SDKAgent:
    """An autonomous agent backed by claude-agent-sdk."""

    def __init__(
        self,
        name: str,
        options: ClaudeAgentOptions,
        mode: str = "query",
    ) -> None:
        self._name = name
        self._options = options
        self._mode = mode
        self._state = AgentState.idle
        self._client: ClaudeSDKClient | None = None
        self._log = get_logger(f"orchestration.providers.sdk.agent.{name}")

    # -- Protocol properties ------------------------------------------------

    @property
    def name(self) -> str:
        return self._name

    @property
    def agent_type(self) -> str:
        return "sdk"

    @property
    def state(self) -> AgentState:
        return self._state

    # -- Message handling ---------------------------------------------------

    async def handle_message(self, message: Message) -> AsyncIterator[Message]:
        """Route to query or client mode based on configuration."""
        if self._mode == "client":
            async for msg in self._handle_client_mode(message):
                yield msg
        else:
            async for msg in self._handle_query_mode(message):
                yield msg

    async def _handle_query_mode(self, message: Message) -> AsyncIterator[Message]:
        """One-shot execution via ``sdk_query``."""
        self._state = AgentState.processing
        try:
            async for sdk_msg in sdk_query(
                prompt=message.content, options=self._options
            ):
                for translated in translate_sdk_message(sdk_msg, sender=self._name):
                    yield translated
            self._state = AgentState.idle
        except CLINotFoundError as exc:
            self._state = AgentState.failed
            raise ProviderAuthError(str(exc)) from exc
        except ProcessError as exc:
            self._state = AgentState.failed
            raise ProviderAPIError(
                str(exc), status_code=getattr(exc, "exit_code", None)
            ) from exc
        except (CLIConnectionError, CLIJSONDecodeError, ClaudeSDKError) as exc:
            self._state = AgentState.failed
            raise ProviderError(str(exc)) from exc

    async def _handle_client_mode(self, message: Message) -> AsyncIterator[Message]:
        """Multi-turn execution via ``ClaudeSDKClient``."""
        self._state = AgentState.processing
        try:
            if self._client is None:
                self._client = ClaudeSDKClient(options=self._options)
                await self._client.connect()
            await self._client.query(prompt=message.content)
            async for sdk_msg in self._client.receive_response():
                for translated in translate_sdk_message(sdk_msg, sender=self._name):
                    yield translated
            self._state = AgentState.idle
        except CLINotFoundError as exc:
            self._state = AgentState.failed
            raise ProviderAuthError(str(exc)) from exc
        except ProcessError as exc:
            self._state = AgentState.failed
            raise ProviderAPIError(
                str(exc), status_code=getattr(exc, "exit_code", None)
            ) from exc
        except (CLIConnectionError, CLIJSONDecodeError, ClaudeSDKError) as exc:
            self._state = AgentState.failed
            raise ProviderError(str(exc)) from exc

    # -- Lifecycle ----------------------------------------------------------

    async def shutdown(self) -> None:
        """Disconnect client if in multi-turn mode."""
        if self._client is not None:
            try:
                await self._client.disconnect()
            except Exception:
                pass  # Best-effort cleanup
            self._client = None
        self._state = AgentState.terminated

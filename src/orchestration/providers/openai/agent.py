"""OpenAICompatibleAgent — stub placeholder, implemented in T7."""

from __future__ import annotations

from typing import Any

from openai import AsyncOpenAI

from orchestration.core.models import AgentState, Message


class OpenAICompatibleAgent:
    """Conversational agent backed by the OpenAI Chat Completions API."""

    def __init__(
        self,
        name: str,
        client: AsyncOpenAI,
        model: str,
        system_prompt: str | None,
    ) -> None:
        self._name = name
        self._client = client
        self._model = model
        self._history: list[dict[str, Any]] = []
        self._state = AgentState.idle

        if system_prompt is not None:
            self._history.append({"role": "system", "content": system_prompt})

    @property
    def name(self) -> str:
        return self._name

    @property
    def agent_type(self) -> str:
        return "api"

    @property
    def state(self) -> AgentState:
        return self._state

    async def handle_message(self, message: Message) -> Any:  # noqa: ANN401
        raise NotImplementedError("Implemented in T7")

    async def shutdown(self) -> None:
        raise NotImplementedError("Implemented in T7")

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Generator


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class LLMResponse:
    content: str | None = None
    tool_calls: list[ToolCall] | None = None
    usage: dict[str, int] = field(default_factory=dict)


@dataclass
class StreamEvent:
    type: str  # "content", "tool_call", "done"
    delta: str | dict | None = None


class BaseLLMProvider(ABC):
    def __init__(self, api_key: str, base_url: str, model: str, timeout: float = 120.0):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.timeout = timeout

    def generate(self, prompt: str, **kwargs) -> str:
        result = self.chat(messages=[{"role": "user", "content": prompt}], **kwargs)
        return result.content or ""

    def generate_with_tools(
        self, prompt: str, tools: list[dict[str, Any]], **kwargs
    ) -> str:
        result = self.chat(
            messages=[{"role": "user", "content": prompt}], tools=tools, **kwargs
        )
        if result.tool_calls:
            import json

            return json.dumps(
                [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": json.dumps(tc.arguments),
                        },
                    }
                    for tc in result.tool_calls
                ]
            )
        return result.content or ""

    def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        system_prompt: str | None = None,
        stream: bool = False,
        **kwargs,
    ) -> LLMResponse | Generator[StreamEvent, None, None]:
        if stream:
            return self._chat_stream(
                messages, tools=tools, system_prompt=system_prompt, **kwargs
            )
        return self._chat(messages, tools=tools, system_prompt=system_prompt, **kwargs)

    @abstractmethod
    def _chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        system_prompt: str | None = None,
        **kwargs,
    ) -> LLMResponse:
        ...

    def _chat_stream(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        system_prompt: str | None = None,
        **kwargs,
    ) -> Generator[StreamEvent, None, None]:
        """Override in provider subclass to support streaming."""
        result = self._chat(messages, tools=tools, system_prompt=system_prompt, **kwargs)
        yield StreamEvent(type="content", delta=result.content or "")
        if result.tool_calls:
            for tc in result.tool_calls:
                yield StreamEvent(
                    type="tool_call",
                    delta={"id": tc.id, "name": tc.name, "arguments": tc.arguments},
                )
        yield StreamEvent(type="done")
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


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


class BaseLLMProvider(ABC):
    def __init__(self, api_key: str, base_url: str, model: str):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model

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

    @abstractmethod
    def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        system_prompt: str | None = None,
        **kwargs,
    ) -> LLMResponse:
        pass

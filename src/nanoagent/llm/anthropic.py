from __future__ import annotations

from typing import Any

import anthropic

from .base import BaseLLMProvider, LLMResponse, ToolCall


class AnthropicProvider(BaseLLMProvider):

    def __init__(self, api_key: str, base_url: str, model: str):
        super().__init__(api_key, base_url, model)
        self.client = anthropic.Anthropic(
            api_key=self.api_key,
            base_url=self.base_url or None,
        )

    def chat(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None = None,
             system_prompt: str | None = None, **kwargs) -> LLMResponse:
        params = dict(
            model=self.model,
            max_tokens=kwargs.pop("max_tokens", 4096),
            messages=messages,
        )
        if system_prompt:
            params["system"] = system_prompt
        if tools:
            params["tools"] = tools

        try:
            response = self.client.messages.create(**params)
        except Exception as e:
            raise RuntimeError(f"Anthropic API error: {e}") from e

        content = []
        tcs = None
        for block in response.content:
            if block.type == "text":
                content.append(block.text)
            elif block.type == "tool_use":
                if tcs is None:
                    tcs = []
                tcs.append(ToolCall(id=block.id, name=block.name, arguments=block.input))

        return LLMResponse(
            content="".join(content) if content else None,
            tool_calls=tcs,
            usage={
                "input_tokens": response.usage.input_tokens if response.usage else 0,
                "output_tokens": response.usage.output_tokens if response.usage else 0,
            },
        )

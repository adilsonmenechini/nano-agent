from __future__ import annotations

import json
from typing import Any

import openai

from .base import BaseLLMProvider, LLMResponse, ToolCall


class OpenAIProvider(BaseLLMProvider):
    def __init__(self, api_key: str, base_url: str, model: str):
        super().__init__(api_key, base_url, model)
        self.client = openai.OpenAI(api_key=self.api_key, base_url=self.base_url)

    def _chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        system_prompt: str | None = None,
        **kwargs,
    ) -> LLMResponse:
        full = []
        if system_prompt:
            full.append({"role": "system", "content": system_prompt})
        full.extend(messages)

        params = dict(model=self.model, messages=full, **kwargs)
        if tools:
            params["tools"] = tools

        try:
            response = self.client.chat.completions.create(**params)
        except Exception as e:
            raise RuntimeError(f"OpenAI API error: {e}") from e

        msg = response.choices[0].message
        usage = response.usage
        tcs = None
        if msg.tool_calls:
            tcs = [
                ToolCall(
                    id=tc.id,
                    name=tc.function.name,
                    arguments=json.loads(tc.function.arguments),
                )
                for tc in msg.tool_calls
            ]
        return LLMResponse(
            content=msg.content,
            tool_calls=tcs,
            usage={
                "prompt_tokens": usage.prompt_tokens if usage else 0,
                "completion_tokens": usage.completion_tokens if usage else 0,
            },
        )

    def _chat_stream(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        system_prompt: str | None = None,
        **kwargs,
    ):
        from .base import StreamEvent

        full = []
        if system_prompt:
            full.append({"role": "system", "content": system_prompt})
        full.extend(messages)

        params = dict(model=self.model, messages=full, stream=True, **kwargs)
        if tools:
            params["tools"] = tools

        try:
            stream = self.client.chat.completions.create(**params)
        except Exception as e:
            raise RuntimeError(f"OpenAI API error: {e}") from e

        for chunk in stream:
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta and delta.content:
                yield StreamEvent(type="content", delta=delta.content)
            if delta and delta.tool_calls:
                for tc in delta.tool_calls:
                    yield StreamEvent(
                        type="tool_call",
                        delta={"id": tc.id, "function": tc.function},
                    )

        yield StreamEvent(type="done")

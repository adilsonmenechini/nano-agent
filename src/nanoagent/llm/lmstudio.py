from __future__ import annotations

import json
from typing import Any

import openai

from .base import BaseLLMProvider, LLMResponse, ToolCall


class LMStudioProvider(BaseLLMProvider):
    def __init__(self, api_key: str, base_url: str, model: str, timeout: float = 120.0):
        super().__init__(api_key, base_url, model, timeout)
        self.client = openai.OpenAI(
            api_key=self.api_key, base_url=self.base_url, timeout=timeout
        )

    def generate(self, prompt: str, **kwargs) -> str:
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                **kwargs,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            raise RuntimeError(f"LM Studio API error: {e}") from e

    def generate_with_tools(
        self, prompt: str, tools: list[dict[str, Any]], **kwargs
    ) -> str:
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                tools=tools,
                **kwargs,
            )
            if response.choices[0].message.tool_calls:
                return json.dumps(
                    [tc.model_dump() for tc in response.choices[0].message.tool_calls]
                )
            return response.choices[0].message.content or ""
        except Exception as e:
            raise RuntimeError(f"LM Studio API error with tools: {e}") from e

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
        except openai.BadRequestError as e:
            body = getattr(e, "body", {}) or {}
            msg = (
                body.get("error", {}).get("message", str(e))
                if isinstance(body, dict)
                else str(e)
            )
            if "jinja" in msg.lower() or "template" in msg.lower():
                raise RuntimeError(
                    f"Model '{self.model}' has a broken prompt template in LM Studio. "
                    f"Go to the model settings and clear the Prompt Template field."
                ) from e
            raise RuntimeError(f"LM Studio API error: {msg}") from e
        except Exception as e:
            raise RuntimeError(f"LM Studio API error: {e}") from e

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
        except openai.BadRequestError as e:
            body = getattr(e, "body", {}) or {}
            msg_str = (
                body.get("error", {}).get("message", str(e))
                if isinstance(body, dict)
                else str(e)
            )
            raise RuntimeError(f"LM Studio API error: {msg_str}") from e
        except Exception as e:
            raise RuntimeError(f"LM Studio API error: {e}") from e

        for chunk in stream:
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta and delta.content:
                yield StreamEvent(type="content", delta=delta.content)

        yield StreamEvent(type="done")

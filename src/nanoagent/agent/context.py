from __future__ import annotations

import tiktoken
from typing import Any


# Per-provider tokenizer mapping
_TOKENIZER_REGISTRY: dict[str, str] = {
    "openai": "cl100k_base",
    "anthropic": "cl100k_base",
    "lmstudio": "cl100k_base",
}


def set_tokenizer(provider: str, encoding_name: str) -> None:
    """Register a tokenizer for a provider."""
    _TOKENIZER_REGISTRY[provider] = encoding_name


def count_tokens(text: str, provider: str = "openai") -> int:
    """Count tokens in text using provider-appropriate tokenization."""
    encoding_name = _TOKENIZER_REGISTRY.get(provider, "cl100k_base")
    try:
        enc = tiktoken.get_encoding(encoding_name)
        return len(enc.encode(text))
    except Exception:
        return _estimate_tokens(text)


def _estimate_tokens(text: str) -> int:
    """Fallback character-based estimation (~4 chars per token)."""
    return len(text) // 4 + 1


def count_messages_tokens(
    messages: list[dict[str, Any]],
    provider: str = "openai",
) -> int:
    """Count total tokens across a message list."""
    total = 0
    for msg in messages:
        for value in msg.values():
            if isinstance(value, str):
                total += count_tokens(value, provider)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        for v in item.values():
                            if isinstance(v, str):
                                total += count_tokens(v, provider)
    return total


def truncate_messages(
    messages: list[dict[str, Any]],
    max_tokens: int,
    provider: str = "openai",
) -> list[dict[str, Any]]:
    """Truncate message history to fit within token limit."""
    if count_messages_tokens(messages, provider) <= max_tokens:
        return messages

    # Keep system message, remove oldest user/assistant pairs
    result = list(messages)
    while len(result) > 1 and count_messages_tokens(result, provider) > max_tokens:
        for i, msg in enumerate(result):
            if msg.get("role") != "system":
                result.pop(i)
                break
    return result


def select_top_memories(
    entries: list[str],
    max_tokens: int,
    importance_scores: list[float] | None = None,
    provider: str = "openai",
) -> list[str]:
    """Select memories by importance up to a token budget."""
    if importance_scores is None:
        importance_scores = [1.0] * len(entries)
    indexed = list(zip(importance_scores, entries))
    indexed.sort(key=lambda x: x[0], reverse=True)
    selected: list[str] = []
    total = 0
    for score, text in indexed:
        tokens = count_tokens(text, provider)
        if total + tokens > max_tokens:
            continue
        selected.append(text)
        total += tokens
    return selected

# Provider Interface Contract

## `BaseLLMProvider`

All LLM providers must implement this interface.

### Methods

#### `chat(messages, max_tokens=None, temperature=None, stream=False)`

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `messages` | `list[dict]` | yes | — | Chat message history |
| `max_tokens` | `int` | no | Provider default | Max response tokens |
| `temperature` | `float` | no | Provider default | Response creativity (0.0–2.0) |
| `stream` | `bool` | no | `False` | Enable streaming response |

**Returns (non-streaming):**
```python
{
    "content": str,       # Response text
    "tool_calls": list,   # Tool call requests (or empty list)
}
```

**Returns (streaming):**
```python
Generator[dict, None, None]  # Yields {"type": "content"|"tool_call", "delta": str|dict}
```

**Streaming Events:**
| Type | Delta | Description |
|------|-------|-------------|
| `content` | `str` | Text token delta |
| `tool_call` | `dict` | Partial tool call data |
| `done` | `None` | Stream complete |

**Error Handling:**
- Transient errors (timeout, 429, 5xx): raise `ProviderRetryableError`
- Permanent errors (auth, 400, model not found): raise `ProviderFatalError`
- All errors inherit from `ProviderError`

### Implementations

- `OpenAIProvider` — OpenAI API (and compatible: LM Studio)
- `AnthropicProvider` — Anthropic API

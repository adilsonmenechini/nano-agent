# State Machine Contract

## States

```mermaid
stateDiagram-v2
    [*] --> IDLE
    IDLE --> THINKING: user_input()
    THINKING --> EXECUTING_TOOLS: tool_calls_detected()
    THINKING --> IDLE: response_ready()
    THINKING --> AWAITING_INPUT: clarification_needed()
    EXECUTING_TOOLS --> THINKING: tools_complete()
    EXECUTING_TOOLS --> ERROR: tool_error()
    AWAITING_INPUT --> IDLE: user_provides_input()
    ERROR --> IDLE: recover()
    ERROR --> THINKING: retry_available()
```

## Callbacks

Each state transition fires a callback:

```python
@dataclass
class StateTransition:
    from_state: AgentState
    to_state: AgentState
    reason: str
    timestamp: datetime
    metadata: dict  # Context-specific data (e.g., tool results, error info)

# Registered callbacks receive StateTransition
callbacks.on_state_change(transition)
```

## Error Recovery

| Error | Recovery Action |
|-------|----------------|
| Tool execution timeout | Log, transition to ERROR, prompt user to retry |
| Provider rate limit | Wait, retry (up to retry_attempts) |
| Provider auth failure | Transition to ERROR, show configuration help |
| Unknown tool call | Skip tool, log warning, return to THINKING |

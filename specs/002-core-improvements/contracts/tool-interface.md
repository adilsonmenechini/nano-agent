# Tool Interface Contract

## `@tool` Decorator

Converts a function into an agent tool with automatic JSON schema inference.

### Usage

```python
@tool
def my_tool(param1: str, param2: int = 0) -> str:
    """Tool description (used as tool description).
    
    Args:
        param1: Description of param1
        param2: Description of param2 (default: 0)
    """
    return f"Result: {param1}, {param2}"
```

### Schema Inference Rules

| Type Hint | JSON Schema Type |
|-----------|-----------------|
| `str` | `string` |
| `int` | `integer` |
| `float` | `number` |
| `bool` | `boolean` |
| `list[str]` | `array` with `string` items |
| `dict` | `object` |
| `Optional[str]` | `string` (not required) |

### Execution Contract

Each tool call receives:
- `**kwargs`: Parameters matching the function signature, parsed from the LLM's JSON tool call
- Returns: `str` — the tool result text

### Tool Registry

```python
registry = ToolRegistry()

# Register
registry.add("my_tool", my_tool_fn, description="...", schema={...})

# Execute
result = registry.execute("my_tool", {"param1": "value"})

# Execute parallel (NEW)
results = registry.execute_parallel([
    ("tool_a", {"arg": 1}),
    ("tool_b", {"arg": 2}),
])
# Returns: [result_a, result_b] — runs in parallel if no dependencies
```

### Error Contract
- Tool execution errors are caught and returned as error strings
- Tools should not raise exceptions for expected failure modes
- Unexpected exceptions are caught by the agent loop and surfaced as error states

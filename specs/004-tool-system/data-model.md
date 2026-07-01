# Data Model: Agent Tool System

## Entities

### Tool

A callable function with type-hint-inferred JSON Schema. Defined in `nanoagent/tool.py` (existing).

| Field | Type | Description |
|-------|------|-------------|
| `name` | `str` | Unique tool identifier (e.g., "run_shell", "read_file") |
| `description` | `str` | LLM-facing description of what the tool does |
| `fn` | `Callable` | The underlying Python function |
| `parameters` | `dict` | JSON Schema object for LLM function calling |
| `schema` (property) | `dict` | OpenAI-compatible tool schema |
| `anthropic_schema` (property) | `dict` | Anthropic-compatible tool schema |

**Creation**: Via `@tool` decorator or `Tool(callable, name=..., description=...)`.

**Validation**: Parameters schema inferred from function type hints via `infer_parameters_schema()`.

---

### PermissionRule

A single access control rule for tool invocations.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `tool_name` | `str` | — | Name of the tool this rule applies to (`"*"` for all tools) |
| `match_type` | `Literal["exact", "prefix", "regex"]` | `"exact"` | How to match `command` against the invocation |
| `pattern` | `str` | `"*"` | Pattern/command string to match |
| `mode` | `Literal["allow", "deny", "ask"]` | — | Action when this rule matches |

**Matching behavior**:
- `exact`: `invocation == pattern`
- `prefix`: `invocation.startswith(pattern)`
- `regex`: `re.match(pattern, invocation)` is truthy

**Rule evaluation order**:
1. Rules sorted by specificity (exact > prefix > regex, tool-specific > wildcard)
2. First matching rule wins (highest priority)
3. If no rule matches, fall back to `default_mode`

---

### PermissionManager

Central authority that evaluates and enforces tool access.

| Field | Type | Description |
|-------|------|-------------|
| `rules` | `list[PermissionRule]` | Loaded from TOML config at startup |
| `default_mode` | `str` | Default mode when no rule matches (`"allow"` or `"deny"`) |

**Methods**:
- `check(tool_name, command="") -> PermissionResult`: Evaluate access
- `intercept(registry) -> ToolRegistry`: Return wrapped registry that checks permissions before execution

**State transitions**:
```
check() → ALLOWED  → execute tool
check() → DENIED   → return error without executing
check() → ASK      → signal for human approval (deferred to agent loop)
```

---

### OutputTruncator

Applies size limits to tool output.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `max_chars` | `int` | `10_240` | Maximum characters before truncation |
| `suffix` | `str` | `"[truncated %d lines, %d chars]"` | Marker appended to truncated output |

**Truncation algorithm**:
1. Count lines and characters in output
2. If within `max_chars`, return unchanged
3. If exceeded, find last `\n` at or before `max_chars` position
4. Truncate at that line boundary
5. Append truncation suffix with count of omitted lines and chars
6. If no newline before threshold, truncate at `max_chars` directly

---

### ToolRegistry (extended)

Existing registry with additional integration points.

| Method | Existing | Extended |
|--------|----------|----------|
| `register(tool)` | ✅ | ✅ (unchanged) |
| `get(name)` | ✅ | ✅ (unchanged) |
| `execute(name, args)` | ✅ | Extended: apply PermissionManager + OutputTruncator |
| `execute_parallel(calls)` | ✅ | Extended: apply same checks as `execute()` |
| `openai_schemas()` | ✅ | ✅ (unchanged) |
| `anthropic_schemas()` | ✅ | ✅ (unchanged) |
| `register_builtin_tools()` | ❌ | **NEW**: register all shell/file/git tools |

---

## Relationships

```
Agent
 ├── ToolRegistry (1)
 │    ├── Tool (0..N) — registered by name
 │    ├── PermissionManager (0..1) — wraps execute()
 │    └── OutputTruncator (0..1) — post-processes execute() results
 └── AgentConfig (1)
      └── [tools.permissions] — TOML section → PermissionRule list
```

## Validation Rules

| Rule | Applies To | Enforcement |
|------|-----------|-------------|
| Tool names must be unique | ToolRegistry | `register()` overwrites silently (existing behavior) |
| Write target must be within project dir | `write_file` tool | `Path.resolve().is_relative_to(project_dir)` check; returns error if violated |
| Shell command timeout must be > 0 | `run_shell` tool | Clamped to minimum 1s |
| Truncation threshold must be > 0 | OutputTruncator | Clamped to minimum 1 character |
| Permission rule modes must be valid | PermissionRule | Validated at config load time |
| Tool name must match existing tool | PermissionManager | Permission rule with nonexistent tool name is allowed (rule becomes no-op) |

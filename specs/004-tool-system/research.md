# Research: Agent Tool System

**Date**: 2026-06-29 | **Feature**: 004-tool-system

## Phase 0 Findings

### 1. Tool Implementation Pattern

**Decision**: Use the existing `@tool` decorator and `Tool` dataclass from `nanoagent/tool.py` for all new built-in tools.

**Rationale**: The codebase has two tool patterns:
- **Newer**: `Tool` dataclass + `@tool` decorator in `nanoagent/tool.py` — type-hint-based JSON Schema inference, used by `ToolRegistry`
- **Legacy**: `BaseTool` ABC in `agent/tools/base.py` — older class-based approach with manual schema, used by `TodoTool` and `WebTool`

The `ToolRegistry` only manages `Tool` instances. The legacy `BaseTool` tools are bridged via `_from_legacy_tool()` in `agent.py`. New tools should use the `@tool` decorator pattern exclusively.

**Alternatives considered**: Extending `BaseTool` with new subclasses. Rejected because it would require maintaining the bridge function and produces duplicate code.

### 2. Permission Integration Strategy

**Decision**: Implement `PermissionManager` as a wrapper/interceptor around `ToolRegistry.execute()`. The agent calls `permission_manager.execute(name, args)` instead of `registry.execute(name, args)`.

**Rationale**: This provides a clean separation of concerns — the registry remains a pure tool store, and permissions add a security layer on top. The agent only needs one integration point.

**Permission rule structure**:
```python
@dataclass
class PermissionRule:
    tool_name: str         # Which tool this applies to ("*" for all)
    command_pattern: str   # Glob/prefix/regex pattern for shell commands
    match_type: str        # "exact" | "prefix" | "regex"
    mode: str              # "allow" | "deny" | "ask"
```

**Config format** (TOML, added to existing `~/.config/nanoagent/config.toml`):
```toml
[tools.permissions]
default_mode = "allow"

[tools.permissions.rules]
# Deny dangerous shell commands
deny_rm = { tool = "run_shell", type = "prefix", pattern = "rm -rf", mode = "deny" }
deny_sudo = { tool = "run_shell", type = "prefix", pattern = "sudo", mode = "ask" }

# Allow file reads always (already safe)
allow_read = { tool = "read_file", type = "exact", pattern = "*", mode = "allow" }
```

**Alternatives considered**:
- Decorator-based permissions on each tool function: Rejected — too verbose, requires modifying every tool function
- Subclassing `ToolRegistry`: Rejected — permissions are orthogonal to tool storage/retrieval

### 3. Output Truncation Strategy

**Decision**: Create `OutputTruncator` as a standalone utility applied at the tool return boundary. The truncator is called in `PermissionManager.execute()` (or `ToolRegistry.execute()`) before returning results to the agent.

**Rationale**: Truncation is a cross-cutting concern that applies to all tools uniformly. Applying it at the return boundary ensures no tool output can bypass it.

**Default threshold**: 10,240 characters (10KB)

**Truncation algorithm**:
1. If output is within threshold, return as-is
2. If output exceeds threshold, find the last `\n` character before the threshold
3. Truncate there and append `[truncated N lines, M chars]`
4. If no `\n` found before threshold (single extremely long line), truncate at threshold

**Alternatives considered**:
- Per-tool truncation strategies: Rejected in v1 — adds unnecessary complexity
- Truncation at the agent/message level: Rejected — tools should self-truncate for cleaner error messages

### 4. Tool Parameter Schema Design

**Decision**: Use the existing `@tool` decorator for all new tools, relying on type hints for automatic JSON Schema generation.

**Shell tool** (`run_shell`):
```python
@tool
def run_shell(command: str, timeout: int = 30, workdir: str = "") -> str:
    """Execute a shell command and return its output."""
```

**File tools**:
```python
@tool
def read_file(path: str) -> str:
    """Read a file's contents."""

@tool
def write_file(path: str, content: str) -> str:
    """Write content to a file."""

@tool
def glob_file(pattern: str, path: str = ".") -> str:
    """Find files matching a glob pattern."""

@tool
def grep_file(pattern: str, path: str = ".", context: int = 0) -> str:
    """Search file contents for a pattern."""
```

**Git tools**:
```python
@tool
def git_status(path: str = ".") -> str:
    """Show working tree status."""

@tool
def git_diff(path: str = ".") -> str:
    """Show unstaged changes."""

@tool
def git_log(path: str = ".", max_count: int = 10) -> str:
    """Show recent commits."""
```

### 5. Path Traversal Protection

**Decision**: File write operations must validate the target path resolves within the project directory.

**Algorithm**:
1. Resolve the target path to an absolute path
2. Resolve the project directory to an absolute path
3. Use `Path.resolve()` to eliminate `..` traversal
4. Check `target_path.resolve().is_relative_to(project_dir.resolve())`
5. If not relative, return permission error

### 6. Existing Code Integration Points

- **ToolRegistry** (`src/nanoagent/registry.py`): Add `PermissionManager` integration. Extend `execute()` with permission check + output truncation.
- **Agent** (`src/nanoagent/agent/agent.py`): Add `register_builtin_tools()` method called at agent init.
- **__init__** (`src/nanoagent/__init__.py`): Export new public symbols.
- **AgentConfig** (`src/nanoagent/config.py`): Add `permissions_config` field and TOML parsing for `[tools.permissions]`.

### 7. Permission Evaluation Logic

```python
def check_permission(self, tool_name: str, command: str = "") -> PermissionResult:
    """
    1. Check tool-level rules first
    2. Check command-level rules for shell tools
    3. Fall back to default_mode
    """
    rules = self._get_matching_rules(tool_name, command)
    if any(r.mode == "deny" for r in rules):
        return DENIED
    if any(r.mode == "ask" for r in rules):
        return ASK
    return ALLOWED
```

Rules are ordered by specificity (more specific = higher priority). If a deny rule matches, deny takes precedence. If only ask rules match, require human approval.

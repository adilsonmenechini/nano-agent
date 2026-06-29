# Quickstart: Agent Tool System Validation

## Prerequisites

- Python 3.13+
- `pip install -e ".[dev]"` from project root
- `nanoagent` CLI available

## Setup

```bash
cd /path/to/nanoagent
source .venv/bin/activate
```

## Validation Scenarios

### 1. Shell Tool — Basic Execution

```python
from nanoagent.tool import tool
from nanoagent.registry import ToolRegistry

# Run this in a Python shell or test
from nanoagent.agent.tools.shell import run_shell

registry = ToolRegistry()
registry.register(run_shell)

result = registry.execute("run_shell", {"command": "echo hello"})
assert "hello" in result
```

**Expected**: Returns `"hello\n"` with exit code 0.

---

### 2. File Tools — Read and Write

```python
import tempfile, os
from nanoagent.agent.tools.file_tools import read_file, write_file

registry = ToolRegistry()
registry.register(read_file)
registry.register(write_file)

with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
    f.write("test content")
    tmp = f.name

content = registry.execute("read_file", {"path": tmp})
assert content == "test content"

result = registry.execute("write_file", {"path": tmp, "content": "updated"})
assert result == "OK"

content = registry.execute("read_file", {"path": tmp})
assert content == "updated"

os.unlink(tmp)
```

**Expected**: Read returns file contents, write updates file successfully.

---

### 3. Git Tools — Status and Log

```python
# Must be run inside a git repository
from nanoagent.agent.tools.git_tools import git_status, git_log

registry = ToolRegistry()
registry.register(git_status)
registry.register(git_log)

status = registry.execute("git_status", {"path": "."})
assert isinstance(status, str)  # Returns git status output

log = registry.execute("git_log", {"path": ".", "max_count": 5})
assert isinstance(log, str)
assert "commit" in log.lower()
```

**Expected**: Status returns working tree state, log returns commit history.

---

### 4. Permission System — Deny Blocked Commands

```python
from nanoagent.permissions import PermissionManager, PermissionRule

pm = PermissionManager(default_mode="allow")
pm.add_rule(PermissionRule(
    tool_name="run_shell",
    match_type="prefix",
    pattern="rm -rf",
    mode="deny",
))

result = pm.check("run_shell", "rm -rf /")
assert result == "DENIED"

result = pm.check("run_shell", "echo safe")
assert result == "ALLOWED"
```

**Expected**: Denied command returns DENIED without execution. Safe command returns ALLOWED.

---

### 5. Permission System — Ask Mode

```python
pm.add_rule(PermissionRule(
    tool_name="run_shell",
    match_type="prefix",
    pattern="sudo",
    mode="ask",
))

result = pm.check("run_shell", "sudo rm -rf /")
assert result == "ASK"
```

**Expected**: Commands matching "ask" rules return ASK status, deferring to human approval.

---

### 6. Output Truncation

```python
from nanoagent.truncation import OutputTruncator

truncator = OutputTruncator(max_chars=100)

short = "hello world"
assert truncator.truncate(short) == short

long = "line1\n" + "x" * 200 + "\nline3"
result = truncator.truncate(long)
assert len(result) <= 100 + len("[truncated 1 lines, 189 chars]")
assert "[truncated" in result
```

**Expected**: Short output unchanged, long output truncated at line boundary with marker.

---

### 7. Path Traversal Protection

```python
from nanoagent.agent.tools.file_tools import write_file

# Attempt to write outside project dir
result = registry.execute("write_file", {
    "path": "/etc/passwd",
    "content": "evil"
})
assert "Error" in result or "denied" in result or "outside" in result
```

**Expected**: Write to path outside project directory is rejected with error.

---

### 8. Full Integration Test

```bash
# Start nanoagent CLI with permissions
nanoagent --config test_config.toml

# Agent should have all built-in tools available
# Try: "run shell command: echo hello"
# Try: "read file: nanoagent/__init__.py"
# Try: "git status"
```

**Expected**: All tools available, permissions enforced, outputs truncated when large.

## Running Automated Tests

```bash
# Run all tool-related tests
pytest tests/test_shell_tool.py tests/test_file_tools.py tests/test_git_tools.py tests/test_permissions.py tests/test_truncation.py -v

# Run with coverage
pytest --cov=src/nanoagent --cov-report=term-missing tests/test_*.py
```

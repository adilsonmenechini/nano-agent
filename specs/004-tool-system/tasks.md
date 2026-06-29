---

description: "Task list for Agent Tool System feature implementation"
---

# Tasks: Agent Tool System

**Input**: Design documents from `specs/004-tool-system/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

**Tests**: Test tasks are included per the TDD mandate in the project constitution (80% line coverage required).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1=shell, US2=file, US3=git, US4=permissions, US5=truncation)
- Include exact file paths in descriptions

---

## Phase 1: Setup

**Purpose**: Create package scaffolding for new modules

- [ ] T001 [P] Create `agent/tools/__init__.py` that exports all built-in tool functions in `src/nanoagent/agent/tools/__init__.py`
- [ ] T002 [P] Create `permissions.py` skeleton with PermissionMode enum in `src/nanoagent/permissions.py`
- [ ] T003 [P] Create `truncation.py` skeleton with OutputTruncator stub in `src/nanoagent/truncation.py`
- [ ] T004 Update `__init__.py` to export new public symbols (PermissionManager, OutputTruncator, register_builtin_tools) in `src/nanoagent/__init__.py`

---

## Phase 2: Foundational — OutputTruncator (US5 — P2)

**Story Goal**: Output truncation prevents context overflow from large tool outputs. Tools returning more than the configured threshold get truncated at a line boundary with a truncation marker appended.

**Independent Test**: `from nanoagent.truncation import OutputTruncator; t = OutputTruncator(max_chars=100); result = t.truncate("a" * 200); assert "[truncated" in result`

### Test Tasks

- [ ] T005 (Test) Test truncation within threshold — output unchanged in `tests/test_truncation.py`
- [ ] T006 (Test) Test truncation exceeding threshold — truncated with marker in `tests/test_truncation.py`
- [ ] T007 (Test) Test truncation snaps to line boundary — mid-line truncation returns to previous `\n` in `tests/test_truncation.py`
- [ ] T008 (Test) Test edge case: no newline before threshold — truncates at max_chars in `tests/test_truncation.py`
- [ ] T009 (Test) Test zero-length output — passes through unchanged in `tests/test_truncation.py`
- [ ] T010 (Test) Test configurable max_chars in `tests/test_truncation.py`

### Implementation Tasks

- [ ] T011 Implement `OutputTruncator` class with `max_chars`, `suffix` fields in `src/nanoagent/truncation.py`
- [ ] T012 Implement `truncate(text: str) -> str` method — counts lines/chars, truncates at line boundary, appends `[truncated N lines, M chars]` marker

---

## Phase 3: Foundational — PermissionManager (US4 — P1)

**Story Goal**: Permission-based tool access control. The PermissionManager evaluates tool invocations against configured rules (allow/deny/ask) and rejects blocked operations before execution.

**Independent Test**: `from nanoagent.permissions import PermissionManager, PermissionRule; pm = PermissionManager(default_mode="allow"); pm.add_rule(PermissionRule(tool_name="run_shell", match_type="prefix", pattern="rm", mode="deny")); assert pm.check("run_shell", "rm -rf /") == "DENIED"`

### Test Tasks

- [ ] T013 (Test) Test allow mode — matching rule returns ALLOWED in `tests/test_permissions.py`
- [ ] T014 (Test) Test deny mode — matching rule returns DENIED in `tests/test_permissions.py`
- [ ] T015 [P] (Test) Test ask mode — matching rule returns ASK in `tests/test_permissions.py`
- [ ] T016 [P] (Test) Test exact matching — only exact command matched in `tests/test_permissions.py`
- [ ] T017 [P] (Test) Test prefix matching — command starts with pattern in `tests/test_permissions.py`
- [ ] T018 [P] (Test) Test regex matching — pattern regex matched against command in `tests/test_permissions.py`
- [ ] T019 [P] (Test) Test no matching rule — falls back to default_mode in `tests/test_permissions.py`
- [ ] T020 [P] (Test) Test `default_mode="deny"` — deny when no rule matches in `tests/test_permissions.py`
- [ ] T021 [P] (Test) Test rule with tool_name="*" — applies to all tools in `tests/test_permissions.py`
- [ ] T022 [P] (Test) Test multiple rules — most specific wins in `tests/test_permissions.py`
- [ ] T023 [P] (Test) Test TOML config loading — permissions loaded from config dict in `tests/test_permissions.py`

### Implementation Tasks

- [ ] T024 Implement `PermissionMode` enum (`ALLOW`, `DENY`, `ASK`) and `PermissionRule` dataclass (`tool_name`, `match_type`, `pattern`, `mode`) in `src/nanoagent/permissions.py`
- [ ] T025 [P] Implement `PermissionManager` class with `rules`, `default_mode` fields in `src/nanoagent/permissions.py`
- [ ] T026 [P] Implement `add_rule(rule)` method in `src/nanoagent/permissions.py`
- [ ] T027 Implement `check(tool_name, command="")` method — evaluates rules in priority order (exact > prefix > regex, tool-specific > wildcard), returns `PermissionMode` in `src/nanoagent/permissions.py`
- [ ] T028 Implement `load_from_config(config_dict)` class method — parses `[tools.permissions]` TOML section into PermissionRule list in `src/nanoagent/permissions.py`

---

## Phase 4: Shell Tool — run_shell (US1 — P1)

**Story Goal**: The agent can execute shell commands with configurable timeout and permission enforcement. The tool returns stdout, stderr, and exit code.

**Independent Test**: `from nanoagent.agent.tools.shell import run_shell; result = run_shell(command="echo hello"); assert "hello" in result`

**Dependencies**: US4 (permission check) and US5 (output truncation)

### Test Tasks

- [ ] T029 (Test) Test basic shell command execution — returns stdout in `tests/test_shell_tool.py`
- [ ] T030 [P] (Test) Test non-zero exit code — returns stderr and exit code in `tests/test_shell_tool.py`
- [ ] T031 [P] (Test) Test command timeout — raises/returns timeout error in `tests/test_shell_tool.py`
- [ ] T032 [P] (Test) Test empty command — returns error message in `tests/test_shell_tool.py`
- [ ] T033 [P] (Test) Test working directory parameter — command runs in specified dir in `tests/test_shell_tool.py`
- [ ] T034 [P] (Test) Test shell tool registration in ToolRegistry — works via `@tool` decorator in `tests/test_shell_tool.py`

### Implementation Tasks

- [ ] T035 Implement `run_shell` function with `@tool` decorator — parameters: `command: str`, `timeout: int = 30`, `workdir: str = ""` in `src/nanoagent/agent/tools/shell.py`
- [ ] T036 Implement shell execution using `subprocess.run()` with `timeout` parameter, capturing stdout/stderr/returncode in `src/nanoagent/agent/tools/shell.py`
- [ ] T037 Handle timeout via `subprocess.TimeoutExpired` — return structured error with timeout message in `src/nanoagent/agent/tools/shell.py`
- [ ] T038 Handle non-zero exit codes — include exit code and stderr in return string in `src/nanoagent/agent/tools/shell.py`

---

## Phase 5: File Tools — read_file, write_file, glob_file, grep_file (US2 — P1)

**Story Goal**: The agent can read, write, and search project files. File operations validate path safety (no traversal outside project directory).

**Independent Test**: `from nanoagent.agent.tools.file_tools import read_file; content = read_file(path="/tmp/test.txt"); assert isinstance(content, str)`

**Dependencies**: US5 (output truncation for large file reads)

### Test Tasks

- [ ] T039 (Test) Test read_file — existing file returns contents in `tests/test_file_tools.py`
- [ ] T040 [P] (Test) Test read_file — missing file returns not-found error in `tests/test_file_tools.py`
- [ ] T041 [P] (Test) Test write_file — writes content to path and confirms success in `tests/test_file_tools.py`
- [ ] T042 [P] (Test) Test glob_file — pattern matches expected files in `tests/test_file_tools.py`
- [ ] T043 [P] (Test) Test grep_file — pattern finds matching lines in `tests/test_file_tools.py`
- [ ] T044 [P] (Test) Test path traversal protection — write to path outside project dir returns error in `tests/test_file_tools.py`
- [ ] T045 [P] (Test) Test read_file with binary content — handles non-UTF8 gracefully in `tests/test_file_tools.py`
- [ ] T046 [P] (Test) Test file tool registration in ToolRegistry — works via `@tool` decorator in `tests/test_file_tools.py`

### Implementation Tasks

- [ ] T047 Implement `read_file` with `@tool` decorator — param `path: str`, opens file, returns contents in `src/nanoagent/agent/tools/file_tools.py`
- [ ] T048 Implement `write_file` with `@tool` decorator — params `path: str`, `content: str`, writes to file in `src/nanoagent/agent/tools/file_tools.py`
- [ ] T049 Implement `glob_file` with `@tool` decorator — params `pattern: str`, `path: str`, returns matching files in `src/nanoagent/agent/tools/file_tools.py`
- [ ] T050 Implement `grep_file` with `@tool` decorator — params `pattern: str`, `path: str`, `context: int = 0`, returns matching lines with context in `src/nanoagent/agent/tools/file_tools.py`
- [ ] T051 Implement `_validate_path(path)` helper — resolves path and checks `Path.resolve().is_relative_to(project_path)` for traversal protection in `src/nanoagent/agent/tools/file_tools.py`
- [ ] T052 Implement error handling — FileNotFoundError, PermissionError, UnicodeDecodeError all return structured error messages in `src/nanoagent/agent/tools/file_tools.py`

---

## Phase 6: Git Tools — git_status, git_diff, git_log (US3 — P2)

**Story Goal**: The agent can inspect git repository state — working tree status, unstaged diffs, and commit history.

**Independent Test**: `from nanoagent.agent.tools.git_tools import git_status; status = git_status(path="."); assert isinstance(status, str)`

**Dependencies**: US5 (output truncation) — shell permission enforcement via US4 when git tools use subprocess

### Test Tasks

- [ ] T053 (Test) Test git_status — returns status output in `tests/test_git_tools.py`
- [ ] T054 [P] (Test) Test git_diff — returns diff output in `tests/test_git_tools.py`
- [ ] T055 [P] (Test) Test git_log — returns commit history in `tests/test_git_tools.py`
- [ ] T056 [P] (Test) Test git_log with max_count — returns limited entries in `tests/test_git_tools.py`
- [ ] T057 [P] (Test) Test non-git directory — returns error message in `tests/test_git_tools.py`
- [ ] T058 [P] (Test) Test git not installed — returns error message in `tests/test_git_tools.py`
- [ ] T059 [P] (Test) Test git tool registration in ToolRegistry — works via `@tool` decorator in `tests/test_git_tools.py`

### Implementation Tasks

- [ ] T060 Implement `git_status` with `@tool` decorator — runs `git status --short` via subprocess in `src/nanoagent/agent/tools/git_tools.py`
- [ ] T061 Implement `git_diff` with `@tool` decorator — runs `git diff` via subprocess in `src/nanoagent/agent/tools/git_tools.py`
- [ ] T062 Implement `git_log` with `@tool` decorator — runs `git log --oneline -{max_count}` via subprocess in `src/nanoagent/agent/tools/git_tools.py`
- [ ] T063 Implement `_git_cmd(args, path)` helper — runs git subprocess command, checks for git repo validity, handles `git not found` error in `src/nanoagent/agent/tools/git_tools.py`

---

## Phase 7: Integration & Registration

**Purpose**: Wire everything together — register built-in tools at agent init, integrate PermissionManager and OutputTruncator into ToolRegistry.

- [ ] T064 [P] Implement `register_builtin_tools(registry)` function — registers all shell/file/git tools in a ToolRegistry instance in `src/nanoagent/agent/tools/__init__.py`
- [ ] T065 [P] Integrate PermissionManager into ToolRegistry — modify `ToolRegistry.execute()` to check permissions before execution, returning structured DENIED/ASK error in `src/nanoagent/registry.py`
- [ ] T066 [P] Integrate OutputTruncator into ToolRegistry — modify `ToolRegistry.execute()` to truncate results after tool execution in `src/nanoagent/registry.py`
- [ ] T067 Modify `Agent.__init__()` to call `register_builtin_tools()` and create PermissionManager from config in `src/nanoagent/agent/agent.py`
- [ ] T068 (Test) Integration test — agent starts with all tools registered, permissions enforced, truncation active in `tests/integration/test_agent_full.py`
- [ ] T069 (Test) End-to-end test — PermissionManager + OutputTruncator + ToolRegistry work together end-to-end in `tests/integration/test_tool_integration.py`
- [ ] T070 Update AgentConfig to parse `[tools.permissions]` TOML section from config file in `src/nanoagent/config.py`

---

## Phase 8: Polish & Cross-Cutting

**Purpose**: Logging, documentation, edge case hardening.

- [ ] T071 [P] Add tool invocation logging — log each tool call with timestamp, tool name, params, duration, outcome in `src/nanoagent/agent/logging.py` or new module
- [ ] T072 [P] Update README.md with built-in tools documentation
- [ ] T073 [P] Add example permissions config to `.env.example` or create `permissions.example.toml` in project root
- [ ] T074 [P] Run full test suite — verify 80% coverage on `src/nanoagent/`
- [ ] T075 [P] Run static analysis — Ruff, Pyright, Vulture (constitution gate)

---

## Dependencies

```text
Phase 1 (Setup) — no deps
    ↓
Phase 2 (OutputTruncator - US5) — no deps
    ↓ ↓
Phase 3 (PermissionManager - US4) — no deps
    ↓ ↓
Phase 4 (Shell - US1) — depends on US4 + US5
    ↓
Phase 5 (File - US2) — depends on US5 (truncation for large reads)
    ↓
Phase 6 (Git - US3) — depends on US5 (truncation for large output)
    ↓
Phase 7 (Integration) — depends on ALL (US1 + US2 + US3 + US4 + US5)
    ↓
Phase 8 (Polish) — depends on Phase 7
```

## Parallel Execution Opportunities

| Parallel Group | Tasks | Description |
|---|---|---|
| **Group A** | T001, T002, T003 | Create all 3 new module stubs simultaneously |
| **Group B** | T013-T023 | All PermissionManager test tasks (independent tests) |
| **Group C** | T029-T034 | All shell tool test tasks |
| **Group D** | T039-T046 | All file tool test tasks |
| **Group E** | T053-T059 | All git tool test tasks |
| **Group F** | T064, T065, T066, T070 | Integration tasks: register, permissions, truncation, config |

## Implementation Strategy

### MVP (Phase 2 + Phase 3 + Phase 4)
The minimum viable implementation delivers:
1. OutputTruncator — safe output handling
2. PermissionManager — controlled execution
3. Shell tool — fundamental automation
4. Integration wiring — all connected and testable

This covers all P1 items: US1 (Shell), US4 (Permissions), and the foundational US5 (Truncation).

### Incremental Delivery
1. **Wave 1**: Phases 1-3 (infrastructure — truncation + permissions)
2. **Wave 2**: Phase 4 (shell tool — first real tool with safety)
3. **Wave 3**: Phase 5 (file tools)
4. **Wave 4**: Phase 6 (git tools)
5. **Wave 5**: Phases 7-8 (integration, polish, docs)

Each wave is independently testable via the Independent Test defined in each phase.

## Format Validation

All tasks above follow the required format:
- `- [ ] Tnnn` — checkbox + sequential ID
- `[P]` present on parallelizable tasks
- `[Story]` label on user story phase tasks (e.g., `US1`)
- Exact file path in description

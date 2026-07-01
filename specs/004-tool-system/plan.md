# Implementation Plan: Agent Tool System

**Branch**: `004-tool-system` | **Date**: 2026-06-29 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/004-tool-system/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Add built-in tools (shell, file, git) to NanoAgent's existing Tool/ToolRegistry infrastructure, a permission-based access control system, and smart output truncation. The shell tool wraps `subprocess` with timeout, the file tools wrap filesystem operations, and git tools wrap CLI git commands. The permission manager enforces allow/deny/ask rules loaded from TOML config. Output truncation caps tool return size at a configurable threshold (default 10KB) respecting line boundaries.

## Technical Context

**Language/Version**: Python 3.13+

**Primary Dependencies**: None new. Uses stdlib (`subprocess`, `pathlib`, `os`) for shell/file/git tools. Permissions config via existing TOML parsing (`tomllib` in stdlib). All tools use the existing `Tool` dataclass from `nanoagent/tool.py` with type-hint-based JSON Schema inference.

**Storage**: Permission rules loaded from TOML config at startup (`~/.config/nanoagent/config.toml` under a `[tools.permissions]` section). No new persistence layer.

**Testing**: pytest via existing test suite (`tests/`). Existing coverage target: 80% line coverage on `src/nanoagent/`.

**Target Platform**: macOS (primary), Linux (secondary) — CLI tool. Shell tool uses POSIX-compatible subprocess.

**Project Type**: CLI agent framework (single-user, session-based).

**Performance Goals**:
- Shell tool executes `echo hello` in under 500ms (SC-001)
- File tool reads 100KB file in under 200ms (SC-002)
- Permission check completes in under 10ms (SC-003)
- Output truncation reduces 1MB output to 10KB threshold with correct marker (SC-005)

**Constraints**:
- Shell tool must support configurable timeout (default 30s) (FR-016)
- No concurrent tool execution for shell/file/git in v1 (sequential only)
- Path traversal protection for file writes: must validate target is within project directory (FR-018)
- Permission system supports 3 modes: allow, deny, ask (FR-010)
- Matching modes: exact, prefix, regex (FR-009)
- Truncation must be line-boundary aware (FR-013)
- Existing Tool/ToolRegistry pattern MUST be used (not BaseTool ABC) — see `src/nanoagent/agent/tools/base.py` vs `src/nanoagent/tool.py`

**Scale/Scope**: Single-user interactive CLI session. Permissions config is static per session. Tools operate synchronously.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Gate | Status | Rationale |
|------|--------|-----------|
| **I. Test-First (NON-NEGOTIABLE)** | ✅ PASS | Spec defines 15 acceptance scenarios across 5 user stories. Phase 2 will create test files first. |
| **II. Spec-Driven Development** | ✅ PASS | Spec (spec.md) fully defines scope, actors, acceptance criteria. |
| **III. Quality Gates (80% coverage)** | ✅ PASS | Feature adds ~400-600 LOC to `src/nanoagent/`. Tests will maintain 80% coverage. |
| **IV. Static Analysis (Ruff, Pyright, Vulture)** | ✅ PASS | All new code will pass existing tooling. No new dependencies introduced. |
| **V. Simplicity (YAGNI)** | ✅ PASS | Feature reuses existing Tool/ToolRegistry infrastructure. No new abstractions beyond the PermissionManager and OutputTruncator. |

## Project Structure

### Documentation (this feature)

```text
specs/004-tool-system/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
src/nanoagent/
├── __init__.py              # Export new: register_builtin_tools, PermissionManager
├── agent/
│   ├── tools/
│   │   ├── base.py          # Existing BaseTool ABC (unchanged)
│   │   ├── todo.py          # Existing todo tool (unchanged)
│   │   ├── web_tool.py      # Existing web tools (unchanged)
│   │   ├── shell.py         # NEW: run_shell tool
│   │   ├── file_tools.py    # NEW: read_file, write_file, glob_file, grep_file tools
│   │   ├── git_tools.py     # NEW: git_status, git_diff, git_log tools
│   │   └── __init__.py      # NEW: export built-in tool functions
│   └── agent.py             # Modify: register built-in tools at startup
├── permissions.py            # NEW: PermissionManager, PermissionRule, PermissionMode
├── truncation.py             # NEW: OutputTruncator

tests/
├── test_permissions.py       # NEW: PermissionManager unit tests
├── test_truncation.py        # NEW: OutputTruncator unit tests
├── test_shell_tool.py        # NEW: Shell tool unit tests
├── test_file_tools.py        # NEW: File tool unit tests
├── test_git_tools.py         # NEW: Git tool unit tests
```

**Structure Decision**: Single project (src/nanoagent/). New modules at package root level (`permissions.py`, `truncation.py`) with tool implementations under `agent/tools/` matching existing pattern.

## Complexity Tracking

*No constitutional violations. The feature is additive, reuses existing infrastructure, and introduces only the minimal new abstractions required by the spec.*

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | — | — |

# Feature Specification: Agent Tool System

**Feature Branch**: `004-tool-system`

**Created**: 2026-06-29

**Status**: Draft

**Input**: User description: "Built-in tools (file/shell/git agent tools), Permissions system, Smart output truncation"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Run Shell Commands via Agent (Priority: P1)

As a developer using NanoAgent, I want the agent to be able to run shell commands (with permission-based approval) so that I can automate terminal workflows without manually executing them.

**Why this priority**: Shell execution is the most fundamental tool — it unlocks all terminal automation and is the foundation that file/git tools extend.

**Independent Test**: A mock tool registry with a `run_shell` tool can be created, registered, and invoked through the agent tool interface. The tool receives a command string and returns stdout/stderr.

**Acceptance Scenarios**:

1. **Given** a registered `run_shell` tool, **When** the agent invokes it with `echo hello`, **Then** the tool returns stdout containing `hello`
2. **Given** a shell command with non-zero exit code, **When** the agent invokes the tool, **Then** the tool returns stderr content and the exit code
3. **Given** a command that exceeds a configured timeout, **When** the tool times out, **Then** the tool returns a timeout error without hanging indefinitely

---

### User Story 2 - Read/Write Files via Agent (Priority: P1)

As a developer using NanoAgent, I want the agent to be able to read, write, and search project files so that it can modify code and understand the codebase without manual copy-paste.

**Why this priority**: File operations are the second most critical tool — they enable the agent to perform code changes and understand project structure.

**Independent Test**: A `read_file` tool can be registered, invoked with a file path, and returns the file contents. A `write_file` tool writes content to a path and confirms success.

**Acceptance Scenarios**:

1. **Given** a file exists, **When** the agent invokes `read_file`, **Then** the tool returns the file contents
2. **Given** a file path, **When** the agent invokes `write_file` with new content, **Then** the file is updated and the tool returns success
3. **Given** a non-existent file path, **When** the agent invokes `read_file`, **Then** the tool returns a clear file-not-found error

---

### User Story 3 - Git Operations via Agent (Priority: P2)

As a developer using NanoAgent, I want the agent to be able to run common git commands (status, diff, log, add, commit) so that it can manage version control workflows.

**Why this priority**: Git operations have safety implications (commit/push) and depend on the shell tool infrastructure, but are a natural extension of the tool system.

**Independent Test**: A `git_status` tool returns the current working tree status. A `git_diff` tool returns unstaged changes. Both can be tested with a known git repository.

**Acceptance Scenarios**:

1. **Given** a git repository with uncommitted changes, **When** the agent invokes `git_status`, **Then** the tool returns modified/untracked file paths
2. **Given** a git repository, **When** the agent invokes `git_log` with a limit, **Then** the tool returns recent commit messages and hashes
3. **Given** a git repository, **When** the agent invokes `git_diff` without arguments, **Then** the tool returns the diff of unstaged changes

---

### User Story 4 - Permission-Based Tool Access Control (Priority: P1)

As a developer using NanoAgent, I want to define which tools the agent can use and require approval for dangerous operations so that I maintain control over destructive actions.

**Why this priority**: Safety is a prerequisite for any tool system — without permissions, shell/file/git tools are a security risk.

**Independent Test**: A permission registry can be configured with tool-specific allow/deny/ask-before-exec rules. A tool call blocked by permissions returns a denied error without executing.

**Acceptance Scenarios**:

1. **Given** `rm` is in a deny list, **When** the agent invokes a tool with command `rm -rf /`, **Then** the tool returns a permission denied error without executing
2. **Given** a tool requires approval, **When** the agent invokes it, **Then** the tool returns a pending-approval status and waits for human confirmation
3. **Given** tool categories defined with different permission levels, **When** the agent invokes a read-only tool, **Then** it executes without additional approval

---

### User Story 5 - Smart Output Truncation (Priority: P2)

As a developer using NanoAgent, I want tool outputs to be automatically truncated when they exceed a threshold so that the LLM context is not overwhelmed by large command outputs.

**Why this priority**: Truncation prevents context overflow from verbose commands, keeping the agent responsive. Important but not as critical as having the tools work at all.

**Independent Test**: A tool returning more than N characters of output has its content truncated to N with a truncation indicator appended. Original truncation boundary respects line breaks.

**Acceptance Scenarios**:

1. **Given** a command produces 20KB of output, **When** the truncation threshold is 10KB, **Then** the returned output is ≤10KB and includes a `[truncated...]` marker
2. **Given** a command produces output under the threshold, **When** the tool returns it, **Then** the output is returned in full without any truncation marker
3. **Given** truncation occurs mid-line, **When** the boundary lands in the middle of a line, **Then** the truncation snaps to the nearest line boundary before the threshold

---

### Edge Cases

- What happens when shell tool is invoked with no arguments?
- How does the system handle concurrent tool invocations?
- How does it behave when git is not installed or not in a git repository?
- What happens when a file write targets a path outside the project working directory?
- How does permission system interact with tool chaining (tool calling another tool)?
- What if truncation produces zero content (extremely long single line)?
- How does the system handle binary/non-UTF8 output from shell commands?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a `ToolRegistry` that allows dynamic registration and discovery of tools
- **FR-002**: System MUST provide a `run_shell` tool that executes shell commands with configurable timeout and returns stdout/stderr/exit_code
- **FR-003**: System MUST provide a `read_file` tool that reads file contents given an absolute path
- **FR-004**: System MUST provide a `write_file` tool that writes content to a file given an absolute path
- **FR-005**: System MUST provide a `glob` tool that finds files matching a glob pattern
- **FR-006**: System MUST provide a `grep` tool that searches file contents by pattern
- **FR-007**: System MUST provide `git_status`, `git_diff`, `git_log` tools for common git operations
- **FR-008**: System MUST provide a `PermissionManager` that controls tool access via configurable allow/deny/ask rules
- **FR-009**: Permission rules MUST support exact command matching, prefix matching, and regex matching for shell commands
- **FR-010**: Permission system MUST support three modes: `allow`, `deny`, and `ask` (require human approval)
- **FR-011**: Permission system MUST support tool-level and command-level rules (e.g., allow `read_file` always, deny `run_shell` with `rm -rf`)
- **FR-012**: System MUST provide an `OutputTruncator` that truncates tool output exceeding a configurable threshold
- **FR-013**: Truncation MUST respect line boundaries (snap to nearest line break before the threshold)
- **FR-014**: Truncated output MUST append a clear `[truncated N lines, M chars]` marker
- **FR-015**: All tools MUST report their schema/parameters in a standardized format for LLM consumption
- **FR-016**: Tool execution timeout MUST be configurable per-tool and per-invocation (default: 30s for shell, 10s for file/git)
- **FR-017**: System MUST log all tool invocations with timestamps, parameters, and outcome (success/failure/denied)
- **FR-018**: File write operations MUST validate that the target path is within the project directory (path traversal protection)

### Key Entities

- **ToolRegistry**: Central registry managing tool definitions, lookup by name, and lifecycle
- **ToolDefinition**: Schema describing a tool — name, description, parameters (JSON Schema), handler function
- **PermissionManager**: Evaluates whether a tool invocation is allowed, denied, or requires approval
- **PermissionRule**: A single rule with pattern, mode (allow/deny/ask), and optional scope (tool/command)
- **OutputTruncator**: Truncates large outputs respecting configurable thresholds and line boundaries
- **ToolResult**: Standardized result structure — success flag, content (stdout/file data), error message, metadata (exit code, duration, truncated flag)

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Shell tool executes a simple command (`echo hello`) and returns output within 500ms
- **SC-002**: File tool reads a 100KB file in under 200ms
- **SC-003**: Permission system denies a blocked command in under 10ms without executing it
- **SC-004**: Output truncation reduces 1MB output to configured threshold (e.g., 10KB) with correct truncation marker
- **SC-005**: Git tool returns status of a repository with 1000+ files in under 1s
- **SC-006**: All 6+ built-in tools are documented and return valid JSON Schema for LLM consumption
- **SC-007**: Permission system supports at least 3 rule types (exact, prefix, regex) for shell commands
- **SC-008**: Path traversal protection blocks write attempts to paths outside the project directory

## Assumptions

- Shell tool runs commands synchronously (sequential, not parallel)
- Permission configuration is static per session (no dynamic rule changes during execution)
- Truncation threshold is global (not per-tool) in v1
- Working directory for shell commands is the project root
- Git tools assume `git` CLI is installed and accessible via PATH
- Permission rules are loaded from a configuration file (YAML/JSON) at startup
- File operations use absolute paths only (no relative path resolution beyond the working directory)
- All text-based tools assume UTF-8 encoding for file content
- Output truncation is applied at the tool return boundary, not during streaming

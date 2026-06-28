# Feature Specification: Core Improvements

**Feature Branch**: `002-core-improvements`

**Created**: 2026-06-27

**Status**: Draft

**Input**: User description: "Critical gaps analysis for nano-agent — 50 gaps across 7 categories identified for a from-scratch fork"

**Constitution Reference**: This feature addresses gaps across all constitutional principles — strengthens the agent loop (Principle I), adds static analysis (Principle IV), and improves overall quality infrastructure.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Developer runs agent with streaming responses (Priority: P1)

As a user of the agent, I want to see responses appear incrementally as they are generated so that I get immediate feedback and a sense of progress during long responses.

**Why this priority**: Streaming is the most visible UX gap — without it, the agent feels unresponsive and slow.

**Independent Test**: Send a prompt requesting a long response and observe output appearing token-by-token rather than all at once.

**Acceptance Scenarios**:

1. **Given** the agent processes a prompt, **When** the LLM provider returns a streaming response, **Then** output is displayed incrementally as tokens arrive.
2. **Given** a streaming response is in progress, **When** the user cancels mid-stream, **Then** the agent stops gracefully.
3. **Given** the user prefers batch output, **When** configured, **Then** the agent can fall back to non-streaming mode.

---

### User Story 2 - Developer uses configurable LLM parameters (Priority: P1)

As a developer using the agent, I want to configure parameters like `max_tokens`, `temperature`, and retry behavior so that I can control response cost, creativity, and reliability.

**Why this priority**: Hardcoded parameters limit flexibility and can lead to runaway costs or unreliable behavior.

**Independent Test**: Set different temperature values and observe variance in response creativity; set max_tokens low and observe truncation.

**Acceptance Scenarios**:

1. **Given** the agent is configured with `max_tokens=50`, **When** a prompt would generate a long response, **Then** the response is truncated at approximately 50 tokens.
2. **Given** the agent is configured with `temperature=0`, **When** the same prompt is sent twice, **Then** responses are deterministic.
3. **Given** an API call fails with a transient error, **When** retry is enabled, **Then** the agent retries the call up to the configured limit before surfacing the error.

---

### User Story 3 - Developer benefits from semantic memory (Priority: P2)

As a user of the agent, I want the agent to retrieve relevant past information based on meaning, not just exact keyword matches, so that it can make better associations and provide more contextually relevant responses.

**Why this priority**: Semantic memory is the core differentiator between a basic agent and a truly intelligent one.

**Independent Test**: Store several memories, then query with semantically similar but lexically different terms — observe the agent retrieving relevant memories.

**Acceptance Scenarios**:

1. **Given** the agent has stored memories about "meeting schedules", **When** the user asks about "appointments", **Then** the agent retrieves the relevant stored memories.
2. **Given** memories have different importance levels, **When** context window is limited, **Then** the agent prioritizes higher-importance memories.

---

### User Story 4 - Developer creates skills that are loaded and executed from storage (Priority: P2)

As a developer building skills, I want skills stored in the database to be automatically loaded and executed at runtime so that I can add capabilities without modifying agent code.

**Why this priority**: Skills are stored but never executed from DB — this is a critical gap that makes the skill system incomplete.

**Independent Test**: Register a skill via the skill system, then invoke it — observe the agent loading and executing it from persistent storage.

**Acceptance Scenarios**:

1. **Given** a skill is stored in the database, **When** the agent starts, **Then** the skill is automatically loaded and available for execution.
2. **Given** a skill depends on specific tools, **When** the skill executes, **Then** it has access to those tools via runtime injection.

---

### User Story 5 - Developer uses health checks and configuration (Priority: P3)

As a developer setting up the agent, I want to verify provider connectivity and have a persistent configuration file so that setup and troubleshooting are straightforward.

**Why this priority**: Developer experience improvements reduce friction and debugging time.

**Independent Test**: Run a health check command with providers configured and unconfigured — observe different status outputs.

**Acceptance Scenarios**:

1. **Given** a provider is correctly configured, **When** the health check runs, **Then** it shows the provider as connected.
2. **Given** no API key is set for a provider, **When** the health check runs, **Then** it shows the provider as disconnected with a clear message.

---

### User Story 6 - Developer integrates CI with quality checks (Priority: P3)

As a project maintainer, I want CI to run all quality checks (tests, lint, type-check, dead code detection) on every push so that regressions are caught automatically.

**Why this priority**: CI automation enforces quality gates and prevents issues from reaching production.

**Independent Test**: Push a change with a type error — observe CI failing at the type-check stage.

**Acceptance Scenarios**:

1. **Given** a push is made, **When** CI runs, **Then** tests, ruff, pyright, and vulture all execute automatically.
2. **Given** any quality check fails, **When** CI completes, **Then** the pipeline status is "failed" with details.

---

### Edge Cases

- **Streaming with tool calls**: Streaming must handle the transition from text generation to tool call execution gracefully.
- **Retry with idempotency**: Retried API calls must be safe — LLM chat completions are naturally idempotent (same input = same output at temperature=0).
- **Memory with limited context**: When context exceeds token limits, the agent must intelligently summarize or drop least important memories.
- **Skill execution errors**: Failed skill execution should not crash the agent — errors must be caught and reported.
- **Configuration file migration**: Existing env-var-based configurations must continue to work after introducing config files.
- **CI with rate-limited providers**: CI tests that might hit provider APIs must be marked as external and excluded from default runs.

## Requirements *(mandatory)*

### Functional Requirements

#### Agent Execution & Loop

- **FR-001**: All LLM providers MUST support streaming responses, with output delivered incrementally as tokens are generated.
- **FR-002**: The agent MUST expose configurable parameters: `max_tokens` (with a sensible default), `temperature`, and `retry_attempts` (default: 3).
- **FR-003**: The agent MUST implement automatic retry with exponential backoff for transient API failures (timeouts, rate limits, 5xx errors).
- **FR-004**: The agent MUST support parallel execution of independent tool calls within a single agent turn.
- **FR-005**: The agent MUST implement semantic loop detection that identifies repeated patterns even when arguments vary.

#### Memory System

- **FR-006**: The memory system MUST support semantic search via embeddings (cosine similarity) in addition to FTS5 keyword search.
- **FR-007**: Memories MUST have an importance score that influences retrieval priority and context window allocation.
- **FR-008**: The agent MUST automatically decay and archive stale memories based on age and access frequency.
- **FR-009**: Memory consolidation MUST have a fallback mechanism when the LLM provider is unavailable.
- **FR-010**: Context limits MUST be calculated in tokens, not characters, using provider-appropriate tokenization.

#### Skills System

- **FR-011**: Skills stored in the database MUST be automatically loaded and available for execution at agent startup.
- **FR-012**: Skills MUST support dependency declarations (required tools, other skills) that are validated before execution.
- **FR-013**: Skills MUST receive runtime injection of tools and agent context during execution.
- **FR-014**: The skill system MUST support versioning with history — updating a skill creates a new version rather than overwriting.

#### Architecture

- **FR-015**: The agent MUST implement a state machine with explicit states (idle, thinking, executing_tools, awaiting_input, error).
- **FR-016**: Tool execution pipelines MUST support DAG-style workflows with dependency ordering.
- **FR-017**: The system MUST support basic multi-agent delegation — spawning sub-agents for independent tasks.
- **FR-018**: The agent MUST provide structured logging with configurable verbosity levels.
- **FR-019**: Callbacks MUST be available for monitoring agent behavior (tool calls, state transitions, errors).

#### CLI & UX

- **FR-020**: The REPL MUST support tab completion for commands and common actions.
- **FR-021**: The agent MUST support a persistent configuration file (TOML or YAML) that can override environment variables.
- **FR-022**: The agent MUST provide a health/status command that checks provider connectivity.
- **FR-023**: The agent MUST support structured output formats (JSON) in addition to rich markdown.

#### Testing & CI

- **FR-024**: The test suite MUST include integration tests for each LLM provider using mocked API responses.
- **FR-025**: CI pipeline MUST run tests, ruff, pyright, and vulture on every push and PR.
- **FR-026**: Type checking (pyright) MUST pass without errors on all `src/` code.

### Key Entities

- **Provider Config**: Configuration for each LLM provider including endpoint, API key, max_tokens, temperature.
- **Memory Embedding**: Vector representation of memory content for semantic search.
- **Skill Version**: Versioned snapshot of a skill's code and metadata.
- **Agent State**: Current state of the agent in its state machine lifecycle.
- **Tool Pipeline**: Directed acyclic graph of tool execution steps.
- **Config File**: Persistent TOML/YAML file for agent configuration.
- **Health Status**: Snapshot of provider connectivity and system health.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Streaming responses display the first token within 500ms of the prompt being submitted.
- **SC-002**: Retry mechanism recovers from transient failures in under 10 seconds without user-visible errors.
- **SC-003**: Semantic memory search returns relevant results for semantically similar queries 90% of the time (measured against a test corpus).
- **SC-004**: Skills stored in the database are loaded and available within 1 second of agent startup.
- **SC-005**: The config file supports all parameters currently available via environment variables.
- **SC-006**: CI pipeline completes all quality checks within 5 minutes of push.
- **SC-007**: All LLM providers (OpenAI, Anthropic, LM Studio) support streaming in their agent integration.
- **SC-008**: State machine transitions are logged and observable via callbacks.

## Constitution Alignment

This spec directly implements **Principle I (Test-First)** by requiring tests for all new streaming, memory, and skills functionality. It implements **Principle IV (Static Analysis & Linting)** by requiring CI enforcement of ruff, pyright, and vulture. It also addresses foundational architectural gaps that enable all other quality practices.

## Assumptions

- Streaming will be implemented at the provider level first, then exposed through the agent loop.
- Embeddings will use a lightweight local model (e.g., sentence-transformers) for offline capability.
- The configuration file will be optional — environment variables remain the primary configuration mechanism.
- The state machine will be a simple enum-based implementation in v1, not a full workflow engine.
- Parallel tool execution will start with independent tool calls only (no shared state between parallel branches).
- Skills stored in the database use the same interface as runtime-registered skills.
- Existing tests will be preserved and updated as needed for compatibility.

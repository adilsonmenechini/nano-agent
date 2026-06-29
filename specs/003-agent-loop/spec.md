# Feature Specification: Agent Loop Engineering

**Feature Branch**: `003-agent-loop`

**Created**: 2026-06-28

**Status**: Draft

**Input**: User description: "Loop Engineering"

**Constitution Reference**: This feature addresses the core agent execution loop, strengthening testability (Principle I) and reliability of the main interaction path. Incorporates Engineering Cybernetics principles (feedback control, stability monitoring, self-healing) inspired by Qian Xuesen's control theory applied to AI agent loops.

## References

- **MiniCode-Python**: Reference implementation for cybernetic agent loop patterns — turn kernel with phase-based execution, feedback/feedforward controllers, progress controller, stability monitor, self-healing engine, and verification controller. These patterns inform the design but NanoAgent's implementation will be tailored to its own architecture.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Developer runs agent with reliable phased execution (Priority: P1)

As a user of the agent, I want the agent to process my prompts through a structured, phase-based execution cycle so that each turn is predictable, observable, and resilient.

**Why this priority**: A phased loop with sense-control-act cycles is the foundation of reliable agent behavior — it transforms a black-box LLM call into an engineered system.

**Independent Test**: Send a prompt and observe the agent progressing through turn phases (receive → explore → execute → verify → respond) with clear phase transitions visible.

**Acceptance Scenarios**:

1. **Given** the agent receives a text prompt, **When** the turn starts, **Then** it progresses through discrete phases (explore, execute, verify) with observable transitions.
2. **Given** the agent completes all phases successfully, **When** the turn finishes, **Then** it returns a complete response and the reason for stopping is "done".
3. **Given** the agent is in the middle of a turn, **When** a second prompt arrives, **Then** the second prompt is queued until the current turn completes.
4. **Given** a turn completes, **When** the loop iteration finishes, **Then** the agent returns to a ready state with turn budget and metrics reset.

---

### User Story 2 - Developer sees real-time loop health and progress (Priority: P1)

As a user of the agent, I want visibility into loop health so that I know whether execution is progressing normally, stalled, or degrading.

**Why this priority**: Without health visibility, silent degradation or infinite loops appear as unresponsive agents.

**Independent Test**: Send a prompt that triggers multiple tool calls and observe health indicators (healthy, degraded, warning, critical) updating in real-time.

**Acceptance Scenarios**:

1. **Given** the agent is executing a turn, **When** the progress controller detects healthy progress, **Then** the health indicator shows "healthy" with current phase and step count visible.
2. **Given** tool calls are failing repeatedly, **When** the error rate exceeds a threshold, **Then** the health indicator degrades and the agent shows a stall warning.
3. **Given** the loop detects repeated identical tool calls (oscillation), **When** the oscillation index exceeds a threshold, **Then** the agent breaks the cycle and reports the stall reason.
4. **Given** the user wants detailed diagnostics, **When** diagnostics mode is enabled, **Then** per-phase timing, tool call duration, and stability metrics are displayed.

---

### User Story 3 - Developer benefits from resilient loop self-healing (Priority: P2)

As a user of the agent, I want the execution loop to detect faults and automatically recover so that transient failures don't crash my session.

**Why this priority**: Self-healing transforms the agent from fragile (crashes on any error) to resilient (recovers from common failures).

**Independent Test**: Simulate a transient API failure during a turn and observe the agent auto-recovering and completing the request without user intervention.

**Acceptance Scenarios**:

1. **Given** an LLM provider call fails with a transient error, **When** the self-healing engine detects the fault, **Then** it applies the configured healing strategy (e.g., retry with backoff) and continues the turn.
2. **Given** context usage exceeds 80% of the window, **When** the stability monitor detects context pressure, **Then** the agent triggers automatic compaction and continues.
3. **Given** repeated failures exceed the retry limit, **When** the self-healing engine cannot recover, **Then** it surfaces the fault with severity level and recommended action to the user.
4. **Given** a tool execution times out, **When** the fault is classified as TOOL_TIMEOUT, **Then** the agent logs the timeout, cancels the hanging call, and continues with remaining tools.

---

### User Story 4 - Developer debugs loop behavior with cybernetic diagnostics (Priority: P3)

As a developer operating the agent, I want diagnostic information about each loop execution so that I can troubleshoot performance and stability issues.

**Why this priority**: Diagnostics accelerate development and debugging but are not essential for basic operation.

**Independent Test**: Enable diagnostics mode and observe detailed loop metrics (phase timing, iteration count, tool call results, stability scores) after each prompt.

**Acceptance Scenarios**:

1. **Given** diagnostics mode is enabled, **When** the agent completes a loop iteration, **Then** a structured diagnostics report shows phase-by-phase timing with sub-second precision.
2. **Given** the stability monitor detects anomalies, **When** diagnostics mode is active, **Then** each anomaly is recorded with metric name, value, threshold, and severity.
3. **Given** a healing action is executed, **When** diagnostics mode is on, **Then** the action is logged with fault type, strategy used, execution time, and success status.
4. **Given** diagnostics mode is disabled, **When** the agent processes a prompt, **Then** no diagnostic information is shown.

---

### Edge Cases

- What happens when the turn starts but no LLM provider is configured? (Fault: RESOURCE_EXHAUSTION, severity: CRITICAL)
- What happens when a loop iteration exceeds the maximum step budget? (Stop reason: max_steps)
- What happens when the agent enters an oscillation cycle of repeated tool calls? (Fault: OSCILLATION)
- What happens when context usage exceeds 90% mid-turn? (Fault: CONTEXT_OVERFLOW → auto-compaction)
- What happens when the user sends an interruption signal during tool execution? (Stop reason: await_user)
- What happens when the progress controller detects a stall with no output change after 5+ tool calls?
- What happens when the agent receives an empty or whitespace-only prompt?
- What happens when a healing strategy itself fails? (Fallback: surface fault to user with full context)

## Requirements *(mandatory)*

### Functional Requirements

#### Turn Kernel & Phased Execution

- **FR-001**: The agent MUST process each user prompt through a structured turn consisting of discrete, observable phases: explore (understand intent), execute (run tools/LLM calls), and verify (check results).
- **FR-002**: Each turn MUST have a stop reason indicating why it ended: "done", "max_steps", "await_user", "blocked", or "verification_failed".
- **FR-003**: The turn MUST maintain a step budget with maximum steps per turn (configurable, default: 50). When the budget is exhausted, the turn MUST stop with reason "max_steps".
- **FR-004**: The agent MUST queue incoming prompts while a turn is in progress, processing them sequentially in FIFO order.
- **FR-005**: The agent MUST return to a ready state (IDLE) after each turn completes, regardless of stop reason.

#### Progress Control & Health Monitoring

- **FR-006**: The agent MUST implement a progress controller that senses step count, completion ratio, error rate, tool call frequency, and output changes each turn.
- **FR-007**: Based on progress signals, the controller MUST decide whether to: continue, switch strategy, narrow scope, request user confirmation, or stop.
- **FR-008**: The agent MUST compute a health score (0.0–1.0) each turn based on success rate, error frequency, context usage, and oscillation index.
- **FR-009**: The agent MUST expose a health level indicator with four levels: healthy, degraded, warning, critical — visible during turn execution.
- **FR-010**: The agent MUST detect oscillation (repeated identical tool calls) and break the cycle within 3 iterations of the pattern starting.
- **FR-011**: The agent MUST support a stall detection mechanism: if 5+ tool calls produce no output change, the controller must flag the stall and suggest a strategy switch.

#### Self-Healing & Fault Recovery

- **FR-012**: The agent MUST detect and classify faults into categories: resource exhaustion, context overflow, tool timeout, error spike, oscillation, deadlock.
- **FR-013**: For each fault category, the agent MUST have a healing strategy that defines: action, expected recovery time, and success probability.
- **FR-014**: The agent MUST track healing effectiveness per strategy (execution count, success count) and prefer historically successful strategies.
- **FR-015**: The agent MUST automatically trigger context compaction when context usage exceeds 80% of the window.
- **FR-016**: The agent MUST support configurable timeout limits per turn phase to prevent infinite hangs (default: 30s for tool calls, 120s for LLM response).
- **FR-017**: When a healing strategy fails, the agent MUST surface the fault to the user with severity level, fault type, and recommended action.

#### Diagnostics & Observability

- **FR-018**: The agent MUST support a diagnostics mode that exposes per-phase timing, step count, tool call details, and health metrics.
- **FR-019**: Each anomaly detected by the stability monitor MUST be recorded with: timestamp, metric name, value, threshold exceeded, and severity.
- **FR-020**: Each healing action MUST be logged with: fault type, strategy name, execution time, success status, and side effects.
- **FR-021**: The agent MUST handle empty or invalid prompts by returning a helpful message rather than entering the execution loop.

### Key Entities

- **Turn**: A single cycle of agent execution triggered by a user prompt. Contains phases (explore, execute, verify), a stop reason, and a step budget.
- **TurnBudget**: Tracks remaining steps, tool error count, and whether the max step limit was hit for the current turn.
- **TurnStepPolicy**: Dynamic policy for the current turn phase — defines whether to allow widening, compact aggressively, or continue with current strategy.
- **ProgressSignal**: Snapshot of turn progress including completion ratio, failure ratio, tool calls, output changes, and elapsed time.
- **ProgressDecision**: Output of the progress controller — action to take (continue, narrow scope, switch strategy, request confirmation, stop) with health and stall scores.
- **HealthLevel**: Enumeration of system health: healthy, degraded, warning, critical — computed from multi-dimensional metrics.
- **FaultRecord**: Detection record with fault type, severity, timestamp, metrics snapshot, and associated healing action ID.
- **HealingAction**: Self-healing execution record with strategy name, expected/actual recovery time, success confidence, and side effects.
- **StabilityReport**: Comprehensive report generated by the stability monitor containing health level, stability index, robustness score, and anomaly list.
- **DiagnosticsReport**: Structured summary of a completed turn containing per-phase timing, tool call records, stability metrics, and healing actions.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A text-only prompt completes a full turn cycle and displays the first response content within 500ms of submission.
- **SC-002**: The progress controller detects and reports a stall (5+ tool calls with no output change) within 2 seconds of the stall condition being met.
- **SC-003**: The agent detects and breaks an oscillation cycle of repeated identical tool calls within 3 iterations of the pattern starting.
- **SC-004**: The agent recovers from a simulated transient network failure within 10 seconds without losing conversation context or requiring user intervention.
- **SC-005**: Automatic context compaction triggers when context usage exceeds 80%, and completes in under 1 second without disrupting the current turn.
- **SC-006**: The turn step budget (default: 50) prevents any single prompt from exceeding the configured maximum iterations.
- **SC-007**: A user can interrupt an in-progress turn and the agent returns to a ready state within 2 seconds of the stop signal.
- **SC-008**: Diagnostics mode displays per-phase timing with sub-second precision for all turn phases.
- **SC-009**: The stability monitor correctly classifies at least 3 distinct anomaly types (oscillation, error spike, context overflow) during automated testing.
- **SC-010**: Healing effectiveness tracking correctly records execution count and success count for at least 2 distinct healing strategies.

## Assumptions

- The execution loop operates sequentially (one turn at a time) for v1 — concurrent prompt handling is out of scope.
- The user's connection to the LLM provider is assumed to be available with intermittent transient failures (timeouts, 5xx).
- Turns are expected to complete within seconds under normal conditions; multi-minute iterations represent edge cases.
- The diagnostics mode is a developer feature and will not be the default user experience.
- The existing state machine (IDLE, THINKING, EXECUTING_TOOLS, AWAITING_INPUT, ERROR) will be extended or refactored to support the phased turn model.
- Healing strategies are predefined for known fault categories — no AI-generated healing in v1.
- The progress controller thresholds (5 tool calls without output change, 50 max steps) are configurable defaults that can be tuned per deployment.
- Stability monitoring is passive (read-only) and does not modify agent behavior — it only recommends actions to the progress controller.

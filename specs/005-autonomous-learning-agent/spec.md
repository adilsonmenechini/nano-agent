# Feature Specification: Autonomous Learning Agent

**Feature Branch**: `005-autonomous-learning-agent`

**Created**: 2026-06-29

**Status**: Draft

**Input**: User description: "preciso que seja analisado o projeto agora deixa mais clean e funcional para que seja um agent autonomo que aprende e refleta sobre novas harness. Vamos usa o metodos Smart para analisar o projeto."

**Constitution Reference**: This feature implements **Principle I (Test-First)**, **Principle II (Spec-Driven)**, and **Principle V (Simplicity)** — adding self-reflection and learning capabilities while maintaining testability and avoiding premature abstraction.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Agent Reflects on Completed Tasks (Priority: P1)

As a user of NanoAgent, I want the agent to automatically analyze what happened after each task so that it improves over time without me having to manually guide it.

**Why this priority**: Reflection is the foundation of all learning — without post-task analysis, the agent cannot identify patterns, mistakes, or optimization opportunities. Every other learning capability depends on this.

**Independent Test**: After the agent completes a task (e.g., "find all Python files and count them"), it produces a structured reflection containing: which tools were used, how many steps were taken, whether there were failures or retries, and what could be improved next time. The reflection is stored and retrievable by the user.

**Acceptance Scenarios**:

1. **Given** the agent completes a multi-step task, **When** the turn finishes, **Then** a reflection record is automatically created containing the task summary, tool usage stats, step count, and any errors encountered
2. **Given** a reflection record exists, **When** the user queries past reflections, **Then** the agent can retrieve and present the reflection in a human-readable format
3. **Given** the agent encounters a tool error during execution, **When** the turn completes, **Then** the reflection includes the error context and whether it was resolved

---

### User Story 2 - Agent Learns from Past Experience (Priority: P1)

As a user of NanoAgent, I want the agent to reference its past successes and failures when faced with similar tasks so that it makes better decisions without repeating mistakes.

**Why this priority**: Experience-based learning is the core differentiator between a static script and an autonomous agent. Without this, the agent treats every task as if it's the first time.

**Independent Test**: The agent fails at task A with error X. Later, when presented with a similar task B that would trigger the same error, the agent proactively avoids the error (e.g., chooses a different tool or approach) and mentions learning from the past experience.

**Acceptance Scenarios**:

1. **Given** the agent previously failed a `run_shell` command with a permission error, **When** a new task would trigger the same command, **Then** the agent either asks for permission proactively or chooses an alternative approach
2. **Given** the agent previously succeeded at a file refactoring task using a specific sequence of tools, **When** a similar refactoring task appears, **Then** the agent recalls the successful pattern and applies it
3. **Given** accumulated experience records, **When** the agent is deciding which tool to use, **Then** it factors in past success rates of each tool for the given context

---

### User Story 3 - Agent Introspects Its Own Harness (Priority: P2)

As a developer using NanoAgent, I want the agent to analyze its own loop configuration, tool usage patterns, memory effectiveness, and performance metrics so that it can self-optimize without me manually tuning settings.

**Why this priority**: Harness introspection enables the agent to evolve its own execution environment. This is what makes it "autonomous" — it doesn't just use tools, it improves how it operates.

**Independent Test**: The agent examines its own configuration (loop settings, permission rules, tool registry) and produces a report identifying: unused tools, suboptimal timeout settings, frequently denied commands, and recommendations for config changes.

**Acceptance Scenarios**:

1. **Given** the agent has access to its own configuration, **When** asked to self-analyze, **Then** it produces a structured report of current settings and their effectiveness
2. **Given** the agent identifies a suboptimal setting (e.g., tool timeout too short for a frequently used tool), **When** it has a clear recommendation, **Then** it surfaces the suggestion to the user for approval
3. **Given** introspection data shows a tool has never been used after 50 turns, **When** producing a harness report, **Then** the agent flags the tool as a candidate for removal or permission relaxation

---

### User Story 4 - Agent Runs Proactive Background Cycles (Priority: P2)

As a user of NanoAgent, I want the agent to operate autonomously in the background — running scheduled reflection cycles, memory consolidation, and improvement scans — so that it continuously improves without requiring my direct interaction.

**Why this priority**: True autonomy requires the agent to act without being explicitly prompted. Background cycles transform the agent from reactive (response-only) to proactive (self-improving).

**Independent Test**: After a configurable interval (e.g., every 10 turns or every hour), the agent automatically triggers a background cycle that: (a) reviews recent reflections for patterns, (b) consolidates related memories, (c) produces a summary of what it learned, and (d) stores the summary for user review.

**Acceptance Scenarios**:

1. **Given** the agent has completed N turns since the last background cycle, **When** the turn threshold is reached, **Then** a background cycle triggers automatically without blocking active use
2. **Given** a background cycle completes, **When** the user checks agent status, **Then** the cycle results (learnings, consolidations, suggestions) are available
3. **Given** the user is in an active conversation, **When** a background cycle is due, **Then** the cycle runs in a non-blocking manner and defers any user-facing output

---

### User Story 5 - Agent Creates Skills from Observed Patterns (Priority: P3)

As a user of NanoAgent, I want the agent to automatically create reusable skills when it detects repeated successful patterns so that common workflows become single-step operations over time.

**Why this priority**: Skill synthesis is the highest level of autonomous learning — it represents the agent actively extending its own capabilities. It depends on all previous stories (reflection, experience learning, introspection) being in place.

**Independent Test**: After observing the user (or itself) successfully executing a 3-step pattern (e.g., "find Python files → read each → summarize contents") three times, the agent proposes a new skill encapsulating that pattern. The user can accept, modify, or reject the proposed skill.

**Acceptance Scenarios**:

1. **Given** a sequence of tools is used in the same order across 3+ independent tasks, **When** the pattern detector identifies the repetition, **Then** the agent proposes a new skill wrapping that sequence
2. **Given** a proposed skill exists, **When** the user approves it, **Then** the skill is saved to the skill store and becomes available for future use
3. **Given** the user rejects a proposed skill, **When** the same pattern occurs again, **Then** the agent does not re-propose the same skill (respects the rejection)

---

### Edge Cases

- What happens when reflection analysis finds no meaningful patterns? → The agent records a "no insights" result and avoids creating noise
- How does the agent handle conflicting past experiences (same situation, different outcomes)? → It records both and notes the conditions that differed
- What happens when the agent identifies a configuration change that would break existing functionality? → It flags the risk and requires explicit user approval
- How does background cycle interact with user-initiated tasks? → Background yields to user tasks, never preempts active conversation

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Agent MUST automatically generate a structured reflection record after each completed turn, containing: tool calls made, steps taken, errors encountered, outcome summary, and duration
- **FR-002**: Agent MUST store reflection records in persistent memory, retrievable by task type, date, and outcome
- **FR-003**: Agent MUST analyze past reflection records when planning a new task and surface relevant past patterns (successes and failures) to inform current decisions
- **FR-004**: Agent MUST adjust its behavior (tool selection, approach strategy) based on accumulated experience from past successes and failures
- **FR-005**: Agent MUST be able to read and report on its own configuration: loop settings, permission rules, tool registry, and memory stats
- **FR-006**: Agent MUST generate optimization recommendations from introspection data (unused tools, frequent errors, suboptimal timeouts)
- **FR-007**: Agent MUST support background execution of learning cycles (reflection review, pattern detection, memory consolidation) on a configurable schedule
- **FR-008**: Background cycles MUST NOT block or interrupt active user-agent conversations
- **FR-009**: Agent MUST detect repeated tool usage patterns (same sequence across 3+ tasks) and flag them as skill candidates
- **FR-010**: Agent MUST allow users to approve, modify, or reject proposed skill creations
- **FR-011**: Agent MUST track the effectiveness of its own learning — measuring whether reflected-upon improvements actually reduce errors over time
- **FR-012**: Agent MUST expose reflection and introspection data through CLI commands (e.g., `nanoagent reflection list`, `nanoagent harness report`)

### Key Entities *(include if feature involves data)*

- **ReflectionRecord**: Structured data for a single turn analysis — turn_id, timestamp, task_description, tool_calls[], steps_taken, errors[], outcome, duration_ms, lessons_learned[]
- **ExperiencePattern**: A learned correlation between context and outcome — trigger_conditions, recommended_action, success_rate, sample_size, first_observed, last_applied
- **HarnessSnapshot**: A point-in-time view of agent configuration and state — config values, registered tools, permission rules, memory stats, performance metrics
- **BackgroundCycle**: A scheduled autonomous execution — cycle_id, cycle_type (consolidate/reflect/scan), trigger (turn_count/interval), last_run, results
- **SkillProposal**: A candidate skill detected from pattern analysis — pattern_sequence, frequency, suggested_name, approval_status (pending/approved/rejected), proposed_code

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Within 10 tasks, the agent shows measurable improvement in task completion (fewer errors, fewer steps, less user intervention) compared to a baseline without reflection
- **SC-002**: After 50 turns, the agent can autonomously recall and apply lessons from at least 3 past experiences that are relevant to new tasks
- **SC-003**: Background cycles complete in under 5 seconds and never block user interaction for more than 100ms
- **SC-004**: The agent correctly identifies repeated patterns and proposes a skill after 3+ occurrences of the same tool sequence with ≥80% precision (no false positives)
- **SC-005**: Users can retrieve any past reflection record within one command (e.g., `nanoagent reflection list --last`)
- **SC-006**: Harness introspection reports uncover at least one actionable optimization (unused tool, misconfigured timeout, redundant permission rule) within the first 100 turns of usage
- **SC-007**: Post-learning error rate decreases by at least 30% compared to pre-learning baseline over a 200-turn window

## Assumptions

- The existing memory system (SQLiteMemoryStore) will be extended to store reflection records and experience patterns — no new database required
- The existing reflection capabilities in `background_review.py` and `correction_detector.py` provide foundational patterns that will be extended, not replaced
- The agent loop (Turn, TurnBudget, StopReason) provides sufficient hooks for post-turn reflection
- Background cycles run in the existing `threading` infrastructure used by AgentJob
- Skill proposals are presented to the user for approval — the agent does not auto-create skills without consent
- The user has the `sentence-transformers` optional dependency installed for semantic pattern matching; if not, pattern detection falls back to exact-sequence matching
- Background cycles are opt-in by configuration (disabled by default to not surprise users)

---

description: "Task list for Agent Loop Engineering feature implementation"
---

# Tasks: Agent Loop Engineering

**Feature Branch**: `003-agent-loop`

**Input**: Design documents from `specs/003-agent-loop/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/, quickstart.md

**Tests**: Included per constitution Principle I (Test-First, NON-NEGOTIABLE). Each implementable component has a corresponding Red/Green/Refactor test cycle.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `src/`, `tests/` at repository root
- New package: `src/nanoagent/loop/` created in Setup phase
- Tests: `tests/unit/loop/`, `tests/integration/`, `tests/contract/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the loop package structure and foundational configuration

- [X] T001 Create `src/nanoagent/loop/` package directory with `__init__.py`
- [X] T002 [P] Add `LoopConfig` import into existing `src/nanoagent/config.py` config system
- [X] T003 [P] Add `loop` module to package exports in `src/nanoagent/__init__.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core enums, data classes, and constants that ALL user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Tests for Foundational Layer

- [X] T004 [P] Write unit tests for enum definitions (Phase, StopReason, HealthLevel, FaultCategory, FaultSeverity, HealingStrategyType, ProgressAction) in `tests/unit/loop/test_constants.py`
- [X] T005 [P] Write unit tests for LoopConfig dataclass validation in `tests/unit/loop/test_constants.py`

### Implementation for Foundational Layer

- [X] T006 [P] Implement all enums (Phase, StopReason, HealthLevel, FaultCategory, FaultSeverity, HealingStrategyType, ProgressAction) in `src/nanoagent/loop/constants.py`
- [X] T007 [P] Implement LoopConfig dataclass with `__post_init__` validation and DEFAULT_CONFIG in `src/nanoagent/loop/constants.py`
- [X] T008 [P] Create public API re-exports in `src/nanoagent/loop/__init__.py` (all types from constants.py)
- [X] T009 [P] Implement `create_loop()` factory function in `src/nanoagent/loop/__init__.py`

**Checkpoint**: Foundation ready — all enums, constants, and config validated. User story implementation can begin.

---

## Phase 3: User Story 1 — Phased Turn Execution (Priority: P1) 🎯 MVP

**Goal**: The agent processes prompts through a structured, phase-based turn cycle (RECEIVE → EXPLORE → EXECUTE → VERIFY → RESPOND) with observable phase transitions, step budget, and stop reasons.

**Independent Test**: Send a prompt and observe the agent progressing through turn phases with a valid stop reason ("done") when completed. Verify step budget enforces max limit.

### Tests for User Story 1 ⚠️

> **Write these tests FIRST, ensure they FAIL before implementation (Red phase)**

- [X] T010 [P] [US1] Write unit test for Turn.start() full cycle (all phases, stop_reason="done") in `tests/unit/loop/test_turn.py`
- [X] T011 [P] [US1] Write unit test for TurnBudget step decrement and exhaustion in `tests/unit/loop/test_turn.py`
- [X] T012 [P] [US1] Write unit test for TurnStepPolicy strategy switching in `tests/unit/loop/test_turn.py`
- [X] T013 [P] [US1] Write unit test for Phase sequential transitions (no skip/backward) in `tests/unit/loop/test_turn.py`
- [X] T014 [P] [US1] Write unit test for empty/whitespace prompt handling (FR-021) in `tests/unit/loop/test_turn.py`
- [X] T015 [P] [US1] Write integration test for prompt queuing (non-overlapping turns, FR-004) in `tests/integration/test_loop_integration.py`

### Implementation for User Story 1

- [X] T016 [P] [US1] Implement TurnBudget class (max_steps, remaining_steps, tool_error_count, budget_exhausted) in `src/nanoagent/loop/turn.py`
- [X] T017 [P] [US1] Implement TurnStepPolicy class (allow_widening, compact_aggressively, current_strategy) in `src/nanoagent/loop/turn.py`
- [X] T018 [US1] Implement Turn class with phase orchestration (RECEIVE → EXPLORE → EXECUTE → VERIFY → RESPOND) and stop reason reporting in `src/nanoagent/loop/turn.py`
- [X] T019 [US1] Implement prompt queuing (FIFO) and sequential turn execution in `src/nanoagent/loop/turn.py`
- [X] T020 [US1] Integrate turn kernel with existing `src/nanoagent/agent/agent.py` — wrap the existing invoke() as the EXECUTE phase body
- [X] T021 [US1] Add empty/whitespace prompt validation returning helpful message instead of entering loop in `src/nanoagent/loop/turn.py`
- [X] T022 [US1] Update public exports in `src/nanoagent/loop/__init__.py` with Turn, TurnBudget, TurnStepPolicy

**Checkpoint**: US1 functional — agent processes prompts through phased turn loop with budget enforcement and stop reasons. MVP deliverable.

---

## Phase 4: User Story 2 — Loop Health & Progress (Priority: P1)

**Goal**: The progress controller monitors turn health (healthy/degraded/warning/critical), detects stalls and oscillations, and reports decisions to the turn kernel. Health indicator visible during execution.

**Independent Test**: Send a prompt that triggers multiple tool calls and observe health indicators updating. Simulate oscillation or stall and verify detection within configured thresholds.

### Tests for User Story 2 ⚠️

> **Write these tests FIRST**

- [X] T023 [P] [US2] Write unit test for ProgressSignal metric computation in `tests/unit/loop/test_progress.py`
- [X] T024 [P] [US2] Write unit test for ProgressController.evaluate() health scoring formula in `tests/unit/loop/test_progress.py`
- [X] T025 [P] [US2] Write unit test for HealthLevel mapping (score → level boundaries) in `tests/unit/loop/test_health.py`
- [X] T026 [P] [US2] Write unit test for StabilityMonitor oscillation detection (3+ identical calls) in `tests/unit/loop/test_health.py`
- [X] T027 [P] [US2] Write unit test for stall detection (5 tool calls with no output change) in `tests/unit/loop/test_progress.py`
- [X] T028 [US2] Write integration test for health display in CLI output in `tests/integration/test_loop_integration.py`

### Implementation for User Story 2

- [X] T029 [P] [US2] Implement ProgressSignal dataclass in `src/nanoagent/loop/progress.py`
- [X] T030 [P] [US2] Implement ProgressDecision dataclass in `src/nanoagent/loop/progress.py`
- [X] T031 [US2] Implement ProgressController with sliding window, health formula, stall/oscillation scoring in `src/nanoagent/loop/progress.py`
- [X] T032 [P] [US2] Implement HealthMetrics helper and HealthLevel mapping in `src/nanoagent/loop/health.py`
- [X] T033 [P] [US2] Implement StabilityMonitor with oscillation and stall detection in `src/nanoagent/loop/health.py`
- [X] T034 [P] [US2] Implement StabilityReport dataclass in `src/nanoagent/loop/health.py`
- [X] T035 [US2] Integrate ProgressController into Turn turn execution loop (evaluate after each step) in `src/nanoagent/loop/turn.py`
- [X] T036 [US2] Integrate StabilityMonitor into progress controller (anomaly detection feed) in `src/nanoagent/loop/progress.py`
- [X] T037 [US2] Add health indicator to CLI prompt line (when --health flag active) in `src/nanoagent/cli.py`
- [X] T038 [US2] Update public exports in `src/nanoagent/loop/__init__.py` with ProgressController, ProgressSignal, ProgressDecision, StabilityMonitor, StabilityReport

**Checkpoint**: US2 functional — progress controller monitors turn health, detects stalls/oscillation, displays health indicator in CLI.

---

## Phase 5: User Story 3 — Self-Healing & Fault Recovery (Priority: P2)

**Goal**: The healing engine detects faults (resource exhaustion, context overflow, tool timeout, error spike, oscillation, deadlock) and applies predefined healing strategies. Tracks strategy effectiveness. Surfaces unrecoverable faults to user.

**Independent Test**: Simulate a transient API failure and observe the agent auto-recovering. Simulate context overflow and verify auto-compaction triggers at 80%.

### Tests for User Story 3 ⚠️

> **Write these tests FIRST**

- [X] T039 [P] [US3] Write unit test for FaultRecord creation and severity classification in `tests/unit/loop/test_healing.py`
- [X] T040 [P] [US3] Write unit test for HealingEngine strategy selection (matches fault → strategy) in `tests/unit/loop/test_healing.py`
- [X] T041 [P] [US3] Write unit test for HealingEngine effectiveness tracking (execution/success counts) in `tests/unit/loop/test_healing.py`
- [X] T042 [P] [US3] Write unit test for HealingStrategy default definitions in `tests/unit/loop/test_healing.py`
- [X] T043 [P] [US3] Write unit test for context compaction trigger at 80% threshold (FR-015) in `tests/unit/loop/test_healing.py`
- [X] T044 [P] [US3] Write unit test for fail-case when no strategy applies (returns None, FR-017) in `tests/unit/loop/test_healing.py`
- [X] T045 [US3] Write integration test for self-healing cycle (fault → strategy → recovery → log) in `tests/integration/test_loop_integration.py`

### Implementation for User Story 3

- [X] T046 [P] [US3] Implement FaultRecord dataclass in `src/nanoagent/loop/constants.py`
- [X] T047 [P] [US3] Implement HealingStrategy dataclass with default strategies table in `src/nanoagent/loop/healing.py`
- [X] T048 [P] [US3] Implement HealingAction dataclass in `src/nanoagent/loop/constants.py`
- [X] T049 [US3] Implement HealingEngine with strategy selection, effectiveness tracking, and fault surfacing in `src/nanoagent/loop/healing.py`
- [X] T050 [US3] Integrate HealingEngine with progress controller (auto-heal on fault detection) in `src/nanoagent/loop/progress.py`
- [X] T051 [US3] Implement context compaction trigger and execution in `src/nanoagent/loop/turn.py`
- [X] T052 [P] [US3] Add timeout enforcement per turn phase (FR-016) in `src/nanoagent/loop/turn.py`
- [X] T053 [US3] Update public exports in `src/nanoagent/loop/__init__.py` with HealingEngine, HealingStrategy, HealingAction, FaultRecord

**Checkpoint**: US3 functional — agent detects and recovers from common fault types automatically.

---

## Phase 6: User Story 4 — Diagnostics & Observability (Priority: P3)

**Goal**: When diagnostics mode is enabled, per-phase timing, tool call details, stability metrics, and healing actions are recorded and displayed in a structured report after each turn. No overhead when disabled.

**Independent Test**: Enable diagnostics mode and observe detailed loop metrics after each prompt. Verify no diagnostics info when mode is off.

### Tests for User Story 4 ⚠️

> **Write these tests FIRST**

- [X] T054 [P] [US4] Write unit test for DiagnosticsCollector recording phase timings in `tests/unit/loop/test_diagnostics.py`
- [X] T055 [P] [US4] Write unit test for DiagnosticsReport structure and field correctness in `tests/unit/loop/test_diagnostics.py`
- [X] T056 [P] [US4] Write unit test for no-op mode when diagnostics disabled in `tests/unit/loop/test_diagnostics.py`
- [X] T057 [P] [US4] Write unit test for diagnostics rendering output format in `tests/unit/loop/test_diagnostics.py`
- [X] T058 [US4] Write integration test for --diagnostics flag CLI output in `tests/integration/test_loop_integration.py`

### Implementation for User Story 4

- [X] T059 [P] [US4] Implement DiagnosticsReport dataclass in `src/nanoagent/loop/diagnostics.py`
- [X] T060 [US4] Implement DiagnosticsCollector with recording, reporting, and no-op disabled mode in `src/nanoagent/loop/diagnostics.py`
- [X] T061 [US4] Implement diagnostics output rendering (Rich table format) in `src/nanoagent/loop/diagnostics.py`
- [X] T062 [US4] Integrate DiagnosticsCollector into Turn (record phases, tool calls, health) in `src/nanoagent/loop/turn.py`
- [X] T063 [US4] Add --diagnostics CLI flag support in `src/nanoagent/cli.py`
- [X] T064 [US4] Integrate diagnostics display into CLI output after turn completion in `src/nanoagent/cli.py`
- [X] T065 [US4] Add --health flag for health indicator in CLI prompt in `src/nanoagent/cli.py`
- [X] T066 [US4] Update public exports in `src/nanoagent/loop/__init__.py` with DiagnosticsCollector, DiagnosticsReport

**Checkpoint**: US4 functional — diagnostics mode provides structured per-turn metrics via CLI.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Logging, edge case hardening, final integration, documentation

- [X] T067 [P] Add structured logging throughout loop components in `src/nanoagent/loop/*.py`
- [X] T068 [P] Handle edge case: no LLM provider configured → stop with RESOURCE_EXHAUSTION fault in `src/nanoagent/loop/turn.py`
- [X] T069 [P] Handle edge case: user interruption during tool execution → stop_reason "await_user" in `src/nanoagent/agent/agent.py`
- [X] T070 [P] Handle edge case: healing strategy failure → surface to user with full context (FR-017) in `src/nanoagent/loop/healing.py`
- [X] T071 Create final integration/end-to-end test covering all 4 user stories in `tests/integration/test_loop_integration.py`
- [X] T072 Run full lint/type check: ruff, pyright, vulture on all new files
- [X] T073 Verify overall line coverage on `src/nanoagent/` meets ≥80% threshold
- [X] T074 Update AGENTS.md SPECKIT section with final plan reference (verify correct)

---

## Dependency Graph

```
Phase 1 (Setup)
    │
    ▼
Phase 2 (Foundational — enums, config, constants)
    │
    ├──────────────────────────────────┐
    ▼                                  ▼
Phase 3: US1 (Turn Kernel)     Phase 4: US2 (Health/Progress)
    │                                  │
    └──────────────┬───────────────────┘
                   ▼
          Phase 5: US3 (Self-Healing)
                   │
                   ▼
          Phase 6: US4 (Diagnostics)
                   │
                   ▼
          Phase 7: Polish & Cross-Cutting
```

**Notes**:
- US3 depends on US1 (turn phases) and US2 (progress signals for fault detection)
- US4 depends on US1 (turn phases) and US2 (health metrics for display) and US3 (healing actions for display)
- Within each phase, [P] tasks can execute in parallel
- Phase 2 must be complete before any user story phase starts

---

## Parallel Execution Opportunities

### Within Phase 3 (US1):
- T010, T011, T012, T013, T014 (tests) — ALL parallel (different features)
- T016, T017 (implementation) — parallel (TurnBudget vs TurnStepPolicy)
- T020, T021 (integration) — can start after T018 is done

### Within Phase 4 (US2):
- T023, T024, T025, T026, T027 (tests) — ALL parallel
- T029, T030, T032, T033, T034 (implementation) — ALL parallel
- T035 (integration with Turn) — after T029, T031 are done
- T037 (CLI health) — independent of other US2 implementation

### Within Phase 5 (US3):
- T039, T040, T041, T042, T043, T044 (tests) — ALL parallel
- T046, T047, T048 (implementation) — ALL parallel

### Within Phase 6 (US4):
- T054, T055, T056, T057 (tests) — ALL parallel
- T059, T065 (implementation) — parallel

---

## Implementation Strategy

### MVP Scope

**Phase 1 + Phase 2 + Phase 3 (US1)** is the MVP deliverable:

```
T001–T003: Setup package structure
T004–T008: Foundational enums, constants, config
T010–T022: Turn kernel with phased execution, step budget, stop reasons
```

At MVP completion, the agent runs through a structured turn cycle with observable phases and budget enforcement. This delivers the core value of predictable, observable execution.

### Incremental Delivery

| Increment | Scope | User Value |
|-----------|-------|------------|
| MVP | US1 (Turn Kernel) | Predictable phased execution with budget |
| Increment 2 | US2 (Health) | Real-time visibility into loop health |
| Increment 3 | US3 (Healing) | Automatic recovery from failures |
| Increment 4 | US4 (Diagnostics) | Developer debugging tools |

### Test Strategy

- **Unit tests** (`tests/unit/loop/`): Each component in isolation with mocked dependencies
- **Integration tests** (`tests/integration/`): Cross-component flow (Turn + ProgressController, Turn + HealingEngine)
- **Contract tests** (`tests/contract/`): LoopConfig validation, public API shape
- **Test-first**: Each implementation task has a corresponding test task (written first, ensures Red phase)
- **Coverage target**: ≥85% line coverage for `src/nanoagent/loop/` package

---

## Summary

| Dimension | Value |
|-----------|-------|
| **Total tasks** | 74 |
| **Phase 1 (Setup)** | 3 |
| **Phase 2 (Foundational)** | 6 |
| **Phase 3 (US1 — Turn)** | 13 |
| **Phase 4 (US2 — Health)** | 16 |
| **Phase 5 (US3 — Healing)** | 15 |
| **Phase 6 (US4 — Diagnostics)** | 13 |
| **Phase 7 (Polish)** | 8 |
| **Parallel-capable tasks** | 46 (62%) |
| **Test tasks** | 29 (39%) |
| **MVP scope** | T001–T022 (Phase 1 + 2 + 3) |
| **MVP test count** | 7 (T010–T015) |
| **Constitution compliance** | Test-First: ✅ All impl tasks have corresponding test tasks |

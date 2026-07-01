# Implementation Plan: Agent Loop Engineering

**Branch**: `003-agent-loop` | **Date**: 2026-06-28 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/003-agent-loop/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Engineer the NanoAgent execution loop using Engineering Cybernetics principles — replacing the current black-box LLM call with a structured, phased turn kernel (receive → explore → execute → verify → respond). The loop adds progress control with health monitoring (healthy/degraded/warning/critical), self-healing fault recovery, and developer diagnostics. Inspired by MiniCode-Python's cybernetic architecture (feedback controller, progress controller, stability monitor, self-healing engine) but tailored to NanoAgent's existing agent/CLI architecture with no external runtime dependencies.

## Technical Context

**Language/Version**: Python 3.13+

**Primary Dependencies**: None new beyond existing stack (openai, anthropic, click, mcp, rich, pyyaml). All loop components will use stdlib (dataclasses, enum, time, typing) plus existing rich (for diagnostics display).

**Storage**: N/A — loop state is in-memory per session (dataclass instances). No persistence layer required for v1.

**Testing**: pytest via existing test suite (`tests/`). Existing coverage target: 80% line coverage on `src/nanoagent/`.

**Target Platform**: macOS (primary), Linux (secondary) — CLI tool. No browser/UI.

**Project Type**: CLI agent framework (single-user, session-based).

**Performance Goals**:
- Simple text-only prompt: first response content within 500ms (SC-001)
- Oscillation detection: break cycle within 3 iterations (SC-003)
- Stall detection: report within 2s of condition met (SC-002)
- Context compaction: <1s at 80% threshold (SC-005)
- Recovery from transient failure: <10s with context preserved (SC-004)

**Constraints**:
- 50 max steps per turn default, configurable (SC-006)
- LLM provider timeout: 30s tool calls, 120s LLM response (FR-016)
- Existing state machine (IDLE, THINKING, EXECUTING_TOOLS, AWAITING_INPUT, ERROR) will be extended, not replaced
- No AI-generated healing in v1 — strategies are predefined (Assumption)
- No concurrent prompt handling in v1 — sequential only (Assumption)

**Scale/Scope**: Single-user interactive CLI session. One turn at a time. No multi-tenancy, no server mode.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Gate | Status | Rationale |
|------|--------|-----------|
| **I. Test-First (NON-NEGOTIABLE)** | ✅ PASS | Spec defines acceptance scenarios per user story. Phase 1 will define test patterns. Implementation MUST start with tests for each component. |
| **II. Spec-Driven Development** | ✅ PASS | Complete spec exists with 4 user stories, 21 FRs, 10 SCs, 9 edge cases. Spec quality validated via checklist (all 16 items pass). |
| **III. Quality Gates (80% coverage)** | ⚠️ WARNING | Current coverage ~83% (20/24 components). New components will add coverage surface. Must maintain ≥80% on `src/nanoagent/` — plan to add tests for 4 untested memory components alongside this feature. |
| **IV. Static Analysis (Ruff/Pyright/Vulture)** | ✅ PASS | Consistent with existing project standard. All new code must pass Ruff, Pyright, Vulture before merge. |
| **V. Simplicity (YAGNI)** | ✅ PASS | No new dependencies beyond existing stack. All components use stdlib. Healing strategies are predefined (no AI healing). Concurrent prompts explicitly out of scope for v1. No persistence layer. |

**Gate Decision**: PASS — proceed to Phase 0. The 80% coverage warning is a soft constraint that will be addressed by adding tests for untested memory components alongside this feature.

## Project Structure

### Documentation (this feature)

```text
specs/003-agent-loop/
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
├── loop/                           # NEW: Agent loop engineering package
│   ├── __init__.py                 # Public API exports
│   ├── turn.py                     # Turn, TurnBudget, TurnStepPolicy
│   ├── progress.py                 # ProgressSignal, ProgressDecision, ProgressController
│   ├── health.py                   # HealthLevel, StabilityMonitor, StabilityReport
│   ├── healing.py                  # FaultRecord, HealingAction, HealingEngine
│   ├── diagnostics.py              # DiagnosticsReport, diagnostics rendering
│   └── constants.py                # Default thresholds, timeouts, budget limits
├── agent/
│   ├── agent.py                    # [MODIFY] Integrate phased turn kernel
│   └── errors.py                   # [MODIFY] Add loop-specific error types
├── cli.py                          # [MODIFY] Add diagnostics mode flag, health display
├── config.py                       # [MODIFY] Add loop configuration options
└── memory/                         # Existing - add tests for untested components

tests/
├── unit/
│   └── loop/                       # NEW: Unit tests for loop components
│       ├── test_turn.py
│       ├── test_progress.py
│       ├── test_health.py
│       ├── test_healing.py
│       └── test_diagnostics.py
├── integration/
│   └── test_loop_integration.py    # NEW: Integration tests for loop end-to-end
└── contract/
    └── test_loop_contract.py       # NEW: Contract tests for loop interfaces
```

**Structure Decision**: New `loop/` package under `src/nanoagent/loop/` — decoupled from existing agent code to minimize refactoring risk. Existing files are modified minimally (agent.py for integration, cli.py for UI, config.py for settings). Each component in its own file for testability.

## Complexity Tracking

> No violations detected. All design choices are within the constitution's simplicity principle:
> - New package (`loop/`) avoids tangled coupling with existing `agent.py`
> - Stdlib only — no external dependencies introduced
> - Predefined healing strategies (no AI-generated logic)
> - Sequential execution (no async/concurrent complexity for v1)

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |

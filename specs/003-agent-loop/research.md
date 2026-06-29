# Research: Agent Loop Engineering

## Overview

All technical context items were resolved from existing codebase knowledge. No NEEDS CLARIFICATION markers were present after populating the plan. This document consolidates design decisions and alternatives considered.

## Design Decisions

### Decision 1: New `loop/` Package

- **Decision**: Create `src/nanoagent/loop/` as a new package with dedicated components
- **Rationale**: Existing `agent/agent.py` is already complex. A separate package keeps the loop engineering decoupled, testable, and independently maintainable.
- **Alternatives Considered**:
  1. **Inline in agent.py**: Rejected — would bloat an already-dense file and make unit testing harder
  2. **Mixins on Agent class**: Rejected — Python mixins add complexity and implicit coupling
  3. **New top-level package**: Accepted — clean module boundary, clear ownership

### Decision 2: Stdlib-Only Components

- **Decision**: All loop components use Python stdlib (dataclasses, enum, time, typing, collections, statistics)
- **Rationale**: Zero new dependencies. Matches constitution Principle V (Simplicity). Faster CI, no security surface.
- **Alternatives Considered**:
  1. **Pydantic models**: Rejected — adds dependency; only needed if we want serialization which is out of scope for v1
  2. **NumPy for metrics**: Rejected — heavy dependency for simple health scoring
  3. **asyncio**: Rejected — v1 is sequential; async adds complexity without benefit for single-user CLI

### Decision 3: Extend State Machine, Don't Replace

- **Decision**: Extend existing state machine (IDLE, THINKING, EXECUTING_TOOLS, AWAITING_INPUT, ERROR) with new phases (EXPLORE, VERIFY) rather than replacing it
- **Rationale**: Existing states are used throughout the codebase — replacement would be a massive refactor. Extension is minimal and additive.
- **Alternatives Considered**:
  1. **Full replacement with Phase enum**: Rejected — too invasive for v1, violates YAGNI
  2. **Adapter layer**: Rejected — adds abstraction without clear benefit

### Decision 4: Predefined Healing Strategies Only

- **Decision**: All healing strategies are hardcoded per fault category — no AI-generated or learned strategies in v1
- **Rationale**: Predictability, testability, and safety. AI-generated healing could have unpredictable side effects.
- **Alternatives Considered**:
  1. **LLM-based strategy selection**: Deferred to v2 — requires safety validation and guardrails
  2. **Configuration-driven strategies**: Deferred — hardcoded strategies are simpler and sufficient for known fault patterns

### Decision 5: Read-Only Stability Monitor

- **Decision**: The stability monitor is passive — it detects, classifies, and reports anomalies but does not modify agent behavior directly
- **Rationale**: Clear separation of concerns — the monitor provides data, the progress controller decides actions (consistent with Engineering Cybernetics sense-control-act cycle)
- **Alternatives Considered**:
  1. **Monolithic controller**: Rejected — violates separation of concerns
  2. **Active monitor with auto-action**: Rejected — could cause unpredictable behavior; progress controller should own decisions

### Decision 6: Integration with Existing Agent Loop

- **Decision**: The phased turn kernel wraps the existing execution flow rather than replacing it. The agent's existing `invoke()` method becomes the "execute" phase inside the new loop.
- **Rationale**: Reuses proven tool calling, error handling, and LLM interaction code. Minimizes regression risk.
- **Alternatives Considered**:
  1. **Full rewrite of agent.py**: Rejected — high risk, high effort, no user-visible benefit
  2. **Decorator-based wrapping**: Considered but rejected as less explicit than explicit phase orchestration

## Technology Choices

| Technology | Decision | Rationale |
|-----------|----------|-----------|
| Python version | 3.13+ | Existing project constraint — no change needed |
| State representation | `StrEnum` | Python 3.11+ native — no dependency needed |
| Metrics tracking | `collections.deque` | Fixed-size window for health scoring — O(1) push/pop |
| Health scoring | Weighted formula | Simple, transparent, easy to test |
| Diagnostics output | `rich` tables | Already a project dependency — consistent with existing CLI UI |
| Thread safety | `threading.Lock` | Sufficient for sequential single-user CLI |

## Existing Codebase Integration Points

| Component | Integration | Risk Level |
|-----------|-------------|------------|
| `agent/agent.py::invoke()` | Becomes the "execute" phase body | Medium — wrapping logic needed |
| `cli.py::repl_loop()` | Add health display + diagnostics flag | Low — additive UI change |
| `agent/errors.py` | Add loop-specific error types | Low — additive |
| `config.py` | Add loop thresholds | Low — additive |
| Existing state machine | Extend with EXPLORE, VERIFY phases | Medium — must not break existing state transitions |

## Open Questions (Resolved)

> All questions resolved during research. No outstanding NEEDS CLARIFICATION items.

| Question | Answer |
|----------|--------|
| What happens when all healing strategies fail? | Surface fault to user with severity, type, and recommended action (FR-017) |
| How does diagnostics mode toggle? | CLI flag `--diagnostics` or runtime toggle — documented in contracts |
| What is the default step budget? | 50 steps per turn (FR-003) — configurable |
| What is the stall detection threshold? | 5+ tool calls with no output change (FR-011) — configurable |
| How is context compaction triggered? | At 80% context usage, automatic (FR-015) |

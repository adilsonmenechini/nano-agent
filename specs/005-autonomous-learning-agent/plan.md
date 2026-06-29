# Implementation Plan: Autonomous Learning Agent

**Branch**: `005-autonomous-learning-agent` | **Date**: 2026-06-29 | **Spec**: [spec.md](file:///Users/adilsonmenechini/SRE/AI/nano-agent/specs/005-autonomous-learning-agent/spec.md)

**Input**: Feature specification from `specs/005-autonomous-learning-agent/spec.md`

---

## Summary

Transform NanoAgent from a reactive tool-using agent into an autonomous learning system that reflects on completed tasks, learns from past experience, introspects its own harness, runs background learning cycles, and synthesizes reusable skills from observed patterns. The feature extends existing infrastructure (background_review, correction_detector, memory store, agent loop) with structured reflection, experience-based pattern matching, harness introspection, and skill synthesis capabilities.

Approach: Extend existing components rather than creating new subsystems — reflection hooks in the agent loop, experience records in SQLiteMemoryStore, introspection via a new HarnessAnalyzer, background cycles via the existing threading infrastructure, and skill proposals via SkillStorage.

## Technical Context

**Language/Version**: Python 3.13+

**Primary Dependencies**: Existing project dependencies (openai, anthropic, click, rich, httpx, sqlite3 stdlib). No new external dependencies required — all learning/reflection logic uses existing infrastructure (SQLiteMemoryStore for persistence, Agent loop hooks for reflection triggers, SkillStorage for skill proposals).

**Storage**: SQLite via existing `SQLiteMemoryStore` — extended with new tables for `reflection_records` and `experience_patterns`. No new database system required.

**Testing**: pytest (existing — 504 tests). New tests will follow existing patterns in `tests/test_agent.py`, `tests/test_memory/`, and `tests/test_loop/`.

**Target Platform**: macOS/Linux (current support). Same as project.

**Project Type**: CLI tool + Python library. Existing structure.

**Performance Goals**: Background cycles <5s, must never block user interaction for >100ms. Reflection generation <200ms per turn. Pattern detection runs asynchronously.

**Constraints**: 
- Zero new external dependencies
- Must not break existing 504-test suite
- Background cycles must be opt-in (disabled by default)
- Skill proposals require user approval (never auto-create)
- All new data stored in existing SQLite database

**Scale/Scope**: Single-user desktop agent. Learning scales with usage — at ~1000 turns, reflection DB is expected to be <10MB.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| **I. Test-First** | ✅ PASS | All 12 FRs have GIVEN/WHEN/THEN acceptance scenarios. Tests written before implementation. |
| **II. Spec-Driven** | ✅ PASS | Spec written and validated via `/speckit.specify`. 5 user stories, 12 FRs, 7 success criteria. |
| **III. Quality Gates** | ⚠️ Partial | 80% coverage target — new code will be extensively tested. Existing coverage baseline ~55% (pre-existing gap, not caused by this feature). |
| **IV. Static Analysis** | ✅ PASS | Ruff, Pyright, Vulture will be run on all new code before merge. |
| **V. Simplicity** | ✅ PASS | Design extends existing components rather than creating new subsystems. No premature abstraction — reflection, learning, introspection are separate concerns that can be built independently. |

**Post-Design Re-check**: Re-evaluate after Phase 1 to ensure no scope creep.

## Project Structure

### Documentation (this feature)

```text
specs/005-autonomous-learning-agent/
├── spec.md               # Feature specification (/speckit.specify output)
├── plan.md               # This file (/speckit.plan output)
├── research.md           # Phase 0 output — technical research findings
├── data-model.md         # Phase 1 output — entity definitions and relationships
├── quickstart.md         # Phase 1 output — validation guide
├── contracts/            # Phase 1 output — interface contracts
│   ├── reflection.md     # ReflectionRecord schema and storage contract
│   ├── learning.md       # ExperiencePattern and pattern matching contract
│   ├── introspection.md  # HarnessSnapshot and analysis contract
│   └── background.md     # BackgroundCycle contract
└── tasks.md              # Phase 2 output — task breakdown (/speckit.tasks)
```

### Source Code (repository root)

```text
src/nanoagent/
├── agent/
│   ├── agent.py           # [MODIFY] Add post-turn reflection hook
│   ├── logging.py         # [MODIFY] Add reflection event logging
│   └── tools/
│       └── introspection.py  # [NEW] Harness introspection tool for the agent
├── learning/              # [NEW] Learning subsystem
│   ├── __init__.py
│   ├── reflector.py       # Post-turn reflection engine
│   ├── experience.py      # Pattern detection and experience matching
│   ├── background.py      # Background cycle scheduler and executor
│   └── synthesizer.py     # Skill proposal from pattern detection
├── evolution/             # [NEW] Skill evolution subsystem (opt-in, requires DSPy)
│   ├── __init__.py
│   ├── config.py          # EvolutionConfig — model, iterations, constraint limits
│   ├── dataset.py         # DatasetBuilder — eval sets from reflection_records or synthetic
│   ├── fitness.py         # SkillFitness — success_rate, latency, quality scoring
│   ├── constraints.py     # ConstraintValidator — size, structure, growth gates
│   ├── optimizer.py       # GeptOptimizer — DSPy-based prompt mutation + Pareto selection
│   └── pipeline.py        # EvolutionPipeline — full evolve loop orchestrator
├── introspection.py       # [NEW] HarnessAnalyzer — reads config, tools, memory stats
├── memory/
│   └── sqlite_memory_store.py  # [MODIFY] Add reflection_records + experience_patterns tables
├── skills/
│   └── loader.py          # [MODIFY] Support auto-loading proposed skills
├── cli.py                 # [MODIFY] Add `reflection`, `harness`, and `skill evolve` CLI commands
└── __init__.py            # [MODIFY] Export new public API

tests/
├── test_reflector.py              # [NEW] Unit tests for reflection engine
├── test_experience.py             # [NEW] Unit tests for pattern detection
├── test_background.py             # [NEW] Unit tests for background cycles
├── test_synthesizer.py            # [NEW] Unit tests for skill proposal
├── test_introspection.py          # [NEW] Unit tests for harness introspection
├── test_evolution_setup.py        # [NEW] Unit tests for evolution config + dataset
├── test_evolution_fitness.py      # [NEW] Unit tests for fitness scoring + constraints
├── test_evolution_pipeline.py     # [NEW] Integration tests for full evolution pipeline
├── test_cli_evolution.py          # [NEW] CLI tests for skill evolve command
├── test_memory/
│   └── test_reflections.py        # [NEW] Memory persistence for reflection/experience tables
└── integration/
    └── test_learning.py           # [NEW] End-to-end reflection → learning → improvement flow
```

## Complexity Tracking

No constitutional violations. The design is additive and extends existing patterns. Simpler alternatives considered and rejected:

| Rejected Approach | Why Not Chosen |
|------------------|----------------|
| External ML model for pattern detection | Overkill for single-user agent; heuristic pattern matching suffices and has zero deps |
| Separate reflection database | Existing SQLite works fine; new tables keep schema clean without connection overhead |
| Event-sourced learning store | Adds complexity without benefit — current patterns work for single-user, single-process agent |
| Auto-create skills without user approval | Violates safety principle; user must explicitly approve capability extensions |
| Always-on DSPy evolution | Evolution is expensive (~$2-10/run) and requires DSPy installed; opt-in CLI command only |

---

## Phase 0: Research

Research findings in [research.md](file:///Users/adilsonmenechini/SRE/AI/nano-agent/specs/005-autonomous-learning-agent/research.md).

### Research Tasks

| # | Task | Method | Status |
|---|------|--------|--------|
| R1 | Analyze existing `background_review.py` patterns for reuse | Codebase exploration | ⏳ |
| R2 | Analyze `correction_detector.py` for failure→learning patterns | Codebase exploration | ⏳ |
| R3 | Analyze agent loop hooks for reflection trigger points | Codebase exploration | ⏳ |
| R4 | Analyze `SQLiteMemoryStore` schema for extension | Codebase exploration | ⏳ |
| R5 | Analyze existing CLI commands for patterns to follow | Codebase exploration | ⏳ |
| R6 | Analyze SkillStorage for skill creation patterns | Codebase exploration | ⏳ |

---

## Phase 1: Design

Design artifacts:
- [data-model.md](file:///Users/adilsonmenechini/SRE/AI/nano-agent/specs/005-autonomous-learning-agent/data-model.md)
- [contracts/](file:///Users/adilsonmenechini/SRE/AI/nano-agent/specs/005-autonomous-learning-agent/contracts/)
  - [reflection.md](file:///Users/adilsonmenechini/SRE/AI/nano-agent/specs/005-autonomous-learning-agent/contracts/reflection.md)
  - [learning.md](file:///Users/adilsonmenechini/SRE/AI/nano-agent/specs/005-autonomous-learning-agent/contracts/learning.md)
  - [introspection.md](file:///Users/adilsonmenechini/SRE/AI/nano-agent/specs/005-autonomous-learning-agent/contracts/introspection.md)
  - [background.md](file:///Users/adilsonmenechini/SRE/AI/nano-agent/specs/005-autonomous-learning-agent/contracts/background.md)
- [quickstart.md](file:///Users/adilsonmenechini/SRE/AI/nano-agent/specs/005-autonomous-learning-agent/quickstart.md)

---

## Phase 7: Skill Evolution — DSPy + GEPA Pipeline

**Goal**: After skills are synthesized from patterns (Phase 6), evolve them through an offline optimization pipeline inspired by Hermes Agent Self-Evolution. Use DSPy + GEPA (Genetic-Pareto Prompt Evolution) to automatically improve skill descriptions, tool sequences, and prompts — producing measurably better versions through reflective evolutionary search.

### Why This Phase Exists

Skills generated by the Synthesizer (Phase 6) are based on raw pattern detection. They work, but they're not optimal. This phase adds a closed-loop improvement cycle:

1. **Evaluate** — Run the skill against real or synthetic tasks, measure success rate and latency
2. **Mutate** — Use DSPy to generate variant skill prompts/descriptions
3. **Select** — Use GEPA-style Pareto optimization to pick the best variant
4. **Promote** — If the evolved variant beats the baseline, offer it for user approval

### Key Components

| Component | Purpose | Parallel to Hermes |
|-----------|---------|-------------------|
| `EvolutionConfig` | DSPy model config, iteration count, eval source | `EvolutionConfig` |
| `DatasetBuilder` | Build eval datasets from reflection records (real sessions) or synthetic | `SyntheticDatasetBuilder` |
| `SkillFitness` | Evaluate skill variants: success rate, latency, output quality | `skill_fitness_metric` |
| `GEPSOptimizer` | DSPy-based optimizer that mutates skill prompts and selects best variant | GEPA engine |
| `ConstraintValidator` | Validate evolved variants: size limits, structural integrity, test suite | `ConstraintValidator` |

### Evolution Pipeline Flow

```
Read current skill ──► Build eval dataset from reflection_records
                              │
                              ▼
                        DSPy Optimizer
                              │
                              ▼
                    N candidate variants
                              │
                              ▼
                    Evaluate each variant
                              │
                    ┌─────────┴─────────┐
                    ▼                   ▼
            Constraint gates    Fitness scoring
                    │                   │
                    └─────────┬─────────┘
                              ▼
                    Best variant ──► prompt user: accept/reject
                              │
                         if accepted:
                              ▼
                    Update skill, record improvement
```

### Dependencies

- **Requires Phase 6** (US5 — needs synthesized skills to evolve)
- **Optional dependency**: DSPy (`pip install dspy-ai`)
- Skill evolution is **opt-in**, disabled by default, controlled via `[evolution]` config section

### Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Dependencies | DSPy is optional — evolution disabled if not installed | Keep core agent zero-dependency; evolution is a power-user feature |
| When to run | Explicit CLI command (`nanoagent skill evolve <slug>`), not automatic | Evolution is computationally expensive (~$2-10 per run); user must opt in |
| Eval source | Default: synthetic dataset. Option: real reflection_records | Synthetic is fast and offline; real data is more accurate but requires session history |
| Baseline comparison | Always compare evolved variant vs current before accepting | Prevents regressions; user sees before/after metrics |
| DSPy model | Configurable via `[evolution]` section, default `gpt-4.1-mini` | Balance of quality vs cost; user can upgrade to stronger model |

---
description: "Task list for Autonomous Learning Agent feature"
---

# Tasks: Autonomous Learning Agent

**Input**: Design documents from `specs/005-autonomous-learning-agent/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Organization**: Tasks grouped by user story. Each story is independently testable.

---

## Phase 1: Setup — Package Structure & Schema

**Purpose**: Create the learning subsystem package and extend database schema.

- [X] T001 Create `src/nanoagent/learning/` package with `__init__.py`
- [X] T002 Add `reflection_records` and `experience_patterns` tables to `SQLiteMemoryStore._create_tables()` in `src/nanoagent/memory/sqlite_memory_store.py`
- [X] T002b Add `status TEXT DEFAULT 'active'` column to `skills` table in `src/nanoagent/memory/sqlite_memory_store.py`
- [X] T003 [P] Add `ReflectionRecord` and `ExperiencePattern` dataclasses to `src/nanoagent/learning/__init__.py`
- [X] T004 [P] Create `tests/test_memory/test_reflections.py` with schema creation and table verification tests

---

## Phase 2: Foundational — Reflector + Agent Hook

**Purpose**: Core reflection infrastructure that all user stories depend on.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

### Reflector Implementation

- [X] T005 Implement `Reflector` class in `src/nanoagent/learning/reflector.py` with `reflect()`, `get_recent()`, `get_by_turn_id()`, `search()`, `get_stats()` methods
- [X] T006 Implement `Reflector.reflect()` — analyze messages, tool_results, errors, duration → create `ReflectionRecord` → persist to `reflection_records` table
- [X] T007 [P] Create `tests/test_reflector.py` with unit tests for Reflector (reflect, retrieval, search, stats)

### Agent Hook Integration

- [X] T008 Add `on_turn_complete` hook to `Agent.__init__()` in `src/nanoagent/agent/agent.py` (following existing `on_tool_call`, `on_tool_result` pattern)
- [X] T009 Wire `on_turn_complete` call at end of `Agent.run()` — invoked with `(response, messages, tool_results, errors, duration_ms)` after turn completes, before `_trigger_background_ops()`
- [X] T010 [P] Add `turn_complete()` method to `AgentLogger` in `src/nanoagent/agent/logging.py` for reflection event logging
- [X] T011 [P] Create `tests/test_agent.py` tests for `on_turn_complete` hook — mock the hook, run agent, verify hook called with correct arguments

---

## Phase 3: [US1] Post-Turn Reflection

**Goal**: Agent automatically reflects on each completed turn. Reflections are stored, retrievable, and searchable.

**Independent Test**: After `agent.run("list Python files")`, a reflection record exists containing tool names, step count, and outcome. The reflection can be retrieved by `reflector.get_recent()` and displays correctly.

### US1 — Wire Reflection into Agent

- [X] T012 [US1] Instantiate `Reflector` in `Agent.__init__()` when `AgentConfig` is provided, assign `self.on_turn_complete = self._reflector.reflect` to auto-reflect each turn
- [X] T013 [P] [US1] Create `tests/test_reflector.py` integration test — run agent with mock LLM, verify reflection record created after turn
- [X] T014 [US1] Export `Reflector`, `ReflectionRecord` from `src/nanoagent/__init__.py`

### US1 — CLI Commands

- [X] T015 [P] [US1] Add `reflection` Click command group in `src/nanoagent/cli.py` with `list`, `show`, `search` subcommands (following existing `memory` group pattern)
- [X] T016 [US1] Implement `reflection list` — query `Reflector.get_recent()`, display in Rich Table with turn_id, task_description, outcome, duration
- [X] T017 [US1] Implement `reflection show` — query `Reflector.get_by_turn_id()`, display full reflection detail in Rich Markdown
- [X] T018 [US1] Implement `reflection search` — query `Reflector.search()`, display results in Rich Table
- [X] T019 [P] [US1] Create `tests/test_cli_reflection.py` with CLI command tests (mock agent, invoke reflection commands, verify output format)

---

## Phase 4: [US2] Experience-Based Learning

**Goal**: Agent detects patterns across reflection records, stores them as experience patterns, and retrieves relevant past experiences to inform new decisions.

**Independent Test**: After 3+ similar tasks (e.g., "find all .py files", "find all .md files"), `ExperienceEngine.analyze_reflections()` returns a pattern with `sample_size >= 3` and the correct tool sequence.

**⚠️ Depends on**: Phase 3 (US1) — pattern detection requires reflection records to analyze

### US2 — Experience Engine

- [X] T020 [US2] Implement `ExperienceEngine` class in `src/nanoagent/learning/experience.py` with `analyze_reflections()`, `get_relevant_patterns()`, `record_outcome()`, `get_stats()` methods
- [X] T021 [US2] Implement `analyze_reflections()` — group reflections by keyword overlap in task_description, find common tool sequences (ordered subsets), compute success/failure ratios, return patterns with `sample_size >= 3`
- [X] T022 [US2] Implement `get_relevant_patterns(task_description)` — keyword-match trigger_context, sort by success_rate descending, return top N active patterns
- [X] T023 [US2] Implement `record_outcome(pattern_id, succeeded)` — update success_count/failure_count/sample_size for a stored pattern
- [X] T024 [P] [US2] Create `tests/test_experience.py` with unit tests: pattern detection from mock reflections, relevance matching, outcome recording, empty/edge cases

### US2 — Wire Experience into Agent

- [X] T025 [US2] Instantiate `ExperienceEngine` in `Agent.__init__()`, store as `self._experience`
- [X] T026 [US2] Modify `Agent.run()` to call `self._experience.get_relevant_patterns(task_description)` during memory context assembly — inject relevant patterns into system prompt as "past experiences"
- [X] T027 [P] [US2] Create integration test in `tests/integration/test_learning.py` — simulate 3 task runs, verify pattern detected, verify pattern influences agent behavior

---

## Phase 5: [US4] Background Learning Cycles

**Goal**: Agent automatically runs scheduled background cycles — reviewing reflections, detecting patterns, consolidating learnings — without blocking user interaction.

**Independent Test**: With `[learning] enabled = true` and `cycle_interval_turns = 5`, after 5 agent turns, `BackgroundLearner.start_if_due(5)` returns True and `execute_cycle()` produces a `CycleResult`.

**⚠️ Depends on**: Phase 3 (US1) + Phase 4 (US2)

### US4 — Background Scheduler

- [X] T028 [US4] Implement `BackgroundLearner` class in `src/nanoagent/learning/background.py` with `start_if_due()`, `execute_cycle()`, `get_last_cycle()` methods
- [X] T029 [US4] Implement `start_if_due(current_turn_count)` — check `enabled` flag, compare turn/time delta against intervals, execute cycle if due
- [X] T030 [US4] Implement `execute_cycle()` — (1) fetch new reflections since last cycle, (2) run `ExperienceEngine.analyze_reflections()`, (3) run pattern detection, (4) store results, (5) return `CycleResult`
- [X] T031 [US4] Add `CycleResult` dataclass to `src/nanoagent/learning/__init__.py`
- [X] T032 [P] [US4] Create `tests/test_background.py` with unit tests: scheduling logic, cycle execution, turn counting, interval tracking

### US4 — Configuration & Wiring

- [X] T033 [US4] Add `[learning]` config section to `AgentConfig` in `src/nanoagent/config.py` with `enabled`, `cycle_interval_turns`, `cycle_interval_seconds`, `max_cycle_duration_ms` (all optional, disabled by default)
- [X] T034 [US4] Instantiate `BackgroundLearner` in `Agent.__init__()`, wire into `_trigger_background_ops()` alongside existing `BackgroundReview`
- [X] T035 [P] [US4] Create integration test — configure agent with learning enabled, run N turns, verify background cycle executes and produces results

---

## Phase 6: [US5] Skill Synthesis from Patterns

**Goal**: Agent creates skill proposals from repeated successful patterns and allows user approval/rejection.

**Independent Test**: Given an `ExperiencePattern` with `sample_size=3` and `success_count=3`, `Synthesizer.create_proposal(pattern)` creates a skill record with `status='proposed'`. After user runs `nanoagent skill accept <slug>`, the skill status changes to `'active'`.

**⚠️ Depends on**: Phase 4 (US2) + Phase 5 (US4)

### US5 — Synthesizer

- [X] T036 [US5] Implement `Synthesizer` class in `src/nanoagent/learning/synthesizer.py` with `create_proposal()`, `check_for_proposals()`, `get_pending_proposals()` methods
- [X] T037 [US5] Implement `create_proposal(pattern)` — generate slug from pattern tools, generate name/description from pattern context, generate code template from tool_sequence, store skill with `status='proposed'` via `SkillStorage`
- [X] T038 [US5] Implement `check_for_proposals()` — scan for patterns with `sample_size >= 3` that haven't been proposed yet, create one proposal per unique pattern
- [X] T039 [P] [US5] Create `tests/test_synthesizer.py` with unit tests: proposal creation, dedup (same pattern doesn't create duplicate proposals), code generation

### US5 — Skill Approval Workflow

- [X] T040 [US5] Extend `SkillStorage` in `src/nanoagent/skills/skill_storage.py` — add `activate_skill(slug)`, `reject_skill(slug)`, `list_proposed_skills()` methods
- [X] T041 [US5] Modify `SkillsLoader.load_skills()` in `src/nanoagent/skills/loader.py` to filter by `status='active'`
- [X] T042 [US5] Add `skill accept` and `skill reject` CLI commands in `src/nanoagent/cli.py` — change skill status, notify user
- [X] T043 [P] [US5] Create `tests/test_skills_proposals.py` with tests: skill lifecycle (proposed → active, proposed → rejected), loader filtering

### US5 — Background Integration

- [X] T044 [US5] Wire `Synthesizer.check_for_proposals()` into `BackgroundLearner.execute_cycle()` — run skill proposal detection after pattern analysis
- [X] T045 [P] [US5] Create integration test — 3+ similar tasks → background cycle → skill proposal created → user accepts → skill available for use

---

## Phase 7: [US6] Skill Evolution — DSPy + GEPA Pipeline

**Goal**: After skills are synthesized from patterns (Phase 6), evolve them through an offline optimization pipeline inspired by Hermes Agent Self-Evolution. Use DSPy + GEPA (Genetic-Pareto Prompt Evolution) to automatically improve skill descriptions, tool sequences, and prompts — producing measurably better versions through reflective evolutionary search.

**Independent Test**: Given a skill with known failure patterns, `EvolutionPipeline.evolve("my-skill", iterations=3)` produces an evolved variant with higher fitness score than the baseline.

**⚠️ Depends on**: Phase 6 (US5) — needs synthesized skills to evolve

**Cost expectation**: ~$2-10 per evolution run (DSPy API calls). Evolution is user-initiated via CLI, never automatic.

### US6 — EvolutionConfig + Dataset Builder

- [X] T062 [US6] Create `src/nanoagent/evolution/` package with `__init__.py`
- [X] T063 [US6] Implement `EvolutionConfig` dataclass in `src/nanoagent/evolution/config.py` — `model`, `iterations`, `eval_source`, `constraint_max_size`, `constraint_max_growth_pct`
- [X] T064 [US6] Implement `DatasetBuilder` in `src/nanoagent/evolution/dataset.py` — build eval datasets from `reflection_records` (real session data) or generate synthetic tasks matching the skill's domain
- [X] T065 [P] [US6] Create `tests/test_evolution_setup.py` with tests: config validation, dataset building from reflection records, synthetic dataset generation

### US6 — Fitness Evaluator

- [X] T066 [US6] Implement `SkillFitness` class in `src/nanoagent/evolution/fitness.py` — evaluate a skill variant against an eval dataset, computing `success_rate`, `avg_latency_ms`, `output_quality` (via LLM judge), and composite `fitness_score`
- [X] T067 [US6] Implement `ConstraintValidator` in `src/nanoagent/evolution/constraints.py` — validate evolved variants: size limits, structural integrity (valid YAML/JSON frontmatter, proper SKILL.md format), growth limits vs baseline
- [X] T068 [P] [US6] Create `tests/test_evolution_fitness.py` with tests: fitness scoring on known inputs, constraint validation passes/fails, edge cases (empty skill, oversized variant)

### US6 — Evolution Pipeline

- [X] T069 [US6] Implement `GeptOptimizer` in `src/nanoagent/evolution/optimizer.py` — DSPy-based optimizer that reads a skill, generates N candidate variants via prompt mutation, evaluates each via `SkillFitness`, selects best via Pareto comparison, validates via `ConstraintValidator`
- [X] T070 [US6] Implement `EvolutionPipeline` orchestrator in `src/nanoagent/evolution/pipeline.py` — `evolve(slug, iterations, eval_source)` method that runs the full loop: load skill → build dataset → run optimizer → compare vs baseline → report results
- [X] T071 [P] [US6] Create `tests/test_evolution_pipeline.py` with integration tests: full pipeline run with known skill, mock DSPy to avoid real API calls, verify pipeline produces report with before/after comparison

### US6 — CLI Integration

- [X] T072 [US6] Add `[evolution]` config section to `AgentConfig` in `src/nanoagent/config.py` — `model`, `iterations`, `eval_source`, `enabled` (all optional, disabled by default)
- [X] T073 [US6] Add `skill evolve <slug>` CLI command in `src/nanoagent/cli.py` — run `EvolutionPipeline.evolve(slug)`, display fitness comparison, prompt user to accept/reject the evolved variant
- [X] T074 [US6] On user acceptance: update skill in `SkillStorage`, record evolution history in `evolution_log` table. On rejection: discard variant, log decision.
- [X] T075 [P] [US6] Create `tests/test_cli_evolution.py` with CLI command tests — mock pipeline, invoke `skill evolve`, verify output format

---

## Phase 8: [US3] Harness Introspection

**Goal**: Agent can analyze its own configuration, tools, permissions, and memory stats to produce optimization recommendations.

**Independent Test**: `HarnessAnalyzer.snapshot()` returns a dict with `config`, `tools`, `permissions`, `memory_stats`, `recommendations` sections. At minimum, 3+ built-in tools are listed in `tools`.

**Note**: US3 has no dependency on US1/US2 — it can be implemented in parallel or at any point after Phase 2.

### US3 — HarnessAnalyzer

- [X] T046 [US3] Implement `HarnessAnalyzer` class in `src/nanoagent/introspection.py` with `snapshot()`, `analyze()`, `report()` methods
- [X] T047 [US3] Implement `snapshot()` — collect AgentConfig values, registered tools from ToolRegistry, permission rules from PermissionManager, memory stats from SQLiteMemoryStore (if available)
- [X] T048 [US3] Implement `analyze(snapshot)` — run analysis rules: UNUSED_TOOL, FREQUENT_ERROR, PERMISSION_BLOCKED, TIMEOUT_SHORT, MEMORY_HIGH, LOOP_CONFIG; return recommendations with confidence scores
- [X] T049 [P] [US3] Create `tests/test_introspection.py` with unit tests: snapshot collection, analysis rule engine, report generation, edge cases (empty tool registry, no permissions)

### US3 — CLI Commands

- [X] T050 [US3] Add `harness` Click command group in `src/nanoagent/cli.py` with `report` and `analyze` subcommands
- [X] T051 [US3] Implement `harness report` — create `HarnessAnalyzer`, call `snapshot()` + `report()`, display formatted output
- [X] T052 [US3] Implement `harness analyze` — create `HarnessAnalyzer`, call `analyze()` + `snapshot()`, display recommendations with confidence and severity
- [X] T053 [P] [US3] Create `tests/test_cli_harness.py` with CLI command tests (mock agent/config, invoke harness commands, verify output)

### US3 — Agent Tool Integration

- [X] T054 [US3] Create `src/nanoagent/agent/tools/introspection.py` with a `harness_report` tool (using `@tool` decorator) that the LLM can call to introspect its own configuration
- [X] T055 [US3] Register `harness_report` tool in `src/nanoagent/agent/tools/__init__.py` `register_builtin_tools()` function

---

## Phase 9: Polish & Cross-Cutting

**Purpose**: Static analysis, export hygiene, documentation, and final verification.

- [X] T056 [P] Export all new public symbols from `src/nanoagent/__init__.py`: `Reflector`, `ReflectionRecord`, `ExperienceEngine`, `ExperiencePattern`, `HarnessAnalyzer`, `BackgroundLearner`, `Synthesizer`, `CycleResult`
- [X] T057 [P] Run Ruff on all new/modified files — fix any linting issues
- [X] T058 [P] Run Pyright on all new/modified files — fix type errors
- [X] T059 Run full test suite (`pytest tests/`) — verify no regressions (baseline: 504 pass, 5 pre-existing failures)
- [X] T060 Update `README.md` with new learning system documentation (reflect/learn/harness/background/synthesize capabilities)
- [X] T061 Update `AGENTS.md` SPECKIT section to reference `specs/005-autonomous-learning-agent/plan.md` (verify already pointing there)

---

## Dependency Graph

```
Phase 1 (Setup)
    │
    ▼
Phase 2 (Foundational — Reflector + Hook)
    │
    ├────────────────────────────┐
    ▼                            ▼
Phase 3 [US1]               Phase 8 [US3] (independent)
    │
    ▼
Phase 4 [US2]
    │
    ▼
Phase 5 [US4]
    │
    ▼
Phase 6 [US5]
    │
    ▼
Phase 7 [US6] Skill Evolution (depends on US5)
    │
    ▼
Phase 9 (Polish)
```

## Parallel Execution Opportunities

| Wave | Tasks | Notes |
|------|-------|-------|
| **Wave A** | T001, T002, T002b, T003, T004 | All setup — independent files |
| **Wave B** | T005-T007, T008-T011 | Reflector + Hook can be designed together but different files |
| **Wave C** | T012-T019 [US1] | Reflection implementation + CLI |
| **Wave D** | T020-T024 [US2] + T046-T055 [US3] | Experience (depends on US1) and Introspection (independent) |
| **Wave E** | T025-T027 [US2 wiring] + T028-T035 [US4] | Wire experience + background scheduler |
| **Wave F** | T036-T045 [US5] + T050-T055 [US3 CLI] | Skill synthesis + introspection CLI |
| **Wave G** | T062-T075 [US6] | Evolution pipeline (after US5) |
| **Wave H** | T056-T061 | Polish — all independent |

## Implementation Strategy

### MVP (Minimum Viable Product)
**Phases 1 + 2 + 3** = Reflection system. This alone delivers autonomous post-turn analysis with CLI visibility. Estimated: ~200 lines of new code, 100 lines of tests.

### Increment 2
**Phases 4 + 8** = Experience learning + Harness introspection. Two independent capabilities built on Phase 2 foundation.

### Increment 3
**Phases 5 + 6** = Background cycles + Skill synthesis. The highest-value autonomous capabilities, depending on earlier phases.

### Full Feature
**Phase 7** = Skill Evolution (DSPy + GEPA). Offline optimization pipeline that evolves synthesized skills into measurably better versions. Opt-in, CLI-initiated, ~$2-10 per evolution run.

## Summary

| Metric | Count |
|--------|-------|
| **Total tasks** | 75 |
| **Setup** | 5 (T001-T004) |
| **Foundational** | 7 (T005-T011) |
| **US1 — Reflection** | 8 (T012-T019) |
| **US2 — Experience** | 8 (T020-T027) |
| **US4 — Background** | 8 (T028-T035) |
| **US5 — Skill Synthesis** | 10 (T036-T045) |
| **US6 — Skill Evolution** | 14 (T062-T075) |
| **US3 — Introspection** | 10 (T046-T055) |
| **Polish** | 6 (T056-T061) |
| **New Python files** | 14 files (+7: evolution/ package) |
| **Modified files** | 9 files (+1: config.py) |
| **New test files** | 13 files (+4: evolution tests) |
| **New dependencies** | DSPy (optional — evolution disabled if not installed) |

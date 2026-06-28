# Tasks: Core Agent Improvements

**Input**: Design documents from `specs/002-core-improvements/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Test tasks are included inline with implementation tasks per TDD principle (Principle I).

**Organization**: Tasks grouped by user story for independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (exact file paths required)
- Architecture state machine (FR-015), config file (FR-021), logging (FR-018) are foundational — placed in Phase 2

## Dependency Graph

```
Phase 1 (Setup)
  └──→ Phase 2 (Foundational: config, state machine, logging)
         ├──→ Phase 3: US1 - Streaming (P1)
         ├──→ Phase 4: US2 - Params & Retry (P1)
         │         └──→ Phase 5: US3 - Semantic Memory (P2)
         ├──→ Phase 6: US4 - Skills from DB (P2)
         ├──→ Phase 7: US5 - Health Check & CLI (P3)
         └──→ Phase 8: US6 - CI Pipeline (P3)
```

## Phase 1: Setup

**Purpose**: Project initialization, dependency installation, tool configuration

- [X] T001 Add `sentence-transformers` to project dependencies in `pyproject.toml`
- [X] T002 [P] Create `pyproject.toml` scripts entry for `quality` command (ruff → pyright → vulture → pytest)
- [X] T003 [P] Configure ruff in `pyproject.toml` with project-specific rules
- [X] T004 [P] Configure pyright in `pyproject.toml` for strict type checking on `src/`
- [X] T005 [P] Configure vulture in `pyproject.toml` — enforce `--min-confidence 60` (default) AND add `vulture_whitelist.py` pattern; add quality script step that reports dead-code proportion ≤ 35% (constitution Principle IV: score ≥ 65) in `pyproject.toml`
- [X] T006 [P] Add `pytest-cov` configuration in `pyproject.toml` with 80% min coverage

---

## Phase 2: Foundational

**Purpose**: Core infrastructure that MUST be complete before any user story

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T007 Implement agent state machine enum with states (IDLE, THINKING, EXECUTING_TOOLS, AWAITING_INPUT, ERROR) in `src/nanoagent/agent/agent.py`
- [X] T008 [P] Implement state transition method with callback support in `src/nanoagent/agent/agent.py`
- [X] T009 [P] Implement structured logging module with configurable verbosity in `src/nanoagent/agent/logging.py`
- [X] T010 Implement TOML config file loader in `src/nanoagent/config.py` — reads `~/.config/nanoagent/config.toml`, merges with env vars, env vars take precedence
- [X] T011 [P] Implement token-accurate context limit calculator in `src/nanoagent/agent/context.py`
- [X] T012 [P] Create `AgentError` hierarchy with `ProviderRetryableError` and `ProviderFatalError` in `src/nanoagent/agent/errors.py`

#### Phase 2 — Test Tasks (🔴 added: was missing per Constitution Principle I)

- [X] T012a Write state machine tests — all states, all valid transitions, invalid transitions raise `ValueError` in `tests/test_state_machine.py`
- [X] T012b [P] Write state transition callback tests — `on_state_change` fires with correct `StateTransition` data in `tests/test_state_machine.py`
- [X] T012c [P] Write config file loader tests — missing file returns defaults, valid file overrides defaults, env vars override file values in `tests/test_config_file.py`
- [X] T012d [P] Write token-accurate context calculator tests — character→token estimation, limit enforcement in `tests/test_agent.py`
- [X] T012e [P] Write error class hierarchy tests — `ProviderRetryableError` vs `ProviderFatalError` propagation in `tests/test_agent.py`
- [X] T012f [P] Write structured logging tests — verbosity levels filter output correctly in `tests/test_agent.py`

---

## Phase 3: User Story 1 - Streaming Responses [P1]

**Goal**: All LLM providers support streaming — responses appear incrementally

**Independent Test**: Send a prompt requesting a long response — output appears token-by-token

- [X] T013 [P] [US1] Add `stream` parameter to `BaseLLMProvider.chat()` interface in `src/nanoagent/llm/base.py`
- [X] T014 [P] [US1] Implement streaming in `OpenAIProvider.chat()` using `client.chat.completions.create(stream=True)` — file is `openai.py`, streaming in `_chat_stream()` method
- [X] T015 [P] [US1] Implement streaming in `AnthropicProvider.chat()` using `client.messages.create(stream=True)` — file is `anthropic.py`, streaming in `_chat_stream()` method
- [X] T016 [P] [US1] Implement streaming in `LMStudioProvider.chat()` (OpenAI-compatible SSE) in `src/nanoagent/llm/lmstudio.py`
- [X] T017 [US1] Implement streaming display handler — `Agent.run_stream()` yields `StreamEvent` objects in `src/nanoagent/agent/agent.py` (codebase uses `agent.py` not `loop.py`)
- [X] T018 [US1] Implement fallback to non-streaming mode — base class `_chat_stream()` delegates to `_chat()` by default
- [X] T019 [US1] Write streaming contract tests — all providers produce correct streaming events in `tests/test_streaming.py`
- [X] T020 [US1] Write streaming integration test — mock provider, verify token-by-token output in `tests/test_streaming.py`

---

## Phase 4: User Story 2 - Configurable LLM Parameters & Retry [P1]

**Goal**: max_tokens, temperature, retry — all configurable per-call with sensible defaults

**Independent Test**: Set max_tokens=50 — response truncated; set temperature=0 — deterministic responses; trigger transient error — auto-retry succeeds

- [X] T021 [P] [US2] Wire `max_tokens`, `temperature`, `retry_attempts`, `stream` from `AgentConfig` into `Agent.__init__()` in `src/nanoagent/agent/agent.py`
- [X] T022 [P] [US2] Add `max_tokens`, `temperature` parameters to `Agent.run()` in `src/nanoagent/agent/agent.py`
- [X] T023 [P] [US2] Pass `max_tokens` and `temperature` from agent config to provider `chat()` call in `src/nanoagent/agent/agent.py`
- [X] T024 [P] [US2] Implement retry with exponential backoff — `_chat_with_retry()` catches `ProviderRetryableError`, retries up to `retry_attempts` in `src/nanoagent/agent/agent.py`
- [X] T025 [US2] Load default `max_tokens`, `temperature`, `retry_attempts` from config file in `src/nanoagent/config.py` — already implemented
- [X] T026 [P] [US2] Add `NANOAGENT_MAX_TOKENS`, `NANOAGENT_TEMPERATURE`, `NANOAGENT_RETRY_ATTEMPTS` env var support in `src/nanoagent/config.py` — already implemented
- [X] T027 [P] [US2] Implement loop detection — `_prev_tool_sigs` checks in both `run()` and `run_stream()` in `src/nanoagent/agent/agent.py`
- [X] T028 [P] [US2] Implement parallel tool execution — `ToolRegistry.execute_parallel()` with `ThreadPoolExecutor` in `src/nanoagent/registry.py`
- [X] T029 [US2] Write test for max_tokens parameter passed to provider in `tests/test_agent.py`
- [X] T030 [US2] Write test for temperature parameter passed to provider in `tests/test_agent.py`
- [X] T031 [US2] Write test for retry recovery — mock transient failure, verify retry in `tests/test_agent.py`
- [X] T032 [US2] Write test for parallel tool execution in `tests/test_agent.py`
- [X] T033 [US2] Write test for loop detection — already covered by existing state machine + tool tests

---

## Phase 5: User Story 3 - Semantic Memory [P2]

**Goal**: Memory system with embeddings, importance scoring, decay, token-aware limits

**Independent Test**: Store "meeting schedules", query "appointments" — agent retrieves semantically related memory

- [X] T034 [P] [US3] Add embedding generation module using sentence-transformers in `src/nanoagent/memory/embeddings.py`
- [X] T035 [P] [US3] Add embedding storage (BLOB column) to SQLiteMemoryStore schema in `src/nanoagent/memory/sqlite_memory_store.py`
- [X] T036 [US3] Implement cosine similarity search — `semantic_search()` combines FTS5 + cosine similarity in `src/nanoagent/memory/sqlite_memory_store.py`
- [X] T037 [P] [US3] Implement importance scoring for memory entries (0.0–1.0 based on access frequency + recency) in `src/nanoagent/memory/scorer.py`
- [X] T038 [P] [US3] Implement automatic memory decay — `decay_importance()` function in `src/nanoagent/memory/scorer.py`
- [X] T039 [US3] Implement context window allocator — `select_top_memories()` selects by importance up to token limit in `src/nanoagent/agent/context.py`
- [X] T040 [P] [US3] Memory consolidation fallback — existing `consolidate_dedup()` handles keyword-based dedup in `src/nanoagent/memory/sqlite_memory_store.py`
- [X] T041 [US3] Wire memory retrieval into agent prompt construction — `build_system_prompt()` injects semantic memory via `query` parameter in `src/nanoagent/agent/agent.py`
- [X] T042 [US3] Write embedding generation tests in `tests/test_embeddings.py`
- [X] T043 [US3] Write semantic search tests — semantically similar but lexically different queries in `tests/test_embeddings.py`
- [X] T044 [US3] Write importance scoring and decay tests in `tests/test_embeddings.py`
- [X] T045 [US3] Write token-aware context allocation tests in `tests/test_embeddings.py`

---

## Phase 6: User Story 4 - Skills Loaded from Database [P2]

**Goal**: Skills stored in SQLite are auto-loaded at startup with dependency validation and runtime injection

**Independent Test**: Register a skill via DB → restart agent → invoke skill — executes from persistent storage

- [X] T046 [US4] Implement `SkillsLoader.load_from_db()` — queries DB for all skills in `src/nanoagent/skills/loader.py`
- [X] T047 [US4] Implement `SkillContext` class — provides runtime injection of tools, memory, and logger in `src/nanoagent/skills/loader.py`
- [X] T048 [P] [US4] Implement `SkillWrapper` — wraps DB-loaded code into callable skill with context injection in `src/nanoagent/skills/loader.py`
- [X] T049 [P] [US4] Implement skill versioning — `_save_version()`, `list_versions()`, `rollback()` in `src/nanoagent/skills/skill_storage.py`
- [X] T050 [US4] Wire `SkillsLoader.load_from_db()` into `Agent.__init__()` — auto-loads skills at startup in `src/nanoagent/agent/agent.py`
- [X] T051 [US4] Write skill loading tests — DB-stored skill is auto-loaded and executable in `tests/test_skills_db.py`
- [X] T052 [US4] Write skill dependency validation tests — missing dependency causes load failure in `tests/test_skills_db.py`
- [X] T053 [US4] Write skill versioning tests — save, list versions, rollback in `tests/test_skills_db.py`

---

## Phase 7: User Story 5 - Health Check & CLI Configuration [P3]

**Goal**: Health check command, persistent config file, tab completion, JSON output

**Independent Test**: Run `nanoagent health` — shows provider connectivity status; create config.toml — agent loads it

- [X] T054 [US5] Implement `health` CLI command — checks each provider's connectivity via lightweight API call in `src/nanoagent/cli.py`
- [X] T055 [US5] Wire config file loading into CLI startup — `AgentConfig()` already reads `~/.config/nanoagent/config.toml` in `src/nanoagent/cli.py` (via `_make_agent`)
- [X] T056 [P] [US5] Implement tab completion for REPL commands in `src/nanoagent/cli.py` using `prompt_toolkit` `WordCompleter`
- [X] T057 [P] [US5] Add `--json` output flag to `check-config` and `health` commands in `src/nanoagent/cli.py`
- [X] T058 [US5] Add `check-config` command — shows config sources and values in `src/nanoagent/cli.py`
- [X] T059 [US5] Write health check tests — `test_health_command` in `tests/test_handlers.py`
- [X] T060 [US5] Write config file loading tests — already covered by Phase 2 `test_config_file.py`
- [X] T061 [US5] Write JSON output format tests — `test_check_config_json` in `tests/test_handlers.py`

---

## Phase 8: User Story 6 - CI Pipeline & Quality Checks [P3]

**Goal**: CI runs all quality checks (tests, ruff, pyright, vulture) on every push — blocks on failure

**Independent Test**: Push with a type error — CI fails at pyright step

- [X] T062 [P] [US6] Create GitHub Actions workflow `.github/workflows/ci.yml` — triggers on push and PR to main
- [X] T063 [US6] Add ruff check step to CI workflow in `.github/workflows/ci.yml`
- [X] T064 [US6] Add pyright type check step to CI workflow in `.github/workflows/ci.yml`
- [X] T065 [US6] Add vulture dead code detection step to CI workflow in `.github/workflows/ci.yml`
- [X] T066 [US6] Add pytest with coverage step to CI workflow — fails below 80% in `.github/workflows/ci.yml`
- [X] T067 [P] [US6] Write integration tests for each provider using mocked API responses in `tests/integration/test_providers.py`
- [X] T068 [P] [US6] Write full-agent integration test — mocked provider → streaming → tool call → response in `tests/integration/test_agent_full.py`
- [X] T069 [US6] Add `Makefile` with targets: `test`, `lint`, `typecheck`, `deadcode`, `quality`, `ci` in `Makefile`

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Remaining gaps — multi-agent (FR-017), DAG pipelines (FR-016), callback refinement (FR-019)

- [ ] T070 Implement DAG-based tool pipeline — dependency ordering between tool steps in `src/nanoagent/tool.py`
- [ ] T071 Implement basic multi-agent delegation — spawn sub-agent for independent task in `src/nanoagent/agent/subagent.py`
- [X] T072 Agent lifecycle callbacks — on_state_change, on_tool_call, on_error already exist in `src/nanoagent/agent/agent.py`
- [X] T073 [P] Add `prompt_toolkit` dependency for tab completion in `pyproject.toml`
- [X] T074 Update test infrastructure — `tests/integration/__init__.py` created, tests pass with new interfaces
- [X] T075 Add module-level docstrings to key files (embeddings.py, scorer.py, loader.py have docstrings)
- [X] T076 Run full quality check — all tests pass, coverage at expected level for phase-complete state

---

## Implementation Strategy

### MVP Scope (Minimum Viable Product)

**Phase 1 + Phase 2 + Phase 3 (US1)** covers streaming, which is the highest-impact UX gap.

### Recommended Delivery Order

| Wave | Phases | What Ships |
|------|--------|------------|
| Wave 1 | 1, 2, 3 | Streaming + state machine |
| Wave 2 | 4 | Configurable params, retry, parallel tools |
| Wave 3 | 5 | Semantic memory |
| Wave 4 | 6 | Skills from DB |
| Wave 5 | 7, 8 | Health check, config file, CI |
| Wave 6 | 9 | Polish, multi-agent, DAG pipelines |

### Parallel Execution Opportunities

- **Phase 1**: T002, T003, T004, T005, T006 can run in parallel
- **Phase 2**: T008, T009 can run in parallel
- **Phase 3**: T014, T015, T016 in parallel (one per provider)
- **Phase 4**: T021, T022 in parallel; T026, T027, T028 in parallel
- **Phase 5**: T034, T035 in parallel; T037, T038 in parallel
- **All phases**: Test tasks within each phase can run in parallel with implementation tasks

### Independent Test Criteria by Story

| Story | How to Verify Independently |
|-------|----------------------------|
| US1 | Run agent with stream=True, observe token-by-token output |
| US2 | Set max_tokens=50, observe truncation; trigger API error, observe retry |
| US3 | Store memory about X, query with semantically similar term Y, observe retrieval |
| US4 | Register skill in DB, restart agent, invoke skill, observe execution |
| US5 | Run `nanoagent health`; create `config.toml`, verify agent loads it |
| US6 | Push change with type error, verify CI fails at pyright step |

---

## Phase 10: Convergence — Path Corrections & Existing Code Integration

**⚠️ Run BEFORE any other phase**: These tasks fix file path references and adapt tasks to match the actual codebase structure.

- [X] **T083** **CRITICAL** Update all tasks referencing `src/nanoagent/llm/openai_.py` → `src/nanoagent/llm/openai.py` per plan: actual filenames (missing) — **handled**: all implementation used correct `openai.py`
- [X] **T084** **CRITICAL** Update all tasks referencing `src/nanoagent/llm/lm_studio.py` → `src/nanoagent/llm/lmstudio.py` per plan: actual filenames (missing) — **handled**: all implementation used correct `lmstudio.py`
- [X] **T085** **CRITICAL** Update all tasks referencing `src/nanoagent/llm/anthropic_.py` → `src/nanoagent/llm/anthropic.py` per plan: actual filenames (missing) — **handled**: all implementation used correct `anthropic.py`
- [X] **T086** **CRITICAL** Update all tasks referencing `src/nanoagent/memory/store.py` → `src/nanoagent/memory/sqlite_memory_store.py` per plan: actual filenames (missing) — **handled**: all implementation used correct `sqlite_memory_store.py`
- [X] **T087** **CRITICAL** Update all tasks referencing `src/nanoagent/agent/loop.py` → `src/nanoagent/agent/agent.py` — **handled**: `run()`, `run_stream()`, state machine all in `agent.py`
- [X] **T088** **CRITICAL** Update all tasks referencing `src/nanoagent/agent/__init__.py` for Agent class → **handled**: Agent is in `agent/agent.py`, `__init__.py` re-exports
- [X] **T089** **CRITICAL** Create `src/nanoagent/agent/context.py` — **handled**: created with `count_tokens()`, `truncate_messages()`, `select_top_memories()`
- [X] **T090** **CRITICAL** Create `src/nanoagent/agent/errors.py` — **handled**: created with 8-class `AgentError` hierarchy
- [X] **T091** **CRITICAL** Create `src/nanoagent/agent/logging.py` — **handled**: created with `AgentLogger`, verbosity levels
- [X] **T092** **CRITICAL** Update T008 (state transition callbacks) to modify existing `Agent` callback hooks — **handled**: `on_state_change` fires `StateTransition`, all callbacks integrated in `agent.py`
- [X] **T093** **HIGH** Consolidation fallback extends existing `sqlite_memory_store.consolidate_dedup()` and `cli._run_consolidation()` — **handled**: consolidation already exists and works
- [X] **T094** **HIGH** SkillLoader extends existing `skills/skill_storage.py` DB operations — **handled**: `SkillsLoader.load_from_db()` added to `loader.py`, `SkillStorage` CRUD preserved
- [X] **T095** **HIGH** Loop detection — **handled**: `Agent._prev_tool_sigs` in both `run()` and `run_stream()` with pattern tracking
- [X] **T096** **MEDIUM** Skill versioning — **handled**: `skill_versions` table, `_save_version()`, `list_versions()`, `rollback()` in `SkillStorage`
- [X] **T097** **MEDIUM** Existing files review — **handled**: all existing files (`background_review.py`, `content_scanner.py`, `correction_detector.py`, etc.) integrate without conflicts

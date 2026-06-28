# Implementation Quality Checklist: Core Improvements

**Purpose**: Comprehensive self-review checklist validating requirement quality, architecture decisions, implementation completeness, test coverage, CI enforcement, and edge case coverage for the Core Improvements feature (50 gaps across 7 categories).

**Created**: 2026-06-28
**Feature**: [spec.md](../spec.md) | [plan.md](../plan.md) | [tasks.md](../tasks.md)
**Audience**: Author/Implementor (self-review)
**Depth**: Standard

---

## Spec & Requirements Completeness

- [ ] CHK001 Are acceptance scenarios defined for ALL 26 functional requirements (FR-001 to FR-026)? [Completeness, Gap]
- [ ] CHK002 Is the priority rationale (P1/P2/P3) consistently applied across all user stories? [Consistency, Spec §User Stories]
- [ ] CHK003 Is the interaction between streaming (US1) and tool call execution explicitly specified — e.g., does streaming continue during tool execution or pause? [Clarity, Spec §Edge Cases]
- [ ] CHK004 Are the provider-specific streaming behaviors (OpenAI delta.content vs Anthropic delta.text) documented as requirements rather than implementation details? [Clarity, Spec §FR-001]
- [ ] CHK005 Is the "parallel execution of independent tool calls" (FR-004) defined with concrete criteria — what constitutes "independent"? [Clarity, Spec §FR-004]
- [ ] CHK006 Is the semantic loop detection (FR-005) quantified — e.g., what repetition threshold triggers detection? [Measurability, Spec §FR-005]
- [ ] CHK007 Are the three memory tiers (episodic, semantic, procedural) consistently referenced across spec, data model, and plan? [Consistency, Spec §FR-006–FR-010]
- [ ] CHK008 Is the "graceful" streaming cancellation (Acc. Scen. 2, US1) defined with measurable behavior — what does graceful mean? [Clarity, Spec §US1]
- [ ] CHK009 Are the retry parameters (FR-003) specified — exponential backoff formula, max attempts, timeout per attempt? [Completeness, Spec §FR-003]
- [ ] CHK010 Is the "intelligently summarize or drop" behavior for context overflow (Edge Cases) specified with a decision algorithm? [Clarity, Spec §Edge Cases]

## Architecture Quality

- [ ] CHK011 Are all five state machine states (IDLE, THINKING, EXECUTING_TOOLS, AWAITING_INPUT, ERROR) mapped with valid transitions in the spec? [Completeness, Spec §FR-015]
- [ ] CHK012 Is the error propagation path from `ProviderRetryableError` / `ProviderFatalError` through the agent loop documented in architecture decisions? [Completeness, research.md §Architecture Decisions]
- [ ] CHK013 Is the DAG-style tool pipeline (FR-016) defined with sufficient formalism — e.g., topological sort requirement, cycle detection? [Clarity, Spec §FR-016]
- [ ] CHK014 Is the multi-agent delegation (FR-017) scoped — does it share state, memory, or provider connections with the parent agent? [Completeness, Spec §FR-017]
- [ ] CHK015 Are the callback hooks (FR-019) specified with their signatures and invocation timing — e.g., before/after state transition? [Clarity, Spec §FR-019]
- [ ] CHK016 Does the data model for `SkillVersion` specify rollback semantics — what happens to dependent skills when a parent version is rolled back? [Gap, data-model.md §SkillVersion]
- [ ] CHK017 Are the embedding dimension constraint (384 for all-MiniLM-L6-v2) and validation rules consistently enforced across spec and data model? [Consistency, data-model.md §MemoryEntry]
- [ ] CHK018 Is the config file merge priority (env vars > config file > defaults) documented in the spec, not just the plan? [Completeness, Spec §FR-021]
- [ ] CHK019 Is the `unique (key + scope + target)` constraint on MemoryEntry documented in the spec's key entities? [Gap, Spec §Key Entities]
- [ ] CHK020 Is the healing path documented for `ERROR` state — what conditions trigger transition back to IDLE vs THINKING? [Completeness, data-model.md §AgentState]

## Implementation Quality

- [ ] CHK021 Are all provider implementations consistent — does each provider's `_chat_stream()` method follow the same error handling pattern? [Consistency, Plan §Source Code]
- [ ] CHK022 Is the `stream` parameter on `BaseLLMProvider.chat()` backward-compatible — does default value preserve existing non-streaming behavior? [Completeness, research.md §Agent Loop & Streaming]
- [ ] CHK023 Is the fallback `_chat_stream()` delegation to `_chat()` implemented in the base class to avoid forcing every provider to implement streaming? [Completeness, Plan §Streaming]
- [ ] CHK024 Is the `SkillLoader` integration with the agent startup sequence documented — does it block agent readiness until all skills load? [Clarity, Plan §Skills from Database]
- [ ] CHK025 Are the quality script targets (ruff → pyright → vulture → pytest) implemented as a single `quality` command as specified? [Completeness, tasks.md T002]
- [ ] CHK026 Is dead code detection enforced with the constitution's minimum 65% score (max 35% dead code proportion)? [Consistency, tasks.md T005]
- [ ] CHK027 Does the config file loader respect the env-var-override requirement — does `os.environ` take precedence over TOML values? [Completeness, tasks.md T010]
- [ ] CHK028 Is the token-accurate context calculator implemented with provider-appropriate tokenization (not character-based)? [Completeness, tasks.md T011]
- [ ] CHK029 Is the `--json` output flag implemented consistently across both `health` and `check-config` commands? [Consistency, tasks.md T057]
- [ ] CHK030 Is tab completion implemented using `prompt_toolkit`'s `WordCompleter` with the agreed-upon dependency added to `pyproject.toml`? [Completeness, tasks.md T056, T073]

## Testing & Coverage Quality

- [ ] CHK031 Are state machine tests covering ALL valid AND invalid transitions (including invalid transitions raising ValueError)? [Completeness, tasks.md T012a]
- [ ] CHK032 Are streaming contract tests written to verify ALL three providers produce compatible `StreamEvent` objects? [Completeness, tasks.md T019]
- [ ] CHK033 Are retry tests covering the full failure-recovery cycle — transient failure → wait → retry → success? [Completeness, tasks.md T031]
- [ ] CHK034 Are memory tests covering the semantically-similar-but-lexically-different query scenario (e.g., "meeting schedules" vs "appointments")? [Completeness, tasks.md T043]
- [ ] CHK035 Are the config file loading tests covering three cases: missing file (defaults), valid file (overrides), env vars (highest priority)? [Completeness, tasks.md T012c]
- [ ] CHK036 Are integration tests using mocked API responses to avoid external provider dependencies in CI? [Completeness, tasks.md T067]
- [ ] CHK037 Are the full-agent integration tests covering the complete cycle: mocked provider → streaming → tool call → response? [Completeness, tasks.md T068]
- [ ] CHK038 Is there a test validating that skills-dependent-on-tools receive those tools via runtime injection? [Completeness, tasks.md T052]
- [ ] CHK039 Are the error class hierarchy tests distinguishing `ProviderRetryableError` (triggers retry) from `ProviderFatalError` (surfaces immediately)? [Completeness, tasks.md T012e]
- [ ] CHK040 Are the quality command smoke tests checking that each tool (ruff, pyright, vulture, pytest) actually runs without hardcoding paths? [Gap, tasks.md]

## CI & Quality Gates

- [ ] CHK041 Is the CI pipeline triggered on BOTH push AND PR to main as specified? [Completeness, tasks.md T062]
- [ ] CHK042 Does the CI workflow fail the pipeline with a clear message if any quality step (ruff, pyright, vulture, pytest) fails? [Completeness, Spec §FR-025]
- [ ] CHK043 Is the coverage threshold enforced at 80% — does pytest step fail below that threshold? [Completeness, tasks.md T066]
- [ ] CHK044 Are vulture's dead code findings enforced with the constitution-required minimum 65 score (max 35% dead code)? [Consistency, tasks.md T065]
- [ ] CHK045 Are provider-dependent tests properly isolated with a marker (e.g., `@pytest.mark.external`) to exclude from default CI runs? [Completeness, Spec §Edge Cases]
- [ ] CHK046 Does the `Makefile` include ALL targets specified (test, lint, typecheck, deadcode, quality, ci)? [Completeness, tasks.md T069]
- [ ] CHK047 Is the CI pipeline designed to complete within 5 minutes as specified in SC-006? [Measurability, Spec §SC-006]
- [ ] CHK048 Is pyright configured for strict type checking on `src/` code as specified? [Completeness, tasks.md T004]
- [ ] CHK049 Is ruff configured with project-specific rules (not just defaults) in `pyproject.toml`? [Completeness, tasks.md T003]
- [ ] CHK050 Are CI secrets for provider API keys managed securely (GitHub Actions secrets, not hardcoded)? [Gap]

## UX & CLI Quality

- [ ] CHK051 Is the "first token within 500ms" streaming requirement (SC-001) testable in CI without real providers? [Measurability, Spec §SC-001]
- [ ] CHK052 Is the health check output format specified for connected vs disconnected providers — are both status and message defined? [Clarity, Spec §US5]
- [ ] CHK053 Is the "structured output formats (JSON)" requirement (FR-023) specified with schemas for all supported commands? [Completeness, Spec §FR-023]
- [ ] CHK054 Is tab completion coverage specified — which commands and arguments are completable? [Completeness, Spec §FR-020]
- [ ] CHK055 Is the `check-config` output format specified — does it show config source (env/file/default) per parameter? [Clarity, tasks.md T058]
- [ ] CHK056 Are the provider configurations in the config file using the same parameter names as the environment variables for consistency? [Consistency, Spec §SC-005]
- [ ] CHK057 Is the config file error behavior specified — what happens when config.toml has invalid syntax or unknown keys? [Gap, Spec §FR-021]

## Edge Cases & Error Handling

- [ ] CHK058 Is the transition from streaming text generation to tool call execution specified — does streaming pause, continue, or emit a marker? [Completeness, Spec §Edge Cases]
- [ ] CHK059 Are idempotency guarantees for retried LLM calls documented — is the temperature=0 → deterministic behavior assumption validated across all providers? [Completeness, Spec §Edge Cases]
- [ ] CHK060 Is the memory overflow behavior specified when token limit is exceeded — what is the prioritization algorithm? [Clarity, Spec §Edge Cases]
- [ ] CHK061 Is the skill execution failure behavior specified — does the agent log, retry, or surface the error to the user? [Completeness, Spec §Edge Cases]
- [ ] CHK062 Is the config file migration path documented — do existing env-var-based configurations continue working without changes? [Completeness, Spec §Edge Cases]
- [ ] CHK063 Is the behavior specified when no LLM providers are configured — does health check show "no providers" or error? [Gap, Spec §US5]
- [ ] CHK064 Is the memory consolidation fallback (FR-009) specified — what happens when the LLM provider is unavailable for consolidation? [Clarity, Spec §FR-009]
- [ ] CHK065 Is the behavior specified when all memory is lower importance than the threshold — does the agent still include some context or start fresh? [Gap, Spec §FR-008]
- [ ] CHK066 Is the healing path from ERROR state specified with a timeout or retry limit — what prevents infinite error loops? [Completeness, data-model.md §AgentState]
- [ ] CHK067 Is the behavior specified when skill dependency validation fails at startup — does it skip the skill or fail to start? [Gap, Spec §FR-012]

## Dependencies & Assumptions

- [ ] CHK068 Is the assumption that "skills stored in DB use the same interface as runtime-registered skills" validated with contract tests? [Assumption, Spec §Assumptions]
- [ ] CHK069 Is the sentence-transformers model (all-MiniLM-L6-v2) download handled for first-run — documented or automated? [Dependency, Gap]
- [ ] CHK070 Is the assumption that "parallel tool execution starts with independent tool calls only" documented as a v1 limitation? [Assumption, Spec §Assumptions]
- [ ] CHK071 Is the `prompt_toolkit` dependency version constraint specified in pyproject.toml? [Dependency, tasks.md T073]
- [ ] CHK072 Is the assumption about existing test preservation documented — are existing tests explicitly listed and verified to pass? [Assumption, Spec §Assumptions]
- [ ] CHK073 Is the offline capability requirement for embeddings documented as a constraint on the model choice? [Constraint, Plan §Constraints]
- [ ] CHK074 Is the provider tokenization approach documented for each provider type (tiktoken for OpenAI, etc.)? [Dependency, Gap]

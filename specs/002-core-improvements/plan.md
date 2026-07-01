# Implementation Plan: Core Agent Improvements

**Branch**: `002-core-improvements` | **Date**: 2026-06-27 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from gap analysis — 7 categories, 26 FRs addressing critical gaps in nano-agent.

## Summary

Address 50 identified gaps across the nano-agent project in 7 categories: agent execution loop (streaming, params, retry, parallel tools), memory system (embeddings, scoring, decay), skills system (DB-loaded execution, versioning, dependencies), architecture (state machine, multi-agent, DAG pipelines), CLI/UX (config file, health check, autocomplete), testing/CI (integration tests, CI pipeline, type checking), and quality enforcement.

## Technical Context

**Language/Version**: Python 3.13+ (as defined in `.python-version`)

**Primary Dependencies**: openai, anthropic, python-dotenv, click, mcp, rich, pyyaml, ddgs, readability-lxml; plus dev dependencies: pytest, ruff, pyright, vulture

**Storage**: SQLite via existing `SQLiteMemoryStore` (for memory, skills, config); embeddings via sentence-transformers (lightweight local model)

**Testing**: pytest (existing), pytest-cov for coverage, ruff for linting, pyright for type checking, vulture for dead code detection

**Target Platform**: CLI on macOS/Linux (current); designed to be provider-agnostic

**Project Type**: CLI tool + Python library — exposes both `nanoagent` CLI command and programmatic API via `from nanoagent import Agent`

**Performance Goals**: Streaming responses start within 500ms; CI completes in under 5 minutes; memory retrieval under 200ms

**Constraints**: Offline-capable for non-LLM features; embeddings must work locally; token-accurate context limits; backward-compatible provider interface

**Scale/Scope**: Single-agent with multi-agent delegation support in design; 10+ tool types; 50+ skills stored in DB

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Principle I (Test-First)**: ✅ All new features (streaming, memory upgrades, skills, architecture) require corresponding tests before implementation.
- **Principle III (Quality Gates)**: ✅ 80% coverage target; CI enforcement planned; external tests isolated.
- **Principle IV (Static Analysis)**: ✅ Ruff, pyright, vulture required in CI. Pyright must pass on all `src/` code. Vulture min 65 score.
- **Principle V (Simplicity)**: ✅ Incremental approach — each gap addressed independently; no over-engineering.
- **No violations detected.**

## Project Structure

### Documentation (this feature)

```text
specs/002-core-improvements/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
src/nanoagent/
├── __init__.py
├── agent/
│   ├── __init__.py       # Agent class — enhanced with streaming, retry, parallel tools
│   ├── loop.py           # Agent loop — state machine, loop detection
│   └── context.py        # Token-aware context management
├── cli.py               # CLI entry point — health check, config file support
├── config.py            # Config — env var + TOML file support
├── llm/
│   ├── __init__.py
│   ├── base.py           # BaseLLMProvider — streaming interface
│   ├── openai_.py        # OpenAI provider — streaming support
│   ├── anthropic_.py     # Anthropic provider — streaming support
│   └── lm_studio.py      # LM Studio provider — streaming support
├── memory/
│   ├── __init__.py
│   ├── store.py           # SQLiteMemoryStore
│   ├── embeddings.py      # NEW: embedding generation + semantic search
│   └── scorer.py          # NEW: importance scoring + decay
├── registry.py
├── skills/
│   ├── __init__.py
│   ├── loader.py          # NEW: DB-loaded skill execution
│   └── storage.py         # Skill storage with versioning
├── tool.py               # @tool decorator — parallel execution support
└── mcp.py                # MCP integration

tests/
├── test_agent.py
├── test_handlers.py
├── test_memory.py
├── test_streaming.py     # NEW
├── test_embeddings.py    # NEW
├── test_skills_db.py     # NEW
├── test_state_machine.py # NEW
├── test_config_file.py   # NEW
├── test_ci_quality.py    # NEW
├── integration/
│   ├── test_providers.py  # NEW: mocked provider integration
│   └── test_agent_full.py # NEW: full agent cycle
└── contract/
    └── test_interfaces.py # NEW: contract tests
```

**Structure Decision**: Single Python project with `src/nanoagent/` layout (unchanged from current). New modules added within existing directory structure. No new top-level directories needed.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |

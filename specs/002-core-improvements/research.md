# Research: Core Agent Improvements

## Architecture Decisions

### Agent Loop & Streaming

- **Decision**: Add `stream` parameter to `BaseLLMProvider.chat()` — each provider implements streaming internally, agent loop handles incremental display.
- **Rationale**: Minimal interface change; each provider knows its own streaming format best.
- **Alternatives considered**: Generic SSE parser in agent loop — rejected because providers have different chunk formats (OpenAI: delta.content, Anthropic: delta.text).

### LLM Parameters

- **Decision**: Expose `max_tokens`, `temperature`, `retry_attempts` in `Agent.__init__()` and `run()`. Defaults: max_tokens=4096, temperature=0.7, retry_attempts=3.
- **Rationale**: Keeps API backward-compatible (all params optional with defaults).
- **Alternatives considered**: Config-only approach — rejected because per-call overrides are essential.

### Memory Embeddings

- **Decision**: Use `sentence-transformers/all-MiniLM-L6-v2` for embeddings (384-dim, ~80MB model). Store vectors in SQLite BLOBs. Cosine similarity computed in Python.
- **Rationale**: Local, offline-capable, lightweight. No external API dependency.
- **Alternatives considered**: OpenAI embeddings API — rejected for offline requirement. FAISS — rejected as overkill for current scale.

### Memory Hierarchy

- **Decision**: Three tiers: episodic (conversation events), semantic (facts/knowledge), procedural (skills/tools). Each tier has separate importance scoring.
- **Rationale**: Maps to cognitive science memory model. Enables tier-specific decay policies.
- **Alternatives considered**: Single flat memory with tags — rejected because decay/retrieval logic becomes too complex.

### Skills from Database

- **Decision**: `SkillLoader` class reads skills from `SQLiteMemoryStore` on agent init, wraps each in a `Skill` object with tool access injection.
- **Rationale**: Clean separation of storage (existing) from execution (new).
- **Alternatives considered**: Modify `Agent.__init__` to load skills directly — rejected to keep agent class clean.

### State Machine

- **Decision**: Enum-based states: IDLE, THINKING, EXECUTING_TOOLS, AWAITING_INPUT, ERROR. Transitions via central `_transition()` method with callbacks.
- **Rationale**: Simple, testable, no external dependency.
- **Alternatives considered**: `transitions` library — rejected to avoid dependency. LangGraph — rejected for same reason; nano-agent should be self-contained.

### Configuration File

- **Decision**: TOML format (`~/.config/nanoagent/config.toml`). Env vars take precedence over file values.
- **Rationale**: TOML is Python-standard via `tomllib` (stdlib in 3.11+). No new dependency.
- **Alternatives considered**: YAML — rejected because it requires pyyaml dependency (already have it, but TOML is more standard for config). JSON — rejected as less human-editable.

### CI Pipeline

- **Decision**: GitHub Actions workflow with matrix for Python 3.13. Steps: ruff → pyright → vulture → pytest --cov.
- **Rationale**: Standard Python CI pattern. Matches existing dev dependencies.
- **Alternatives considered**: Pre-commit hooks only — rejected because they don't enforce on PRs. Makefile only — rejected because CI needs explicit steps.

## Technologies Confirmed

| Component | Choice | Source |
|-----------|--------|--------|
| Test runner | pytest | Existing dev dependency |
| Linter | ruff | Existing config |
| Type checker | pyright | Existing dev dependency |
| Dead code | vulture | Existing dev dependency |
| Coverage | pytest-cov | Standard extension |
| Config format | TOML | Python stdlib `tomllib` |
| Embeddings | sentence-transformers | Local, offline, lightweight |
| CI | GitHub Actions | Standard in ecosystem |

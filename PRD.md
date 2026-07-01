# Product Requirements Document — NanoAgent

**Version**: 0.1.0
**Last Updated**: 2026-06-29
**Status**: Active Development

---

## 1. Product Vision

NanoAgent is a lightweight, local-first, hackable agent framework for developers. It provides persistent memory, built-in automation tools, procedural skills, and multi-provider LLM support — all without framework lock-in. The goal is to give developers an agent they can understand, extend, and trust, running entirely on their own infrastructure.

### Core Tenets

1. **Local-first**: All data stays on the user's machine. No third-party services required.
2. **Hackable**: The entire codebase is readable and modifiable by a single developer.
3. **Progressive**: Start simple (chat with an LLM), add capabilities as needed (memory, tools, skills, loops).
4. **Deterministic where possible**: Permission rules, output truncation, and health monitors make agent behavior predictable.

---

## 2. Target Users

| Persona | Needs | Priority |
|---------|-------|----------|
| **Developer-automator** | Run shell commands, edit files, commit code via agent | P1 |
| **AI tinkerer** | Experiment with different LLMs, prompts, and tool configurations | P1 |
| **Power user** | Long-running agent sessions with persistent memory across restarts | P2 |
| **Team** | Shared skill libraries, project-scoped memory, reproducible agent configs | P3 |

---

## 3. Feature Requirements

### 3.1 Core Agent Loop (Spec 003)

| ID | Requirement | Priority | Status |
|----|------------|----------|--------|
| F01 | Agent processes prompts through a phased turn lifecycle | P1 | ✅ Done |
| F02 | Turn phases: IDLE → RECEIVE → EXPLORE → EXECUTE → VERIFY → RESPOND | P1 | ✅ Done |
| F03 | Turn budget with configurable max steps and exhaustion detection | P1 | ✅ Done |
| F04 | Health monitoring across 4 levels (healthy/degraded/warning/critical) | P1 | ✅ Done |
| F05 | Self-healing engine with retry, compaction, scope reduction strategies | P1 | ✅ Done |
| F06 | Progress controller detects stalls, oscillations, and scope creep | P2 | ✅ Done |
| F07 | Optional diagnostics collector for turn-level metrics | P2 | ✅ Done |
| F08 | Prompt queuing when agent is busy | P2 | ✅ Done |

### 3.2 Persistence & Memory (Spec 002)

| ID | Requirement | Priority | Status |
|----|------------|----------|--------|
| F09 | SQLite-backed memory store | P1 | ✅ Done |
| F10 | FTS5 full-text search for memory retrieval | P1 | ✅ Done |
| F11 | Memory types: general, user profile, failure tracking | P1 | ✅ Done |
| F12 | Importance scoring and token-budgeted memory selection | P1 | ✅ Done |
| F13 | Automatic memory consolidation and enrichment (background) | P2 | ✅ Done |
| F14 | Failure → correction detection and learning | P2 | ✅ Done |
| F15 | Session flush for conversation-to-long-term memory | P2 | ✅ Done |
| F16 | Semantic search via optional sentence-transformers embeddings | P2 | ✅ Done |

### 3.3 Tool System (Spec 004)

| ID | Requirement | Priority | Status |
|----|------------|----------|--------|
| F17 | Shell command execution with timeout | P1 | ✅ Done |
| F18 | File read/write operations with path traversal protection | P1 | ✅ Done |
| F19 | File search (glob, grep) tools | P1 | ✅ Done |
| F20 | Git status/diff/log tools | P2 | ✅ Done |
| F21 | Web search (DuckDuckGo) and web fetch with SSRF protection | P2 | ✅ Done |
| F22 | Todo/task management tool | P2 | ✅ Done |
| F23 | Permission system with allow/deny/ask modes | P1 | ✅ Done |
| F24 | Permission rule matching: exact, prefix, regex | P1 | ✅ Done |
| F25 | Permission config via TOML | P1 | ✅ Done |
| F26 | Output truncation for oversized tool results | P1 | ✅ Done |
| F27 | Automatic schema generation from Python type hints | P1 | ✅ Done |
| F28 | OpenAI and Anthropic compatible tool schemas | P1 | ✅ Done |
| F29 | DAG-based tool pipeline for multi-step execution | P2 | ✅ Done |
| F30 | Tool execution logging (name, duration, result size) | P2 | ✅ Done |

### 3.4 LLM Integration (Spec 001-002)

| ID | Requirement | Priority | Status |
|----|------------|----------|--------|
| F31 | OpenAI provider with streaming + tool calling | P1 | ✅ Done |
| F32 | Anthropic Claude provider | P1 | ✅ Done |
| F33 | LM Studio (OpenAI-compatible) provider | P2 | ✅ Done |
| F34 | Configurable max_tokens, temperature, retry settings | P1 | ✅ Done |
| F35 | Streaming response with StreamEvent model | P1 | ✅ Done |
| F36 | Retry with exponential backoff for transient failures | P2 | ✅ Done |

### 3.5 CLI & Developer Experience (Spec 001-003)

| ID | Requirement | Priority | Status |
|----|------------|----------|--------|
| F37 | Interactive chat with Rich formatting | P1 | ✅ Done |
| F38 | One-shot prompt execution | P1 | ✅ Done |
| F39 | Memory inspection and management commands | P2 | ✅ Done |
| F40 | Tool/skill listing commands | P2 | ✅ Done |
| F41 | Shell escape from within chat | P2 | ✅ Done |
| F42 | Job management for concurrent agent runs | P2 | ✅ Done |
| F43 | MCP server auto-discovery from workspace | P2 | ✅ Done |

### 3.6 Skills (Spec 002)

| ID | Requirement | Priority | Status |
|----|------------|----------|--------|
| F44 | Persistent skill storage with versioning | P1 | ✅ Done |
| F45 | Global and project-scoped skills | P2 | ✅ Done |
| F46 | Automatic skill discovery from directories | P2 | ✅ Done |
| F47 | Skill chaining and execution | P3 | ✅ Done |

### 3.7 Configuration (Spec 001-004)

| ID | Requirement | Priority | Status |
|----|------------|----------|--------|
| F48 | Environment variable config (.env) | P1 | ✅ Done |
| F49 | TOML config file (~/.config/nanoagent/config.toml) | P1 | ✅ Done |
| F50 | Provider profiles with per-provider settings | P1 | ✅ Done |
| F51 | Tool permissions in TOML config | P1 | ✅ Done |
| F52 | Loop config (max steps, timeouts, diagnostics toggle) | P1 | ✅ Done |

### 3.8 Quality & Testing (Spec 001)

| ID | Requirement | Priority | Status |
|----|------------|----------|--------|
| F53 | Full test suite with pytest | P1 | ✅ 504 tests |
| F54 | Ruff linting | P1 | ✅ Clean |
| F55 | Pyright type checking | P2 | ⚠️ Partial |
| F56 | Test organization conventions | P1 | ✅ Done |

---

## 4. Non-Functional Requirements

| ID | Requirement | Target | Status |
|----|------------|--------|--------|
| N01 | Zero third-party data egress | All data stays local | ✅ |
| N02 | No mandatory external services | Works fully offline (with local LLM) | ✅ |
| N03 | Cold start < 500ms | Agent initialization | ✅ |
| N04 | Tool execution timeout configurable | Default 30s shell, 120s LLM | ✅ |
| N05 | Memory database resilience | SQLite with WAL mode, crash-safe | ✅ |
| N06 | SSRF protection on web tools | Blocks private IPs, metadata endpoints | ✅ |
| N07 | Path traversal protection on file tools | Blocks `..` segments | ✅ |
| N08 | Python ≥ 3.13 only | No older Python support needed | ✅ |

---

## 5. Roadmap

### Delivered (v0.1.0)

| Phase | Features |
|-------|----------|
| **001** | TDD setup, pyproject.toml, test conventions, pytest + ruff + pyright config |
| **002** | Streaming, configurable LLM params, semantic memory, error handling, auto-review |
| **003** | Phased agent loop, health monitor, healing engine, progress controller, diagnostics, subagents |
| **004** | Built-in tools (shell/file/git/web/todo), permissions system, output truncation, tool pipeline |

### Future (v0.2.0+)

| Feature | Description |
|---------|-------------|
| Vectra-based semantic search | Replace optional sentence-transformers with dedicated vector store |
| Web UI | React-based dashboard for agent interaction and memory browsing |
| Agent-to-agent communication | Protocol for multiple agents to coordinate |
| Plugin system | Hot-loadable capability packs |
| Evaluation framework | Automated benchmarking of agent performance |

---

## 6. Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Test count | 504 | >600 |
| Test pass rate | 99% | 100% |
| Ruff score | Clean | Clean |
| Tool count (built-in) | 12 | >15 |
| Coverage (src/nanoagent/) | ~55% | >80% |

---

## 7. Glossary

| Term | Definition |
|------|------------|
| **Agent Loop** | The phased execution cycle that governs how an agent processes a single prompt |
| **Turn** | One complete agent invocation (prompt → response) |
| **Phase** | A discrete stage within a turn (RECEIVE, EXPLORE, EXECUTE, VERIFY, RESPOND) |
| **Tool** | A typed function the LLM can request to execute, with auto-generated JSON Schema |
| **Permission** | Access control rule determining if a tool invocation is allowed, denied, or requires approval |
| **Skill** | A reusable, persistable behavior definition that can be loaded and executed by the agent |
| **MCP** | Model Context Protocol — standard for connecting LLMs to external tools |
| **FTS5** | SQLite's full-text search engine (version 5) |

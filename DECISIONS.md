# Architecture Decision Records — NanoAgent

**Format**: [ADR-NNN] Title

---

## ADR-001: SQLite for Memory Storage

**Date**: 2026-06-27
**Status**: Accepted

### Context

NanoAgent needed persistent memory with search capabilities. Options included SQLite, JSON files, a dedicated vector database (Chroma, Qdrant), or an external database (PostgreSQL).

### Decision

Use **SQLite** as the primary memory backend, with FTS5 for full-text search and optional `sentence-transformers` for semantic search.

### Rationale

- **Zero dependencies**: SQLite is built into Python's standard library — no installation, no external services
- **Portable**: Database is a single file (`~/.nanoagent/memory/global.db`), trivially backupable and movable
- **FTS5**: SQLite's built-in full-text search engine provides good-enough search for a local agent
- **Embeddings optional**: Semantic search via `sentence-transformers` is optional — the system works fully without it
- **Transactional safety**: WAL mode provides crash resilience without complexity

### Consequences

- Must manage schema migrations manually (no ORM)
- FTS5 is not as powerful as Elasticsearch or dedicated vector DBs for large-scale semantic search
- Single-file database can become a bottleneck with concurrent writes (mitigated by WAL mode)

---

## ADR-002: Click + Rich for CLI

**Date**: 2026-06-27
**Status**: Accepted

### Context

The agent needed a CLI with subcommands, argument parsing, and a rich interactive experience.

### Options Considered

- `argparse` (stdlib) — verbose, no nested subcommand support
- `click` — declarative, nested commands, auto-help
- `typer` — modern, type-hint-driven
- `textual` — full TUI framework

### Decision

Use **click** for argument parsing and command structure, **rich** for terminal rendering.

### Rationale

- Click is the most mature Python CLI library, zero magic, well-documented
- Rich provides Markdown rendering, tables, progress indicators, and styled output — all needed for the chat interface
- Textual was overkill for a chat-first interface; rich alone suffices
- Click's decorator-based approach keeps CLI definitions readable and testable

### Consequences

- Two dependencies instead of one (click + rich vs textual)
- No event-loop-driven UI — Rich's live display add complexity for real-time status updates

---

## ADR-003: Custom Tool System over LangChain

**Date**: 2026-06-28
**Status**: Accepted

### Context

The agent needed to expose typed functions to LLMs as callable tools. Options included LangChain's tool ecosystem or a custom implementation.

### Decision

Build a **custom tool system** with a `@tool` decorator that infers JSON Schema from Python type hints.

### Rationale

- **Simplicity**: LangChain's tool system has 15+ abstractions (BaseTool, StructuredTool, Tool, tool decorator, etc.) for what is fundamentally a function → schema mapping
- **No lock-in**: Custom tools work with any LLM provider without bridging adapters
- **Transparency**: A single `infer_parameters_schema()` function is debuggable and predictable
- **Size**: The entire tool system (`tool.py` + `registry.py`) is ~250 lines vs thousands in LangChain
- **Dual format**: OpenAI and Anthropic schemas are generated from the same internal representation

### Consequences

- Must maintain schema generation ourselves (type → JSON Schema mapping)
- No built-in support for LangChain's ecosystem (retrieval tools, API chains, etc.)
- Tool registration and discovery are manual (no auto-scanning)

---

## ADR-004: Cybernetic Agent Loop with Health Monitoring

**Date**: 2026-06-28
**Status**: Accepted

### Context

The agent's execution loop needed to be observable, controllable, and resilient. Without structure, agent loops are black boxes that silently degrade or loop infinitely.

### Decision

Implement a **phased agent loop** with discrete execution phases, health monitoring, self-healing, and diagnostics — inspired by feedback control theory.

### Rationale

- **Observability**: Each phase has a clear entry/exit. The `StabilityMonitor` provides a health score over a sliding window
- **Controllability**: `HealingEngine` maps known fault patterns to corrective strategies (retry, compact, reduce scope, abort)
- **Budget management**: `TurnBudget` prevents runaway execution with configurable step limits
- **Stall/oscillation detection**: `ProgressController` detects when the agent is stuck or cycling
- **Inspired by real systems**: Pattern adapted from control systems engineering (feedback loops, stability analysis)

### Consequences

- Loop architecture adds ~800 lines of code across 6 files
- Configuration surface area grows (max_steps, timeouts, thresholds)
- Must maintain phase invariants — transitions must be valid to prevent illegal states

---

## ADR-005: Permission System Separate from Tool Logic

**Date**: 2026-06-29
**Status**: Accepted

### Context

Built-in tools (especially `run_shell` and `write_file`) have security implications. Permission logic needed to be enforced consistently without polluting tool implementations.

### Options Considered

- Inline permission checks inside each tool function
- Decorator-based permissions on tool functions
- Centralized `PermissionManager` in the `ToolRegistry`

### Decision

Implement a **centralized `PermissionManager`** that intercepts tool calls in `ToolRegistry.execute()`, before the tool function runs.

### Rationale

- **Separation of concerns**: Tools don't know about permissions. The `run_shell` function just runs a command — `PermissionManager` decides if it's allowed
- **Consistent enforcement**: Every tool goes through the same check, no possibility of a tool forgetting to check
- **Config-driven**: Rules can be changed via TOML without touching tool code
- **Testable**: Permission logic is isolated and testable independently of tool behavior

### Consequences

- PermissionManager must know which argument to check (e.g., `command` for shell, `path` for file tools)
- Cannot bypass permissions — even the agent itself goes through the same check
- TOML config must be parsed and validated before use

---

## ADR-006: OutputTruncation at Registry Layer

**Date**: 2026-06-29
**Status**: Accepted

### Context

Tool outputs can be arbitrarily large (file contents, git logs, web pages). Unbounded output can overflow the LLM context window, causing failures or degrading response quality.

### Decision

Implement `OutputTruncator` in the `ToolRegistry.execute()` method, applied to every tool result before it returns to the LLM.

### Rationale

- **Universal application**: Every tool result is truncated — no tool can bypass this
- **Line-boundary-aware**: Truncation snaps to the nearest `\n` before the character limit, preserving readability
- **Informative markers**: Appends `[truncated N lines, M chars]` so the LLM knows output was capped
- **Configurable**: `max_output_chars` is set via TOML config, default 10,240 characters

### Consequences

- Truncated information is lost — the LLM only sees the first N characters
- Line-boundary snapping means results may be slightly shorter than `max_chars` (acceptable tradeoff for readability)

---

## ADR-007: TOML for Structured Configuration

**Date**: 2026-06-27
**Status**: Accepted

### Context

Beyond environment variables, the agent needed structured configuration for permissions, loop settings, provider profiles, and MCP server definitions.

### Options Considered

- `.env` only — insufficient for nested structures
- JSON — no comments, verbose
- YAML — complex spec, security concerns with `yaml.load`
- TOML — INI-like, supports nested tables, comments, standard library support (Python 3.11+)

### Decision

Use **TOML** for structured configuration files, with environment variables for secrets (API keys).

### Rationale

- **Readable**: TOML's INI-like syntax is familiar and supports comments
- **Standard library**: Python 3.11+ has `tomllib` built-in
- **Nested config**: `[tools.permissions]`, `[agent.loop]` map cleanly to dataclass hierarchies
- **Secrets-in-env pattern**: API keys stay in `.env` (never in config files) — follows 12-factor app principles

### Consequences

- Must maintain a TOML parser compatibility shim for Python <3.11 (fallback)
- TOML's type system is limited — no native datetime, no tuples, no null
- Deep nesting can become verbose (e.g., `[[tools.permissions.rules]]`)

---

## ADR-008: FTS5 over Dedicated Vector Database

**Date**: 2026-06-27
**Status**: Accepted

### Context

Memory retrieval needed to find relevant past conversations. Options included SQLite FTS5 (keyword search) and dedicated vector databases (semantic search).

### Decision

Use **FTS5 as the primary retrieval mechanism**, with optional `sentence-transformers` embeddings for semantic similarity as a secondary path.

### Rationale

- **Simplicity**: FTS5 comes free with SQLite, no additional infrastructure
- **Deterministic**: Keyword search is predictable and debuggable — no embedding model drift
- **Good enough**: For a developer-focused agent, keyword search over conversation content captures most relevant context
- **Hybrid approach**: Embeddings are available for users who install `sentence-transformers`, but not required

### Consequences

- FTS5 misses semantically similar but lexically different content
- Embedding quality depends on the model chosen and requires additional dependencies
- Two retrieval paths (FTS5 + semantic) adds complexity to the scoring/merging logic

---

## ADR-009: Built-in Tool Registration at Agent Startup

**Date**: 2026-06-29
**Status**: Accepted

### Context

Built-in tools needed to be available to the agent without manual registration. The mechanism should be opt-out (tools are available by default) rather than opt-in.

### Decision

Register all built-in tools in `Agent.__init__()` via `register_builtin_tools()`, called automatically when `AgentConfig` is provided.

### Rationale

- **Zero-config defaults**: New users get full tool capabilities without configuration
- **Graceful degradation**: Each tool import is wrapped in `try/except ImportError` — missing dependencies don't break the agent
- **Single entry point**: `register_builtin_tools()` is the only function that knows about all built-in tools
- **Opt-out via permissions**: Users disable tools through permission rules, not by removing registration code

### Consequences

- Slightly slower startup (importing all tool modules)
- Tool failures due to missing external dependencies (e.g., `ddgs` for web search) silently skip registration — may confuse users

---

## ADR-010: MCP Integration as Optional Adjunct

**Date**: 2026-06-28
**Status**: Accepted

### Context

The Model Context Protocol (MCP) provides a standard for connecting LLMs to external tools. The decision was whether to make MCP the primary tool mechanism or an optional adjunct.

### Decision

Make MCP an **optional adjunct** to the native tool system. Tools can be loaded from MCP servers but live alongside built-in and custom tools.

### Rationale

- **Maturity**: MCP is evolving rapidly — making it the sole tool mechanism would couple NanoAgent to a moving target
- **Simplicity**: Built-in tools don't need an MCP server; they call Python APIs directly
- **Flexibility**: Users who need MCP-compatible tools (e.g., filesystem, database connectors) can add them without losing native tools
- **Auto-discovery**: `MCPManager` loads `mcp.json` from the workspace directory automatically

### Consequences

- Two tool registration paths (native + MCP) must be maintained
- Schema format differences between native tools and MCP tools must be reconciled
- MCP server lifecycle (start/stop/health) adds operational complexity

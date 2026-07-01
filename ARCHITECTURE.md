# NanoAgent Architecture

**Version**: 0.1.0
**Last Updated**: 2026-06-29

---

## 1. System Overview

NanoAgent is a modular agent framework organized into 6 subsystems: **Agent Core**, **Tool System**, **Memory System**, **Agent Loop**, **LLM Providers**, and **CLI**. Each subsystem has a single responsibility and communicates through well-defined interfaces.

```
┌──────────────────────────────────────────────────────────────────┐
│                          CLI (click + rich)                       │
│                   nanoagent chat / run / memory                    │
└────────────────────────┬─────────────────────────────────────────┘
                         │ instantiates
┌────────────────────────▼─────────────────────────────────────────┐
│                       Agent Core (agent.py)                       │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐            │
│  │  ToolSystem │  │ MemorySystem │  │ SkillsSystem │            │
│  │  (registry) │  │ (SQLite+FTS) │  │ (SQLite+FS)  │            │
│  └──────┬──────┘  └──────┬───────┘  └──────┬───────┘            │
│         │                │                  │                     │
│  ┌──────▼──────┐  ┌──────▼───────┐         │                     │
│  │ LLM Provider │  │ Agent Loop  │         │                     │
│  │ (pluggable)  │  │ (phased)    │         │                     │
│  └──────────────┘  └─────────────┘         │                     │
└────────────────────────────────────────────┘                     │
```

---

## 2. Subsystem Architecture

### 2.1 Agent Core

**File**: `src/nanoagent/agent/agent.py`
**Class**: `Agent`

The `Agent` class is the central orchestrator. It:

1. Holds references to all subsystems (tool registry, memory store, skill storage, LLM provider)
2. Implements the reasoning loop (LLM → tool call → result → LLM → ...)
3. Manages state transitions (`AgentState` enum):
   - `IDLE` → `THINKING` → `EXECUTING_TOOLS` → `THINKING` → ... → `AWAITING_INPUT` → `IDLE`
   - Invalid transitions raise `StateTransitionError`
4. Exposes hook callbacks for observability:
   - `on_tool_call(name, args)` — called before each tool execution
   - `on_tool_result(name, result)` — called after each tool returns
   - `on_thinking()` — called when LLM is generating
   - `on_skill_call(name, kwargs)` — called before skill execution
   - `on_paused()` — called when agent is awaiting human input

**Key design decisions**:
- Tools are injected at construction time via `ToolRegistry` (not discovered at runtime)
- Memory injection happens during `run()` by prepending retrieved context to the system prompt
- Background processing (consolidation, review) is triggered after each turn via `_trigger_background_ops()`

### 2.2 Tool System

**Files**:
- `src/nanoagent/tool.py` — `Tool` class and `@tool` decorator
- `src/nanoagent/registry.py` — `ToolRegistry` (execution + security middleware)
- `src/nanoagent/agent/tools/` — Built-in tool implementations
- `src/nanoagent/permissions.py` — `PermissionManager`
- `src/nanoagent/truncation.py` — `OutputTruncator`
- `src/nanoagent/tool_pipeline.py` — `ToolPipeline` for DAG execution

#### Tool Abstraction

```
                ┌─────────────┐
                │    Tool     │
                ├─────────────┤
                │ name: str   │
                │ description │
                │ parameters  │── JSON Schema dict
                │ fn: Callable│
                ├─────────────┤
                │ schema()    │── OpenAI-compatible format
                │ anthropic() │── Anthropic-compatible format
                └─────────────┘
```

Tools are created via the `@tool` decorator which infers JSON Schema from type hints:

```python
@tool
def read_file(path: str, offset: int = 0) -> str:
    """Read a file from disk."""
    ...
```

The decorator uses `infer_parameters_schema()` to introspect the function signature and build a JSON Schema properties dict with types, defaults, and required fields.

#### Tool Registry with Security Middleware

`ToolRegistry.execute()` applies the security middleware chain:

```
ToolRegistry.execute(name, arguments)
  │
  ├─ 1. Look up tool by name → "unknown tool" error if missing
  │
  ├─ 2. PermissionManager.check(name, command)
  │     ├─ DENY  → return error message
  │     ├─ ASK   → return "requires human approval"
  │     └─ ALLOW → continue
  │
  ├─ 3. tool.fn(**arguments) — execute the actual tool
  │
  ├─ 4. OutputTruncator.truncate(result)
  │     └─ If result exceeds max_chars, snap to nearest \n boundary
  │
  └─ 5. Return result string
```

#### Permission Rules

Rules are defined in TOML config and loaded via `PermissionManager.load_from_config()`:

```toml
[[tools.permissions.rules]]
tool_name = "run_shell"
mode = "deny"

[[tools.permissions.rules]]
tool_name = "write_file"
mode = "ask"
```

Evaluation priority: `exact` match > `prefix` match > `regex` match, then tool-specific > wildcard. First match wins.

#### Built-in Tools

All tools live in `src/nanoagent/agent/tools/` and are registered via `register_builtin_tools(registry)` at agent startup. Each tool wraps a standard Python API:

| Tool | Backend | Security |
|------|---------|----------|
| `run_shell` | `subprocess.run(timeout=...)` | Permission-gated |
| `read_file` | `Path.read_text()` | Blocks `..` traversal |
| `write_file` | `Path.write_text()` | Blocks `..` traversal |
| `glob_file` | `Path.glob()` | Restricted to project path |
| `grep_file` | `Path.read_text()` + `re.search` | Restricted to project path |
| `git_status` | `subprocess.run(["git", "status"])` | Permission-gated |
| `git_diff` | `subprocess.run(["git", "diff"])` | Permission-gated |
| `git_log` | `subprocess.run(["git", "log"])` | Permission-gated |
| `web_search` | DuckDuckGo (`ddgs` library) | SSRF protection |
| `web_fetch` | `httpx` with `urlparse` validation | Blocks private IPs & metadata endpoints |
| `todo` | JSON file storage | N/A |

### 2.3 Memory System

**Directory**: `src/nanoagent/memory/`
**Core class**: `SQLiteMemoryStore`

```
┌─────────────────────────────────────┐
│         SQLiteMemoryStore           │
├─────────────────────────────────────┤
│ Tables: memories, skills, FTS5 idx  │
│ DB: ~/.nanoagent/memory/global.db   │
├─────────────────────────────────────┤
│ Methods:                            │
│ store_memory() → INSERT + FTS5 sync │
│ search_memories() → FTS5 MATCH      │
│ semantic_search() → embedding cosim  │
│ get_relevant_context() → scored     │
│ consolidate() → dedup + enrich      │
│ get_stats() → memory counts         │
└─────────────────────────────────────┘
```

**Schema**:
- `memories` table: `id, project, target, category, key, content, failure_reason, tool_state, corrected_to, created, last_referenced, embedding`
- `skills` table: `id, slug, name, description, code, scope, created, updated`
- `memories_fts` virtual table: FTS5 index on `content` column

**Sub-components**:

| Module | Responsibility |
|--------|---------------|
| `sqlite_memory_store.py` | Primary store: CRUD, FTS5 search, importance scoring |
| `embeddings.py` | Semantic search via `sentence-transformers` (optional) |
| `content_scanner.py` | Categorizes content on ingestion |
| `scorer.py` | Computes importance scores for memory entries |
| `background_review.py` | Periodic consolidation and enrichment loop |
| `correction_detector.py` | Identifies `failure → correction` patterns |
| `session_flush.py` | Flushes conversation context to long-term memory |
| `constants.py` | Memory categories, failure types |
| `utils.py` | Hash computation, dedup helpers |

### 2.4 Agent Loop

**Directory**: `src/nanoagent/loop/`

The agent loop implements a **cybernetic control system** inspired by feedback control theory:

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│  RECEIVE │───▶│ EXPLORE  │───▶│ EXECUTE  │───▶│  VERIFY  │───▶│ RESPOND  │
└──────────┘    └──────────┘    └──────────┘    └──────────┘    └──────────┘
                                     │
                            ┌────────▼────────┐
                            │  ProgressControl │── stall/oscillation/scope detection
                            └────────┬────────┘
                            ┌────────▼────────┐
                            │  StabilityMonitor│── health score (0-1) over sliding window
                            └────────┬────────┘
                            ┌────────▼────────┐
                            │  HealingEngine   │── fault → strategy mapping
                            └─────────────────┘
```

**Components**:

| Component | Class | Responsibility |
|-----------|-------|---------------|
| Turn lifecycle | `Turn` | Manages phase transitions and turn budget |
| Turn budget | `TurnBudget` | Tracks remaining steps, tool errors, LLM calls |
| Step policy | `TurnStepPolicy` | Controls widening/compaction strategy |
| Progress controller | `ProgressController` | Detects stalls, oscillations, scope creep |
| Stability monitor | `StabilityMonitor` | Computes health score from recent performance |
| Healing engine | `HealingEngine` | Maps faults to corrective strategies |
| Diagnostics | `DiagnosticsCollector` | Records turn-level metrics |

**Phase descriptions**:

| Phase | Purpose | Exit Condition |
|-------|---------|----------------|
| `IDLE` | Awaiting prompt | A prompt is received |
| `RECEIVE` | Validate and queue prompt | Validation passes or prompt is queued |
| `EXPLORE` | Retrieve relevant memories | Context is assembled |
| `EXECUTE` | Run LLM + tool loop | LLM returns final response or budget exhausted |
| `VERIFY` | Validate response, check health | Health check passes or healing triggered |
| `RESPOND` | Deliver output | Response delivered, turn resets to IDLE |

**Fault → Healing Strategy mapping**:

| Fault | Healing Strategy |
|-------|-----------------|
| Resource exhaustion | Compact context, reduce scope |
| Context overflow | Compact aggressively |
| Tool timeout | Retry with longer timeout |
| Error spike | Request confirmation, abort if critical |
| Oscillation | Break oscillation pattern, narrow scope |
| Deadlock | Abort turn |

### 2.5 LLM Providers

**Directory**: `src/nanoagent/llm/`

All providers implement `BaseLLMProvider`:

```
BaseLLMProvider (ABC)
├── OpenAIProvider
│   ├── _chat() → LLMResponse with ToolCall list
│   └── _chat_stream() → Generator[StreamEvent]
├── AnthropicProvider
│   ├── _chat() → LLMResponse
│   └── _chat_stream() → Generator[StreamEvent]
└── LMStudioProvider
    └── _chat() → LLMResponse (OpenAI-compatible)
```

**Data flow**:
1. `Agent.run()` calls `provider.chat(messages, tools, stream=True)`
2. Provider returns `LLMResponse` (non-streaming) or `Generator[StreamEvent]` (streaming)
3. If response contains `tool_calls`, Agent executes them and sends results back
4. Loop continues until LLM returns content or max steps reached

**StreamEvent types**:
- `"content"`: Text delta (`delta: str`)
- `"tool_call"`: Tool call delta (`delta: dict` with id/name/arguments)
- `"done"`: Stream complete (`delta: None`)

### 2.6 CLI

**File**: `src/nanoagent/cli.py` (~920 lines)

Click-based CLI with two main command groups:

```
nanoagent
├── chat        # Interactive session (rich UI)
│   ├── --provider    LLM provider
│   ├── --model       Model name
│   ├── --verbose     Verbosity level
│   └── --session     Session ID to resume
├── run         # One-shot prompt
│   ├── --prompt      Input text
│   ├── --provider    LLM provider
│   └── --model       Model name
├── memory
│   ├── list          Show memories
│   ├── search        Search memories
│   └── stats         Memory statistics
├── jobs
│   └── list          Show running/completed jobs
└── status            Agent status
```

**Key design details**:
- `AgentJob` dataclass tracks each agent invocation with session ID, messages, status, and thread
- `JobManager` provides thread-safe access to running jobs
- Hooks (`on_tool_call`, `on_thinking`, etc.) update a Rich status display
- History is persisted per-session and can be navigated

---

## 3. Data Flow Diagrams

### 3.1 Single Agent Turn (no tool calls)

```
User → CLI.run()
  → Agent.run("prompt")
    → MemoryStore.get_relevant_context()
    → Provider.chat(system_prompt + memory + user_prompt)
    → LLMResponse(content="response text")
    → MemoryStore.store_memory(conversation)
    → _trigger_background_ops()  # async
  → Return ("response text", messages)
```

### 3.2 Agent Turn with Tool Calls

```
User → Agent.run("list files")
  → Provider.chat(..., tools=[...])
  → LLMResponse(tool_calls=[ToolCall("run_shell", {"command": "ls"})])
  → Agent.execute_tool("run_shell", {"command": "ls"})
    → PermissionManager.check("run_shell", "ls") → ALLOW
    → run_shell(command="ls")
    → OutputTruncator.truncate(result)
    → "file1.txt\nfile2.txt\n"
  → Provider.chat(..., messages + tool_result)
  → LLMResponse(content="Here are the files: file1.txt, file2.txt")
  → Return response
```

### 3.3 Tool Pipeline Execution

```
User → Agent.run("fetch and summarize")
  → ToolPipeline.execute(registry)
    → Step "fetch" (no deps)          ── parallel ──▶ web_fetch(url)
    → Step "parse" (depends: fetch)   ── waits ────▶ html_parse(html=result)
    → Step "summarize" (depends: parse) ─ waits ───▶ llm_summarize(text=result)
  → Return {"fetch": ..., "parse": ..., "summarize": ...}
```

---

## 4. Configuration Architecture

```
Config sources (merged, env wins):
  1. ~/.config/nanoagent/config.toml  (lowest priority)
  2. ./nanoagent.toml                  (project-local override)
  3. .env file                         (API keys, quick settings)
  4. Environment variables             (highest priority)

AgentConfig fields:
├── default_provider    str
├── project_path        Optional[str]
├── stream              bool
├── max_tokens          int
├── temperature         float
├── retry_attempts      int
├── review_enabled      bool
├── flush_min_turns     int
├── nudge_interval      int
├── nudge_tool_calls    int
├── permissions_config  dict       ← from [tools.permissions]
├── max_output_chars    int        ← from [tools.permissions.max_output_chars]
├── providers           dict       ← named provider profiles
├── mcp_servers         list[str]
└── loop                LoopConfig ← from [agent.loop]
```

---

## 5. Error Handling Strategy

| Layer | Strategy |
|-------|----------|
| **LLM provider** | Retry with exponential backoff (configurable attempts). `ProviderRetryableError` for transient, `ProviderFatalError` for permanent. |
| **Tool execution** | Permission errors → return `"Error: permission denied"`. Runtime errors → return `"Error: {message}"`. |
| **Agent loop** | `HealingEngine` maps fault types to strategies. Critical faults → abort turn. |
| **Memory** | SQLite WAL mode for crash safety. FTS5 rebuild on schema mismatch. |
| **CLI** | Click handles parse errors. Agent errors surface in job status. |

---

## 6. Dependencies

| Dependency | Purpose | Scope |
|------------|---------|-------|
| `openai >= 1.0.0` | OpenAI API client | Runtime |
| `anthropic >= 0.0.0` | Anthropic API client | Runtime |
| `python-dotenv >= 1.0.0` | .env file loading | Runtime |
| `click >= 8.0.0` | CLI framework | Runtime |
| `rich >= 15.0.0` | Terminal UI | Runtime |
| `mcp >= 1.0.0` | Model Context Protocol | Runtime |
| `pyyaml >= 6.0.3` | YAML parsing | Runtime |
| `httpx` | HTTP client (web tools) | Runtime |
| `ddgs >= 9.14.4` | DuckDuckGo search | Runtime |
| `tiktoken` | Token counting | Runtime |
| `sentence-transformers` | Semantic embeddings (optional) | Runtime |
| `pytest >= 7.0.0` | Testing | Dev |
| `ruff >= 0.15.0` | Linting | Dev |
| `pyright >= 1.1.0` | Type checking | Dev |
| `vulture >= 2.15` | Dead code detection | Dev |

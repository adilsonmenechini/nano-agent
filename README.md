<p align="center">
  <img alt="NanoAgent Logo" src="https://via.placeholder.com/350x150?text=NanoAgent" width="350px">
</p>

<h1 align="center">NanoAgent</h1>

<p align="center">
  <strong>A lightweight agent framework with persistent memory, built-in tools, skill system, and multi-LLM support</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.13%2B-blue?logo=python&logoColor=white" alt="Python"/>
  <img src="https://img.shields.io/badge/license-MIT-green" alt="License"/>
  <img src="https://img.shields.io/badge/status-active-brightgreen" alt="Status"/>
</p>

<p align="center">
  <a href="#overview">Overview</a> •
  <a href="#features">Features</a> •
  <a href="#how-it-works">How It Works</a> •
  <a href="#architecture">Architecture</a> •
  <a href="#installation--usage">Installation & Usage</a> •
  <a href="#configuration">Configuration</a> •
  <a href="#built-in-tools">Built-in Tools</a> •
  <a href="#permissions--security">Permissions & Security</a> •
  <a href="#project-structure">Project Structure</a> •
  <a href="#running-tests">Running Tests</a> •
  <a href="#code-quality">Code Quality</a> •
  <a href="#specs">Specifications</a>
</p>

---

## Overview

NanoAgent is a lightweight, extensible agent framework for building AI agents with persistent memory, a modular tool system, procedural skills, and multi-provider LLM support. It is designed for developers who need a local-first, hackable agent that can automate workflows, manipulate files, run shell commands, manage git operations, and maintain long-term context across sessions.

NanoAgent was built incrementally across 5 specification phases, each adding a layer of capability: TDD infrastructure, core improvements (streaming, config, memory), a cybernetic agent loop, a built-in tool system with permissions and output safety, and an autonomous learning subsystem with reflection, experience matching, skill synthesis, and evolution.

### What's inside

| Feature | Description |
|---------|-------------|
| **Persistent Memory** | SQLite-based with FTS5 full-text search and semantic embeddings |
| **Built-in Tools** | Shell, file read/write/search, git operations — ready out of the box |
| **Tool Permissions** | Granular allow/deny/ask rules with glob, prefix, and regex matching |
| **Output Safety** | Automatic truncation of oversized tool results to protect context windows |
| **Agent Loop** | Phased execution (receive → explore → execute → verify → respond) with health monitoring and self-healing |
| **Procedural Skills** | Persistent skill definitions with versioning, scoping, and auto-discovery |
| **Multi-LLM Support** | OpenAI, Anthropic, and LM Studio (OpenAI-compatible) providers |
| **MCP Integration** | Model Context Protocol support for extending agent capabilities |
| **CLI Interface** | Interactive Rich-powered chat with job management, memory inspection, and shell escape |
| **Autonomous Learning** | Post-turn reflection, experience pattern matching, background learning cycles, skill synthesis from patterns, and DSPy + GEPA skill evolution |
| **Tool Pipeline** | DAG-based multi-step tool execution with parallel steps and inter-step references |

## Features

### 🧠 Persistent Memory

- **SQLite Backbone**: Zero-dependency storage using Python's built-in `sqlite3`
- **FTS5 Search**: Full-text search for fast memory retrieval across sessions
- **Memory Types**: General memories, user profiles, failure tracking with correction detection
- **Semantic Search**: Embedding-based similarity search via `sentence-transformers` (optional)
- **Importance Scoring**: Relevance-based memory ranking and token-budgeted selection
- **Automatic Consolidation**: Background deduplication, enrichment, and review cycles
- **Failure Learning**: Tracks failures and corrections to avoid repeated mistakes
- **Session Flush**: Periodically persists conversation context to long-term memory

### 🔧 Tool System

- **Built-in Tools**: Shell, file read/write/glob/grep, git status/diff/log — auto-registered on agent startup
- **Web Tools**: `web_search` (DuckDuckGo) and `web_fetch` with SSRF protection
- **Todo Tool**: Task management with priorities, due dates, and JSON persistence
- **Permission Control**: `PermissionManager` with `allow`/`deny`/`ask` rules, evaluated in priority order
- **Output Truncation**: `OutputTruncator` caps tool return size at configurable threshold with line-boundary-aware truncation
- **Schema Inference**: Automatic JSON Schema generation from Python type annotations via the `@tool` decorator
- **Dual Format**: Supports both OpenAI and Anthropic tool schema formats
- **Dynamic Registration**: Register/unregister tools at runtime
- **MCP Compatibility**: Load tools from any MCP-compatible server

### 📚 Procedural Skills

- **Persistent Storage**: Skills stored in SQLite with version tracking
- **Dual Scope**: Global (user-wide) and project-scoped skills for appropriate isolation
- **Auto-Discovery**: Skills loaded from filesystem directories on agent startup
- **Legacy Support**: Both `BaseSkill` objects and simple callables are supported

### 🤖 Multi-LLM Provider Support

- **Unified Interface**: All providers share a common `BaseLLMProvider` abstract class
- **OpenAI**: Full support with streaming, tool calling, configurable parameters
- **Anthropic**: Native Claude integration with tool calling
- **LM Studio**: OpenAI-compatible endpoint for local models
- **Streaming**: Incremental token output with `StreamEvent` model
- **Retry**: Configurable retry with exponential backoff for transient failures

### ⚡ Agent Loop

- **Phased Execution**: Structured turn lifecycle — `IDLE → RECEIVE → EXPLORE → EXECUTE → VERIFY → RESPOND → IDLE`
- **Health Monitoring**: `StabilityMonitor` tracks execution health across `healthy/degraded/warning/critical` levels
- **Self-Healing**: `HealingEngine` applies strategies (retry, compact, reduce scope, break oscillation) upon fault detection
- **Turn Budget**: Configurable max steps per turn with budget exhaustion detection
- **Progress Control**: `ProgressController` detects stalls, oscillations, and scope creep
- **Diagnostics**: Optional `DiagnosticsCollector` for detailed turn-level metrics

### ⚙️ Configuration

- **Environment Variables**: `.env` file for API keys and quick settings
- **TOML Config**: `~/.config/nanoagent/config.toml` for structured settings
- **Provider Profiles**: Named provider configurations for switching between models
- **Permissions Config**: Inline TOML rules for tool access control
- **MCP Auto-Discovery**: Loads `mcp.json` from the workspace directory

### 💻 Developer Experience

- **Interactive CLI**: Rich-powered chat with status indicators, markdown rendering, and inline commands
- **Memory Inspection**: Commands to view, search, and manage agent memories
- **Job Management**: Concurrent agent runs with job tracking and status
- **Shell Escape**: Run system commands without leaving the chat interface
- **Conversation History**: Persistent chat history with session management

## How It Works

NanoAgent follows a modular architecture where the core `Agent` class orchestrates pluggable components through a structured execution loop:

```
┌──────────────────────────────────────────────────┐
│                 NanoAgent Core                    │
├──────────────┬──────────────┬────────────────────┤
│   Memory     │    Tools     │      Skills        │
│ (SQLite+FTS) │  (Registry)  │    (Storage)       │
│              │  Permissions │                    │
│              │  Truncation  │                    │
├──────────────┴──────────────┴────────────────────┤
│              LLM Provider (pluggable)             │
│         OpenAI · Anthropic · LM Studio           │
├──────────────────────────────────────────────────┤
│              Agent Loop (phased)                  │
│  RECEIVE → EXPLORE → EXECUTE → VERIFY → RESPOND  │
│  [Health Monitor · Healing Engine · Diagnostics]  │
└──────────────────────────────────────────────────┘
```

### Turn Lifecycle

1. **RECEIVE**: Incoming prompt is validated and queued
2. **EXPLORE**: Memory system retrieves relevant context (FTS5 + semantic search)
3. **EXECUTE**: Agent loop runs — LLM generates responses and tool calls with permission checks and output truncation
4. **VERIFY**: Results validated, health checked, healing strategies applied if needed
5. **RESPOND**: Final response delivered to the user, conversation stored in memory

### Tool Execution Flow

```
Agent requests tool → PermissionManager checks rules → PermissionMode.ALLOW/DENY/ASK
  → ToolRegistry.execute() → tool function runs
  → OutputTruncator caps result size
  → Result returned to agent loop
```

## Architecture

### Core Components

1. **Agent** (`src/nanoagent/agent/agent.py`) — Main orchestrator
   - Manages the LLM reasoning loop with tool calling
   - Coordinates memory injection, skill execution, and background processing
   - Maintains deterministic state machine (`AgentState.IDLE → THINKING → EXECUTING_TOOLS → ...`)
   - Exposes hooks: `on_tool_call`, `on_tool_result`, `on_skill_call`, `on_thinking`, `on_paused`

2. **Tool System** (`src/nanoagent/tool.py`, `src/nanoagent/registry.py`)
   - `Tool` class: Function wrapper with auto-inferred JSON schema from type hints
   - `@tool` decorator: Registers any typed function as an LLM-callable tool
   - `ToolRegistry`: Central registry with permission manager and output truncator integration
   - `ToolPipeline`: DAG-based multi-step execution with parallel steps

3. **Built-in Tools** (`src/nanoagent/agent/tools/`)
   - `run_shell`: Subprocess execution with timeout and error capture
   - `read_file`, `write_file`, `glob_file`, `grep_file`: File operations with path traversal protection
   - `git_status`, `git_diff`, `git_log`: Git repository inspection
   - `web_search`, `web_fetch`: Web tools with SSRF protection
   - `todo`: Task management tool with JSON persistence

4. **Permissions** (`src/nanoagent/permissions.py`)
   - `PermissionRule`: Tool name + match type (exact/prefix/regex) + mode (allow/deny/ask)
   - `PermissionManager`: Evaluates rules in priority order, supports TOML config loading
   - `load_from_config()`: Creates manager from `[tools.permissions]` section

5. **Output Truncation** (`src/nanoagent/truncation.py`)
   - `OutputTruncator`: Caps tool output at `max_chars` with line-boundary snapping
   - Appends `[truncated N lines, M chars]` marker

6. **Memory System** (`src/nanoagent/memory/`)
   - `SQLiteMemoryStore`: Primary backend with FTS5 search, embeddings, importance scoring
   - `ContentScanner`: Analyzes and categorizes memory content
   - `BackgroundReview`: Periodic consolidation and enrichment
   - `CorrectionDetector`: Identifies failure → correction patterns
   - `SessionFlush`: Persists conversation context periodically

7. **Agent Loop** (`src/nanoagent/loop/`)
   - `Turn`: Phased turn execution with budget management
   - `TurnBudget`: Step counting with exhaustion detection
   - `StabilityMonitor`: Health level tracking over sliding window
   - `HealingEngine`: Fault-strategy mapping and execution
   - `ProgressController`: Stall, oscillation, and scope-creep detection
   - `DiagnosticsCollector`: Optional detailed metrics

8. **LLM Providers** (`src/nanoagent/llm/`)
   - `BaseLLMProvider`: Abstract base with `chat()`, `generate()`, streaming
   - `OpenAIProvider`: Full OpenAI API with streaming + tool calling
   - `AnthropicProvider`: Anthropic Claude API integration
   - `LMStudioProvider`: OpenAI-compatible local endpoint

9. **CLI** (`src/nanoagent/cli.py`)
   - Click-based CLI with Rich formatting
   - Commands: `chat`, `run`, memory management, agent status
   - Job manager for concurrent agent runs

10. **Configuration** (`src/nanoagent/config.py`)
    - `AgentConfig`: Dataclass loaded from `.env` + TOML file
    - `LLMProviderConfig`: Per-provider API key, base URL, model settings
    - Loop config embedded within `AgentConfig.loop`

## Installation & Usage

### Prerequisites

- Python 3.13 or higher
- Git (for cloning)

### Installation

```bash
git clone https://github.com/yourusername/nanoagent.git
cd nanoagent
pip install -e .
pip install -e ".[dev]"   # for testing/linting
```

### CLI Usage

```bash
# Interactive chat session
nanoagent chat --provider openai

# One-shot prompt
nanoagent run --prompt "What is the capital of France?" --provider openai
```

### As a Library

```python
from nanoagent.agent import Agent
from nanoagent.llm.openai import OpenAIProvider

llm = OpenAIProvider(
    api_key="your-key",
    base_url="https://api.openai.com/v1",
    model="gpt-4o",
)

agent = Agent(llm_provider=llm)
response, messages = agent.run("List all files in the current directory")
print(response)
```

## Configuration

### Environment Variables (`.env`)

```env
OPENAI_API_KEY=sk-your-key
OPENAI_MODEL=gpt-4o
ANTHROPIC_API_KEY=sk-ant-your-key
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022
LMSTUDIO_BASE_URL=http://localhost:1234/v1
LMSTUDIO_MODEL=local-model
DEFAULT_PROVIDER=openai

# Memory & Agent
PROJECT_PATH=/path/to/project
MEMORY_REVIEW_ENABLED=true
MEMORY_FLUSH_MIN_TURNS=6
MEMORY_NUDGE_INTERVAL=10
```

### TOML Config (`~/.config/nanoagent/config.toml`)

```toml
[agent]
default_provider = "openai"
project_path = "/home/user/projects/my-project"
stream = true
max_tokens = 4096
temperature = 0.7
retry_attempts = 3

[agent.loop]
max_steps_per_turn = 50
tool_timeout_seconds = 30.0
llm_timeout_seconds = 120.0
diagnostics_enabled = false

[tools.permissions]
max_output_chars = 10_240

[[tools.permissions.rules]]
tool_name = "run_shell"
mode = "deny"

[[tools.permissions.rules]]
tool_name = "write_file"
mode = "ask"

[[tools.permissions.rules]]
tool_name = "*"
mode = "allow"
```

### MCP Configuration (`mcp.json` in workspace)

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/allowed"]
    }
  }
}
```

## Built-in Tools

All built-in tools are registered automatically when `Agent` is initialized with an `AgentConfig`.

### Shell

| Tool | Description |
|------|-------------|
| `run_shell` | Execute a shell command with timeout. Returns stdout, stderr, and exit code. |

### File Operations

| Tool | Description |
|------|-------------|
| `read_file` | Read a file's contents by path. |
| `write_file` | Write content to a file (creates parent directories). |
| `glob_file` | List files matching a glob pattern. |
| `grep_file` | Search file contents with regex. |

### Git

| Tool | Description |
|------|-------------|
| `git_status` | Show working tree status. |
| `git_diff` | Show unstaged diff. |
| `git_log` | Show recent commit history. |

### Web

| Tool | Description |
|------|-------------|
| `web_search` | DuckDuckGo search with result extraction. |
| `web_fetch` | Fetch URL content with SSRF protection (blocks private IPs). |

### Todo

| Tool | Description |
|------|-------------|
| `todo` | Task management: add, list, complete, update, delete with priorities and due dates. |

## Permissions & Security

The permission system controls which tools the LLM may invoke and under what conditions.

### Permission Modes

| Mode | Behavior |
|------|----------|
| `allow` | Tool executes normally |
| `deny` | Tool returns a permission error message |
| `ask` | Tool requires human approval (interrupts execution) |

### Rule Evaluation

1. Rules are sorted by match type priority: `exact` > `prefix` > `regex`
2. Tool-specific rules beat wildcard (`*`) rules
3. First matching rule wins
4. If no rule matches, the default policy applies (`allow` or `deny`)

### Path Traversal Protection

File tools block paths containing `..` segments to prevent directory traversal attacks.

### SSRF Protection

Web tools validate URLs against private IP ranges and blocked hostnames (localhost, metadata endpoints, internal services).

### Output Safety

`OutputTruncator` prevents oversized tool output from overflowing the LLM context window, truncating at the nearest line boundary.

## Project Structure

```
nanoagent/
├── src/nanoagent/
│   ├── __init__.py                # Public API exports
│   ├── agent/
│   │   ├── agent.py               # Core Agent class
│   │   ├── cli.py                 # Click-based CLI (920 lines)
│   │   ├── context.py             # Token counting & message truncation
│   │   ├── errors.py              # Agent-specific exceptions
│   │   ├── logging.py             # Structured logging (AgentLogger)
│   │   ├── subagent.py            # Sub-agent spawning
│   │   └── tools/
│   │       ├── __init__.py        # Built-in tool registration
│   │       ├── base.py            # BaseTool abstract class
│   │       ├── shell.py           # run_shell tool
│   │       ├── file_tools.py      # read/write/glob/grep tools
│   │       ├── git_tools.py       # git_status/diff/log tools
│   │       ├── web_tool.py        # web_search/web_fetch tools
│   │       └── todo.py            # TodoTool for task management
│   ├── config.py                  # AgentConfig from .env + TOML
│   ├── llm/
│   │   ├── base.py                # BaseLLMProvider, ToolCall, LLMResponse, StreamEvent
│   │   ├── openai.py              # OpenAI provider with streaming + tool calling
│   │   ├── anthropic.py           # Anthropic Claude provider
│   │   └── lmstudio.py            # LM Studio (OpenAI-compatible) provider
│   ├── loop/
│   │   ├── __init__.py            # create_loop() factory
│   │   ├── constants.py           # Phase, StopReason, HealthLevel, LoopConfig, etc.
│   │   ├── diagnostics.py         # DiagnosticsCollector
│   │   ├── health.py              # StabilityMonitor
│   │   ├── healing.py             # HealingEngine with strategies
│   │   ├── progress.py            # ProgressController
│   │   └── turn.py                # Turn lifecycle with TurnBudget
│   ├── mcp.py                     # MCP server management
│   ├── memory/
│   │   ├── __init__.py            # Memory module
│   │   ├── sqlite_memory_store.py # SQLite backend with FTS5
│   │   ├── base.py                # Memory alias
│   │   ├── constants.py           # Memory types & failure categories
│   │   ├── content_scanner.py     # Content analysis
│   │   ├── background_review.py   # Periodic consolidation
│   │   ├── correction_detector.py # Failure ↔ correction detection
│   │   ├── embeddings.py          # Semantic search with sentence-transformers
│   │   ├── scorer.py              # Importance scoring
│   │   ├── session_flush.py       # Conversation persistence
│   │   └── utils.py               # Helper utilities
│   ├── permissions.py             # PermissionManager & PermissionRule
│   ├── registry.py                # ToolRegistry with security middleware
│   ├── skills/
│   │   ├── base.py                # BaseSkill abstract class
│   │   ├── loader.py              # Skill discovery from directories
│   │   └── skill_storage.py       # SQLite-backed skill storage
│   ├── tool.py                    # Tool class & @tool decorator
│   ├── tool_pipeline.py           # DAG-based multi-step tool execution
│   └── truncation.py              # OutputTruncator
├── specs/                         # Specification artifacts per feature
│   ├── 001-tdd-setup/             # TDD infrastructure
│   ├── 002-core-improvements/     # Streaming, config, memory enhancements
│   ├── 003-agent-loop/            # Phased loop with cybernetic controls
│   └── 004-tool-system/           # Built-in tools, permissions, truncation
├── tests/                         # Test suite (504 tests)
├── nanoagent.toml                 # Example project-local config
├── .env.example                   # Example environment variables
├── pyproject.toml                 # Project metadata & dependencies
├── PRD.md                         # Product Requirements Document
├── ARCHITECTURE.md                # Architecture documentation
├── DECISIONS.md                   # Technical decision log
└── README.md                      # This file
```

## Running Tests

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific module
python -m pytest tests/test_shell_tool.py -v

# Run with coverage (requires pytest-cov)
python -m pytest tests/ --cov=src/nanoagent --cov-report=html
```

504 tests pass, with 5 pre-existing failures in test_config_file and test_mcp that are unrelated to the core agent functionality.

## Code Quality

```bash
# Linting
ruff check .

# Type checking
pyright .

# Dead code detection
vulture .
```

## Specifications

The project was built across 4 specification phases, each in its own directory under `specs/`:

| Spec | Branch | Description |
|------|--------|-------------|
| 001 | `001-tdd-setup` | TDD infrastructure, test conventions, CI foundations |
| 002 | `002-core-improvements` | Streaming responses, configurable LLM params, semantic memory, error handling |
| 003 | `003-agent-loop` | Phased agent loop with health monitoring, self-healing, diagnostics |
| 004 | `004-tool-system` | Built-in tools (shell/file/git), permissions system, output truncation |

Each spec directory contains: `spec.md`, `plan.md`, `research.md`, `data-model.md`, `contracts/`, `tasks.md`, `quickstart.md`.

---

## License

MIT — see [LICENSE](LICENSE).

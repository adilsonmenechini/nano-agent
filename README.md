<p align="center">
  <img alt="NanoAgent Logo" src="https://via.placeholder.com/350x150?text=NanoAgent" width="350px">
</p>

<h1 align="center">NanoAgent</h1>

<p align="center">
  <strong>A lightweight agent framework with persistent memory, tools, skills, and LLM provider support</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.9%2B-blue?logo=python&logoColor=white" alt="Python"/>
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
  <a href="#project-structure">Project Structure</a> •
  <a href="#running-tests">Running Tests</a> •
  <a href="#code-quality">Code Quality</a> •
  <a href="#future-work">Future Work</a>
</p>

---

## Overview

NanoAgent is a lightweight, extensible agent framework designed for building AI agents with persistent memory, modular tool systems, and skill-based capabilities. Inspired by projects like hermes-agent, NanoAgent provides a solid foundation for creating agents that can learn, remember, and interact with various LLM providers.

### What's inside

| Feature | Description |
|---------|-------------|
| **Persistent Memory** | SQLite-based memory with FTS5 full-text search for efficient storage and retrieval |
| **Extensible Tools** | Pluggable tool system allowing easy addition of custom capabilities |
| **Procedural Skills** | Skill system for encapsulating reusable agent behaviors |
| **Multi-LLM Support** | Compatible with OpenAI, Anthropic, and LM Studio (OpenAI-compatible) providers |
| **MCP Integration** | Model Context Protocol support for extending agent capabilities |
| **CLI Interface** | Interactive command-line interface for chatting with your agent |
| **Background Processing** | Automatic memory consolidation and review systems |

## Features

### 🧠 Persistent Memory
- **SQLite Backbone**: Reliable, zero-dependency storage using Python's built-in SQLite
- **FTS5 Search**: Full-text search capabilities for fast memory retrieval
- **Memory Types**: Separate stores for general memories, user profiles, and failure tracking
- **Automatic Consolidation**: Background processes to deduplicate and enrich memories
- **Failure Learning**: System learns from mistakes through failure tracking and correction

### 🔧 Extensible Tools
- **Dynamic Registration**: Add/remove tools at runtime without restarting the agent
- **Schema Generation**: Automatic OpenAI/Anthropic tool schema generation from function signatures
- **Flexible Interface**: Support for both simple callables and structured tool objects
- **MCP Compatibility**: Seamless integration with Model Context Protocol servers

### 📚 Procedural Skills
- **Skill Storage**: Persistent storage of skill definitions with versioning
- **Scope Management**: Global and project-scoped skills for appropriate isolation
- **Easy Loading**: Automatic skill discovery from directories
- **Skill Chaining**: Combine multiple skills for complex behaviors

### 🤖 Multi-LLM Provider Support
- **Unified Interface**: Consistent API across different LLM providers
- **OpenAI Compatible**: Works with OpenAI, LM Studio, and other OpenAI-compatible endpoints
- **Anthropic Support**: Native support for Claude models
- **Provider Configuration**: Easy switching between providers via configuration
- **Fallback Handling**: Graceful degradation when providers are unavailable

### ⚙️ Configuration & Setup
- **Environment Variables**: Simple `.env` file configuration
- **Provider Profiles**: Named provider configurations for easy switching
- **Project-Specific Settings**: Per-project configuration options
- **MCP Auto-Discovery**: Automatic detection and loading of MCP configurations
- **Skill Paths**: Configurable skill discovery locations

### 💻 Developer Experience
- **Interactive CLI**: Rich command-line interface with helpful commands
- **Memory Inspection**: Built-in commands for examining and managing agent memory
- **Tool & Skill Discovery**: Commands to list available capabilities
- **Shell Escape**: Easy execution of system commands from within the chat
- **Conversation History**: Persistent chat history with navigation

## How It Works

NanoAgent follows a modular architecture where the core `Agent` class orchestrates various pluggable components:

```
┌─────────────────────────────────────┐
│          NanoAgent Core             │
├─────────────┬─────────────┬─────────┤
│   Memory    │   Tools     │ Skills  │
│ (SQLite+FTS)│ (Registry)  │ (Storage)│
└─────────────┴─────────────┴─────────┘
           │           │           │
    ┌──────▼─────┐ ┌───▼──────┐ ┌─▼──────────┐
    │ LLM Provider │ │ MCP      │ │ CLI/       │
    │ (Pluggable)  │ │ Manager  │ │ Interface  │
    └──────────────┘ └──────────┘ └────────────┘
```

### Memory System
The memory system uses SQLite with FTS5 virtual tables for efficient storage and retrieval:
- **Memories Table**: Stores entries with metadata (project, target, category, timestamps)
- **FTS5 Index**: Enables fast full-text search on memory content
- **Skills Table**: Persistent storage for skill definitions and code
- **Triggers**: Automatic FTS5 index updates on memory changes
- **Background Processes**: Automatic consolidation and review of memories

### Tool System
Tools are registered through a `ToolRegistry` that:
- Accepts both legacy callable objects and structured `Tool` instances
- Automatically generates JSON schemas for LLM consumption
- Supports both OpenAI and Anthropic tool formats
- Provides execution mediation between LLMs and tool implementations

### Skill System
Skills are managed through a `SkillStorage` system that:
- Persists skill definitions in SQLite with version tracking
- Supports both global and project-scoped skills
- Provides automatic skill discovery from filesystem
- Allows skills to be simple callables or objects with execute methods

### LLM Integration
The agent communicates with LLM providers through a unified interface:
- **Provider Factory**: Maps provider names to implementation classes
- **Schema Generation**: Converts tools to appropriate format for each provider
- **System Prompt Enhancement**: Injects memory context into system prompts
- **Tool Calling**: Handles the LLM→tool→result→LLM conversation flow
- **Background Processing**: Triggers memory operations after agent turns

## Architecture

### Core Components

1. **Agent Class** (`src/nanoagent/agent/agent.py`)
   - Main orchestrator coordinating memory, tools, skills, and LLM provider
   - Handles the agent's reasoning loop and tool execution
   - Manages memory injection into system prompts
   - Coordinates background memory processes

2. **Memory System** (`src/nanoagent/memory/`)
   - `SQLiteMemoryStore`: Primary memory backend with FTS5 search
   - Various memory scanners and processors for content analysis
   - Background review and consolidation systems
   - Failure tracking and correction detection

3. **Tool System** (`src/nanoagent/agent/tools/` and `src/nanoagent/tool.py`)
   - `ToolRegistry`: Manages tool registration and schema generation
   - `Tool` class: Standardized tool interface
   - Legacy tool adapter for backward compatibility
   - Individual tool implementations in the tools directory

4. **Skill System** (`src/nanoagent/skills/`)
   - `SkillStorage`: Persistent storage for skill definitions
   - `SkillsLoader`: Discovers and loads skills from directories
   - Skill metadata and version tracking

5. **LLM Providers** (`src/nanoagent/llm/`)
   - `BaseLLMProvider`: Abstract interface for all providers
   - Provider-specific implementations (OpenAI, Anthropic, LM Studio)
   - Unified chat and generation interfaces

6. **CLI Interface** (`src/nanoagent/cli.py`)
   - Interactive chat interface with Rich formatting
   - Memory inspection and management commands
   - Tool and skill discovery utilities
   - MCP configuration loading
   - Shell command execution

7. **Configuration** (`src/nanoagent/config.py`)
   - Environment variable-based configuration
   - Provider configuration management
   - Default values and validation

### Data Flow

1. **Input Processing**: User input received via CLI or programmatic API
2. **Context Enhancement**: Memory system retrieves relevant context
3. **Prompt Construction**: System prompt built with memory injections
4. **LLM Call**: Agent queries LLM with enhanced prompt and available tools
5. **Tool Execution**: If LLM requests tools, agent executes them
6. **Result Integration**: Tool results fed back to LLM for continued reasoning
7. **Memory Storage**: Conversation turns stored in memory system
8. **Background Processing**: Consolidation and review triggered periodically

## Installation & Usage

### Prerequisites
- Python 3.9 or higher
- Git (for cloning the repository)

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/nanoagent.git
cd nanoagent

# Install the package in development mode
pip install -e .

# For development dependencies (testing, linting, etc.)
pip install -e ".[dev]"
```

### Configuration

Create a `.env` file in the root directory with your API keys and preferences:

```env
# LLM Provider Configuration
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4o
ANTHROPIC_API_KEY=your_anthropic_api_key
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022
LMSTUDIO_BASE_URL=http://localhost:1234/v1
LMSTUDIO_MODEL=local-model
DEFAULT_PROVIDER=openai

# MCP Servers (comma-separated list)
MCP_SERVERS=http://localhost:3000/mcp,http://localhost:3001/mcp

# Agent Configuration
PROJECT_PATH=/path/to/your/project  # Optional: enables project-scoped memories
```

### As a Library

```python
from nanoagent.agent import Agent
from nanoagent.llm.openai import OpenAIProvider

# Set up the LLM provider
llm_provider = OpenAIProvider(
    api_key="your_openai_api_key",
    base_url="https://api.openai.com/v1",
    model="gpt-4o"
)

# Create the agent
agent = Agent(llm_provider=llm_provider)

# Run the agent
response, messages = agent.run("What is the capital of France?")
print(response)
```

### Via CLI

Start an interactive chat session:

```bash
nanoagent run --prompt "What is the capital of France?" --provider openai
```

Or start an interactive session without an initial prompt:

```bash
nanoagent chat --provider openai
```

### MCP Configuration

Create an `mcp.json` file in your workspace to configure MCP servers:

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-filesystem",
        "/path/to/allowed/files"
      ]
    }
  }
}
```

The agent will automatically load this configuration and register tools from the MCP servers when initialized.

## Project Structure

```
nanoagent/
├── src/
│   └── nanoagent/
│       ├── agent/
│       │   ├── agent.py          # Core agent class
│       │   ├── cli.py            # Command-line interface
│       │   └── tools/            # Tool implementations
│       ├── config.py             # Configuration management
│       ├── llm/                  # LLM provider implementations
│       │   ├── base.py           # Abstract LLM provider interface
│       │   ├── openai.py         # OpenAI provider
│       │   ├── anthropic.py      # Anthropic provider
│       │   └── lmstudio.py       # LM Studio provider
│       ├── memory/               # Memory system (SQLite-based)
│       │   ├── sqlite_memory_store.py  # Main memory implementation
│       │   ├── constants.py      # Memory-related constants
│       │   ├── content_scanner.py      # Content analysis utilities
│       │   ├── background_review.py    # Automatic memory review
│       │   └── correction_detector.py  # Failure correction detection
│       ├── skills/               # Skill system
│       │   ├── skill_storage.py  # Persistent skill storage
│       │   └── loader.py         # Skill discovery and loading
│       ├── tool.py               # Tool interface and registry
│       ├── mcp.py                # MCP manager and integration
│       └── __init__.py           # Package initializer
├── tests/                        # Unit tests
├── .env.example                  # Example environment file
├── pyproject.toml                # Project dependencies and metadata
├── README.md                     # This file
└── LICENSE                       # MIT license
```

## Running Tests

```bash
# Run all tests
python -m pytest tests/ -v

# Run tests with coverage
python -m pytest tests/ --cov=src --cov-report=html

# Run specific test module
python -m pytest tests/test_agent.py -v
```

## Code Quality

We use `ruff` for linting and `pyright` for type checking.

```bash
# Check code style
ruff check .

# Fix auto-fixable issues
ruff check . --fix

# Type checking
pyright .
```

## Future Work

- [ ] Implement automatic skill creation from observed patterns
- [ ] Add more built-in tools (file operations, web search, code execution)
- [ ] Enhance memory system with vector embeddings for semantic search
- [ ] Add background learning and auto-consolidation (like hermes-agent)
- [ ] Add secret scanning for memory entries to prevent credential leakage
- [ ] Extend CLI with more commands (memory management, skill management)
- [ ] Implement streaming responses for better user experience
- [ ] Add support for multimodal inputs (images, audio)
- [ ] Create web interface for agent interaction
- [ ] Add evaluation framework for agent performance testing
- [ ] Implement agent-to-agent communication protocols
- [ ] Add support for agent swarms and collaborative problem solving

---

## License

NanoAgent is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Inspired by [hermes-agent](https://https://github.com/nousresearch/hermes-agent) for the memory system design
- Built with ❤️ using Python and the open-source AI community
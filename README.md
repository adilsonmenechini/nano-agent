# NanoAgent

A lightweight agent framework with persistent memory, tools, skills, and LLM provider support.

## Features

- 🧠 **Persistent Memory**: SQLite-based memory with FTS5 search, inspired by [pi-hermes-memory](https://github.com/chandra447/pi-hermes-memory)
- 🔧 **Tools**: Extensible tool system (e.g., calculator)
- 📚 **Skills**: Procedural skill system (to be extended)
- 🤖 **LLM Providers**: Support for OpenAI, Anthropic, and LM Studio (OpenAI-compatible)
- ⚙️ **Configuration**: Environment variables via `.env` file
- 🖥️ **CLI**: Command-line interface for running the agent
- 🧪 **Tests**: Unit tests for core components

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/nanoagent.git
cd nanoagent

# Install dependencies
pip install -e .

# For development dependencies
pip install -e ".[dev]"
```

## Configuration

Create a `.env` file in the root directory with your API keys and preferences:

```env
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4o
ANTHROPIC_API_KEY=your_anthropic_api_key
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022
LMSTUDIO_BASE_URL=http://localhost:1234/v1
LMSTUDIO_MODEL=local-model
DEFAULT_PROVIDER=openai
MCP_SERVERS=http://localhost:3000/mcp,http://localhost:3001/mcp
```

## Usage

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
response = agent.run("What is the capital of France?")
print(response)
```

### Via CLI

```bash
nanoagent run --prompt "What is the capital of France?" --provider openai
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
│   └── agent/
│       ├── agent.py          # Core agent class
│       ├── config.py         # Configuration management
│       ├── cli.py            # Command-line interface
│       ├── memory/           # Memory system (SQLite-based)
│       ├── llm/              # LLM provider implementations
│       ├── tools/            # Tool implementations
│       └── skills/           # Skill implementations (to be extended)
├── tests/                    # Unit tests
├── .env.example              # Example environment file
├── pyproject.toml            # Project dependencies
└── README.md
```

## Running Tests

```bash
python -m pytest tests/ -v
```

## Code Quality

We use `ruff` for linting and `pyright` for type checking.

```bash
ruff check .
pyright .
```

## Future Work

- [ ] Implement skill system
- [ ] Add more tools (e.g., file operations, web search)
- [ ] Add background learning and auto-consolidation (like pi-hermes-memory)
- [ ] Add secret scanning for memory entries
- [ ] Add failure memory and correction detection
- [ ] Extend CLI with more commands (e.g., memory management, skill management)

## License

MIT
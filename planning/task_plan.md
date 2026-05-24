# Task Plan for Lightweight Agent Project

Goal: Create a lightweight agent project similar to LightAgent and nanobot, with low code, pure design, including options for tools, MCP, skills. Future plan to use same memory base as Hermes memory (github:chandra447/pi-hermes-memory).

## Steps

1. Research and analyze reference projects (LightAgent, nanobot, Hermes memory).
2. Define project architecture and core components.
3. Set up project structure (already started).
4. Implement core agent loop.
5. Implement tool system.
6. Implement MCP (Model Context Protocol) integration.
7. Implement skill system.
8. Implement memory system (based on Hermes memory).
9. Write documentation and examples.
10. Test and refine.

## Current Status
- Project structure set up with src/nanoagent/agent containing core modules.
- Implemented core agent loop (Agent class) with memory, tool, and skill registration.
- Tool system implemented with base class and calculator tool example; added todo tool example.
- Skill system base classes defined.
- Memory system implemented using SQLite with FTS5 search, global/project scope, and support for memory categories (inspired by Hermes memory).
- LLM provider support for OpenAI, Anthropic, and LM Studio (OpenAI-compatible).
- Configuration management via .env file and AgentConfig class.
- CLI interface (nanoagent command) for running the agent with different providers.
- Unit tests for agent and memory components.
- Code quality checks (ruff, pyright, vulture) passing.
- Documentation (README.md) and example usage (example.py) provided.
- Installed in development mode with dependencies.
- MCP dependency added; placeholder MCP manager created.

Completed steps:
1. Research and analyze reference projects (LightAgent, nanobot, Hermes memory). [DONE]
2. Define project architecture and core components. [DONE]
3. Set up project structure. [DONE]
4. Implement core agent loop. [DONE]
5. Implement tool system. [DONE]
6. Implement MCP (Model Context Protocol) integration. [STARTED - dependency added, placeholder created]
7. Implement skill system. [BASE CLASSES DONE, NEED IMPLEMENTATION]
8. Implement memory system (based on Hermes memory). [DONE]
9. Write documentation and examples. [DONE]
10. Test and refine. [ONGOING]

# Quickstart: Agentic Web UI

**Feature**: 006-agentic-web-ui
**Date**: 2026-06-29

## Run tests (focused for web UI)

- Backend handler tests (mocked agent, no extra deps):
PYTHONPATH=src python3 -m pytest tests/web/test_handlers.py -q
- WebSocket protocol test (requires running agent deps if connecting backend):
PYTHONPATH=src python3 -m pytest tests/web/test_websocket.py -q
- Existing E2E (Playwright browser):
python3 -m pytest tests/web/test_e2e.py -q

---

## Prerequisites

- Python 3.13+ with NanoAgent project installed (`uv sync` or `pip install -e .`)
- `aiohttp` package installed (`uv add aiohttp`)
- A running NanoAgent configuration (`.env` with LLM provider keys)

---

## Setup

```bash
# Install aiohttp dependency
uv add aiohttp

# Ensure you have API keys configured
cp .env.example .env
# Edit .env with your LLM provider keys
```

---

## Running the Web UI

```bash
# Start the web server
python -m nanoagent.web.server

# Or using the CLI (after integration):
nanoagent web
```

The server starts on `http://localhost:8080` by default. Open this URL in a browser.

---

## Validation Scenarios

### Scenario 1: Basic Chat (P1)

1. Open `http://localhost:8080` in a browser
2. **Expected**: Page loads with left sidebar (Chat/Session/Skill sections collapsed) and empty chat area
3. Type a message in the chat input and press Enter
4. **Expected**: User message appears in chat, agent begins streaming response
5. Wait for response to complete
6. **Expected**: Full agent response visible, tool calls displayed inline if any

### Scenario 2: Session Management (P2)

1. Complete Scenario 1 first
2. Refresh the browser page
3. **Expected**: Previous session appears in the Sessions list in the sidebar
4. Click the session name
5. **Expected**: Full conversation history loads in the chat panel
6. Click "New Session"
7. **Expected**: Chat clears, new session entry appears

### Scenario 3: Skill Management (P3)

1. Open the Skills section in the sidebar
2. **Expected**: List of available skills with descriptions
3. Toggle a skill off
4. **Expected**: Visual confirmation of toggle change
5. Send a message that would use the toggled skill
6. **Expected**: Agent does not use the disabled skill

---

## API Testing (without browser)

```bash
# Health check
curl http://localhost:8080/api/health

# List sessions
curl http://localhost:8080/api/sessions

# List skills
curl http://localhost:8080/api/skills
```

---

## Contract References

- [REST API Contract](file:///Users/adilsonmenechini/SRE/AI/nano-agent/specs/006-agentic-web-ui/contracts/api-rest.md)
- [WebSocket Protocol](file:///Users/adilsonmenechini/SRE/AI/nano-agent/specs/006-agentic-web-ui/contracts/websocket-protocol.md)
- [Data Model](file:///Users/adilsonmenechini/SRE/AI/nano-agent/specs/006-agentic-web-ui/data-model.md)

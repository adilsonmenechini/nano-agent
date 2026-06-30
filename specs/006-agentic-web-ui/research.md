# Research: Agentic Web UI

**Phase**: 0 — Outline & Research
**Date**: 2026-06-29
**Status**: Resolved (all NEEDS CLARIFICATION items closed)

---

## 1. Backend Web Framework

**Decision**: `aiohttp`

**Rationale**:
- Single dependency that provides HTTP server + WebSocket + static file serving
- Built-in `web.StaticResource` for serving `web-ui/` files with zero config
- First-class async WebSocket support via `web.WebSocketResponse`
- Lower dependency overhead than FastAPI (which needs FastAPI + uvicorn + websockets at minimum)
- Python built-in `http.server` does not support WebSocket natively
- Perfect for a local-first single-user app — no need for middleware, OpenAPI docs, or async DB support

**Alternatives Considered**:

| Option | Pros | Cons |
|--------|------|------|
| **FastAPI + uvicorn** | Auto-docs, middleware ecosystem | Heavy dependency chain, overkill for local-only serving |
| **Starlette** | Lightweight ASGI | Needs separate server (uvicorn); less WebSocket documentation |
| **http.server + websockets** | Zero deps for HTTP | WebSocket lib adds dep anyway; awkward async integration |
| **aiohttp** | One dep, built-in WS + static | No auto-docs |

---

## 2. Frontend Approach

**Decision**: Vanilla HTML + CSS + JavaScript

**Rationale**:
- User explicitly requested "basico" and "nanoagent web" — minimal approach
- Zero build step — no bundlers, no transpilers, no npm install
- Full control over chat streaming rendering (critical for agent tool call display)
- HTMX is excellent for HTML-over-wire but awkward for WebSocket streaming chat UIs where you need fine-grained DOM control for streaming token rendering
- 3-panel layout (sidebar sections + chat area) is straightforward with CSS Grid/Flexbox
- Local-only means no CDN dependencies — everything works offline

**Alternatives Considered**:

| Option | Pros | Cons |
|--------|------|------|
| **HTMX** | Minimal JS, good for forms | Poor fit for streaming chat token rendering; WebSocket limited |
| **Alpine.js** | Reactive, small bundle | Added complexity for no benefit in a 3-panel UI |
| **Preact** | Tiny React alternative | npm/bundler setup needed; overkill |

---

## 3. Frontend Testing

**Decision**: Playwright (via available skill) for E2E browser tests

**Rationale**:
- Playwright skill is available in this environment
- Supports WebSocket testing — critical for verifying streaming agent responses
- Can run headless in CI without a display server
- pytest + httpx for backend-only API tests (unit-level)

**Alternatives Considered**:

| Option | Pros | Cons |
|--------|------|------|
| **Playwright** | Full E2E, WS support, skill available | Heavier setup |
| **pytest + httpx** | Already in project, fast | Cannot test browser behavior or streaming rendering |
| **Manual testing** | Zero setup | Not repeatable, not CI-friendly |

---

## 4. Previously Unresolved Technical Details

| Unknown | Resolution |
|---------|-----------|
| Backend web framework | **aiohttp** — single dependency, WS + static + HTTP |
| Frontend technology | **Vanilla HTML/CSS/JS** — zero build step, full control |
| Frontend testing | **Playwright** — E2E browser tests + **pytest** for backend bridge |
| Coverage scope for frontend | Frontend JS files in `web-ui/` are not covered by pytest. Python backend bridge in `src/nanoagent/web/` IS covered by pytest (same 80% rule). Frontend E2E tests use Playwright separately. |
| Static analysis for frontend | No JS linter in initial version — Python static analysis (Ruff, Pyright, Vulture) continues to cover `src/nanoagent/` only |

## 5. Key Architecture Decisions

### Communication Protocol
- **WebSocket** for bidirectional streaming (agent responses, state updates)
- **HTTP REST** for session listing, skill management (request-response patterns)
- Single `aiohttp` server handles both on the same port

### Session Management
- `GET /api/sessions` — list sessions
- `GET /api/sessions/{id}` — get session with messages
- `POST /api/sessions` — create new session
- `DELETE /api/sessions/{id}` — delete session

### Skills Management
- `GET /api/skills` — list skills
- `PATCH /api/skills/{name}` — toggle enabled/disabled

### Real-time Communication
- `GET /ws/chat` — WebSocket for sending messages and receiving streaming responses
- Messages framed as JSON: `{ type: "message" | "tool_call" | "state" | "error", payload: {...} }`

### Agent Integration
- The bridge wraps the existing `Agent` class from `nanoagent.agent`
- Sessions use the existing `SQLiteMemoryStore` for persistence
- Skills use the existing `SkillsLoader` and `SkillStorage`

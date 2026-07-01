---

description: "Task list for Agentic Web UI feature implementation"

---

# Tasks: Agentic Web UI

**Input**: Design documents from `/specs/006-agentic-web-ui/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Constitution**: Test-First is NON-NEGOTIABLE — tests must precede implementation for all backend code. Frontend E2E tests use Playwright.

**Organization**: Tasks grouped by user story for independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

| Area | Path |
|------|------|
| Web frontend | `web-ui/` |
| Backend bridge | `src/nanoagent/web/` |
| Backend tests | `tests/web/` |
| Documentation | `specs/006-agentic-web-ui/` |

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization, dependency installation, and directory structure

- [X] T001 Install `aiohttp` dependency via `uv add aiohttp`
- [X] T002 Create `src/nanoagent/web/` module directory with `__init__.py`
- [X] T003 Create `tests/web/` test directory with `__init__.py`
- [X] T004 Create `web-ui/` directory structure: `css/`, `js/`, `assets/`
- [X] T005 Create `web-ui/assets/` placeholder (favicon, etc.)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Tests

- [X] T006 [P] Test server startup and static file serving in `tests/web/test_server.py`
- [X] T007 [P] Test health endpoint in `tests/web/test_server.py`
- [X] T008 [P] Test 404 handling in `tests/web/test_server.py`

### Implementation

- [X] T009 [P] Create `src/nanoagent/web/server.py` — aiohttp app factory, static file mount, WebSocket setup, CORS
- [X] T010 [P] Create `src/nanoagent/web/handlers.py` — session REST handlers (list/get/create/delete), skill REST handlers (list/toggle), health check, WebSocket handler skeleton
- [X] T011 [P] Create `src/nanoagent/web/static.py` — static file serving configuration for `web-ui/`

**Checkpoint**: Foundation ready — user story implementation can now begin in parallel

---

## Phase 3: User Story 1 — Chat with the Agent (Priority: P1) 🎯 MVP

**Goal**: User opens web UI and sends messages to the NanoAgent with streaming responses, tool call visibility, and agent state indicators.

**Independent Test**: Open `http://localhost:8080`, type a message, verify agent responds with streaming output and tool calls are visible inline.

### Tests for User Story 1

- [X] T012 [P] [US1] Test WebSocket chat message handler in `tests/web/test_handlers.py`
- [X] T013 [P] [US1] Test streaming response chunking via E2E in `tests/web/test_e2e.py`
- [X] T014 [P] [US1] Test tool call event serialization in `tests/web/test_e2e.py`
- [X] T015 [P] [US1] Test connection error handling in `tests/web/test_e2e.py`

### Implementation for User Story 1

- [X] T016 [P] [US1] Create `web-ui/index.html` — SPA shell with left sidebar placeholder and main chat area
- [X] T017 [P] [US1] Create `web-ui/css/style.css` — layout (sidebar + chat), typography, colors, message bubbles
- [X] T018 [P] [US1] Create `web-ui/js/bridge.js` — WebSocket connection manager with auto-reconnect, message serialization/deserialization
- [X] T019 [P] [US1] Create `web-ui/js/chat.js` — chat panel rendering, message bubbles, streaming delta accumulation, tool call display, agent state indicator
- [X] T020 [US1] Create `web-ui/js/app.js` — main app controller, initializes sidebar and chat, coordinates bridge events → UI updates
- [X] T021 [US1] Implement WebSocket chat loop in `src/nanoagent/web/handlers.py` — connect to agent, stream response chunks, emit tool_call_start/tool_call_result/agent_state_change events
- [X] T022 [US1] Wire cancel message handling in `web-ui/js/bridge.js` and `src/nanoagent/web/handlers.py`

**Checkpoint**: At this point, User Story 1 should be fully functional — user can chat with the agent via the web UI with streaming responses and tool call visibility.

---

## Phase 4: User Story 2 — Browse and Manage Sessions (Priority: P2)

**Goal**: User can view past sessions in the sidebar, click to load full conversation history, and start new sessions.

**Independent Test**: Complete a chat, refresh the page, verify session appears in list. Click it to load history. Click "New Session" to start fresh.

### Tests for User Story 2

- [X] T023 [P] [US2] Test GET /api/sessions returns session list in `tests/web/test_e2e.py`
- [X] T024 [P] [US2] Test GET /api/sessions/{id} returns full conversation in `tests/web/test_e2e.py`
- [X] T025 [P] [US2] Test POST /api/sessions creates new session in `tests/web/test_e2e.py`
- [X] T026 [P] [US2] Test DELETE /api/sessions/{id} removes session via E2E in `tests/web/test_e2e.py`
- [X] T027 [P] [US2] Test session persistence via E2E in `tests/web/test_e2e.py`

### Implementation for User Story 2

- [X] T028 [P] [US2] Implement session REST handlers in `src/nanoagent/web/handlers.py` — list, get, create, delete using existing SQLiteMemoryStore
- [X] T029 [P] [US2] Add session routes to server in `src/nanoagent/web/server.py`
- [X] T030 [P] [US2] Create `web-ui/js/sessions.js` — session list rendering, new session button, session loading, active session highlighting
- [X] T031 [US2] Update `web-ui/index.html` — add Sessions section to left sidebar with new session button and dynamic list container
- [X] T032 [US2] Update `web-ui/js/app.js` — integrate session selection → chat load, new session → clear chat, message posting → update session metadata

**Checkpoint**: At this point, User Stories 1 AND 2 should work independently — full chat with session persistence.

---

## Phase 5: User Story 3 — View and Manage Skills (Priority: P3)

**Goal**: User can see available skills in the sidebar with descriptions and toggle them on/off.

**Independent Test**: Open Skills section, verify list matches registered skills. Toggle a skill off, verify it is no longer used by the agent.

### Tests for User Story 3

- [X] T033 [P] [US3] Test GET /api/skills returns skill list in `tests/web/test_e2e.py`
- [X] T034 [P] [US3] Test PATCH /api/skills/{name} toggles enabled state via E2E in `tests/web/test_e2e.py`
- [X] T035 [P] [US3] Test disabled skill is excluded from agent tools via E2E in `tests/web/test_e2e.py`

### Implementation for User Story 3

- [X] T036 [P] [US3] Implement skill REST handlers in `src/nanoagent/web/handlers.py` — list, toggle using existing SkillStorage/SkillsLoader
- [X] T037 [P] [US3] Add skill routes to server in `src/nanoagent/web/server.py`
- [X] T038 [P] [US3] Create `web-ui/js/skills.js` — skill list rendering, toggle switch, expandable description
- [X] T039 [US3] Update `web-ui/index.html` — add Skills section to left sidebar with toggle UI
- [X] T040 [US3] Update `web-ui/js/app.js` — integrate skill toggle → update agent configuration, refresh skill list on page load

**Checkpoint**: At this point, all three user stories are functional.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Error handling, responsive design, visual refinement, and integration testing.

- [ ] T041 [P] Add comprehensive error handling to `web-ui/js/bridge.js` — connection loss, reconnection, timeout
- [ ] T042 [P] Add responsive layout breakpoints to `web-ui/css/style.css` — 768px tablet sidebar collapse
- [ ] T043 [P] Add loading states and transitions to `web-ui/css/style.css`
- [ ] T044 [P] Add visual polish to `web-ui/css/style.css` — smooth animations, focus states, scrollbar styling, dark theme support
- [ ] T045 Create E2E test script with Playwright in `tests/web/test_e2e.py` — chat flow, session navigation, skill toggle
- [ ] T046 Update `AGENTS.md` if needed to reference latest documentation

---

## Dependencies & Execution Order

### Phase Dependency Graph

```
Phase 1 (Setup)
    │
    ▼
Phase 2 (Foundational)
    │
    ├──────────────────────┐
    ▼                      ▼
Phase 3 (US1 - Chat)  Phase 4 (US2 - Sessions)
    │                      │
    └──────────┬───────────┘
               ▼
         Phase 5 (US3 - Skills)
               │
               ▼
         Phase 6 (Polish)
```

### Execution Strategy

**MVP Scope** (smallest deliverable): Phases 1 + 2 + 3 — this delivers a working chat UI. User types messages, agent responds with streaming. No session persistence, no skill management.

**Full Feature**: All 6 phases.

### Parallel Opportunities

Per phase, tasks marked `[P]` can run in parallel. Cross-phase parallelism:

- **Phase 3 (US1) and Phase 4 (US2)** can be implemented in parallel by two agents:
  - Agent A: Chat UI + WebSocket + index.html shell + app.js
  - Agent B: Session REST handlers + sessions.js + session sidebar HTML
- Integration happens in Phase 5 merging app.js with session management

### Independent Test Criteria

| Story | Test | Delivers Value Alone? |
|-------|------|-----------------------|
| US1 | Open browser, send message, see streaming response | ✅ Yes — full chat experience |
| US2 | Load sessions, switch between them | ✅ Yes — navigation value |
| US3 | View and toggle skills | ✅ Yes — skill control |

---

## Phase 6: Polish & E2E Testing

**Purpose**: End-to-end testing with Playwright, bug fixes, and final polish

- [X] T041 Install Playwright as dev dependency (`uv add --dev pytest-playwright`)
- [X] T042 Create `tests/web/test_e2e.py` — Playwright E2E tests with 10 test cases
- [X] T043 Fix server static file serving — add explicit `/` handler for `index.html`
- [X] T044 Fix `window.app` scoping — change `let app;` to `window.app = new App()` for testability
- [X] T045 Fix bridge message queue — buffer messages sent before WebSocket open
- [X] T046 Fix `handlers.py` — add `import asyncio` to resolve WebSocket `NameError`
- [X] T047 Verify full streaming chat flow E2E — user message + agent response both appear
- [X] T048 All 15 tests passing (10 E2E + 5 unit) — complete feature validation

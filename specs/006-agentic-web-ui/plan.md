# Implementation Plan: Agentic Web UI

**Branch**: `006-agentic-web-ui` | **Date**: 2026-06-29 | **Spec**: [spec.md](file:///Users/adilsonmenechini/SRE/AI/nano-agent/specs/006-agentic-web-ui/spec.md)

**Input**: Feature specification from `/specs/006-agentic-web-ui/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Build a modern web frontend for NanoAgent inside the existing `web-ui/` directory. The UI has a left sidebar with three sections (Chat, Session, Skill) and a main chat area with streaming agent responses. The frontend is served by a lightweight Python web server that bridges to the existing nanoagent backend. Approach: minimal, no heavy framework — vanilla frontend, lightweight Python server-side bridge.

## Technical Context

**Language/Version**: Python 3.13+ (backend), HTML/CSS/JavaScript (frontend)

**Primary Dependencies**:
- Backend: `aiohttp` or `websockets` for WebSocket streaming + static file serving (NEEDS CLARIFICATION: lightweight vs full ASGI framework)
- Frontend: No framework — vanilla JS + CSS (NEEDS CLARIFICATION: consider minimal alternatives like HTMX)
- Existing nanoagent dependencies remain unchanged

**Storage**: SQLite (existing backend memory store persists sessions and skills)

**Testing**: 
- Backend: pytest (existing project standard)
- Frontend: NEEDS CLARIFICATION — Playwright E2E vs manual verification

**Target Platform**: Modern browsers — Chrome 120+, Firefox 120+, Safari 17+ (desktop and tablet 768px+)

**Project Type**: Web application — single-page frontend + Python backend bridge to existing agent framework

**Performance Goals**: 
- Page load <3s
- First response streaming visible <2s after message submit
- Session list loads <1s

**Constraints**: 
- Must use minimal dependencies — "basico somente nanoagent web"
- Must work locally without cloud services
- Must reuse existing backend agent/memory/skill logic without duplication

**Scale/Scope**: Single-user local-first web UI, desktop + tablet responsive

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Based on [constitution.md](file:///Users/adilsonmenechini/SRE/AI/nano-agent/.specify/memory/constitution.md):

| Gate | Requirement | Status | Notes |
|------|------------|--------|-------|
| **I. Test-First** | Tests must precede implementation | ✅ PASS | Backend bridge: pytest-based tests in `tests/web/`. Frontend E2E: Playwright for browser testing. Both defined in research.md. |
| **II. Spec-Driven** | Spec must exist | ✅ PASS | spec.md created and validated |
| **III. Quality Gates** | 80% line coverage on src/nanoagent/ | ✅ PASS | New `src/nanoagent/web/` module falls under same coverage scope. Frontend `web-ui/` JS files are excluded (not Python). |
| **IV. Static Analysis** | Ruff, Pyright, Vulture | ✅ PASS | Python code in `src/nanoagent/web/` passes existing toolchain. Frontend JS files not linted in v1 (research.md documents this boundary). |
| **V. Simplicity** | YAGNI — no premature abstraction | ✅ PASS | Vanilla JS approach. Single aiohttp server. No build step. |

**Gate Assessment**: All gates pass. The web frontend introduces frontend code (`web-ui/`) outside the existing Python coverage scope, but this is documented and acceptable. The backend bridge (`src/nanoagent/web/`) is fully covered by existing quality gates.

## Project Structure

### Documentation (this feature)

```text
specs/006-agentic-web-ui/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
web-ui/                          # Web frontend (already exists, empty)
├── index.html                   # Main SPA entry point
├── css/
│   └── style.css                # All styles
├── js/
│   ├── app.js                   # Main app controller
│   ├── chat.js                  # Chat panel logic
│   ├── sessions.js              # Session management
│   ├── skills.js                # Skills management
│   └── bridge.js                # WebSocket/REST bridge to backend
└── assets/                      # Icons, fonts, etc.

src/nanoagent/
├── web/                         # NEW: backend bridge module
│   ├── __init__.py
│   ├── server.py                # HTTP + WebSocket server
│   ├── handlers.py              # Request/WebSocket handlers
│   └── static.py                # Static file serving

tests/
├── ...existing tests...
└── web/                         # NEW: tests for web bridge
    ├── test_server.py
    ├── test_handlers.py
    └── test_integration.py
```

**Structure Decision**: Selected "Web application" pattern adapted to NanoAgent's single-package layout. The frontend lives in `web-ui/` (vanilla static files). Backend bridge lives in `src/nanoagent/web/` as a new submodule within the existing Python package. Tests mirror this structure in `tests/web/`.

"""HTTP and WebSocket handlers for the NanoAgent Web UI bridge."""

import asyncio
import json
import logging
import threading
import time
import uuid

from aiohttp import web

from nanoagent.agent import Agent
from nanoagent.llm.base import StreamEvent
from .keys import START_TIME

# ── Logger ──────────────────────────────────────────────────────────────────
handler_logger = logging.getLogger("nanoagent.web.handlers")


# ── Agent factory (singleton per process) ──────────────────────────────────

_agent_lock = threading.Lock()
_agent_instance: Agent | None = None


def _get_agent() -> Agent:
    global _agent_instance
    if _agent_instance is not None:
        handler_logger.debug("Agent instance reused from cache")
        return _agent_instance
    with _agent_lock:
        if _agent_instance is not None:
            handler_logger.debug("Agent instance reused from cache (double-checked)")
            return _agent_instance
        from nanoagent.config import AgentConfig

        config = AgentConfig()
        provider_name = config.default_provider
        handler_logger.info("Initializing agent with provider: %s", provider_name)
        llm = None
        if provider_name:
            pc = config.get_provider_config(provider_name)
            if pc:
                from nanoagent.llm.anthropic import AnthropicProvider
                from nanoagent.llm.lmstudio import LMStudioProvider
                from nanoagent.llm.openai import OpenAIProvider

                factory: dict[str, type[OpenAIProvider | AnthropicProvider | LMStudioProvider]] = {
                    "openai": OpenAIProvider,
                    "anthropic": AnthropicProvider,
                    "lmstudio": LMStudioProvider,
                }
                cls = factory.get(provider_name)
                if cls:
                    # Pass timeout from config to LLM provider
                    timeout = config.loop.llm_timeout_seconds if hasattr(config, 'loop') and config.loop else 120.0
                    llm = cls(api_key=pc.api_key, base_url=pc.base_url, model=pc.model, timeout=timeout)
        agent = Agent(llm_provider=llm)
        # The agent's __init__ will now store the loop_config
        _agent_instance = agent
    handler_logger.info("Agent initialized successfully")
    return _agent_instance


# ── JSON helpers ──────────────────────────────────────────────────────────


def _json_response(data: dict[str, object], status: int = 200) -> web.Response:
    return web.Response(
        text=json.dumps(data, ensure_ascii=False),
        content_type="application/json",
        status=status,
        headers={"Cache-Control": "no-store"},
    )


def _error_response(message: str, status: int = 400) -> web.Response:
    return _json_response({"error": message}, status=status)


# ── Middleware ────────────────────────────────────────────────────────────


@web.middleware
async def cors_middleware(request: web.Request, handler) -> web.StreamResponse:
    if request.method == "OPTIONS":
        response = web.Response()
    else:
        response = await handler(request)
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, DELETE, PATCH, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response


# ── Session handlers ──────────────────────────────────────────────────────


async def handle_list_sessions(request: web.Request) -> web.Response:
    handler_logger.info("Listing active sessions")
    agent = _get_agent()
    try:
        sessions = agent.memory.list_sessions(limit=50)
        result: list[dict[str, object]] = []
        for s in sessions:
            messages = s.get("messages", [])
            if not messages:
                continue
            last_msg = messages[-1].get("content", "") if messages else ""
            if last_msg:
                last_msg = str(last_msg)[:80]
            else:
                last_msg = ""
            result.append({
                "id": s["id"],
                "name": last_msg or f"Session {s['id'][:8]}",
                "message_count": len(messages),
                "created_at": s["created"],
                "updated_at": s["updated"],
                "is_active": False,
            })
        handler_logger.debug("Found %d sessions with messages", len(result))
        return _json_response({"sessions": result})
    except Exception as e:
        handler_logger.error("Error listing sessions: %s", str(e), exc_info=True)
        return _error_response(str(e), 500)


async def handle_get_session(request: web.Request) -> web.Response:
    session_id = request.match_info.get("id", "")
    handler_logger.info("Fetching session details: %s", session_id)
    agent = _get_agent()
    try:
        session = agent.memory.load_session(session_id)
        if session is None:
            handler_logger.warning("Attempted to fetch missing session: %s", session_id)
            return _error_response("Session not found", 404)
        messages = session.get("messages", [])
        handler_logger.debug("Loaded session %s: %d messages", session_id, len(messages))
        name = messages[-1].get("content", "") if messages else "Empty session"
        if not name:
            name = "Empty session"
        return _json_response({
            "session": {
                "id": session["id"],
                "name": name,
                "conversation": {"messages": messages},
                "created_at": session["created"],
                "updated_at": session["updated"],
                "is_active": session.get("status") == "active",
            }
        })
    except Exception as e:
        handler_logger.error("Error loading session %s: %s", session_id, str(e), exc_info=True)
        return _error_response(str(e), 500)


async def handle_create_session(request: web.Request) -> web.Response:
    agent = _get_agent()
    session_id = str(uuid.uuid4())
    now = time.time()
    agent.memory.save_session(session_id, [], status="active")
    return _json_response({
        "session": {
            "id": session_id,
            "name": "New session",
            "conversation": {"messages": []},
            "created_at": now,
            "updated_at": now,
            "is_active": True,
        }
    }, status=201)


async def handle_delete_session(request: web.Request) -> web.Response:
    session_id = request.match_info.get("id", "")
    handler_logger.info("Solicitação para deletar sessão: %s", session_id)
    agent = _get_agent()
    try:
        session = agent.memory.load_session(session_id)
        if session is None:
            handler_logger.warning("Tentativa de deletar sessão que não existe: %s", session_id)
            return _error_response("Session not found", 404)
        agent.memory.save_session(session_id, session.get("messages", []), status="cancelled")
        handler_logger.info("Sessão %s deletada com sucesso", session_id)
        return _json_response({"status": "deleted", "session_id": session_id})
    except Exception as e:
        handler_logger.error("Erro ao deletar sessão %s: %s", session_id, str(e), exc_info=True)
        return _error_response(str(e), 500)


# ── Skill handlers ────────────────────────────────────────────────────────


async def handle_list_skills(request: web.Request) -> web.Response:
    handler_logger.info("Listing skills")
    agent = _get_agent()
    try:
        db_skills = agent.skill_storage.list_skills(scope="global")
        skills = []
        for s in db_skills:
            skill_name = s.get("slug", s.get("name", ""))
            skills.append({
                "name": skill_name,
                "description": s.get("description", ""),
                "enabled": s.get("name", "") in agent.skills or s.get("slug", "") in agent.skills,
                "details": "",
                "updated_at": s.get("updated_at", 0),
            })
        handler_logger.info("Returning %d skills", len(skills))
        return _json_response({"skills": skills})
    except Exception as e:
        handler_logger.error("Error listing skills: %s", str(e), exc_info=True)
        return _error_response(str(e), 500)


async def handle_toggle_skill(request: web.Request) -> web.Response:
    skill_name = request.match_info.get("name", "")
    handler_logger.info("Toggling skill: %s", skill_name)
    # Backend placeholder: skill state is managed in frontend cache; extend if persistence is required.
    try:
        body = await request.json()
        enabled = bool(body.get("enabled", True))
    except Exception:
        enabled = True
    handler_logger.debug("Skill %s set to enabled=%s", skill_name, enabled)
    return _json_response({
        "skill": {
            "name": skill_name,
            "description": "",
            "enabled": enabled,
            "updated_at": time.time(),
        }
    })


# ── Health handler ────────────────────────────────────────────────────────


async def handle_health(request: web.Request) -> web.Response:
    app = request.app
    start = app.get(START_TIME, time.time())
    uptime = time.time() - start
    handler_logger.debug("Health check initiated: uptime=%.2fs", uptime)
    return _json_response({
        "status": "ok",
        "version": "0.1.0",
        "uptime_seconds": int(uptime),
    })


# ── WebSocket chat handler ────────────────────────────────────────────────


async def handle_websocket(request: web.Request) -> web.WebSocketResponse:
    handler_logger.info("Nova conexão WebSocket estabelecida")
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    session_id = request.query.get("session_id", str(uuid.uuid4()))
    handler_logger.info("Sessão associada: %s", session_id)
    agent = _get_agent()

    try:
        async for msg in ws:
            if msg.type == web.WSMsgType.TEXT:
                try:
                    data = json.loads(msg.data)
                except json.JSONDecodeError:
                    handler_logger.warning("JSON inválido recebido")
                    await ws.send_json({"type": "error", "payload": {"code": "parse_error", "message": "Invalid JSON"}})
                    continue

                msg_type = data.get("type")
                handler_logger.debug("Recebido evento: %s", msg_type)

                if msg_type == "cancel":
                    handler_logger.warning("Cancelamento recebido para sessão %s", session_id)
                    agent.cancelled = True
                    await ws.send_json({"type": "error", "payload": {"code": "cancelled", "message": "Response cancelled", "session_id": session_id}})
                    continue

                if msg_type == "user_message":
                    content = data.get("payload", {}).get("content", "")
                    if not content:
                        handler_logger.debug("Mensagem vazia ignorada")
                        continue

                    handler_logger.info("Mensagem do usuário recebida (sessao %s): %s...", session_id, content[:50])

                    await ws.send_json({
                        "type": "agent_state_change",
                        "payload": {"state": "thinking", "previous_state": "idle", "session_id": session_id},
                    })

                    stream_events: list[StreamEvent] = []
                    stream_lock = threading.Lock()

                    def run_agent() -> None:
                        nonlocal stream_events
                        try:
                            stored = agent.memory.load_session(session_id)
                            messages = list(stored["messages"]) if stored and stored.get("messages") else []
                            handler_logger.debug("Iniciando stream para sessao %s", session_id)
                            for event in agent.run_stream(content, messages=messages, session_id=session_id):
                                with stream_lock:
                                    stream_events.append(event)
                        except Exception as exc:
                            handler_logger.error("Erro no agente: %s", str(exc), exc_info=True)
                            with stream_lock:
                                stream_events.append(StreamEvent(type="error", delta=str(exc)))

                thread = threading.Thread(target=run_agent, daemon=True)
                thread.start()

                while thread.is_alive() or stream_events:
                    with stream_lock:
                        events_to_send = list(stream_events)
                        stream_events.clear()

                    for event in events_to_send:
                        if event.type == "content":
                            await ws.send_json({
                                "type": "message_chunk",
                                "payload": {"message_id": session_id, "delta": event.delta, "session_id": session_id},
                            })
                        elif event.type == "tool_call":
                            tc = event.delta or {}
                            if isinstance(tc, dict):
                                func = tc.get("function") or {}
                                tool_name = tc.get("name")
                                if not tool_name:
                                    if isinstance(func, dict):
                                        tool_name = func.get("name", "unknown")
                                    else:
                                        tool_name = getattr(func, "name", "unknown")
                                await ws.send_json({
                                    "type": "tool_call_start",
                                    "payload": {
                                        "tool_name": tool_name,
                                        "arguments": tc.get("arguments", {}),
                                        "tool_call_id": str(uuid.uuid4()),
                                        "session_id": session_id,
                                    },
                                })
                                await ws.send_json({
                                    "type": "agent_state_change",
                                    "payload": {"state": "executing_tools", "previous_state": "thinking", "session_id": session_id},
                                })
                        elif event.type == "done":
                            await ws.send_json({
                                "type": "message_complete",
                                "payload": {"message_id": session_id, "session_id": session_id, "full_content": "", "timestamp": time.time()},
                            })
                            await ws.send_json({
                                "type": "agent_state_change",
                                "payload": {"state": "idle", "previous_state": "thinking", "session_id": session_id},
                            })
                        elif event.type == "error":
                            await ws.send_json({
                                "type": "error",
                                "payload": {"code": "agent_error", "message": str(event.delta), "session_id": session_id},
                            })
                            await ws.send_json({
                                "type": "message_complete",
                                "payload": {"message_id": session_id, "session_id": session_id, "full_content": "", "timestamp": time.time()},
                            })
                            await ws.send_json({
                                "type": "agent_state_change",
                                "payload": {"state": "idle", "previous_state": "thinking", "session_id": session_id},
                            })

                    if not stream_events and thread.is_alive():
                        await asyncio.sleep(0.05)

                thread.join()

                await ws.send_json({
                    "type": "session_updated",
                    "payload": {"session_id": session_id, "message_count": 0, "updated_at": time.time()},
                })

            elif msg.type == web.WSMsgType.ERROR:
                handler_logger.warning("WebSocket error for session %s", session_id)
                break
    except Exception as e:
        handler_logger.error("WebSocket error: %s", str(e), exc_info=True)

    handler_logger.info("WebSocket connection closed for session %s", session_id)
    return ws


# ── Route setup ───────────────────────────────────────────────────────────


def setup_routes(app: web.Application) -> None:
    app.middlewares.append(cors_middleware)

    app.router.add_get("/api/health", handle_health)
    app.router.add_get("/api/sessions", handle_list_sessions)
    app.router.add_get("/api/sessions/{id}", handle_get_session)
    app.router.add_post("/api/sessions", handle_create_session)
    app.router.add_delete("/api/sessions/{id}", handle_delete_session)
    app.router.add_get("/api/skills", handle_list_skills)
    app.router.add_patch("/api/skills/{name}", handle_toggle_skill)
    app.router.add_get("/ws/chat", handle_websocket)
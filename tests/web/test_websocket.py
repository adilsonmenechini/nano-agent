"""Tests for the WebSocket chat protocol."""

import asyncio

from aiohttp.test_utils import AioHTTPTestCase
from aiohttp import web

from nanoagent.web.handlers import handle_websocket


class TestWebSocketChat(AioHTTPTestCase):
    async def get_application(self):
        app = web.Application()
        app.router.add_get("/ws/chat", handle_websocket)
        return app

    async def test_websocket_connect_and_stream(self):
        session_id = "test-session-ws"
        async with self.client.ws_connect(f"/ws/chat?session_id={session_id}") as ws:
            await ws.send_json({"type": "user_message", "payload": {"content": "ping"}})
            received = []
            timeout = 5
            deadline = asyncio.get_event_loop().time() + timeout
            while asyncio.get_event_loop().time() < deadline:
                msg = await ws.receive(timeout=timeout)
                if msg.type == web.WSMsgType.TEXT:
                    received.append(msg.data)
                elif msg.type == web.WSMsgType.CLOSED:
                    break
                elif msg.type == web.WSMsgType.ERROR:
                    break
                timeout = max(0, deadline - asyncio.get_event_loop().time())
            types = [__import__("json").loads(m).get("type") for m in received]
            assert "agent_state_change" in types
            assert "message_complete" in types

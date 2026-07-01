"""Tests for web UI HTTP handlers (sessions and skills)."""

from unittest.mock import MagicMock
from uuid import uuid4

from aiohttp.test_utils import AioHTTPTestCase
from aiohttp import web

from nanoagent.web.handlers import (
    handle_create_session,
    handle_delete_session,
    handle_get_session,
    handle_list_sessions,
    handle_list_skills,
    handle_toggle_skill,
)


class TestSessionsHandlers(AioHTTPTestCase):
    async def get_application(self):
        self._mock_agent = MagicMock()
        self._mock_agent.memory.list_sessions.return_value = []
        self._mock_agent.memory.load_session.return_value = None
        self._mock_agent.memory.save_session.return_value = None
        import nanoagent.web.handlers as handlers

        self._orig_get_agent = handlers._get_agent
        handlers._get_agent = lambda: self._mock_agent
        app = web.Application()
        app.router.add_get("/api/sessions", handle_list_sessions)
        app.router.add_get("/api/sessions/{id}", handle_get_session)
        app.router.add_post("/api/sessions", handle_create_session)
        app.router.add_delete("/api/sessions/{id}", handle_delete_session)
        return app

    async def tearDown(self):
        import nanoagent.web.handlers as handlers

        handlers._get_agent = self._orig_get_agent
        await super().tearDown()

    async def test_list_sessions_returns_empty(self):
        resp = await self.client.get("/api/sessions")
        assert resp.status == 200
        data = await resp.json()
        assert "sessions" in data
        assert isinstance(data["sessions"], list)

    async def test_create_session_returns_id(self):
        resp = await self.client.post("/api/sessions")
        assert resp.status == 201
        data = await resp.json()
        assert "session" in data
        assert "id" in data["session"]

    async def test_get_session_not_found(self):
        resp = await self.client.get("/api/sessions/does-not-exist")
        assert resp.status == 404

    async def test_delete_session_not_found(self):
        resp = await self.client.delete("/api/sessions/does-not-exist")
        assert resp.status == 404


class TestSkillsHandlers(AioHTTPTestCase):
    async def get_application(self):
        self._mock_agent = MagicMock()
        self._mock_agent.skill_storage.list_skills.return_value = []
        self._mock_agent.skills = {}
        import nanoagent.web.handlers as handlers

        self._orig_get_agent = handlers._get_agent
        handlers._get_agent = lambda: self._mock_agent
        app = web.Application()
        app.router.add_get("/api/skills", handle_list_skills)
        app.router.add_patch("/api/skills/{name}", handle_toggle_skill)
        return app

    async def tearDown(self):
        import nanoagent.web.handlers as handlers

        handlers._get_agent = self._orig_get_agent
        await super().tearDown()

    async def test_list_skills_returns_list(self):
        resp = await self.client.get("/api/skills")
        assert resp.status == 200
        data = await resp.json()
        assert "skills" in data
        assert isinstance(data["skills"], list)

    async def test_toggle_skill_accepts_payload(self):
        name = uuid4().hex
        resp = await self.client.patch(
            f"/api/skills/{name}",
            json={"enabled": True},
        )
        assert resp.status == 200
        data = await resp.json()
        assert data["skill"]["name"] == name
        assert data["skill"]["enabled"] is True

    async def test_toggle_skill_missing_body(self):
        name = uuid4().hex
        resp = await self.client.patch(
            f"/api/skills/{name}",
            data="not-json",
            headers={"Content-Type": "application/json"},
        )
        assert resp.status == 200

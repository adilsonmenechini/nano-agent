"""Tests for the web UI server module."""

from aiohttp.test_utils import AioHTTPTestCase

from nanoagent.web.server import create_app


class TestServer(AioHTTPTestCase):
    async def get_application(self):
        app = create_app(static_dir=None)
        return app

    async def test_server_creates_app(self):
        self.assertIsNotNone(self.app)

    async def test_health_endpoint(self):
        resp = await self.client.get("/api/health")
        assert resp.status == 200
        data = await resp.json()
        assert data["status"] == "ok"
        assert "version" in data
        assert "uptime_seconds" in data

    async def test_404_nonexistent_api(self):
        resp = await self.client.get("/api/nonexistent")
        assert resp.status == 404

    async def test_404_deep_path(self):
        resp = await self.client.get("/some/deep/path")
        assert resp.status == 404

    async def test_404_nonexistent_session(self):
        resp = await self.client.get("/api/sessions/nonexistent-id-12345")
        assert resp.status == 404

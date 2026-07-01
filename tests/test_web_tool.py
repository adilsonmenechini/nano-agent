"""Tests for WebTool URL validation and dispatch."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch


from nanoagent.agent.tools.web_tool import WebTool, _validate_url


class TestWebTool:
    def test_name(self):
        assert WebTool().name == "web"

    def test_web_search_missing_query(self):
        assert "query is required" in WebTool().execute("web_search")

    def test_web_fetch_missing_url(self):
        assert "url is required" in WebTool().execute("web_fetch")

    def test_web_fetch_unknown_action(self):
        r = WebTool().execute("bad")
        assert "unknown action" in r
        assert "web_search" in r
        assert "web_fetch" in r


class TestWebToolWebSearch:
    def test_success(self):
        items = [
            {"title": "t1", "href": "https://a", "body": "b1"},
            {"title": "t2"},
        ]
        with patch("ddgs.DDGS") as MockDDGS:
            ddgs = MagicMock()
            ddgs.text.return_value = iter(items)
            MockDDGS.return_value.__enter__ = MagicMock(return_value=ddgs)
            MockDDGS.return_value.__exit__ = MagicMock(return_value=False)
            result = WebTool().execute("web_search", query="hello", count=2)
            assert "t1" in result
            assert "t2" in result

    def test_no_results(self):
        with patch("ddgs.DDGS") as MockDDGS:
            ddgs = MagicMock()
            ddgs.text.return_value = iter([])
            MockDDGS.return_value.__enter__ = MagicMock(return_value=ddgs)
            MockDDGS.return_value.__exit__ = MagicMock(return_value=False)
            result = WebTool().execute("web_search", query="asdfqwerty_nonexistent")
            assert "No results" in result

    def test_search_http_query_routes_through_validation(self):
        with (
            patch("ddgs.DDGS", side_effect=RuntimeError("should not reach ddgs")),
            patch(
                "nanoagent.agent.tools.web_tool._validate_url",
                return_value=(False, "Blocked hostname: localhost"),
            ),
        ):
            r = WebTool().execute("web_search", query="http://localhost/x")
            assert "validation failed" in r.lower()


class TestWebToolWebFetch:
    def _make_resp(
        self,
        ctype="text/html",
        text="<html><body><p>hi</p></body></html>",
        url="https://example.com",
        json_body=None,
    ):
        resp = MagicMock()
        resp.headers = {"content-type": ctype}
        resp.text = text
        resp.url = url
        resp.status_code = 200
        resp.raise_for_status = MagicMock()
        resp.json.return_value = json_body or {}
        return resp

    def _patch_httpx(self, resp):
        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        return patch("httpx.AsyncClient", return_value=mock_client)

    def test_fetch_invalid_scheme(self):
        r = WebTool().execute("web_fetch", url="ftp://host/x")
        assert "validation failed" in r.lower()

    def test_fetch_json_response(self):
        payload = {"key": "val", "n": 42}
        resp = self._make_resp(ctype="application/json", json_body=payload)
        with (
            self._patch_httpx(resp),
            patch(
                "nanoagent.agent.tools.web_tool._validate_url", return_value=(True, "")
            ),
        ):
            result = WebTool().execute("web_fetch", url="https://api.example.com/d")
            data = __import__("json").loads(result)
            assert data["status"] == 200

    def test_fetch_plain_text_response(self):
        resp = self._make_resp(ctype="text/plain", text="plain text here")
        with (
            self._patch_httpx(resp),
            patch(
                "nanoagent.agent.tools.web_tool._validate_url", return_value=(True, "")
            ),
        ):
            result = WebTool().execute("web_fetch", url="https://example.com/x")
            data = __import__("json").loads(result)
            assert data["status"] == 200

    def test_fetch_truncation_applied(self):
        big = "x" * 20000
        resp = self._make_resp(text=f"<html><body><p>{big}</p></body></html>")
        # readability.Document is imported inside _web_fetch; patch at readability.Document
        fake_doc = MagicMock()
        fake_doc.summary.return_value = big
        fake_doc.title.return_value = None
        with (
            self._patch_httpx(resp),
            patch(
                "nanoagent.agent.tools.web_tool._validate_url", return_value=(True, "")
            ),
            patch("readability.Document", return_value=fake_doc),
        ):
            result = WebTool().execute(
                "web_fetch", url="https://example.com/big", max_chars=100
            )
            data = __import__("json").loads(result)
            assert data["truncated"] is True
            assert len(data["text"]) <= 100


class TestValidateUrl:
    def test_valid_url_produces_tuple(self):
        ok, msg = _validate_url("https://example.com/page")
        assert isinstance(ok, bool)
        assert isinstance(msg, str)

    def test_invalid_scheme(self):
        ok, msg = _validate_url("ftp://host/x")
        assert ok is False
        assert "http" in msg.lower() or "scheme" in msg.lower()

    def test_localhost_blocked(self):
        ok, msg = _validate_url("http://localhost/x")
        assert ok is False
        assert "local" in msg.lower() or "blocked" in msg.lower()

    def test_127_blocked(self):
        ok, msg = _validate_url("http://127.0.0.1:8080/x")
        assert ok is False

    def test_empty_host(self):
        ok, msg = _validate_url("https://")
        assert ok is False
        assert "domain" in msg.lower()

    def test_link_local_169_blocked(self):
        ok, msg = _validate_url("http://169.254.169.254/latest/meta-data")
        assert ok is False

    def test_aws_metadata_blocked(self):
        for h in (
            "metadata.google.internal",
            "metadata.aws.internal",
            "metadata.azure.com",
        ):
            ok, msg = _validate_url(f"http://{h}/")
            assert ok is False

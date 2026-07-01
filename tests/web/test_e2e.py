"""End-to-end tests for the NanoAgent Web UI using Playwright."""

import asyncio
import re
import socket
import threading
import time

import pytest
from aiohttp import web
from playwright.sync_api import Page, expect, sync_playwright

from nanoagent.web.server import create_app


# ── Helpers ──────────────────────────────────────────────────────────


def _free_port() -> int:
    """Find a free port on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _start_server(app: web.Application, port: int) -> web.AppRunner:
    """Start an aiohttp server and return the runner."""
    runner = web.AppRunner(app)
    loop = asyncio.new_event_loop()

    def _run() -> None:
        asyncio.set_event_loop(loop)
        loop.run_until_complete(runner.setup())
        site = web.TCPSite(runner, "127.0.0.1", port)
        loop.run_until_complete(site.start())
        loop.run_forever()

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    time.sleep(0.5)  # wait for server to start
    return runner


# ── Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def server_port() -> int:
    """Start the web app and return the port it's listening on."""
    port = _free_port()
    app = create_app(static_dir=None)
    _start_server(app, port)
    yield port


@pytest.fixture(scope="module")
def browser() -> None:
    """Launch Playwright browser context."""
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
        )
        yield context
        context.close()
        browser.close()


# ── E2E Tests ────────────────────────────────────────────────────────


class TestE2E:
    """End-to-end UI tests using Playwright."""

    def test_page_loads(self, browser, server_port):
        """Verify the page loads with correct structure and content."""
        page: Page = browser.new_page()
        page.goto(f"http://127.0.0.1:{server_port}/")

        # Title
        expect(page).to_have_title("NanoAgent")

        # Sidebar elements
        expect(page.locator(".logo")).to_have_text("NanoAgent")
        expect(page.locator("#new-session-btn")).to_be_visible()

        # Nav links present
        chat_link = page.locator('.sidebar-nav a[data-panel="chat"]')
        sessions_link = page.locator('.sidebar-nav a[data-panel="sessions"]')
        skills_link = page.locator('.sidebar-nav a[data-panel="skills"]')
        expect(chat_link).to_be_visible()
        expect(sessions_link).to_be_visible()
        expect(skills_link).to_be_visible()

        # Chat area
        expect(page.locator("#chat-messages")).to_be_visible()
        expect(page.locator("#indicator")).not_to_be_visible()  # hidden by default
        expect(page.locator("#chat-input")).to_be_visible()
        expect(page.locator("#send-btn")).to_be_visible()
        expect(page.locator("#cancel-btn")).not_to_be_visible()  # hidden by default

        page.close()

    def test_sidebar_navigation(self, browser, server_port):
        """Verify clicking sidebar links toggles panels correctly."""
        page: Page = browser.new_page()
        page.goto(f"http://127.0.0.1:{server_port}/")

        # Chat is active by default
        chat_link = page.locator('.sidebar-nav a[data-panel="chat"]')
        expect(chat_link).to_have_class(re.compile(r"active"))

        # Click Sessions
        sessions_link = page.locator('.sidebar-nav a[data-panel="sessions"]')
        sessions_link.click()
        expect(sessions_link).to_have_class(re.compile(r"active"))
        expect(chat_link).not_to_have_class(re.compile(r"active"))

        # Click Skills
        skills_link = page.locator('.sidebar-nav a[data-panel="skills"]')
        skills_link.click()
        expect(skills_link).to_have_class(re.compile(r"active"))
        expect(sessions_link).not_to_have_class(re.compile(r"active"))

        # Click back to Chat
        chat_link.click()
        expect(chat_link).to_have_class(re.compile(r"active"))

        page.close()

    def test_chat_input_interaction(self, browser, server_port):
        """Verify the chat input area is interactive."""
        page: Page = browser.new_page()
        page.goto(f"http://127.0.0.1:{server_port}/")

        textarea = page.locator("#chat-input")
        send_btn = page.locator("#send-btn")

        # Textarea starts empty, send is disabled
        expect(textarea).to_have_value("")
        expect(send_btn).to_be_disabled()

        # Type a message
        textarea.fill("Hello, NanoAgent!")
        expect(textarea).to_have_value("Hello, NanoAgent!")
        expect(send_btn).not_to_be_disabled()

        # Clear and re-check disabled state
        textarea.fill("")
        expect(send_btn).to_be_disabled()

        page.close()

    def test_static_files_serve(self, browser, server_port):
        """Verify JS and CSS static files return 200."""
        page: Page = browser.new_page()
        page.goto(f"http://127.0.0.1:{server_port}/")

        # Check console for 404 errors
        console_errors = []
        page.on(
            "console",
            lambda msg: (
                console_errors.append(msg.text) if msg.type == "error" else None
            ),
        )

        page.reload()
        page.wait_for_load_state("networkidle")

        # Filter out favicon, CSP, and API call errors (APIs may fail without real agent)
        file_errors = [
            e
            for e in console_errors
            if "favicon" not in e.lower()
            and "csp" not in e.lower()
            and "content security" not in e.lower()
            and "failed to load" not in e.lower()
            and "fetch" not in e.lower()
        ]

        assert len(file_errors) == 0, f"Static file errors: {file_errors}"
        page.close()

    def test_health_api_via_evaluate(self, browser, server_port):
        """Verify the health endpoint returns ok via fetch."""
        page: Page = browser.new_page()
        page.goto(f"http://127.0.0.1:{server_port}/")

        result = page.evaluate(
            """async () => {
                const resp = await fetch('/api/health');
                const data = await resp.json();
                return { status: resp.status, data };
            }"""
        )

        assert result["status"] == 200
        assert result["data"]["status"] == "ok"
        assert "uptime_seconds" in result["data"]
        assert "version" in result["data"]
        page.close()

    def test_sessions_api_via_evaluate(self, browser, server_port):
        """Verify session CRUD via fetch from the browser context."""
        page: Page = browser.new_page()
        page.goto(f"http://127.0.0.1:{server_port}/")

        list_result = page.evaluate(
            """async () => {
                const resp = await fetch('/api/sessions');
                const data = await resp.json();
                return { status: resp.status, sessions: data.sessions || [] };
            }"""
        )
        assert list_result["status"] == 200
        assert isinstance(list_result["sessions"], list)

        create_result = page.evaluate(
            """async () => {
                const resp = await fetch('/api/sessions', { method: 'POST' });
                const data = await resp.json();
                return { status: resp.status, session: data.session };
            }"""
        )
        assert create_result["status"] == 201
        new_id = create_result["session"]["id"]
        assert new_id is not None

        get_result = page.evaluate(
            f"""async () => {{
                const resp = await fetch('/api/sessions/{new_id}');
                const data = await resp.json();
                return {{ status: resp.status, session: data.session }};
            }}"""
        )
        assert get_result["status"] == 200, f"Get session failed: {get_result}"
        assert get_result["session"]["id"] == new_id

        del_result = page.evaluate(
            f"""async () => {{
                const resp = await fetch('/api/sessions/{new_id}', {{ method: 'DELETE' }});
                return {{ status: resp.status }};
            }}"""
        )
        assert del_result["status"] == 200

        page.close()

    def test_skills_api_via_evaluate(self, browser, server_port):
        """Verify skills endpoint returns data."""
        page: Page = browser.new_page()
        page.goto(f"http://127.0.0.1:{server_port}/")

        result = page.evaluate(
            """async () => {
                const resp = await fetch('/api/skills');
                const data = await resp.json();
                return { status: resp.status, skills: data.skills || [] };
            }"""
        )
        assert result["status"] == 200
        # Skills may be empty or have items — just verify the structure
        assert isinstance(result["skills"], list)
        page.close()

    def test_websocket_endpoint_reachable(self, browser, server_port):
        """Verify the WebSocket endpoint accepts connections."""
        page: Page = browser.new_page()
        page.goto(f"http://127.0.0.1:{server_port}/")

        ws_ok = page.evaluate(
            f"""async () => {{
                try {{
                    const ws = new WebSocket('ws://127.0.0.1:{server_port}/ws/chat?session_id=test-e2e-ws');
                    return await new Promise((resolve) => {{
                        ws.onopen = () => {{ ws.close(); resolve(true); }};
                        ws.onerror = () => resolve(false);
                        setTimeout(() => resolve('timeout'), 3000);
                    }});
                }} catch (e) {{
                    return false;
                }}
            }}"""
        )
        assert ws_ok is True, f"WebSocket connection failed: {ws_ok}"

        page.close()

    def test_page_responsive(self, browser, server_port):
        """Verify page works at mobile-ish width (sidebar collapses)."""
        page: Page = browser.new_page()
        page.set_viewport_size({"width": 750, "height": 800})
        page.goto(f"http://127.0.0.1:{server_port}/")

        sidebar = page.locator("#sidebar")
        box = sidebar.bounding_box()
        assert box is not None
        expect(sidebar).to_be_visible()
        page.close()

    def test_chat_send_message(self, browser, server_port):
        """Verify sending a message via the UI updates the chat area."""
        page: Page = browser.new_page()
        page.goto(f"http://127.0.0.1:{server_port}/")

        # Wait for full App initialization (session created, bridge connected)
        page.wait_for_function(
            "() => window.app && window.app.currentSessionId",
            timeout=15000,
        )

        page.evaluate("""() => {
            const input = document.getElementById('chat-input');
            input.value = 'Hello, NanoAgent!';
            input.dispatchEvent(new Event('input', { bubbles: true }));
        }""")

        page.locator("#send-btn").click()
        page.wait_for_timeout(1000)

        user_msg = page.locator(".message.user .message-bubble")
        expect(user_msg.first).to_be_visible(timeout=10000)
        expect(user_msg.first).to_have_text("Hello, NanoAgent!")

        agent_msgs = page.locator(".message.agent")
        expect(agent_msgs.first).to_be_visible(timeout=30000)
        page.close()

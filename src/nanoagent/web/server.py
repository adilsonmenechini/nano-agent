"""aiohttp web server for the NanoAgent Web UI.

Serves static frontend files and provides WebSocket/REST endpoints
for agent interaction, session management, and skill management.
"""

import time
from pathlib import Path

from aiohttp import web

from nanoagent.web.handlers import setup_routes
from nanoagent.web.keys import START_TIME, HOST, PORT


def create_app(
    static_dir: str | None = None,
    host: str = "0.0.0.0",
    port: int = 8080,
) -> web.Application:
    app = web.Application()

    if static_dir is None:
        static_dir = str(Path(__file__).resolve().parent.parent.parent.parent / "web-ui")

    static_path = Path(static_dir)
    if static_path.is_dir():
        index_path = str(static_path / "index.html")

        async def _index(request: web.Request) -> web.FileResponse:
            return web.FileResponse(index_path)

        app.router.add_get("/", _index)
        app.router.add_static("/", str(static_path), show_index=True)

    setup_routes(app)

    app[START_TIME] = time.time()
    app[HOST] = host
    app[PORT] = port

    return app


def run_server(app: web.Application, host: str | None = None, port: int | None = None) -> None:
    host = host or app.get(HOST, "0.0.0.0")
    port = port or app.get(PORT, 8080)
    web.run_app(app, host=host, port=port)


if __name__ == "__main__":
    app = create_app()
    run_server(app)

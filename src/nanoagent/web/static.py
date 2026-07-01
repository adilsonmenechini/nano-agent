"""Static file serving configuration for the NanoAgent web UI."""

from pathlib import Path


def get_webui_dir() -> Path:
    """Return the absolute path to the web-ui/ static directory."""
    return Path(__file__).resolve().parent.parent.parent.parent / "web-ui"


def get_default_index() -> str:
    """Return the path to the default index.html."""
    return str(get_webui_dir() / "index.html")

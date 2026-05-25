"""Web tools: web_search and web_fetch without LangChain dependencies."""

import html
import ipaddress
import json
import re
from typing import Literal
from urllib.parse import urlparse

import httpx
from .base import BaseTool

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_7_2) AppleWebKit/537.36"
MAX_REDIRECTS = 5

PRIVATE_IP_RANGES = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]

BLOCKED_HOSTNAMES = {
    "localhost",
    "127.0.0.1",
    "::1",
    "169.254.169.254",
    "metadata.google.internal",
    "metadata.azure.com",
    "metadata.aws.internal",
    "kubernetes.default.svc",
}


def _error_response(tool: str, error: str, query: str = "") -> str:
    """Return a structured error response the agent can reason about."""
    return json.dumps(
        {
            "error": True,
            "tool": tool,
            "message": error,
            "query": query,
            "suggestion": "Try a different search query or check your network connection",
        }
    )


def _strip_tags(text: str) -> str:
    """Remove HTML tags and decode entities."""
    text = re.sub(r"<script[\s\S]*?</script>", "", text, flags=re.I)
    text = re.sub(r"<style[\s\S]*?</style>", "", text, flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)
    return html.unescape(text).strip()


def _normalize(text: str) -> str:
    """Normalize whitespace."""
    text = re.sub(r"[ \t]+", " ", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def _is_private_ip(ip: str) -> bool:
    """Check if IP address is in a private range."""
    try:
        ip_obj = ipaddress.ip_address(ip)
        for network in PRIVATE_IP_RANGES:
            if ip_obj in network:
                return True
        return False
    except ValueError:
        return False


def _validate_url(url: str) -> tuple[bool, str]:
    """Validate URL with SSRF protection."""
    try:
        p = urlparse(url)

        if p.scheme not in ("http", "https"):
            return False, f"Only http/https allowed, got '{p.scheme or 'none'}'"

        hostname = p.hostname.lower() if p.hostname else ""
        if not hostname:
            return False, "Missing domain"

        if hostname in BLOCKED_HOSTNAMES:
            return False, f"Blocked hostname: {hostname}"

        import socket

        try:
            ip = socket.gethostbyname(hostname)
            if _is_private_ip(ip):
                return False, f"Private IP blocked: {ip}"
        except socket.gaierror:
            return False, f"Could not resolve hostname: {hostname}"

        return True, ""
    except Exception as e:
        return False, str(e)


def _to_markdown(html: str) -> str:
    """Convert HTML to markdown."""
    text = re.sub(
        r'<a\s+[^>]*href=["\']([^"\']+)["\'][^>]*>([\s\S]*?)</a>',
        lambda m: f"[{_strip_tags(m[2])}]({m[1]})",
        html,
        flags=re.I,
    )
    text = re.sub(
        r"<h([1-6])[^>]*>([\s\S]*?)</h\1>",
        lambda m: f"\n{'#' * int(m[1])} {_strip_tags(m[2])}\n",
        text,
        flags=re.I,
    )
    text = re.sub(
        r"<li[^>]*>([\s\S]*?)</li>",
        lambda m: f"\n- {_strip_tags(m[1])}",
        text,
        flags=re.I,
    )
    text = re.sub(r"</(p|div|section|article)>", "\n\n", text, flags=re.I)
    text = re.sub(r"<(br|hr)\s*/?>", "\n", text, flags=re.I)
    return _normalize(_strip_tags(text))


class WebTool(BaseTool):
    def __init__(self):
        super().__init__(
            name="web",
            description="Web search and fetch capabilities with security hardening",
        )

    def execute(
        self,
        action: str,
        query: str = None,
        url: str = None,
        count: int = 5,
        extract_mode: Literal["markdown", "text"] = "markdown",
        max_chars: int = 50000,
    ) -> str:
        """
        Perform web actions.
        Actions: web_search, web_fetch
        For web_search: query is required, count is optional
        For web_fetch: url is required, extract_mode and max_chars are optional
        """
        if action == "web_search":
            if not query:
                return "Error: query is required for web_search action"
            return self._web_search(query, count)
        elif action == "web_fetch":
            if not url:
                return "Error: url is required for web_fetch action"
            return self._web_fetch(url, extract_mode, max_chars)
        else:
            return f"Error: unknown action '{action}'. Valid actions: web_search, web_fetch"

    def _web_search(self, query: str, count: int = 5) -> str:
        """Search the web using DuckDuckGo."""
        if query.startswith(("http://", "https://")):
            is_valid, error_msg = _validate_url(query)
            if not is_valid:
                return f"Error: URL validation failed for search query: {error_msg}"

        max_retries = 3
        for attempt in range(max_retries):
            try:
                from ddgs import DDGS
                import time

                n = min(max(count, 1), 10)
                results = []
                with DDGS() as ddgs_client:
                    ddgs_gen = ddgs_client.text(query, max_results=n)
                    for r in ddgs_gen:
                        results.append(r)

                if not results:
                    return f"No results for: {query}"

                lines = [f"Results for: {query}\n"]
                for i, item in enumerate(results, 1):
                    lines.append(
                        f"{i}. {item.get('title', '')}\n   {item.get('href', '')}"
                    )
                    if body := item.get("body"):
                        lines.append(f"   {body}")
                return "\n".join(lines)
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(1 * (attempt + 1))
                    continue
                return _error_response("web_search", str(e), query)
        return "Search completed"

    def _web_fetch(
        self,
        url: str,
        extract_mode: Literal["markdown", "text"] = "markdown",
        max_chars: int = 50000,
    ) -> str:
        """Fetch and extract content from a URL using Readability."""
        is_valid, error_msg = _validate_url(url)
        if not is_valid:
            return json.dumps(
                {"error": f"URL validation failed: {error_msg}", "url": url}
            )

        try:
            import asyncio

            async def _fetch():
                async with httpx.AsyncClient(
                    follow_redirects=True, max_redirects=MAX_REDIRECTS, timeout=30.0
                ) as client:
                    r = await client.get(url, headers={"User-Agent": USER_AGENT})
                    r.raise_for_status()
                    return r

            r = asyncio.run(_fetch())

            ctype = r.headers.get("content-type", "")

            if "application/json" in ctype:
                text, extractor = json.dumps(r.json(), indent=2), "json"
            elif "text/html" in ctype or r.text[:256].lower().startswith(
                ("<!doctype", "<html")
            ):
                from readability import Document

                doc = Document(r.text)
                content = (
                    _to_markdown(doc.summary())
                    if extract_mode == "markdown"
                    else _strip_tags(doc.summary())
                )
                text = f"# {doc.title()}\n\n{content}" if doc.title() else content
                extractor = "readability"
            else:
                text, extractor = r.text, "raw"

            truncated = len(text) > max_chars
            if truncated:
                text = text[:max_chars]

            return json.dumps(
                {
                    "url": url,
                    "finalUrl": str(r.url),
                    "status": r.status_code,
                    "extractor": extractor,
                    "truncated": truncated,
                    "length": len(text),
                    "text": text,
                }
            )
        except Exception as e:
            return _error_response("web_fetch", str(e), url)

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from nanoagent.tool import Tool

try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class MCPServerConfig:
    name: str
    command: str
    args: Sequence[str] = ()
    env: dict[str, str] | None = None


def _make_mcp_tool(name: str, desc: str, input_schema: dict, server: MCPServerConfig) -> Tool:
    t = Tool.__new__(Tool)
    t.name = name
    t.description = desc
    t.parameters = input_schema
    t.fn = lambda **kw: _call_mcp_sync(name, kw, server)
    return t


def _call_mcp_sync(name: str, arguments: dict, server: MCPServerConfig) -> str:
    return asyncio.run(_call_mcp_async(name, arguments, server))


async def _call_mcp_async(name: str, arguments: dict, server: MCPServerConfig) -> str:
    params = StdioServerParameters(command=server.command, args=list(server.args), env=server.env)
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(name, arguments)
            if result.isError:
                return f"Error: {result.content[0].text if result.content else 'unknown error'}"
            parts = []
            for item in result.content:
                if hasattr(item, "text"):
                    parts.append(item.text)
                elif hasattr(item, "data"):
                    parts.append(str(item.data))
            return "\n".join(parts)


class MCPManager:

    def __init__(self):
        self.servers: dict[str, MCPServerConfig] = {}

    def add_server(self, config: MCPServerConfig) -> None:
        self.servers[config.name] = config

    def add_json(self, name: str, command: str, args: list[str] | None = None,
                 env: dict[str, str] | None = None) -> None:
        self.add_server(MCPServerConfig(name=name, command=command, args=args or [], env=env))

    def load_json_config(self, path: str) -> None:
        with open(path) as f:
            data = json.load(f)
        for name, cfg in data.get("mcpServers", {}).items():
            self.add_json(name, cfg["command"], cfg.get("args"), cfg.get("env"))

    def discover_tools(self) -> list[Tool]:
        if not MCP_AVAILABLE:
            logger.warning("MCP not available; install 'mcp' package")
            return []
        tools: list[Tool] = []
        for name, server in self.servers.items():
            try:
                server_tools = asyncio.run(self._list_tools(server))
                for st in server_tools:
                    tool_name = st.name
                    if not tool_name.startswith(f"mcp_{name}_"):
                        tool_name = f"mcp_{name}_{st.name}"
                    t = _make_mcp_tool(tool_name, st.description or "", st.inputSchema or {}, server)
                    tools.append(t)
            except Exception as e:
                logger.error("Failed to discover tools from MCP server '%s': %s", name, e)
        return tools

    async def _list_tools(self, server: MCPServerConfig) -> list[Any]:
        params = StdioServerParameters(command=server.command, args=list(server.args), env=server.env)
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.list_tools()
                return result.tools

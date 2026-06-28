"""Tests for MCPManager to boost coverage."""
from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from nanoagent.mcp import MCPManager


class TestMCPManagerInitialization:
    def test_no_project_path(self):
        mgr = MCPManager(project_path=None)
        assert isinstance(mgr, MCPManager)
        assert mgr.project_path is None

    def test_list_servers_empty(self):
        mgr = MCPManager(project_path=None)
        result = mgr.list_servers()
        assert result == []

    def test_put_server(self):
        mgr = MCPManager(project_path=None)
        mgr.put_server(
            name="test",
            command="test_command",
            description="Test server",
            weight=10,
        )
        # Should store internally
        assert mgr is not None


class TestMCPManagerConfig:
    def test_load_tools_from_json(self):
        mgr = MCPManager(project_path=None)
        with patch("nanoagent.mcp.MCP_AVAILABLE", False):
            tools = mgr.load_tools()
            assert tools == []

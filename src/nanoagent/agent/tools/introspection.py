from __future__ import annotations

from nanoagent.tool import tool
from nanoagent.introspection import HarnessAnalyzer
from nanoagent.config import AgentConfig


@tool
def harness_report() -> str:
    """Introspect the agent's own configuration, tools, permissions, and memory usage. Returns a detailed report. Use this when you want to understand your own capabilities or find optimization opportunities."""
    config = AgentConfig()
    analyzer = HarnessAnalyzer(config=config)
    return analyzer.report()

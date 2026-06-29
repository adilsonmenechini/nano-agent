from __future__ import annotations

from nanoagent.introspection import HarnessAnalyzer
from nanoagent.config import AgentConfig


def test_snapshot_collects_sections():
    analyzer = HarnessAnalyzer(config=AgentConfig())
    snap = analyzer.snapshot()
    assert "config" in snap
    assert "tools" in snap
    assert "permissions" in snap
    assert "memory_stats" in snap


def test_snapshot_includes_config_values():
    analyzer = HarnessAnalyzer(config=AgentConfig())
    snap = analyzer.snapshot()
    cfg = snap["config"]
    assert "default_provider" in cfg
    assert "max_tokens" in cfg
    assert "temperature" in cfg


def test_snapshot_no_registry():
    analyzer = HarnessAnalyzer(config=AgentConfig())
    snap = analyzer.snapshot()
    assert snap["tools"] == []


def test_analyze_returns_list():
    analyzer = HarnessAnalyzer(config=AgentConfig())
    recs = analyzer.analyze()
    assert isinstance(recs, list)


def test_report_returns_string():
    analyzer = HarnessAnalyzer(config=AgentConfig())
    report = analyzer.report()
    assert isinstance(report, str)
    assert "Harness Introspection Report" in report


def test_empty_registry_does_not_crash():
    analyzer = HarnessAnalyzer(config=AgentConfig(), tool_registry=None, permission_manager=None)
    snap = analyzer.snapshot()
    assert snap["tools"] == []
    assert snap["permissions"] == []


def test_report_no_tools_analyze():
    analyzer = HarnessAnalyzer(config=AgentConfig())
    snap = analyzer.snapshot()
    recs = analyzer.analyze(snap)
    assert isinstance(recs, list)

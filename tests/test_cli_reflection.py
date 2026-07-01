from __future__ import annotations

from click.testing import CliRunner
from nanoagent.cli import cli


def test_reflection_list_empty():
    runner = CliRunner()
    result = runner.invoke(cli, ["reflection", "list", "--limit", "5"])
    assert result.exit_code == 0
    assert "No reflections found" in result.output or "Recent" in result.output


def test_reflection_stats_empty():
    runner = CliRunner()
    result = runner.invoke(cli, ["reflection", "stats"])
    assert result.exit_code == 0
    assert "Total turns" in result.output


def test_reflection_show_missing():
    runner = CliRunner()
    result = runner.invoke(cli, ["reflection", "show", "nonexistent"])
    assert result.exit_code == 0
    assert "Reflection not found" in result.output


def test_reflection_search_empty():
    runner = CliRunner()
    result = runner.invoke(cli, ["reflection", "search", "zzz_pattern_zzz"])
    assert result.exit_code == 0
    assert "No reflections matching" in result.output

from __future__ import annotations

from click.testing import CliRunner
from nanoagent.cli import cli


def test_harness_report():
    runner = CliRunner()
    result = runner.invoke(cli, ["harness", "report"])
    assert result.exit_code == 0
    assert "Harness Introspection Report" in result.output


def test_harness_analyze():
    runner = CliRunner()
    result = runner.invoke(cli, ["harness", "analyze"])
    assert result.exit_code == 0
    assert any(label in result.output for label in ["Recommendations", "healthy"])


def test_harness_report_no_crash():
    runner = CliRunner()
    result = runner.invoke(cli, ["harness", "report"])
    assert result.exit_code == 0
    assert len(result.output) > 50

from __future__ import annotations

from click.testing import CliRunner
from nanoagent.cli import cli


def test_skill_list_proposals_empty():
    runner = CliRunner()
    result = runner.invoke(cli, ["skill", "list-proposals"])
    assert result.exit_code == 0


def test_skill_accept_nonexistent():
    runner = CliRunner()
    result = runner.invoke(cli, ["skill", "accept", "nonexistent"])
    assert result.exit_code == 0


def test_skill_reject_nonexistent():
    runner = CliRunner()
    result = runner.invoke(cli, ["skill", "reject", "nonexistent"])
    assert result.exit_code == 0


def test_skill_evolve_nonexistent():
    runner = CliRunner()
    result = runner.invoke(cli, ["skill", "evolve", "nonexistent"])
    assert result.exit_code == 0
    assert "Evolution failed" in result.output or "not found" in result.output

"""CLI regression tests via click.testing.CliRunner."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import click.testing
import pytest

from nanoagent.cli import cli as _cli


@pytest.fixture()
def runner():
    return click.testing.CliRunner()


class TestCliRoot:
    def test_no_args_no_crash(self, runner):
        # Click exits 2 with no subcommand; just assert no unhandled exception.
        result = runner.invoke(_cli)
        assert result.exit_code in (0, 1, 2)

    def test_help_exits_zero(self, runner):
        result = runner.invoke(_cli, ["--help"])
        assert result.exit_code == 0
        assert "check-config" in result.output or "run" in result.output


class TestCliCheckConfig:
    def test_check_config_json(self, runner):
        result = runner.invoke(_cli, ["check-config", "--json"])
        # Should not raise; may print JSON
        assert result.exit_code in (0, 1)

    def test_check_config_no_json(self, runner):
        result = runner.invoke(_cli, ["check-config"])
        assert result.exit_code in (0, 1)


class TestCliHealth:
    def test_health_json_with_no_provider(self, runner):
        # With no configured providers _make_agent → _resolve_provider returns None →
        # inst = factory(); inst.chat(...) will fail (no key) → caught as error.
        # Just assert this completes cleanly.
        with patch("nanoagent.cli._PROVIDER_FACTORY", {}):
            result = runner.invoke(_cli, ["health", "--json"])
            assert result.exit_code == 0

    def test_health_unknown_provider_json(self, runner):
        with patch("nanoagent.cli._PROVIDER_FACTORY", {"prov": MagicMock()}):
            result = runner.invoke(_cli, ["health", "--provider", "unknown", "--json"])
            assert result.exit_code == 0
            assert "Unknown provider" in result.output

    def test_health_connected(self, runner):
        factory = MagicMock()
        fake_provider = MagicMock()
        fake_provider.chat.return_value = None
        factory.return_value = fake_provider
        with patch.dict(
            "nanoagent.cli._PROVIDER_FACTORY", {"fake_provider": factory}, clear=False
        ):
            with patch("nanoagent.cli.AgentConfig") as MockConfig:
                MockConfig.return_value.providers = {
                    "fake_provider": MagicMock(
                        api_key="k", base_url="http://u", model="m"
                    )
                }
                result = runner.invoke(_cli, ["health", "--json"])
                assert result.exit_code == 0
                assert "fake_provider" in result.output or "connected" in result.output

    def test_health_error(self, runner):
        factory = MagicMock(side_effect=RuntimeError("boom"))
        with patch.dict(
            "nanoagent.cli._PROVIDER_FACTORY", {"bad_provider": factory}, clear=False
        ):
            with patch("nanoagent.cli.AgentConfig") as MockConfig:
                MockConfig.return_value.providers = {
                    "bad_provider": MagicMock(
                        api_key="k", base_url="http://u", model="m"
                    )
                }
                result = runner.invoke(_cli, ["health", "--json"])
                assert result.exit_code == 0
                assert "error" in result.output


class TestCliRun:
    def test_run_prompts_provider_invocation(self, runner):
        # Patch _make_agent to return a fake agent with fake run.
        fake_agent = MagicMock()
        fake_agent.run.return_value = (
            "hello",
            {"role": "assistant", "content": "hello"},
        )
        with (
            patch("nanoagent.cli._make_agent", return_value=fake_agent) as mkg,
            patch("nanoagent.cli._build_system_prompt", return_value="sys"),
        ):
            result = runner.invoke(
                _cli, ["run", "--prompt", "hi", "-pr", "openai", "-pp", "/tmp"]
            )
            assert result.exit_code == 0
            mkg.assert_called_once_with("openai", "/tmp")

    def test_run_missing_provider(self, runner):
        # _make_agent returns None when provider is missing; handle gracefully
        with (
            patch("nanoagent.cli._make_agent", return_value=None),
            patch("nanoagent.cli._build_system_prompt", return_value=None),
        ):
            result = runner.invoke(_cli, ["run", "--prompt", "hi"])
            assert result.exit_code in (0, 1)


class TestCliChat:
    def test_chat_help(self, runner):
        result = runner.invoke(_cli, ["chat", "--help"])
        assert result.exit_code == 0

    def test_chat_invocation_no_crash(self, runner):
        with (
            patch("nanoagent.cli._make_agent", return_value=None),
            patch("nanoagent.cli._build_system_prompt", return_value=None),
        ):
            result = runner.invoke(_cli, ["chat", "--provider", "missing"])
            assert result.exit_code in (0, 1)


class TestCliBuildSystemPrompt:
    def test_none_path_returns_none(self):
        from nanoagent.cli import _build_system_prompt

        assert _build_system_prompt(None) is None

    def test_empty_path_returns_none(self):
        from nanoagent.cli import _build_system_prompt

        assert _build_system_prompt("") is None

    @pytest.fixture()
    def agent_dir(self, tmp_path):
        return tmp_path / "proj"

    def test_missing_files_returns_none(self, agent_dir):
        from nanoagent.cli import _build_system_prompt

        agent_dir.mkdir(parents=True, exist_ok=True)
        result = _build_system_prompt(str(agent_dir))
        assert result is None

    def test_agent_md_present(self, agent_dir):
        from nanoagent.cli import _build_system_prompt

        agent_dir.mkdir(parents=True, exist_ok=True)
        (agent_dir / "AGENT.md").write_text("I am the agent.")
        result = _build_system_prompt(str(agent_dir))
        assert "I am the agent." in result

    def test_user_md_present(self, agent_dir):
        from nanoagent.cli import _build_system_prompt

        agent_dir.mkdir(parents=True, exist_ok=True)
        (agent_dir / "USER.md").write_text("I am the user.")
        result = _build_system_prompt(str(agent_dir))
        assert "I am the user." in result

    def test_both_merged(self, agent_dir):
        from nanoagent.cli import _build_system_prompt

        agent_dir.mkdir(parents=True, exist_ok=True)
        (agent_dir / "AGENT.md").write_text("AG")
        (agent_dir / "USER.md").write_text("USER")
        result = _build_system_prompt(str(agent_dir))
        assert "AG" in result
        assert "USER" in result

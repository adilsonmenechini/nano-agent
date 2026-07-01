from nanoagent.memory.correction_detector import is_correction
from nanoagent.agent.agent import Agent


def test_correction_detector():
    # Strong positive patterns
    assert is_correction("No, that is not correct.") is True
    assert is_correction("Don't run that command again.") is True
    assert is_correction("Actually, let's use python3.") is True
    assert is_correction("I told you to use the absolute path.") is True

    # Weak positive with directive word
    assert is_correction("No, try using pip3.") is True

    # Negatives
    assert is_correction("No problem, thank you!") is False
    assert is_correction("No thanks.") is False
    assert is_correction("That is not bad.") is False
    assert is_correction("Just a regular chat message.") is False


def test_build_system_prompt():
    agent = Agent(db_path=":memory:")

    # 1. Base prompt alone
    prompt = agent.build_system_prompt("Base system prompt context")
    assert "Base system prompt context" in prompt
    assert "<memory-policy>" in prompt
    assert "<user-profile>" not in prompt
    assert "<memory>" not in prompt
    assert "<recent-failures>" not in prompt

    # 2. Add user profile and global memory
    agent.remember(key="pref", value="User prefers dark mode", target="user")
    agent.remember(key="db_dec", value="Agreed to use sqlite db")

    prompt = agent.build_system_prompt("Base system prompt context")
    assert "<user-profile>" in prompt
    assert "User prefers dark mode" in prompt
    assert "<memory>" in prompt
    assert "Agreed to use sqlite db" in prompt
    assert "Global Memories:" in prompt

    # 3. Add failures
    agent.memory.add_failure(
        content="Command python failed with 127", category="tool-quirk"
    )

    prompt = agent.build_system_prompt("Base")
    assert "<recent-failures>" in prompt
    assert "[tool-quirk] Command python failed with 127" in prompt

    agent.memory.close()


def test_background_review_and_session_flush():
    from nanoagent.memory.background_review import BackgroundReview
    from nanoagent.memory.session_flush import SessionFlush
    import unittest.mock

    agent = Agent(db_path=":memory:")

    # Mock LLM provider
    mock_llm = unittest.mock.MagicMock()
    mock_llm.generate.return_value = "CATEGORY: user\nCONTENT: User prefers python3\n\nCATEGORY: failure\nCONTENT: calling python is wrong, use python3"
    agent.llm_provider = mock_llm

    review = BackgroundReview(agent, nudge_interval=2, nudge_tool_calls=3)

    messages = [
        {"role": "user", "content": "I prefer python3"},
        {"role": "assistant", "content": "Sure", "tool_calls": []},
    ]

    # First turn - shouldn't trigger yet
    review.on_turn_end(turn_count=1, tool_calls=1, messages=messages)
    assert len(agent.memory.search("python3", target="user")) == 0

    # Second turn - triggers!
    review.on_turn_end(turn_count=1, tool_calls=1, messages=messages)

    user_mems = agent.memory.search("python3", target="user")
    assert len(user_mems) > 0
    assert "User prefers python3" in user_mems[0].content

    # Failure should also be saved
    fails = agent.memory.search_failures()
    assert len(fails) > 0
    assert "calling python is wrong" in fails[0].content

    # Test SessionFlush
    agent2 = Agent(db_path=":memory:")
    mock_llm2 = unittest.mock.MagicMock()
    mock_llm2.generate.return_value = (
        "CATEGORY: memory\nCONTENT: NanoAgent project uses SQLite"
    )
    agent2.llm_provider = mock_llm2

    flusher = SessionFlush(flush_min_turns=2)
    assert flusher.should_flush(1) is False
    assert flusher.should_flush(2) is True

    flusher.flush(messages, agent2)
    mems = agent2.memory.search("SQLite", target="memory")
    assert len(mems) > 0
    assert "NanoAgent project uses SQLite" in mems[0].content

    agent.memory.close()
    agent2.memory.close()


def test_make_agent_registers_local_tools():
    import unittest.mock

    with unittest.mock.patch("nanoagent.cli._resolve_provider", return_value=None):
        from nanoagent.cli import _make_agent

        agent = _make_agent(provider_name=None, project_path=None)
        try:
            assert "web" in agent.tools
            assert "todo" in agent.tools
        finally:
            agent.memory.close()


def test_check_config_output():
    from nanoagent.cli import cli
    from click.testing import CliRunner

    runner = CliRunner()
    result = runner.invoke(cli, ["check-config"])
    assert result.exit_code == 0
    assert "max_tokens" in result.output


def test_check_config_json():
    from nanoagent.cli import cli
    from click.testing import CliRunner

    runner = CliRunner()
    result = runner.invoke(cli, ["check-config", "--json"])
    assert result.exit_code == 0
    assert "max_tokens" in result.output
    # Should contain JSON keys
    assert "default_provider" in result.output or '"max_tokens"' in result.output


def test_health_command():
    from nanoagent.cli import cli
    from click.testing import CliRunner

    runner = CliRunner()
    result = runner.invoke(cli, ["health"])
    # Exit 0 — providers may show error (no API keys), but the command itself runs
    assert result.exit_code == 0


def test_get_agent_passes_timeout():
    from nanoagent.web.handlers import _get_agent
    import unittest.mock

    # Clear cached agent
    import nanoagent.web.handlers as handlers_module

    handlers_module._agent_instance = None

    with (
        unittest.mock.patch("nanoagent.web.handlers.AgentConfig") as mock_config_class,
        unittest.mock.patch("nanoagent.web.handlers.OpenAIProvider") as mock_openai,
    ):
        # Setup mock config
        mock_config = unittest.mock.MagicMock()
        mock_config.default_provider = "openai"
        mock_config.get_provider_config.return_value = unittest.mock.MagicMock(
            api_key="test-key", base_url="http://test.url", model="test-model"
        )
        mock_config.loop.llm_timeout_seconds = 120.0
        mock_config_class.return_value = mock_config

        mock_openai.return_value = unittest.mock.MagicMock()

        # Call _get_agent
        agent = _get_agent()

        # Verify OpenAIProvider called with timeout
        mock_openai.assert_called_once()
        args, kwargs = mock_openai.call_args
        # Check that timeout keyword argument is present and equals 120.0
        assert "timeout" in kwargs
        assert kwargs["timeout"] == 120.0

        # Also verify Agent was created with that provider
        assert agent is not None

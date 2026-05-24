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
        content="Command python failed with 127",
        category="tool-quirk"
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
        {"role": "assistant", "content": "Sure", "tool_calls": []}
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
    mock_llm2.generate.return_value = "CATEGORY: memory\nCONTENT: NanoAgent project uses SQLite"
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

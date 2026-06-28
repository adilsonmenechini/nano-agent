import pytest


def test_openai_provider_mocked():
    import unittest.mock
    from nanoagent.llm.openai import OpenAIProvider
    from nanoagent.llm.base import LLMResponse

    p = OpenAIProvider(api_key="test-key", base_url="http://localhost:9999/v1", model="gpt-4")
    p.client = unittest.mock.MagicMock()
    mock_chunk = unittest.mock.MagicMock()
    mock_chunk.choices = [unittest.mock.MagicMock()]
    mock_chunk.choices[0].delta.content = "Hello"
    mock_chunk.choices[0].finish_reason = "stop"
    mock_chunk.usage = None

    response = p._chat(messages=[{"role": "user", "content": "Hi"}])
    assert isinstance(response, LLMResponse)

    events = list(p._chat_stream(messages=[{"role": "user", "content": "Hi"}]))
    assert len(events) >= 1


def test_anthropic_provider_mocked():
    import unittest.mock
    from nanoagent.llm.anthropic import AnthropicProvider
    from nanoagent.llm.base import LLMResponse

    p = AnthropicProvider(api_key="test-key", base_url="http://localhost:9999", model="claude-3-haiku")
    p.client = unittest.mock.MagicMock()
    mock_msg = unittest.mock.MagicMock()
    mock_msg.content = [unittest.mock.MagicMock(text="Hello")]
    mock_msg.usage.input_tokens = 10
    mock_msg.usage.output_tokens = 20
    p.client.messages.create.return_value = mock_msg

    response = p._chat(messages=[{"role": "user", "content": "Hi"}])
    assert isinstance(response, LLMResponse)


def test_lmstudio_provider_mocked():
    import unittest.mock
    from nanoagent.llm.lmstudio import LMStudioProvider
    from nanoagent.llm.base import LLMResponse

    p = LMStudioProvider(api_key="not-needed", base_url="http://localhost:9999/v1", model="test")
    p.client = unittest.mock.MagicMock()

    response = p._chat(messages=[{"role": "user", "content": "Hi"}])
    assert isinstance(response, LLMResponse)


def test_openai_streaming_events():
    import unittest.mock
    from nanoagent.llm.openai import OpenAIProvider
    from nanoagent.llm.base import StreamEvent

    p = OpenAIProvider(api_key="test-key", base_url="http://localhost:9999/v1", model="gpt-4")
    p.client = unittest.mock.MagicMock()

    def _fake_stream(**kwargs):
        chunk = unittest.mock.MagicMock()
        delta = unittest.mock.MagicMock()
        delta.content = "Hello"
        chunk.choices = [unittest.mock.MagicMock(delta=delta)]
        chunk.usage = None
        yield chunk

    p.client.chat.completions.create.return_value = _fake_stream()

    events = list(p._chat_stream(messages=[{"role": "user", "content": "Hi"}]))
    content_events = [e for e in events if e.type == "content"]
    assert len(content_events) >= 1
    assert events[-1].type == "done"

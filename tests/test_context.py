"""Tests for token counting, context truncation, and memory selection."""

from nanoagent.agent.context import (
    _estimate_tokens,
    count_messages_tokens,
    count_tokens,
    select_top_memories,
    set_tokenizer,
    truncate_messages,
)


class TestCountTokens:
    def test_short_text(self):
        assert count_tokens("hello") > 0

    def test_empty_text(self):
        # tiktoken returns 0 for empty, fallback estimate returns 1
        result = count_tokens("")
        assert result == 0 or result == 1

    def test_long_text(self):
        tokens = count_tokens("hello world " * 100)
        assert tokens > 50

    def test_estimate_tokens(self):
        assert _estimate_tokens("hello world") == 3  # 11 // 4 + 1

    def test_empty_estimate(self):
        assert _estimate_tokens("") == 1

    def test_unknown_provider(self):
        tokens = count_tokens("test", provider="unknown")
        assert tokens > 0

    def test_set_tokenizer(self):
        set_tokenizer("test_provider", "cl100k_base")
        # After setting, should be able to use it
        tokens = count_tokens("hello", "test_provider")
        assert tokens > 0


class TestCountMessagesTokens:
    def test_single_message(self):
        msgs = [{"role": "user", "content": "hello"}]
        assert count_messages_tokens(msgs) > 0

    def test_multiple_messages(self):
        msgs = [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "world"},
        ]
        total = count_messages_tokens(msgs)
        assert total > 1

    def test_messages_with_lists(self):
        msgs = [
            {"role": "assistant", "content": [{"text": "hello"}, {"text": "world"}]}
        ]
        assert count_messages_tokens(msgs) > 1

    def test_messages_with_non_string_values(self):
        msgs = [{"role": "user", "content": "hello", "extra": 42, "flag": True}]
        assert count_messages_tokens(msgs) > 0


class TestTruncateMessages:
    def test_within_limit(self):
        msgs = [{"role": "system", "content": "sys"}, {"role": "user", "content": "hi"}]
        result = truncate_messages(msgs, max_tokens=10000)
        assert len(result) == 2

    def test_truncates_to_fit(self):
        long_msg = {"role": "user", "content": "hello " * 500}
        msgs = [{"role": "system", "content": "keep me"}, long_msg]
        result = truncate_messages(msgs, max_tokens=50)
        assert len(result) < len(msgs) or all(m.get("role") == "system" for m in result)

    def test_preserves_system_message(self):
        sys_msg = {"role": "system", "content": "important"}
        msgs = [
            sys_msg,
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "world"},
        ]
        result = truncate_messages(msgs, max_tokens=1)
        assert any(m.get("role") == "system" for m in result)


class TestSelectTopMemories:
    def test_empty_entries(self):
        result = select_top_memories([], max_tokens=100)
        assert result == []

    def test_single_entry(self):
        result = select_top_memories(["hello world"], max_tokens=100)
        assert result == ["hello world"]

    def test_selects_by_importance(self):
        entries = ["low importance", "high importance", "medium importance"]
        scores = [0.1, 0.9, 0.5]
        result = select_top_memories(entries, max_tokens=1000, importance_scores=scores)
        assert result[0] == "high importance"

    def test_truncates_by_token_budget(self):
        entries = ["a " * 50, "b " * 50, "c " * 50]
        result = select_top_memories(entries, max_tokens=30)
        assert len(result) < len(entries)

    def test_default_importance(self):
        entries = ["first", "second", "third"]
        result = select_top_memories(entries, max_tokens=1000)
        assert len(result) == 3

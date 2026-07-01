from __future__ import annotations

import pytest
from nanoagent.memory.sqlite_memory_store import SQLiteMemoryStore
from nanoagent.learning.reflector import Reflector


@pytest.fixture
def store():
    return SQLiteMemoryStore(":memory:")


@pytest.fixture
def reflector(store):
    return Reflector(store)


def test_reflect_creates_record(reflector):
    result = reflector.reflect(
        turn_id="test-1",
        task_description="list files",
        tool_calls=[{"name": "run_shell", "arguments": {"cmd": "ls"}}],
        steps_taken=1,
        outcome="success",
        duration_ms=100,
    )
    assert result is not None
    assert result["turn_id"] == "test-1"
    assert result["task_description"] == "list files"
    assert result["outcome"] == "success"


def test_get_recent_returns_ordered(reflector):
    reflector.reflect(turn_id="t1", task_description="task 1", duration_ms=10)
    reflector.reflect(turn_id="t2", task_description="task 2", duration_ms=20)
    records = reflector.get_recent(limit=10)
    assert len(records) == 2
    assert records[0]["turn_id"] == "t2"


def test_get_by_turn_id(reflector):
    reflector.reflect(turn_id="find-me", task_description="find this", duration_ms=5)
    record = reflector.get_by_turn_id("find-me")
    assert record is not None
    assert record["task_description"] == "find this"


def test_get_by_turn_id_missing(reflector):
    record = reflector.get_by_turn_id("nonexistent")
    assert record is None


def test_search_matches_keyword(reflector):
    reflector.reflect(
        turn_id="t1", task_description="list python files", duration_ms=10
    )
    reflector.reflect(turn_id="t2", task_description="count lines", duration_ms=20)
    results = reflector.search("python", limit=10)
    assert len(results) == 1
    assert results[0]["turn_id"] == "t1"


def test_get_stats_aggregates(reflector):
    reflector.reflect(turn_id="t1", outcome="success", duration_ms=100)
    reflector.reflect(turn_id="t2", outcome="success", duration_ms=200)
    reflector.reflect(turn_id="t3", outcome="failure", duration_ms=50)
    stats = reflector.get_stats()
    assert stats["total"] == 3
    assert stats["success_count"] == 2
    assert stats["failure_count"] == 1
    assert stats["error_count"] == 0
    assert stats["avg_duration_ms"] == pytest.approx(116.66, rel=0.1)


def test_get_stats_empty(reflector):
    stats = reflector.get_stats()
    assert stats["total"] == 0
    assert stats["avg_duration_ms"] == 0

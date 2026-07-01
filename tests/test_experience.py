from __future__ import annotations


from nanoagent.memory.sqlite_memory_store import SQLiteMemoryStore
from nanoagent.learning.experience import ExperienceEngine
from nanoagent.learning.reflector import Reflector


def test_analyze_reflections_creates_patterns():
    store = SQLiteMemoryStore(":memory:")
    reflector = Reflector(store)
    reflector.reflect(
        turn_id="t1",
        task_description="list files",
        tool_calls=[{"name": "run_shell"}],
        outcome="success",
    )
    reflector.reflect(
        turn_id="t2",
        task_description="list dirs",
        tool_calls=[{"name": "run_shell"}],
        outcome="success",
    )
    engine = ExperienceEngine(store)
    reflections = reflector.get_recent(limit=10)
    patterns = engine.analyze_reflections(reflections)
    assert len(patterns) >= 1
    assert patterns[0].success_count >= 1


def test_analyze_empty_returns_empty():
    store = SQLiteMemoryStore(":memory:")
    engine = ExperienceEngine(store)
    patterns = engine.analyze_reflections([])
    assert patterns == []


def test_match_returns_candidates():
    store = SQLiteMemoryStore(":memory:")
    reflector = Reflector(store)
    reflector.reflect(
        turn_id="t1",
        task_description="find python files",
        tool_calls=[{"name": "grep_file"}],
        outcome="success",
    )
    reflector.reflect(
        turn_id="t2",
        task_description="find python code",
        tool_calls=[{"name": "grep_file"}],
        outcome="success",
    )
    engine = ExperienceEngine(store)
    engine.analyze_reflections(reflector.get_recent(limit=10))
    matches = engine.match("python", limit=5)
    assert isinstance(matches, list)


def test_get_stats():
    store = SQLiteMemoryStore(":memory:")
    reflector = Reflector(store)
    reflector.reflect(turn_id="t1", tool_calls=[{"name": "ls"}], outcome="success")
    reflector.reflect(turn_id="t2", tool_calls=[{"name": "ls"}], outcome="success")
    engine = ExperienceEngine(store)
    engine.analyze_reflections(reflector.get_recent(limit=10))
    stats = engine.get_stats()
    assert "total_patterns" in stats

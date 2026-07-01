from __future__ import annotations

from nanoagent.memory.sqlite_memory_store import SQLiteMemoryStore
from nanoagent.learning.background import BackgroundLearner
from nanoagent.learning.reflector import Reflector


def test_start_if_due_disabled():
    learner = BackgroundLearner(None, enabled=False)
    assert learner.start_if_due(100) is False


def test_start_if_due_turns():
    learner = BackgroundLearner(None, enabled=True, cycle_interval_turns=5)
    assert learner.start_if_due(5) is True


def test_execute_cycle_returns_result():
    store = SQLiteMemoryStore(":memory:")
    reflector = Reflector(store)
    reflector.reflect(turn_id="t1", task_description="test", outcome="success")
    learner = BackgroundLearner(store, enabled=True)
    result = learner.execute_cycle()
    assert result.cycle_id is not None
    assert isinstance(result.duration_ms, int)


def test_execute_cycle_no_reflections():
    store = SQLiteMemoryStore(":memory:")
    learner = BackgroundLearner(store, enabled=True)
    result = learner.execute_cycle(reflections=[])
    assert result.patterns_found == 0


def test_get_last_cycle():
    learner = BackgroundLearner(None, enabled=True)
    assert learner.get_last_cycle() == 0.0

from __future__ import annotations

from nanoagent.memory.sqlite_memory_store import SQLiteMemoryStore


def test_reflection_records_table_exists():
    store = SQLiteMemoryStore(":memory:")
    cursor = store.conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='reflection_records'"
    )
    assert cursor.fetchone() is not None, "reflection_records table should exist"


def test_reflection_records_schema():
    store = SQLiteMemoryStore(":memory:")
    cursor = store.conn.execute("PRAGMA table_info(reflection_records)")
    columns = {row["name"]: row for row in cursor.fetchall()}
    assert "turn_id" in columns
    assert "task_description" in columns
    assert "tool_calls" in columns
    assert "steps_taken" in columns
    assert "errors" in columns
    assert "outcome" in columns
    assert "duration_ms" in columns
    assert "lessons" in columns
    assert "created" in columns


def test_experience_patterns_table_exists():
    store = SQLiteMemoryStore(":memory:")
    cursor = store.conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='experience_patterns'"
    )
    assert cursor.fetchone() is not None


def test_experience_patterns_schema():
    store = SQLiteMemoryStore(":memory:")
    cursor = store.conn.execute("PRAGMA table_info(experience_patterns)")
    columns = {row["name"]: row for row in cursor.fetchall()}
    assert "trigger_context" in columns
    assert "tool_sequence" in columns
    assert "recommended_approach" in columns
    assert "success_count" in columns
    assert "failure_count" in columns
    assert "sample_size" in columns
    assert "is_active" in columns


def test_evolution_log_table_exists():
    store = SQLiteMemoryStore(":memory:")
    cursor = store.conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='evolution_log'"
    )
    assert cursor.fetchone() is not None


def test_skills_table_has_status_column():
    store = SQLiteMemoryStore(":memory:")
    cursor = store.conn.execute("PRAGMA table_info(skills)")
    columns = {row["name"]: row for row in cursor.fetchall()}
    assert "status" in columns


def test_skills_status_defaults_to_active():
    store = SQLiteMemoryStore(":memory:")
    entry = store.add_skill("test-status", "Test", "test", "print('hello')")
    assert entry.status == "active"


def test_skills_status_loaded_correctly():
    store = SQLiteMemoryStore(":memory:")
    store.add_skill("test-status", "Test", "test", "print('hello')")
    loaded = store.get_skill("test-status")
    assert loaded is not None
    assert loaded.status == "active"


def test_list_skills_includes_status():
    store = SQLiteMemoryStore(":memory:")
    store.add_skill("s1", "S1", "desc", "code")
    skills = store.list_skills()
    assert len(skills) > 0
    for s in skills:
        assert hasattr(s, "status")
        assert s.status == "active"

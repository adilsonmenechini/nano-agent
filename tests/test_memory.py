import pytest
from nanoagent.memory import SQLiteMemoryStore


@pytest.fixture
def memory_store():
    # Use an in-memory database for testing
    store = SQLiteMemoryStore(db_path=":memory:")
    yield store
    store.close()


def test_add_and_recall(memory_store):
    # Add a memory entry
    memory_store.add(
        target="memory", scope="global", key="test_key", value="test_value"
    )
    # Recall the entry
    result = memory_store.get(target="memory", scope="global", key="test_key")
    assert result == "test_value"


def test_add_project_scope(memory_store):
    # Add a project-scoped memory entry
    memory_store.add(
        target="memory",
        scope="project",
        key="project_key",
        value="project_value",
        project_path="/fake/project",
    )
    # Recall the entry
    result = memory_store.get(
        target="memory",
        scope="project",
        key="project_key",
        project_path="/fake/project",
    )
    assert result == "project_value"


def test_replace(memory_store):
    # Add an entry
    memory_store.add(
        target="memory", scope="global", key="replace_key", value="old_value"
    )
    # Replace the entry
    memory_store.replace(
        target="memory", scope="global", old_text="old_value", new_text="new_value"
    )
    # Recall the entry
    result = memory_store.get(target="memory", scope="global", key="replace_key")
    assert result == "new_value"


def test_remove(memory_store):
    # Add an entry
    memory_store.add(
        target="memory", scope="global", key="remove_key", value="remove_value"
    )
    # Remove the entry
    memory_store.remove(target="memory", scope="global", key="remove_key")
    # Recall the entry (should return None)
    result = memory_store.get(target="memory", scope="global", key="remove_key")
    assert result is None


def test_search(memory_store):
    # Add a few entries
    memory_store.add(
        target="memory", scope="global", key="search_key1", value="Hello world"
    )
    memory_store.add(
        target="memory", scope="global", key="search_key2", value="Goodbye world"
    )
    # Search for 'Hello'
    results = memory_store.search(query="Hello", target="memory", limit=5)
    assert len(results) == 1
    assert results[0].content == "Hello world"
    # Search for 'world'
    results = memory_store.search(query="world", target="memory", limit=5)
    assert len(results) == 2


def test_char_count_and_formatting(memory_store):
    memory_store.add("memory", "global", "k1", "Short value")
    memory_store.add("memory", "global", "k2", "Another global entry")
    memory_store.add(
        "memory",
        "project",
        "k3",
        "Project specific entry",
        project_path="/fake/project",
    )

    assert memory_store.char_count("memory", "global") == len("Short value") + len(
        "Another global entry"
    )
    assert memory_store.char_count("memory", "project", "/fake/project") == len(
        "Project specific entry"
    )

    # Formatting system prompt
    formatted = memory_store.format_for_system_prompt("memory")
    assert "Short value" in formatted
    assert "Another global entry" in formatted
    assert "Project specific entry" not in formatted

    formatted_project = memory_store.format_project_block("memory", "/fake/project")
    assert "Project specific entry" in formatted_project
    assert "Short value" not in formatted_project


def test_char_limits_enforced(memory_store):
    # Enforce limit of 5000 chars by default, but let's test with a mock small limit if possible.
    # We can just change the limit in test or insert large value to trigger limit
    import unittest.mock

    with unittest.mock.patch.object(memory_store, "_char_limit", return_value=30):
        memory_store.add("memory", "global", "k1", "1234567890")
        memory_store.add("memory", "global", "k2", "1234567890")
        # Total is 20. Adding another 15 should exceed limit of 30.
        with pytest.raises(ValueError) as excinfo:
            memory_store.add("memory", "global", "k3", "123456789012345")
        assert "Memory full" in str(excinfo.value)

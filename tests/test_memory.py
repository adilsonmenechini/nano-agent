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
        target='memory',
        scope='global',
        key='test_key',
        value='test_value'
    )
    # Recall the entry
    result = memory_store.get(
        target='memory',
        scope='global',
        key='test_key'
    )
    assert result == 'test_value'

def test_add_project_scope(memory_store):
    # Add a project-scoped memory entry
    memory_store.add(
        target='memory',
        scope='project',
        key='project_key',
        value='project_value',
        project_path='/fake/project'
    )
    # Recall the entry
    result = memory_store.get(
        target='memory',
        scope='project',
        key='project_key',
        project_path='/fake/project'
    )
    assert result == 'project_value'

def test_replace(memory_store):
    # Add an entry
    memory_store.add(
        target='memory',
        scope='global',
        key='replace_key',
        value='old_value'
    )
    # Replace the entry
    memory_store.replace(
        target='memory',
        scope='global',
        old_text='old_value',
        new_text='new_value'
    )
    # Recall the entry
    result = memory_store.get(
        target='memory',
        scope='global',
        key='replace_key'
    )
    assert result == 'new_value'

def test_remove(memory_store):
    # Add an entry
    memory_store.add(
        target='memory',
        scope='global',
        key='remove_key',
        value='remove_value'
    )
    # Remove the entry
    memory_store.remove(
        target='memory',
        scope='global',
        key='remove_key'
    )
    # Recall the entry (should return None)
    result = memory_store.get(
        target='memory',
        scope='global',
        key='remove_key'
    )
    assert result is None

def test_search(memory_store):
    # Add a few entries
    memory_store.add(
        target='memory',
        scope='global',
        key='search_key1',
        value='Hello world'
    )
    memory_store.add(
        target='memory',
        scope='global',
        key='search_key2',
        value='Goodbye world'
    )
    # Search for 'Hello'
    results = memory_store.search(
        query='Hello',
        target='memory',
        limit=5
    )
    assert len(results) == 1
    assert results[0].content == 'Hello world'
    # Search for 'world'
    results = memory_store.search(
        query='world',
        target='memory',
        limit=5
    )
    assert len(results) == 2

def search_and_recall(self):
        # This test is just to show that we can chain operations
        pass
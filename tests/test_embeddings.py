

def test_compute_embedding():
    from nanoagent.memory.embeddings import compute_embedding

    emb = compute_embedding("Hello, world!")
    assert isinstance(emb, list)
    assert len(emb) > 0
    assert all(isinstance(v, float) for v in emb)


def test_cosine_similarity_same():
    from nanoagent.memory.embeddings import compute_embedding, cosine_similarity

    emb = compute_embedding("Same text for comparison")
    sim = cosine_similarity(emb, emb)
    assert abs(sim - 1.0) < 1e-6


def test_cosine_similarity_different():
    from nanoagent.memory.embeddings import compute_embedding, cosine_similarity

    emb1 = compute_embedding("Hello, world!")
    emb2 = compute_embedding("Goodbye, world!")
    sim = cosine_similarity(emb1, emb2)
    assert -1.0 <= sim <= 1.0


def test_embedding_stored_in_db():
    import tempfile
    import os
    from nanoagent.memory.sqlite_memory_store import SQLiteMemoryStore

    tmpdir = tempfile.mkdtemp()
    db_path = os.path.join(tmpdir, "test_emb.db")
    store = SQLiteMemoryStore(db_path=db_path)
    store.add(
        target="memory", scope="global", key="test", value="Semantic memory test entry"
    )
    cursor = store.conn.execute(
        "SELECT embedding FROM memories WHERE key = ?", ("test",)
    )
    row = cursor.fetchone()
    assert row is not None
    blob = row["embedding"]
    assert blob is not None
    assert len(blob) > 0
    store.close()
    import shutil

    shutil.rmtree(tmpdir)


def test_semantic_search_returns_results():
    import tempfile
    import os
    from nanoagent.memory.sqlite_memory_store import SQLiteMemoryStore

    tmpdir = tempfile.mkdtemp()
    db_path = os.path.join(tmpdir, "test_sem.db")
    store = SQLiteMemoryStore(db_path=db_path)
    store.add(
        target="memory",
        scope="global",
        key="k1",
        value="the team meeting was scheduled for next week",
    )
    store.add(target="memory", scope="global", key="k2", value="grocery shopping list")
    cursor = store.conn.execute(
        "SELECT COUNT(*) FROM memories WHERE embedding IS NOT NULL"
    )
    assert cursor.fetchone()[0] == 2
    fts_results = store.search("meeting", target="memory", limit=5)
    assert len(fts_results) >= 1, "FTS5 should find the meeting entry"
    results = store.semantic_search("team meeting scheduled", target="memory", limit=5)
    assert len(results) >= 1
    store.close()
    import shutil

    shutil.rmtree(tmpdir)


def test_importance_scoring():
    from nanoagent.memory.scorer import compute_importance
    import time

    now = time.time()
    score_fresh = compute_importance(access_count=5, last_access=now, now=now)
    score_stale = compute_importance(
        access_count=5, last_access=now - 86400 * 30, now=now
    )
    assert score_fresh > score_stale
    assert 0.0 <= score_fresh <= 1.0
    assert 0.0 <= score_stale <= 1.0


def test_importance_frequency():
    from nanoagent.memory.scorer import compute_importance
    import time

    now = time.time()
    score_high = compute_importance(access_count=50, last_access=now, now=now)
    score_low = compute_importance(access_count=1, last_access=now, now=now)
    assert score_high > score_low


def test_memory_decay():
    from nanoagent.memory.scorer import decay_importance

    decayed = decay_importance(1.0, elapsed=86400 * 7, half_life=86400 * 7)
    assert decayed < 1.0
    assert decayed > 0.0
    assert abs(decayed - 0.5) < 0.01


def test_select_top_memories():
    from nanoagent.agent.context import select_top_memories

    entries = [
        "short",
        "a bit longer text here",
        "the longest entry in the entire list of memories",
    ]
    scores = [0.1, 0.5, 0.9]
    selected = select_top_memories(entries, max_tokens=20, importance_scores=scores)
    assert len(selected) <= len(entries)
    assert all(t in selected for t in selected)

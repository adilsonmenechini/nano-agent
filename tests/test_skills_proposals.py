from nanoagent.memory.sqlite_memory_store import SQLiteMemoryStore
from nanoagent.skills.skill_storage import SkillStorage
from nanoagent.skills.loader import SkillsLoader
from nanoagent.learning import SkillStatus


def test_proposed_skill_not_loaded():
    store = SQLiteMemoryStore(":memory:")
    ss = SkillStorage(store=store)
    ss.add_skill("proposed-test", "Proposed", "should not load", '"""test"""\npass')
    store.conn.execute(
        "UPDATE skills SET status = ? WHERE slug = ?",
        (SkillStatus.PROPOSED.value, "proposed-test"),
    )
    store.conn.commit()
    db_skills = SkillsLoader.load_from_db(skill_storage=ss)
    assert "proposed-test" not in db_skills


def test_activate_proposed_skill():
    store = SQLiteMemoryStore(":memory:")
    ss = SkillStorage(store=store)
    ss.add_skill("activate-me", "Activate", "will be activated", '"""test"""\npass')
    store.conn.execute(
        "UPDATE skills SET status = ? WHERE slug = ?",
        (SkillStatus.PROPOSED.value, "activate-me"),
    )
    store.conn.commit()
    assert ss.activate_skill("activate-me") is True
    entry = ss.get_skill("activate-me")
    assert entry is not None
    assert entry.get("status") == SkillStatus.ACTIVE.value


def test_reject_proposed_skill():
    store = SQLiteMemoryStore(":memory:")
    ss = SkillStorage(store=store)
    ss.add_skill("reject-me", "Reject", "will be rejected", '"""test"""\npass')
    store.conn.execute(
        "UPDATE skills SET status = ? WHERE slug = ?",
        (SkillStatus.PROPOSED.value, "reject-me"),
    )
    store.conn.commit()
    assert ss.reject_skill("reject-me") is True
    entry = ss.get_skill("reject-me")
    assert entry is not None
    assert entry.get("status") == SkillStatus.REJECTED.value


def test_list_proposed_skills():
    store = SQLiteMemoryStore(":memory:")
    ss = SkillStorage(store=store)
    ss.add_skill("proposal-a", "A", "desc a", '"""test"""\npass')
    ss.add_skill("proposal-b", "B", "desc b", '"""test"""\npass')
    ss.add_skill("active-skill", "Active", "desc active", '"""test"""\npass')
    for slug in ("proposal-a", "proposal-b"):
        store.conn.execute(
            "UPDATE skills SET status = ? WHERE slug = ?",
            (SkillStatus.PROPOSED.value, slug),
        )
    store.conn.commit()
    proposed = ss.list_proposed_skills()
    slugs = [s.get("slug") for s in proposed]
    assert "proposal-a" in slugs
    assert "proposal-b" in slugs
    assert "active-skill" not in slugs


def test_activate_nonexistent_returns_false():
    store = SQLiteMemoryStore(":memory:")
    ss = SkillStorage(store=store)
    assert ss.activate_skill("nonexistent") is False


def test_reject_nonexistent_returns_false():
    store = SQLiteMemoryStore(":memory:")
    ss = SkillStorage(store=store)
    assert ss.reject_skill("nonexistent") is False


def test_loader_filters_non_active():
    store = SQLiteMemoryStore(":memory:")
    ss = SkillStorage(store=store)
    ss.add_skill("active-only", "Active", "should load", '"""test"""\npass')
    ss.add_skill("rejected-only", "Rejected", "should not load", '"""test"""\npass')
    store.conn.execute(
        "UPDATE skills SET status = ? WHERE slug = ?",
        (SkillStatus.REJECTED.value, "rejected-only"),
    )
    store.conn.commit()
    db_skills = SkillsLoader.load_from_db(skill_storage=ss)
    assert "active-only" in db_skills
    assert "rejected-only" not in db_skills

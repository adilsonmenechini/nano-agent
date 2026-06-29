from nanoagent.memory.sqlite_memory_store import SQLiteMemoryStore
from nanoagent.learning.reflector import Reflector
from nanoagent.learning.experience import ExperienceEngine
from nanoagent.learning.background import BackgroundLearner
from nanoagent.learning.synthesizer import Synthesizer
from nanoagent.skills.skill_storage import SkillStorage
from nanoagent.skills.loader import SkillsLoader


def test_background_learner_full_cycle():
    """BackgroundLearner executes a full cycle and produces results."""
    store = SQLiteMemoryStore(":memory:")
    reflector = Reflector(store=store)
    for i in range(3):
        reflector.reflect(
            turn_id=f"bg-turn-{i}",
            tool_calls=[{"name": "read_file"}, {"name": "run_shell"}],
        )

    learner = BackgroundLearner(
        store=store,
        enabled=True,
        cycle_interval_turns=1,
        max_cycle_duration_ms=5000,
    )
    result = learner.execute_cycle()
    assert result.turn_count > 0
    assert result.duration_ms >= 0
    assert result.patterns_found >= 0


def test_three_similar_tasks_creates_proposal():
    """3+ similar tasks → background cycle → skill proposal created."""
    store = SQLiteMemoryStore(":memory:")
    reflector = Reflector(store=store)
    engine = ExperienceEngine(store=store)

    for i in range(3):
        reflector.reflect(
            turn_id=f"sim-task-{i}",
            tool_calls=[{"name": "grep_file"}, {"name": "read_file"}, {"name": "run_shell"}],
        )

    reflections = reflector.get_recent(limit=10)
    assert len(reflections) >= 3

    patterns = engine.analyze_reflections(reflections)
    assert len(patterns) >= 1

    synth = Synthesizer(store=store)
    proposals_created = 0
    for pattern in patterns:
        if synth.create_proposal(pattern):
            proposals_created += 1
    assert proposals_created >= 1

    pending = synth.get_pending_proposals()
    assert len(pending) >= 1


def test_proposal_accept_makes_skill_available():
    """User accepts proposal, skill becomes available for loading."""
    store = SQLiteMemoryStore(":memory:")
    reflector = Reflector(store=store)
    engine = ExperienceEngine(store=store)
    synth = Synthesizer(store=store)
    ss = SkillStorage(store=store)

    for i in range(3):
        reflector.reflect(
            turn_id=f"accept-{i}",
            tool_calls=[{"name": "list_dir"}, {"name": "read_file"}],
        )

    reflections = reflector.get_recent(limit=10)
    patterns = engine.analyze_reflections(reflections)
    for pattern in patterns:
        synth.create_proposal(pattern)

    pending = synth.get_pending_proposals()
    assert len(pending) >= 1

    slug = pending[0]["slug"]
    assert ss.activate_skill(slug) is True

    db_skills = SkillsLoader.load_from_db(skill_storage=ss)
    assert slug in db_skills

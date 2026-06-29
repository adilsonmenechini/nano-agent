from __future__ import annotations

from nanoagent.memory.sqlite_memory_store import SQLiteMemoryStore
from nanoagent.learning import ExperiencePattern
from nanoagent.learning.synthesizer import Synthesizer


def test_create_proposal():
    store = SQLiteMemoryStore(":memory:")
    synth = Synthesizer(store)
    pattern = ExperiencePattern(
        tool_sequence=[{"name": "run_shell"}, {"name": "read_file"}],
        recommended_approach="List and read files",
        success_count=3,
        sample_size=3,
    )
    proposal = synth.create_proposal(pattern)
    assert proposal is not None
    assert proposal["status"] == "proposed"


def test_create_proposal_empty_tools():
    store = SQLiteMemoryStore(":memory:")
    synth = Synthesizer(store)
    pattern = ExperiencePattern()
    assert synth.create_proposal(pattern) is None


def test_create_proposal_dedup():
    store = SQLiteMemoryStore(":memory:")
    synth = Synthesizer(store)
    pattern = ExperiencePattern(
        tool_sequence=[{"name": "run_shell"}],
        recommended_approach="Run shell",
        success_count=3,
        sample_size=3,
    )
    first = synth.create_proposal(pattern)
    second = synth.create_proposal(pattern)
    assert first is not None
    assert second is None


def test_get_pending_proposals():
    store = SQLiteMemoryStore(":memory:")
    synth = Synthesizer(store)
    pattern = ExperiencePattern(
        tool_sequence=[{"name": "grep_file"}],
        recommended_approach="Search files",
        success_count=3,
        sample_size=3,
    )
    synth.create_proposal(pattern)
    pending = synth.get_pending_proposals()
    assert len(pending) >= 1
    assert pending[0]["status"] == "proposed"


def test_check_for_proposals_no_patterns():
    store = SQLiteMemoryStore(":memory:")
    synth = Synthesizer(store)
    proposals = synth.check_for_proposals()
    assert proposals == []

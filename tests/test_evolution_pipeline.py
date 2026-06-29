from __future__ import annotations

from nanoagent.memory.sqlite_memory_store import SQLiteMemoryStore
from nanoagent.evolution.pipeline import EvolutionPipeline
from nanoagent.evolution.config import EvolutionConfig


def test_evolve_unknown_skill():
    store = SQLiteMemoryStore(":memory:")
    pipeline = EvolutionPipeline(store=store)
    result = pipeline.evolve("nonexistent")
    assert result.get("success") is False
    assert "error" in result


def test_evolve_creates_report():
    store = SQLiteMemoryStore(":memory:")
    store.add_skill("test-skill", "Test", "a test skill", '"""Test skill"""\nprint("hello")')
    pipeline = EvolutionPipeline(store=store)
    result = pipeline.evolve("test-skill", iterations=2)
    assert result.get("success") is True
    assert "slug" in result
    assert result["slug"] == "test-skill"


def test_accept_evolution_nonexistent():
    store = SQLiteMemoryStore(":memory:")
    pipeline = EvolutionPipeline(store=store)
    assert pipeline.accept_evolution("nonexistent", "new code") is False


def test_accept_evolution_updates():
    store = SQLiteMemoryStore(":memory:")
    store.add_skill("evolve-me", "Evolve", "will be evolved", '"""Original"""\nprint("old")')
    pipeline = EvolutionPipeline(store=store)
    assert pipeline.accept_evolution("evolve-me", '"""Evolved"""\nprint("new")') is True
    updated = store.get_skill("evolve-me")
    assert updated is not None
    assert "new" in updated.code


def test_pipeline_with_config():
    store = SQLiteMemoryStore(":memory:")
    config = EvolutionConfig(iterations=3, eval_source="synthetic")
    pipeline = EvolutionPipeline(store=store, config=config)
    store.add_skill("cfg-test", "Config", "test", '"""test"""\npass')
    result = pipeline.evolve("cfg-test")
    assert result.get("success") is True

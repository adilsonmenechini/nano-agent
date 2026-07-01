from __future__ import annotations

from nanoagent.evolution.config import EvolutionConfig
from nanoagent.evolution.dataset import DatasetBuilder


def test_evolution_config_defaults():
    config = EvolutionConfig()
    assert config.model == "gpt-4.1-mini"
    assert config.iterations == 5
    assert config.eval_source == "synthetic"


def test_dataset_builder_no_store():
    builder = DatasetBuilder(store=None)
    data = builder.build_from_reflections()
    assert data == []


def test_dataset_builder_synthetic():
    builder = DatasetBuilder()
    data = builder.build_synthetic("file_tools", count=5)
    assert len(data) == 5
    assert all("task_description" in d for d in data)


def test_dataset_builder_synthetic_domain_matching():
    builder = DatasetBuilder()
    data = builder.build_synthetic("git_status", count=2)
    assert all(
        "git" in d.get("task_description", "").lower()
        or "commit" in d.get("task_description", "").lower()
        for d in data
    )

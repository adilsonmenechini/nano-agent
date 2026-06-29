from __future__ import annotations

from dataclasses import dataclass


@dataclass
class EvolutionConfig:
    model: str = "gpt-4.1-mini"
    iterations: int = 5
    eval_source: str = "synthetic"
    constraint_max_size: int = 50_000
    constraint_max_growth_pct: float = 50.0

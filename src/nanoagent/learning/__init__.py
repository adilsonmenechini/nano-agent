"""Learning subsystem — reflection, experience, background cycles, skill synthesis, and evolution."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class ReflectionOutcome(str, Enum):
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILURE = "failure"
    ERROR = "error"


class SkillStatus(str, Enum):
    ACTIVE = "active"
    PROPOSED = "proposed"
    REJECTED = "rejected"
    ARCHIVED = "archived"
    EVOLVING = "evolving"


@dataclass
class ReflectionRecord:
    turn_id: str
    task_description: str
    tool_calls: list[dict]
    steps_taken: int
    errors: list[dict]
    outcome: ReflectionOutcome
    duration_ms: int
    lessons: list[str] = field(default_factory=list)
    created: float = 0.0


@dataclass
class ExperiencePattern:
    id: int = 0
    trigger_context: dict = field(default_factory=dict)
    tool_sequence: list[dict] = field(default_factory=list)
    recommended_approach: str = ""
    success_count: int = 0
    failure_count: int = 0
    sample_size: int = 0
    first_observed: float = 0.0
    last_applied: float = 0.0
    is_active: bool = True


@dataclass
class CycleResult:
    cycle_id: str = ""
    turn_count: int = 0
    patterns_found: int = 0
    proposals_created: int = 0
    errors: list[str] = field(default_factory=list)
    duration_ms: int = 0


@dataclass
class EvolutionConfig:
    model: str = "gpt-4.1-mini"
    iterations: int = 5
    eval_source: str = "synthetic"
    constraint_max_size: int = 50_000
    constraint_max_growth_pct: float = 50.0


__all__ = [
    "ReflectionOutcome",
    "SkillStatus",
    "ReflectionRecord",
    "ExperiencePattern",
    "CycleResult",
    "EvolutionConfig",
]

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import final


@final
class Phase(enum.StrEnum):
    IDLE = "idle"
    RECEIVE = "receive"
    EXPLORE = "explore"
    EXECUTE = "execute"
    VERIFY = "verify"
    RESPOND = "respond"


@final
class StopReason(enum.StrEnum):
    done = "done"
    max_steps = "max_steps"
    error = "error"
    await_user = "await_user"
    blocked = "blocked"
    verification_failed = "verification_failed"


@final
class HealthLevel(enum.StrEnum):
    healthy = "healthy"
    degraded = "degraded"
    warning = "warning"
    critical = "critical"

    @staticmethod
    def from_score(score: float) -> HealthLevel:
        if score >= 0.80:
            return HealthLevel.healthy
        if score >= 0.50:
            return HealthLevel.degraded
        if score >= 0.20:
            return HealthLevel.warning
        return HealthLevel.critical


@final
class FaultCategory(enum.StrEnum):
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    CONTEXT_OVERFLOW = "context_overflow"
    TOOL_TIMEOUT = "tool_timeout"
    ERROR_SPIKE = "error_spike"
    OSCILLATION = "oscillation"
    DEADLOCK = "deadlock"


@final
class FaultSeverity(enum.StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@final
class HealingStrategyType(enum.StrEnum):
    retry = "retry"
    compact_context = "compact_context"
    reduce_scope = "reduce_scope"
    break_oscillation = "break_oscillation"
    request_confirmation = "request_confirmation"
    abort_turn = "abort_turn"


@final
class ProgressAction(enum.StrEnum):
    continue_ = "continue"
    switch_strategy = "switch_strategy"
    narrow_scope = "narrow_scope"
    request_confirmation = "request_confirmation"
    stop = "stop"


@dataclass(frozen=True)
class LoopConfig:
    max_steps_per_turn: int = 50
    tool_timeout_seconds: float = 30.0
    llm_timeout_seconds: float = 120.0
    stall_threshold: int = 5
    oscillation_window: int = 3
    compaction_threshold: float = 0.80
    diagnostics_enabled: bool = False
    health_window_size: int = 20

    def __post_init__(self) -> None:
        if not (1 <= self.max_steps_per_turn <= 500):
            msg = f"max_steps_per_turn must be 1-500, got {self.max_steps_per_turn}"
            raise ValueError(msg)
        if self.tool_timeout_seconds <= 0:
            msg = f"tool_timeout_seconds must be positive, got {self.tool_timeout_seconds}"
            raise ValueError(msg)
        if self.llm_timeout_seconds <= 0:
            msg = f"llm_timeout_seconds must be positive, got {self.llm_timeout_seconds}"
            raise ValueError(msg)
        if self.stall_threshold < 1:
            msg = f"stall_threshold must be >= 1, got {self.stall_threshold}"
            raise ValueError(msg)
        if self.oscillation_window < 2:
            msg = f"oscillation_window must be >= 2, got {self.oscillation_window}"
            raise ValueError(msg)
        if not (0.0 <= self.compaction_threshold <= 1.0):
            msg = f"compaction_threshold must be 0.0-1.0, got {self.compaction_threshold}"
            raise ValueError(msg)
        if self.health_window_size < 5:
            msg = f"health_window_size must be >= 5, got {self.health_window_size}"
            raise ValueError(msg)


DEFAULT_CONFIG = LoopConfig()


@dataclass
class FaultRecord:
    fault_type: FaultCategory
    severity: FaultSeverity
    timestamp: float
    metrics_snapshot: dict[str, float] = field(default_factory=dict)
    healing_action_id: str | None = None
    description: str = ""


@dataclass
class HealingAction:
    strategy_type: HealingStrategyType
    fault_type: FaultCategory
    execution_time: float = 0.0
    success: bool = False
    side_effects: list[str] = field(default_factory=list)
    effectiveness_tracking: dict[str, int] = field(default_factory=lambda: {
        "execution_count": 0,
        "success_count": 0,
    })

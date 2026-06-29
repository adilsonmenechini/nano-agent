from __future__ import annotations

from dataclasses import dataclass, field

from nanoagent.loop.constants import (
    FaultCategory,
    FaultRecord,
    HealingAction,
    HealingStrategyType,
)


@dataclass
class HealingStrategy:
    strategy_type: HealingStrategyType
    action: str
    expected_recovery_seconds: float
    success_probability: float
    applies_to: list[FaultCategory] = field(default_factory=list)


DEFAULT_STRATEGIES: list[HealingStrategy] = [
    HealingStrategy(
        strategy_type=HealingStrategyType.retry,
        action="Retry failed operation with backoff",
        expected_recovery_seconds=5.0,
        success_probability=0.70,
        applies_to=[FaultCategory.RESOURCE_EXHAUSTION, FaultCategory.TOOL_TIMEOUT],
    ),
    HealingStrategy(
        strategy_type=HealingStrategyType.compact_context,
        action="Summarize and trim context",
        expected_recovery_seconds=1.0,
        success_probability=0.90,
        applies_to=[FaultCategory.CONTEXT_OVERFLOW],
    ),
    HealingStrategy(
        strategy_type=HealingStrategyType.reduce_scope,
        action="Narrow prompt scope, retry",
        expected_recovery_seconds=3.0,
        success_probability=0.60,
        applies_to=[FaultCategory.ERROR_SPIKE, FaultCategory.DEADLOCK],
    ),
    HealingStrategy(
        strategy_type=HealingStrategyType.break_oscillation,
        action="Block repeated call, suggest alternative",
        expected_recovery_seconds=1.0,
        success_probability=0.85,
        applies_to=[FaultCategory.OSCILLATION],
    ),
    HealingStrategy(
        strategy_type=HealingStrategyType.request_confirmation,
        action="Ask user for guidance",
        expected_recovery_seconds=10.0,
        success_probability=0.50,
        applies_to=[FaultCategory.DEADLOCK, FaultCategory.ERROR_SPIKE],
    ),
    HealingStrategy(
        strategy_type=HealingStrategyType.abort_turn,
        action="Surface fault to user, abort turn",
        expected_recovery_seconds=0.5,
        success_probability=1.0,
        applies_to=[],
    ),
]


class HealingEngine:
    def __init__(self) -> None:
        self._strategies: dict[HealingStrategyType, HealingStrategy] = {
            s.strategy_type: s for s in DEFAULT_STRATEGIES
        }
        self._effectiveness: dict[HealingStrategyType, dict[str, int]] = {
            s.strategy_type: {"execution_count": 0, "success_count": 0}
            for s in DEFAULT_STRATEGIES
        }
        self._action_history: list[HealingAction] = []

    def handle_fault(self, fault: FaultRecord) -> HealingAction | None:
        candidates = [
            s for s in self._strategies.values()
            if s.applies_to and fault.fault_type in s.applies_to
        ]
        if not candidates:
            abort = self._strategies.get(HealingStrategyType.abort_turn)
            if abort:
                candidates = [abort]
            else:
                return None

        candidate = max(
            candidates,
            key=lambda s: (
                self._effectiveness[s.strategy_type]["success_count"]
                / max(1, self._effectiveness[s.strategy_type]["execution_count"])
                if self._effectiveness[s.strategy_type]["execution_count"] > 0
                else s.success_probability
            ),
        )

        action = HealingAction(
            strategy_type=candidate.strategy_type,
            fault_type=fault.fault_type,
            execution_time=0.0,
            success=False,
            effectiveness_tracking=self._effectiveness[candidate.strategy_type],
        )
        self._effectiveness[candidate.strategy_type]["execution_count"] += 1
        self._action_history.append(action)
        return action

    def record_success(self, strategy_type: HealingStrategyType) -> None:
        if strategy_type in self._effectiveness:
            self._effectiveness[strategy_type]["success_count"] += 1

    def effectiveness_summary(self) -> dict[HealingStrategyType, dict[str, int]]:
        return dict(self._effectiveness)

    def action_history(self) -> list[HealingAction]:
        return list(self._action_history)

    def reset(self) -> None:
        self._effectiveness = {
            s.strategy_type: {"execution_count": 0, "success_count": 0}
            for s in DEFAULT_STRATEGIES
        }
        self._action_history.clear()

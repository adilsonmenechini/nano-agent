from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from nanoagent.loop.constants import (
    FaultRecord,
    HealthLevel,
    LoopConfig,
    ProgressAction,
)

if TYPE_CHECKING:
    from nanoagent.loop.healing import HealingEngine
    from nanoagent.loop.health import StabilityMonitor


@dataclass
class ProgressSignal:
    step_count: int = 0
    completion_ratio: float = 0.0
    failure_ratio: float = 0.0
    tool_calls: int = 0
    output_changes: int = 0
    elapsed_seconds: float = 0.0
    error_rate_window: float = 0.0
    oscillation_index: float = 0.0
    context_usage_ratio: float = 0.0


@dataclass
class ProgressDecision:
    action: ProgressAction = ProgressAction.continue_
    health_level: HealthLevel = HealthLevel.healthy
    health_score: float = 1.0
    stall_score: float = 0.0
    oscillation_score: float = 0.0
    reason: str | None = None
    anomalies: list = field(default_factory=list)
    healing_action: object | None = None


class ProgressController:
    def __init__(
        self,
        config: LoopConfig,
        stability_monitor: StabilityMonitor | None = None,
        healing_engine: HealingEngine | None = None,
    ) -> None:
        self._window: deque[ProgressSignal] = deque(maxlen=config.health_window_size)
        self._stall_threshold = config.stall_threshold
        self._oscillation_window = config.oscillation_window
        self._stability_monitor = stability_monitor
        self._healing_engine = healing_engine
        self._detected_faults: list[FaultRecord] = []

    def record_step(self, signal: ProgressSignal) -> None:
        self._window.append(signal)
        if self._stability_monitor is not None:
            report = self._stability_monitor.analyze(signal)
            anomalies = getattr(report, "anomalies", [])
            if anomalies:
                self._detected_faults.extend(anomalies)

    def evaluate(self) -> ProgressDecision:
        if not self._window:
            return ProgressDecision()

        recent = list(self._window)
        total = len(recent)
        if total == 0:
            return ProgressDecision()

        avg_failure = sum(s.failure_ratio for s in recent) / total
        avg_error_rate = sum(s.error_rate_window for s in recent) / total
        avg_context = sum(s.context_usage_ratio for s in recent) / total
        avg_oscillation = sum(s.oscillation_index for s in recent) / total
        unique_tools = max(1, len({s.tool_calls for s in recent}))

        tool_diversity = unique_tools / max(1, sum(s.tool_calls for s in recent))
        success_rate = 1.0 - avg_failure

        w1, w2, w3, w4, w5 = 0.35, 0.25, 0.15, 0.15, 0.10
        health_score = (
            w1 * success_rate
            + w2 * (1.0 - avg_error_rate)
            + w3 * (1.0 - avg_context)
            + w4 * (1.0 - avg_oscillation)
            + w5 * tool_diversity
        ) / (w1 + w2 + w3 + w4 + w5)

        health_score = max(0.0, min(1.0, health_score))
        health_level = HealthLevel.from_score(health_score)

        stall_score = self._compute_stall_score(recent)
        oscillation_score = self._compute_oscillation_score(recent)

        action = self._decide_action(health_level, stall_score, oscillation_score)
        reason = self._compute_reason(action, health_score, stall_score, oscillation_score)

        healing_action = None
        if self._healing_engine is not None and self._detected_faults:
            healing_action = self._healing_engine.handle_fault(self._detected_faults[-1])

        return ProgressDecision(
            action=action,
            health_level=health_level,
            health_score=health_score,
            stall_score=stall_score,
            oscillation_score=oscillation_score,
            reason=reason,
            anomalies=list(self._detected_faults),
            healing_action=healing_action,
        )

    def _compute_stall_score(self, recent: list[ProgressSignal]) -> float:
        if len(recent) < self._stall_threshold:
            return 0.0
        last_n = recent[-self._stall_threshold:]
        total_output_changes = sum(s.output_changes for s in last_n)
        if total_output_changes == 0:
            return 1.0
        return 0.0

    def _compute_oscillation_score(self, recent: list[ProgressSignal]) -> float:
        if len(recent) < self._oscillation_window:
            return 0.0
        last_n = recent[-self._oscillation_window:]
        tool_call_counts = [s.tool_calls for s in last_n]
        if len(set(tool_call_counts)) == 1 and len(tool_call_counts) >= 3:
            return 1.0
        return 0.0

    def _decide_action(
        self, health: HealthLevel, stall_score: float, oscillation_score: float
    ) -> ProgressAction:
        if health == HealthLevel.critical:
            return ProgressAction.stop
        if stall_score >= 0.8:
            return ProgressAction.switch_strategy
        if oscillation_score >= 0.8:
            return ProgressAction.switch_strategy
        if health == HealthLevel.warning:
            return ProgressAction.narrow_scope
        if health == HealthLevel.degraded:
            return ProgressAction.request_confirmation
        return ProgressAction.continue_

    def _compute_reason(
        self,
        action: ProgressAction,
        health_score: float,
        stall_score: float,
        oscillation_score: float,
    ) -> str | None:
        if action == ProgressAction.stop:
            return f"critical health ({health_score:.2f})"
        if action == ProgressAction.switch_strategy:
            if stall_score >= 0.8:
                return f"stall detected (score={stall_score:.2f})"
            if oscillation_score >= 0.8:
                return f"oscillation detected (score={oscillation_score:.2f})"
        if action == ProgressAction.narrow_scope:
            return f"health warning ({health_score:.2f})"
        if action == ProgressAction.request_confirmation:
            return f"health degraded ({health_score:.2f})"
        return None

    def reset(self) -> None:
        self._window.clear()

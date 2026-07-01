from __future__ import annotations

from dataclasses import dataclass, field

from nanoagent.loop.constants import (
    FaultCategory,
    FaultRecord,
    FaultSeverity,
    HealthLevel,
    LoopConfig,
)
from nanoagent.loop.progress import ProgressSignal


@dataclass
class HealthMetrics:
    success_rate: float = 1.0
    error_frequency: float = 0.0
    context_usage: float = 0.0
    oscillation_index: float = 0.0
    tool_diversity: float = 1.0


@dataclass
class StabilityReport:
    health_level: HealthLevel = HealthLevel.healthy
    health_score: float = 1.0
    stability_index: float = 1.0
    robustness_score: float = 1.0
    anomalies: list[FaultRecord] = field(default_factory=list)
    window_metrics: dict[str, float] = field(default_factory=dict)


class StabilityMonitor:
    def __init__(self, config: LoopConfig) -> None:
        self._config = config
        self._previous_signals: list[ProgressSignal] = []
        self._detected_faults: list[FaultRecord] = []

    def analyze(self, signal: ProgressSignal) -> StabilityReport:
        self._previous_signals.append(signal)
        metrics = self._compute_metrics(signal)
        health_level = HealthLevel.from_score(metrics.success_rate)
        stability_index = self._compute_stability_index()
        robustness_score = self._compute_robustness_score(metrics)
        anomalies = self._detect_anomalies_from_window()

        return StabilityReport(
            health_level=health_level,
            health_score=metrics.success_rate,
            stability_index=stability_index,
            robustness_score=robustness_score,
            anomalies=anomalies,
            window_metrics={
                "success_rate": metrics.success_rate,
                "error_frequency": metrics.error_frequency,
                "context_usage": metrics.context_usage,
                "oscillation_index": metrics.oscillation_index,
                "stability_index": stability_index,
                "robustness_score": robustness_score,
            },
        )

    def detect_anomalies(self, signal: ProgressSignal) -> list[FaultRecord]:
        new_faults: list[FaultRecord] = []
        import time

        ts = time.time()

        if signal.oscillation_index > 0.8:
            fault = FaultRecord(
                fault_type=FaultCategory.OSCILLATION,
                severity=FaultSeverity.HIGH,
                timestamp=ts,
                metrics_snapshot={"oscillation_index": signal.oscillation_index},
                description=f"Oscillation detected (index={signal.oscillation_index:.2f})",
            )
            new_faults.append(fault)

        if signal.error_rate_window > 0.5:
            fault = FaultRecord(
                fault_type=FaultCategory.ERROR_SPIKE,
                severity=FaultSeverity.MEDIUM,
                timestamp=ts,
                metrics_snapshot={"error_rate": signal.error_rate_window},
                description=f"Error spike detected (rate={signal.error_rate_window:.2f})",
            )
            new_faults.append(fault)

        if signal.context_usage_ratio > 0.90:
            fault = FaultRecord(
                fault_type=FaultCategory.CONTEXT_OVERFLOW,
                severity=FaultSeverity.HIGH,
                timestamp=ts,
                metrics_snapshot={"context_usage": signal.context_usage_ratio},
                description=f"Context overflow risk at {signal.context_usage_ratio:.0%}",
            )
            new_faults.append(fault)

        self._detected_faults.extend(new_faults)
        return new_faults

    def _compute_metrics(self, signal: ProgressSignal) -> HealthMetrics:
        success_rate = 1.0 - signal.failure_ratio
        tool_total = max(1, signal.tool_calls)
        tool_diversity = min(1.0, signal.output_changes / tool_total)

        return HealthMetrics(
            success_rate=max(0.0, success_rate),
            error_frequency=signal.error_rate_window,
            context_usage=signal.context_usage_ratio,
            oscillation_index=signal.oscillation_index,
            tool_diversity=tool_diversity,
        )

    def _compute_stability_index(self) -> float:
        if not self._previous_signals:
            return 1.0
        recent = self._previous_signals[-20:]
        if len(recent) < 2:
            return 1.0
        success_rates = [1.0 - s.failure_ratio for s in recent]
        avg = sum(success_rates) / len(success_rates)
        variance = sum((r - avg) ** 2 for r in success_rates) / len(success_rates)
        stability = 1.0 - min(1.0, variance * 5)
        return max(0.0, stability)

    def _compute_robustness_score(self, metrics: HealthMetrics) -> float:
        score = (
            0.35 * metrics.success_rate
            + 0.25 * (1.0 - metrics.error_frequency)
            + 0.20 * (1.0 - metrics.context_usage)
            + 0.20 * metrics.tool_diversity
        )
        return max(0.0, min(1.0, score))

    def _detect_anomalies_from_window(self) -> list[FaultRecord]:
        if not self._previous_signals:
            return []
        latest = self._previous_signals[-1]
        return self.detect_anomalies(latest)

    def reset(self) -> None:
        self._previous_signals.clear()
        self._detected_faults.clear()

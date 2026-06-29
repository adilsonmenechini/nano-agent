from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from nanoagent.loop.constants import Phase, StopReason


@dataclass
class DiagnosticsReport:
    phase_timings: dict[str, float] = field(default_factory=dict)
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    health_snapshots: list[dict[str, Any]] = field(default_factory=list)
    stability_report: dict[str, Any] | None = None
    healing_actions: list[dict[str, Any]] = field(default_factory=list)
    stop_reason: str = ""
    total_duration: float = 0.0


class DiagnosticsCollector:
    def __init__(self, enabled: bool = False) -> None:
        self._enabled = enabled
        self._phase_timings: dict[str, float] = {}
        self._tool_calls: list[dict[str, Any]] = []
        self._health_snapshots: list[dict[str, Any]] = []
        self._stability_report: dict[str, Any] | None = None
        self._healing_actions: list[dict[str, Any]] = []
        self._phase_start: float | None = None
        self._turn_start: float | None = None

    def record_phase(self, phase: Phase, duration: float) -> None:
        if not self._enabled:
            return
        self._phase_timings[phase.value] = duration

    def record_tool_call(self, name: str, duration: float, success: bool) -> None:
        if not self._enabled:
            return
        self._tool_calls.append({
            "name": name,
            "duration": duration,
            "success": success,
        })

    def record_health(self, health_score: float, health_level: str) -> None:
        if not self._enabled:
            return
        self._health_snapshots.append({
            "score": health_score,
            "level": health_level,
        })

    def record_healing(self, action: dict[str, Any]) -> None:
        if not self._enabled:
            return
        self._healing_actions.append(action)

    def record_stability(self, report: dict[str, Any]) -> None:
        if not self._enabled:
            return
        self._stability_report = report

    def report(self, stop_reason: StopReason | None = None) -> DiagnosticsReport:
        return DiagnosticsReport(
            phase_timings=dict(self._phase_timings),
            tool_calls=list(self._tool_calls),
            health_snapshots=list(self._health_snapshots),
            stability_report=dict(self._stability_report) if self._stability_report else None,
            healing_actions=list(self._healing_actions),
            stop_reason=stop_reason.value if stop_reason else "",
            total_duration=sum(self._phase_timings.values()),
        )

    def render(self, stop_reason: StopReason | None = None) -> str:
        if not self._enabled or not self._phase_timings:
            return ""
        lines: list[str] = []
        lines.append("━ Diagnostics ━━━")
        lines.append("Phase Timing:")
        for phase, dur in self._phase_timings.items():
            lines.append(f"  {phase}:   {dur:.3f}s")
        lines.append(f"Total: {sum(self._phase_timings.values()):.3f}s")
        if self._health_snapshots:
            latest = self._health_snapshots[-1]
            lines.append(f"Health: {latest['score']:.2f} ({latest['level']})")
        if self._tool_calls:
            unique = len({t["name"] for t in self._tool_calls})
            lines.append(f"Tool calls: {len(self._tool_calls)} ({unique} unique)")
        if self._healing_actions:
            for action in self._healing_actions:
                lines.append("")
                lines.append("━ Healing Action ━━━")
                lines.append(f"Fault: {action.get('fault_type', 'unknown')}")
                lines.append(f"Strategy: {action.get('strategy', 'unknown')}")
                result = "Success" if action.get("success") else "Failed"
                lines.append(f"Result: {result} ({action.get('duration', 0):.3f}s)")
        if stop_reason:
            lines.append(f"Stop reason: {stop_reason.value}")
        lines.append("─" * 19)
        return "\n".join(lines)

    def reset(self) -> None:
        self._phase_timings.clear()
        self._tool_calls.clear()
        self._health_snapshots.clear()
        self._stability_report = None
        self._healing_actions.clear()

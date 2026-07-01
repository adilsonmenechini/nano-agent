from nanoagent.loop.constants import (
    DEFAULT_CONFIG,
    FaultCategory,
    FaultRecord,
    FaultSeverity,
    HealingAction,
    HealthLevel,
    HealingStrategyType,
    LoopConfig,
    Phase,
    ProgressAction,
    StopReason,
)
from nanoagent.loop.diagnostics import DiagnosticsCollector, DiagnosticsReport
from nanoagent.loop.health import StabilityMonitor, StabilityReport
from nanoagent.loop.healing import HealingEngine, HealingStrategy
from nanoagent.loop.progress import ProgressController, ProgressDecision, ProgressSignal
from nanoagent.loop.turn import Turn, TurnBudget, TurnStepPolicy


def create_loop(config: LoopConfig | None = None) -> dict:
    """Factory: creates configured loop components.

    Returns a dict with all loop components wired together:
        'config': LoopConfig
        'turn': Turn
        'progress': ProgressController
        'monitor': StabilityMonitor
        'healing': HealingEngine
        'diagnostics': DiagnosticsCollector

    Each call returns a fresh set of components.
    """
    from nanoagent.loop.diagnostics import DiagnosticsCollector
    from nanoagent.loop.healing import HealingEngine
    from nanoagent.loop.health import StabilityMonitor
    from nanoagent.loop.progress import ProgressController
    from nanoagent.loop.turn import Turn

    resolved = config or DEFAULT_CONFIG
    return {
        "config": resolved,
        "turn": Turn(resolved),
        "progress": ProgressController(resolved),
        "monitor": StabilityMonitor(resolved),
        "healing": HealingEngine(),
        "diagnostics": DiagnosticsCollector(resolved.diagnostics_enabled),
    }


__all__ = [
    "DEFAULT_CONFIG",
    "DiagnosticsCollector",
    "DiagnosticsReport",
    "FaultCategory",
    "FaultRecord",
    "FaultSeverity",
    "HealthLevel",
    "HealingAction",
    "HealingEngine",
    "HealingStrategy",
    "HealingStrategyType",
    "LoopConfig",
    "Phase",
    "ProgressAction",
    "ProgressController",
    "ProgressDecision",
    "ProgressSignal",
    "StopReason",
    "StabilityMonitor",
    "StabilityReport",
    "Turn",
    "TurnBudget",
    "TurnStepPolicy",
    "create_loop",
]

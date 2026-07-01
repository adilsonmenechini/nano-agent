# Public API Contract: Agent Loop

## Module: `nanoagent.loop`

### Public Classes

#### `Turn`

```python
class Turn:
    def __init__(self, config: LoopConfig) -> None
    def start(self, prompt: str) -> StopReason
    def current_phase(self) -> Phase
    def budget(self) -> TurnBudget
    def policy(self) -> TurnStepPolicy
```

**Contract**:
- `start()` orchestrates the full phase cycle (RECEIVE → EXPLORE → EXECUTE → VERIFY → RESPOND)
- Returns a `StopReason` indicating why the turn ended
- `current_phase()` always returns the active phase during execution
- `budget()` and `policy()` are valid after `start()` returns

#### `ProgressController`

```python
class ProgressController:
    def __init__(self, config: LoopConfig) -> None
    def record_step(self, signal: ProgressSignal) -> None
    def evaluate(self) -> ProgressDecision
    def reset(self) -> None
```

**Contract**:
- `record_step()` pushes a signal into the sliding window
- `evaluate()` computes current health and stall/oscillation scores
- `evaluate()` may be called at any time — always reflects current window state
- `reset()` clears the window between turns

#### `StabilityMonitor`

```python
class StabilityMonitor:
    def __init__(self, config: LoopConfig) -> None
    def analyze(self, signal: ProgressSignal) -> StabilityReport
    def detect_anomalies(self, signal: ProgressSignal) -> list[FaultRecord]
    def reset(self) -> None
```

**Contract**:
- `analyze()` computes full stability metrics and health level
- `detect_anomalies()` returns only new anomalies since last call
- Is **read-only** — does NOT modify agent state
- `reset()` clears anomaly state between turns

#### `HealingEngine`

```python
class HealingEngine:
    def __init__(self) -> None
    def handle_fault(self, fault: FaultRecord) -> HealingAction | None
    def effectiveness_summary(self) -> dict[HealingStrategyType, dict[str, int]]
    def reset(self) -> None
```

**Contract**:
- `handle_fault()` selects best strategy based on effectiveness tracking
- Returns `None` if no strategy is available for the fault category
- Prefers strategies with higher historical success count
- `effectiveness_summary()` returns `{strategy: {execution_count, success_count}}`

#### `DiagnosticsCollector`

```python
class DiagnosticsCollector:
    def __init__(self, enabled: bool = False) -> None
    def record_phase(self, phase: Phase, duration: float) -> None
    def record_tool_call(self, name: str, duration: float, success: bool) -> None
    def record_health(self, decision: ProgressDecision) -> None
    def record_healing(self, action: HealingAction) -> None
    def report(self) -> DiagnosticsReport
    def render(self) -> str
    def reset(self) -> None
```

**Contract**:
- If `enabled=False`, all record methods are no-ops
- `report()` always returns a `DiagnosticsReport` (empty if disabled)
- `render()` returns a formatted string suitable for CLI output (empty string if disabled)
- `reset()` clears all recorded data between turns

### Module-Level Functions

```python
def create_loop(config: LoopConfig | None = None) -> dict:
    """Factory: creates configured loop components.
    Returns {'turn': Turn, 'progress': ProgressController,
             'monitor': StabilityMonitor, 'healing': HealingEngine,
             'diagnostics': DiagnosticsCollector, 'config': LoopConfig}
    """
```

### Type Re-exports

```python
from nanoagent.loop.constants import (
    Phase, StopReason, HealthLevel, FaultCategory,
    FaultSeverity, HealingStrategyType, ProgressAction
)
from nanoagent.loop.turn import Turn, TurnBudget, TurnStepPolicy
from nanoagent.loop.progress import ProgressSignal, ProgressDecision, ProgressController
from nanoagent.loop.health import HealthMetrics, HealthLevel, StabilityMonitor, StabilityReport
from nanoagent.loop.healing import FaultRecord, HealingStrategy, HealingAction, HealingEngine
from nanoagent.loop.diagnostics import DiagnosticsReport, DiagnosticsCollector
from nanoagent.loop.constants import LoopConfig, DEFAULT_CONFIG
```

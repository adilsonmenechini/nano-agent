# Quickstart: Agent Loop Engineering Validation Guide

## Prerequisites

- Python 3.13+
- NanoAgent installed in dev mode: `pip install -e ".[dev]"`
- Working directory: project root

## Setup

```bash
# Install development dependencies
pip install -e ".[dev]"

# Verify current test baseline
pytest tests/ --tb=short -q
```

## Validation Scenarios

### Scenario 1: Turn Phase Execution (US-1 / FR-001–FR-003)

**Goal**: Verify that the agent processes a prompt through discrete phases with observable transitions.

```python
# tests/unit/loop/test_turn.py
from nanoagent.loop import Turn, TurnBudget, Phase, StopReason
from nanoagent.loop.constants import LoopConfig, DEFAULT_CONFIG

def test_turn_full_cycle():
    config = LoopConfig(max_steps_per_turn=10)
    turn = Turn(config)
    result = turn.start("hello")
    assert isinstance(result, StopReason)
    assert result in StopReason
```

**Expected outcome**: Turn progresses through RECEIVE → EXPLORE → EXECUTE → VERIFY → RESPOND and returns a valid stop reason.

---

### Scenario 2: Health Indicator Display (US-2 / FR-006–FR-009)

**Goal**: Verify that health level updates during turn execution.

```python
# tests/unit/loop/test_progress.py
from nanoagent.loop import ProgressController, ProgressSignal
from nanoagent.loop.constants import HealthLevel, LoopConfig

def test_health_levels():
    controller = ProgressController(LoopConfig())
    # Simulate healthy steps
    for _ in range(5):
        signal = ProgressSignal(
            step_count=_, completion_ratio=0.2, failure_ratio=0.0,
            tool_calls=1, output_changes=1, elapsed_seconds=0.5,
            error_rate_window=0.0, oscillation_index=0.0, context_usage_ratio=0.1
        )
        controller.record_step(signal)
    decision = controller.evaluate()
    assert decision.health_level == HealthLevel.healthy
```

**Expected outcome**: With all metrics nominal, health is `healthy`. With high error rate, health degrades to `degraded` or `warning`.

---

### Scenario 3: Oscillation Detection (FR-010 / SC-003)

**Goal**: Verify that repeated identical tool calls are detected within 3 iterations.

```python
# tests/unit/loop/test_health.py
from nanoagent.loop import StabilityMonitor, ProgressSignal
from nanoagent.loop.constants import LoopConfig, FaultCategory

def test_oscillation_detection():
    monitor = StabilityMonitor(LoopConfig())
    signals = [
        ProgressSignal(step_count=i, tool_calls=i, output_changes=0,
                       completion_ratio=0.0, failure_ratio=0.0,
                       elapsed_seconds=float(i), error_rate_window=0.0,
                       oscillation_index=0.0, context_usage_ratio=0.1)
        for i in range(5)
    ]
    anomalies = []
    for sig in signals:
        monitor.analyze(sig)
        anomalies.extend(monitor.detect_anomalies(sig))
    # After 3+ iterations with no output change, should detect oscillation
    oscillation_faults = [a for a in anomalies if a.fault_type == FaultCategory.OSCILLATION]
    assert len(oscillation_faults) >= 1
```

**Expected outcome**: At least one OSCILLATION fault is detected within the repeat sequence.

---

### Scenario 4: Self-Healing on Transient Failure (US-3 / FR-012–FR-014)

**Goal**: Verify that the healing engine selects and executes appropriate strategy for a fault.

```python
# tests/unit/loop/test_healing.py
from nanoagent.loop import HealingEngine, FaultRecord
from nanoagent.loop.constants import FaultCategory, FaultSeverity, HealingStrategyType

def test_retry_strategy():
    engine = HealingEngine()
    fault = FaultRecord(
        fault_type=FaultCategory.RESOURCE_EXHAUSTION,
        severity=FaultSeverity.HIGH,
        timestamp=100.0,
        metrics_snapshot={},
        healing_action_id=None,
        description="LLM provider timeout"
    )
    action = engine.handle_fault(fault)
    assert action is not None
    assert action.strategy_type == HealingStrategyType.retry
```

**Expected outcome**: Healing engine selects `retry` strategy for RESOURCE_EXHAUSTION fault.

---

### Scenario 5: Diagnostics Output (US-4 / FR-018–FR-021 / SC-008)

**Goal**: Verify that diagnostics mode produces structured per-phase timing.

```bash
# Run a simple prompt with diagnostics mode
nanoagent --diagnostics "Hello, what can you do?"

# Expected output includes a Diagnostics section with:
# ━━━ Diagnostics ━━━
# Phase Timing:
#   explore:   0.042s
#   execute:   1.237s
#   verify:    0.018s
# Total: 1.297s
# Health: 0.92 (healthy)
```

---

### Scenario 6: Edge Case — Empty Prompt (FR-021)

**Goal**: Verify that empty prompts return helpful message instead of entering execution loop.

```python
# tests/unit/loop/test_turn.py

def test_empty_prompt():
    config = LoopConfig()
    turn = Turn(config)
    result = turn.start("   ")
    assert result == StopReason.done  # or similar graceful handling
```

---

### Scenario 7: Integration — CLI with Loop (End-to-End)

**Goal**: Verify CLI flag integration works correctly.

```python
# tests/integration/test_loop_integration.py

def test_diagnostics_flag_cli():
    """Run nanoagent with --diagnostics flag and verify output."""
    import subprocess
    result = subprocess.run(
        ["python", "-m", "nanoagent", "--diagnostics", "test"],
        capture_output=True, text=True, timeout=10
    )
    assert "Diagnostics" in result.stdout
```

---

### Scenario 8: Contract Test — LoopConfig Validation

**Goal**: Verify config validation rejects invalid values.

```python
# tests/contract/test_loop_contract.py
import pytest
from nanoagent.loop.constants import LoopConfig

def test_config_validation():
    with pytest.raises((ValueError, AssertionError)):
        LoopConfig(max_steps_per_turn=0)
    with pytest.raises((ValueError, AssertionError)):
        LoopConfig(max_steps_per_turn=501)
    with pytest.raises((ValueError, AssertionError)):
        LoopConfig(tool_timeout_seconds=-1.0)
    with pytest.raises((ValueError, AssertionError)):
        LoopConfig(compaction_threshold=1.5)
```

---

## Test Execution

```bash
# Run all loop tests
pytest tests/unit/loop/ -v

# Run integration tests
pytest tests/integration/test_loop_integration.py -v

# Run contract tests
pytest tests/contract/test_loop_contract.py -v

# Full test suite
pytest tests/ --tb=short -q --coverage

# Check coverage
coverage run -m pytest tests/unit/loop/ && coverage report -m
```

## Expected Coverage Impact

| Component | Target Coverage | Notes |
|-----------|----------------|-------|
| `nanoagent/loop/turn.py` | ≥90% | Core orchestration |
| `nanoagent/loop/progress.py` | ≥85% | Complex health scoring |
| `nanoagent/loop/health.py` | ≥85% | Anomaly detection logic |
| `nanoagent/loop/healing.py` | ≥90% | Strategy selection |
| `nanoagent/loop/diagnostics.py` | ≥80% | Rendering — simpler to test |
| `nanoagent/loop/constants.py` | 100% | Pure data — trivial |

**Overall loop package target**: ≥85% line coverage

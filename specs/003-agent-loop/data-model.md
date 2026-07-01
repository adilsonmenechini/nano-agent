# Data Model: Agent Loop Engineering

## Enums

### `Phase`

Turn phase identifier.

| Value | Description |
|-------|-------------|
| `IDLE` | Agent ready, waiting for prompt |
| `RECEIVE` | User input received, initiating turn |
| `EXPLORE` | Understanding intent — analyze prompt, gather context |
| `EXECUTE` | Running tools, making LLM calls, performing actions |
| `VERIFY` | Checking results against intent, validating outputs |
| `RESPOND` | Composing and delivering final response |

**State transitions**: `IDLE → RECEIVE → EXPLORE → EXECUTE → VERIFY → RESPOND → IDLE`
**Allowed transitions**: Sequential only. No skipping phases. No backward transitions within a turn.

---

### `StopReason`

Why a turn ended.

| Value | Description | Source |
|-------|-------------|--------|
| `done` | All phases completed successfully | Turn completion |
| `max_steps` | Step budget exhausted | TurnBudget |
| `await_user` | Waiting for user input/interruption | User action |
| `blocked` | Irrecoverable error condition | ProgressController |
| `verification_failed` | Verify phase checks failed | Verify phase |

---

### `HealthLevel`

Overall agent health indicator.

| Level | Score Range | Meaning |
|-------|-------------|---------|
| `healthy` | 0.80–1.00 | Normal operation, all metrics nominal |
| `degraded` | 0.50–0.79 | Some metrics偏离 baseline, but operation continues |
| `warning` | 0.20–0.49 | Multiple metrics degraded, risk of failure |
| `critical` | 0.00–0.19 | Severe degradation, likely failure imminent |

---

### `FaultCategory`

Classification of detected faults.

| Value | Description |
|-------|-------------|
| `RESOURCE_EXHAUSTION` | LLM provider unavailable, API quota exceeded |
| `CONTEXT_OVERFLOW` | Context window approaching/exceeding limits |
| `TOOL_TIMEOUT` | Tool call exceeded timeout |
| `ERROR_SPIKE` | Sudden increase in error rate |
| `OSCILLATION` | Repeated identical tool calls |
| `DEADLOCK` | Mutual dependency between tool calls |

---

### `FaultSeverity`

Severity level for fault classification.

| Level | Meaning |
|-------|---------|
| `LOW` | Non-critical, can continue with degraded performance |
| `MEDIUM` | Affects current turn quality, may need strategy switch |
| `HIGH` | Likely to cause turn failure without intervention |
| `CRITICAL` | Guaranteed turn failure, abort immediately |

---

### `HealingStrategyType`

Identifiable healing strategy.

| Value | Applied To |
|-------|-----------|
| `retry` | RESOURCE_EXHAUSTION, TOOL_TIMEOUT |
| `compact_context` | CONTEXT_OVERFLOW |
| `reduce_scope` | ERROR_SPIKE, DEADLOCK |
| `break_oscillation` | OSCILLATION |
| `request_confirmation` | DEADLOCK, ERROR_SPIKE |
| `abort_turn` | Any unrecoverable fault |

---

### `ProgressAction`

Decision output from the progress controller.

| Value | Meaning |
|-------|---------|
| `continue` | Proceed with current strategy |
| `switch_strategy` | Change approach within current phase |
| `narrow_scope` | Reduce scope of current turn |
| `request_confirmation` | Pause and ask user |
| `stop` | End turn with reason |

---

## Data Classes

### `TurnBudget`

Tracks resource consumption for a single turn.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `max_steps` | `int` | `50` | Maximum steps allowed in this turn |
| `remaining_steps` | `int` | `50` | Steps remaining |
| `tool_error_count` | `int` | `0` | Count of tool errors this turn |
| `total_llm_calls` | `int` | `0` | Total LLM calls made |
| `total_tool_calls` | `int` | `0` | Total tool calls made |
| `budget_exhausted` | `bool` | `False` | Whether max steps were hit |

**Validation**:
- `max_steps` must be >= 1 (config range: 1–500)
- `remaining_steps` must be <= `max_steps`
- `tool_error_count` must be <= `total_tool_calls`

---

### `TurnStepPolicy`

Dynamic strategy for the current turn phase.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `allow_widening` | `bool` | `True` | Whether to explore broader context |
| `compact_aggressively` | `bool` | `False` | Whether to compact before next step |
| `current_strategy` | `str` | `"normal"` | Current strategy name (normal, narrowed, retrying) |

---

### `ProgressSignal`

Snapshot of turn progress metrics.

| Field | Type | Description |
|-------|------|-------------|
| `step_count` | `int` | Steps completed in current turn |
| `completion_ratio` | `float` | Fraction of expected work done (0.0–1.0) |
| `failure_ratio` | `float` | Fraction of steps that failed (0.0–1.0) |
| `tool_calls` | `int` | Total tool calls made |
| `output_changes` | `int` | Unique output states produced |
| `elapsed_seconds` | `float` | Seconds since turn started |
| `error_rate_window` | `float` | Recent error rate over sliding window |
| `oscillation_index` | `float` | Repetition detection score (0.0–1.0) |
| `context_usage_ratio` | `float` | Context window usage (0.0–1.0) |

---

### `ProgressDecision`

Output of the progress controller.

| Field | Type | Description |
|-------|------|-------------|
| `action` | `ProgressAction` | What to do next |
| `health_level` | `HealthLevel` | Current health assessment |
| `health_score` | `float` | Raw health score (0.0–1.0) |
| `stall_score` | `float` | Stall likelihood (0.0–1.0) |
| `oscillation_score` | `float` | Oscillation likelihood (0.0–1.0) |
| `reason` | `str | None` | Human-readable justification |

---

### `HealthMetrics`

Container for health computation inputs.

| Field | Type | Description |
|-------|------|-------------|
| `success_rate` | `float` | Recent success rate (0.0–1.0) |
| `error_frequency` | `float` | Errors per step |
| `context_usage` | `float` | Context window usage (0.0–1.0) |
| `oscillation_index` | `float` | Repetition index (0.0–1.0) |
| `tool_diversity` | `float` | Unique tools / total tool calls ratio |

**Health Score Formula**:
```
health_score = (
    w1 * success_rate +
    w2 * (1 - error_frequency) +
    w3 * (1 - context_usage) +
    w4 * (1 - oscillation_index) +
    w5 * tool_diversity
) / (w1 + w2 + w3 + w4 + w5)
```

Default weights: `w1=0.35, w2=0.25, w3=0.15, w4=0.15, w5=0.10`

---

### `FaultRecord`

Detection record from stability monitor.

| Field | Type | Description |
|-------|------|-------------|
| `fault_type` | `FaultCategory` | Classification of the fault |
| `severity` | `FaultSeverity` | Severity assessment |
| `timestamp` | `float` | Unix timestamp of detection |
| `metrics_snapshot` | `dict[str, float]` | Relevant metrics at time of detection |
| `healing_action_id` | `str | None` | Associated healing action, if any |
| `description` | `str` | Human-readable fault description |

---

### `HealingStrategy`

Definition of a healing strategy.

| Field | Type | Description |
|-------|------|-------------|
| `strategy_type` | `HealingStrategyType` | Strategy identifier |
| `action` | `str` | Description of the action to take |
| `expected_recovery_seconds` | `float` | Expected time to recover |
| `success_probability` | `float` | Estimated success probability (0.0–1.0) |
| `applies_to` | `list[FaultCategory]` | Fault categories this strategy handles |

**Default Strategies**:

| Strategy | Action | Expected Recovery | Success Prob | Applies To |
|----------|--------|-------------------|-------------|------------|
| `retry` | Retry failed operation with backoff | 5s | 0.70 | RESOURCE_EXHAUSTION, TOOL_TIMEOUT |
| `compact_context` | Summarize and trim context | 1s | 0.90 | CONTEXT_OVERFLOW |
| `reduce_scope` | Narrow prompt scope, retry | 3s | 0.60 | ERROR_SPIKE, DEADLOCK |
| `break_oscillation` | Block repeated call, suggest alternative | 1s | 0.85 | OSCILLATION |
| `request_confirmation` | Ask user for guidance | 10s | 0.50 | DEADLOCK, ERROR_SPIKE |
| `abort_turn` | Surface fault to user, abort turn | 0.5s | 1.00 | Any unrecoverable |

---

### `HealingAction`

Execution record of a healing operation.

| Field | Type | Description |
|-------|------|-------------|
| `strategy_type` | `HealingStrategyType` | Strategy used |
| `fault_type` | `FaultCategory` | Fault being addressed |
| `execution_time` | `float` | Seconds to execute |
| `success` | `bool` | Whether the action succeeded |
| `side_effects` | `list[str]` | Any side effects observed |
| `effectiveness_tracking` | `dict[str, int]` | `{execution_count, success_count}` |

---

### `StabilityReport`

Comprehensive report from stability monitor.

| Field | Type | Description |
|-------|------|-------------|
| `health_level` | `HealthLevel` | Current health |
| `health_score` | `float` | Raw health score |
| `stability_index` | `float` | Stability metric (0.0–1.0) |
| `robustness_score` | `float` | Robustness metric (0.0–1.0) |
| `anomalies` | `list[FaultRecord]` | Active anomalies |
| `window_metrics` | `dict[str, float]` | Windowed metric values |

---

### `DiagnosticsReport`

Structured summary of a completed turn.

| Field | Type | Description |
|-------|------|-------------|
| `phase_timings` | `dict[Phase, float]` | Per-phase wall-clock time in seconds |
| `tool_calls` | `list[dict]` | Tool call records (name, duration, success) |
| `health_snapshots` | `list[dict]` | Health score snapshots during turn |
| `stability_report` | `StabilityReport | None` | Stability summary |
| `healing_actions` | `list[HealingAction]` | Healing actions taken |
| `stop_reason` | `StopReason` | Why the turn ended |
| `total_duration` | `float` | Total turn duration in seconds |

---

### `LoopConfig`

Configuration for the agent loop.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `max_steps_per_turn` | `int` | `50` | Maximum steps per turn |
| `tool_timeout_seconds` | `float` | `30.0` | Timeout for individual tool calls |
| `llm_timeout_seconds` | `float` | `120.0` | Timeout for LLM responses |
| `stall_threshold` | `int` | `5` | Tool calls without output change to flag stall |
| `oscillation_window` | `int` | `3` | Identical calls to detect oscillation |
| `compaction_threshold` | `float` | `0.80` | Context usage ratio to trigger compaction |
| `diagnostics_enabled` | `bool` | `False` | Whether diagnostics mode is active |
| `health_window_size` | `int` | `20` | Number of steps for health score window |

---

## Entity Relationships

```
LoopConfig ──configures──► Turn
Turn ──contains──► Phase[] ──sequential──► TurnStepPolicy
Turn ──has──► TurnBudget
Turn ──produces──► DiagnosticsReport

ProgressController ──reads──► ProgressSignal ──produces──► ProgressDecision
ProgressController ──uses──► HealthLevel
ProgressController ──detects──► Stall, Oscillation

StabilityMonitor ──monitors──► ProgressSignal
StabilityMonitor ──produces──► StabilityReport
StabilityMonitor ──detects──► FaultRecord

HealingEngine ──receives──► FaultRecord
HealingEngine ──selects──► HealingStrategy ──produces──► HealingAction
HealingEngine ──tracks──► HealingStrategy.effectiveness_tracking
```

## Validation Rules

| Entity | Rule | Source |
|--------|------|--------|
| Turn | Must have exactly one stop reason | FR-002 |
| TurnBudget | remaining_steps must never exceed max_steps | FR-003 |
| TurnBudget | Steps decremented by exactly 1 per step | — |
| ProgressSignal | All ratios must be in 0.0–1.0 range | — |
| HealthLevel | Score boundaries are inclusive on lower bound | — |
| HealingStrategy | success_probability must be 0.0–1.0 | — |
| HealingStrategy | expected_recovery_seconds must be > 0 | FR-013 |
| LoopConfig | max_steps_per_turn must be 1–500 | — |
| LoopConfig | compaction_threshold must be 0.0–1.0 | FR-015 |
| ProgressDecision | Only one action per decision | — |

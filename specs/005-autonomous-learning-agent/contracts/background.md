# Background Cycle Contract

## Purpose

Define the scheduling and execution interface for autonomous background learning cycles.

---

## Configuration

TOML settings under `[learning]` section in `~/.config/nanoagent/config.toml`:

```toml
[learning]
enabled = false                  # Opt-in (disabled by default)
cycle_interval_turns = 10        # Run cycle every N turns
cycle_interval_seconds = 3600    # Or every N seconds (whichever comes first)
max_cycle_duration_ms = 5000     # Max time per cycle (soft limit)
```

## Public API

### `learning/background.py`

```python
class BackgroundLearner:
    """Schedules and executes background learning cycles.
    
    A cycle consists of:
    1. Collect recent reflections (since last cycle)
    2. Run pattern detection on new reflections
    3. Check for skill proposals
    4. Consolidate results
    
    Cycles run in a daemon thread and yield to active user turns.
    """

    def __init__(
        self,
        memory_store: SQLiteMemoryStore,
        config: AgentConfig,
        reflector: Reflector,
        experience_engine: ExperienceEngine,
        synthesizer: Synthesizer,
    ):
        """Initialize with all learning subsystem components."""

    def start_if_due(self, current_turn_count: int) -> bool:
        """Check if a cycle is due and execute if so.
        
        Args:
            current_turn_count: Current total turn count from agent.
            
        Returns:
            True if a cycle was executed, False if not due.
            
        Checks:
        1. learning.enabled == true
        2. Turn count delta >= cycle_interval_turns
           OR time delta >= cycle_interval_seconds
        3. Agent is not currently in a user turn
        """

    def execute_cycle(self) -> CycleResult:
        """Execute one complete learning cycle.
        
        Steps:
        1. Fetch reflections since last cycle
        2. Run ExperienceEngine.analyze_reflections()
        3. Run Synthesizer.check_for_proposals()
        4. Store results
        
        Returns:
            CycleResult with summary of what was done.
        """

    def get_last_cycle(self) -> CycleResult | None:
        """Return the most recent cycle result."""
```

### `CycleResult` dataclass

```python
@dataclass
class CycleResult:
    cycle_id: str
    started_at: float
    duration_ms: int
    reflections_analyzed: int
    patterns_found: int
    proposals_created: int
    errors: list[str] | None
```

## Threading Model

```
Agent.run()
  → _trigger_background_ops()
    → BackgroundReview.start_if_due()
    → BackgroundLearner.start_if_due(turn_count)
      → (if due) execute_cycle() in current thread
        → returns quickly (<5s)
```

Key rules:
- Background cycles run in the agent's call path (same thread as `_trigger_background_ops`)
- If a cycle would exceed `max_cycle_duration_ms`, it aborts and resumes next interval
- Background cycles never spawn new threads themselves
- The `enabled = false` default ensures no performance impact until user opts in

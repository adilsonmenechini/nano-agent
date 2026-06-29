# Introspection Contract

## Purpose

Define the interface for generating harness introspection reports and optimization recommendations.

---

## Public API

### `introspection.py`

```python
class HarnessAnalyzer:
    """Reads agent configuration, tool registry, and runtime metrics
    to produce introspection reports and recommendations."""

    def __init__(
        self,
        agent_config: AgentConfig,
        tool_registry: ToolRegistry,
        memory_store: SQLiteMemoryStore | None = None,
    ):
        """Initialize with references to agent components."""

    def snapshot(self) -> HarnessSnapshot:
        """Capture current state of all harness components.
        
        Returns:
            HarnessSnapshot containing all current values.
            
        This method is read-only and safe to call at any time.
        """

    def analyze(self, snapshot: HarnessSnapshot | None = None) -> list[Recommendation]:
        """Generate optimization recommendations from a snapshot.
        
        Analysis rules:
        1. UNUSED_TOOL: Tool registered but never called in N+ turns
        2. FREQUENT_ERROR: Tool with error rate > threshold
        3. PERMISSION_BLOCKED: Tool frequently blocked by permission rules
        4. TIMEOUT_SHORT: Tool consistently near timeout limit
        5. MEMORY_HIGH: Memory store approaching size threshold
        6. LOOP_CONFIG: Suboptimal loop settings (e.g., diagnostics disabled
           with high error rate)
        
        Returns:
            List of recommendations with confidence scores.
        """

    def report(self) -> str:
        """Generate a human-readable harness report.
        
        Combines snapshot + analysis into formatted text
        suitable for CLI display or agent consumption.
        """
```

### `HarnessSnapshot` dataclass

```python
@dataclass
class HarnessSnapshot:
    config: dict                    # Current AgentConfig
    tools: list[ToolInfo]           # Registered tools with metadata
    permissions: list[PermissionRule]  # Active permission rules
    memory_stats: dict | None       # Memory store stats
    loop_metrics: dict              # Turn budget, health history, error rates
    recommendations: list[Recommendation]  # Generated suggestions
```

### `ToolInfo` dataclass

```python
@dataclass
class ToolInfo:
    name: str
    description: str
    call_count: int           # from agent turn history
    error_count: int
    avg_duration_ms: float
    last_called: float | None  # unix timestamp
```

### `Recommendation` dataclass

```python
@dataclass
class Recommendation:
    type: str                # e.g., "unused_tool", "frequent_error"
    severity: str            # "info", "warning", "critical"
    message: str             # Human-readable suggestion
    confidence: float        # 0.0 to 1.0
    actionable: bool         # Whether agent can auto-apply
```

## CLI Integration

```python
# In cli.py:

@cli.group()
def harness():
    """Inspect and analyze agent harness configuration."""
    pass

@harness.command()
@click.option("--agent-id", default=None)
def report(agent_id):
    """Generate a full harness introspection report."""
    pass

@harness.command()
@click.option("--agent-id", default=None)
def analyze(agent_id):
    """Run pattern analysis and generate recommendations."""
    pass
```

# Reflection Contract

## Purpose

Define the interface for generating, storing, and retrieving post-turn reflection records.

---

## Storage Schema

**Table**: `reflection_records` in existing SQLite database (`~/.nanoagent/memory/global.db`)

```sql
CREATE TABLE IF NOT EXISTS reflection_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    turn_id TEXT NOT NULL UNIQUE,
    task_description TEXT NOT NULL,
    tool_calls TEXT NOT NULL,        -- JSON array of strings
    steps_taken INTEGER NOT NULL,
    errors TEXT,                      -- JSON array or NULL
    outcome TEXT NOT NULL             -- 'success' | 'partial' | 'failure'
        CHECK(outcome IN ('success', 'partial', 'failure')),
    duration_ms INTEGER NOT NULL CHECK(duration_ms >= 0),
    lessons_learned TEXT,             -- JSON array or NULL
    created REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_reflection_created ON reflection_records(created);
CREATE INDEX IF NOT EXISTS idx_reflection_outcome ON reflection_records(outcome);
```

## Public API

### `learning/reflector.py`

```python
class Reflector:
    """Generates and stores post-turn reflection records."""
    
    def __init__(self, memory_store: SQLiteMemoryStore):
        """Initialize with reference to the memory store."""
    
    def reflect(
        self,
        turn_id: str,
        messages: list[dict],
        tool_results: list[ToolResult],
        duration_ms: int,
    ) -> ReflectionRecord:
        """Analyze a completed turn and store a reflection record.
        
        Args:
            turn_id: Unique identifier for the turn.
            messages: Full message list from the turn.
            tool_results: Tool call results with name, args, result, error.
            duration_ms: Total turn duration.
        
        Returns:
            The created ReflectionRecord.
        
        Side effects:
            Inserts a row into reflection_records table.
            
        Raises:
            ReflectionError: If reflection generation fails.
        """
    
    def get_recent(self, limit: int = 10) -> list[ReflectionRecord]:
        """Return most recent reflection records."""
    
    def get_by_turn_id(self, turn_id: str) -> ReflectionRecord | None:
        """Return a specific reflection by turn ID."""
    
    def search(self, query: str, limit: int = 10) -> list[ReflectionRecord]:
        """Search reflection records by task description or lessons."""
    
    def get_stats(self) -> dict:
        """Return aggregate stats: total reflections, success rate, avg duration."""
```

### `ReflectionRecord` dataclass

```python
@dataclass
class ReflectionRecord:
    turn_id: str
    task_description: str
    tool_calls: list[str]
    steps_taken: int
    errors: list[dict] | None
    outcome: Literal["success", "partial", "failure"]
    duration_ms: int
    lessons_learned: list[str] | None
    created: float  # unix timestamp
```

## Integration Point

**Triggered from**: `Agent.on_turn_complete` hook in `agent.py`

```python
# In Agent.run(), after turn completes:
if self.on_turn_complete:
    self.on_turn_complete(response, messages, tool_results, errors, duration_ms)

# Hook wired in Agent.__init__() or externally (cli.py):
agent.on_turn_complete = lambda resp, msgs, tools, errs, dur: \
    reflector.reflect(turn_id, msgs, tools, dur)
```

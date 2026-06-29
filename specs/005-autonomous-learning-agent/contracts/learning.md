# Learning Contract

## Purpose

Define the interface for detecting, storing, and applying experience patterns derived from reflection records.

---

## Storage Schema

**Table**: `experience_patterns` in existing SQLite database

```sql
CREATE TABLE IF NOT EXISTS experience_patterns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trigger_context TEXT NOT NULL,        -- JSON: conditions description
    tool_sequence TEXT NOT NULL,          -- JSON array of tool names
    recommended_approach TEXT NOT NULL,
    success_count INTEGER DEFAULT 0 CHECK(success_count >= 0),
    failure_count INTEGER DEFAULT 0 CHECK(failure_count >= 0),
    sample_size INTEGER DEFAULT 0 CHECK(sample_size >= 0),
    first_observed REAL NOT NULL,
    last_applied REAL,
    is_active INTEGER DEFAULT 1
);

CREATE INDEX IF NOT EXISTS idx_pattern_active ON experience_patterns(is_active);
CREATE INDEX IF NOT EXISTS idx_pattern_sample ON experience_patterns(sample_size);
```

## Public API

### `learning/experience.py`

```python
class ExperienceEngine:
    """Detects patterns from reflection records and retrieves relevant
    past experiences to inform current decisions."""

    def __init__(self, memory_store: SQLiteMemoryStore):
        """Initialize with memory store for reading reflections + patterns."""

    def analyze_reflections(
        self,
        reflections: list[ReflectionRecord],
    ) -> list[ExperiencePattern]:
        """Scan reflection records for repeated tool sequences and outcomes.
        
        Detection algorithm:
        1. Group reflections by similar task_description (keyword overlap)
        2. Within each group, find common tool sequences (ordered subsets)
        3. For sequences appearing 3+ times, compute success/failure ratio
        4. Return patterns with sample_size >= 3
        
        Returns:
            Newly detected patterns (not yet stored).
        """

    def get_relevant_patterns(
        self,
        task_description: str,
        limit: int = 5,
    ) -> list[ExperiencePattern]:
        """Return active patterns relevant to the given task.
        
        Matching: keyword overlap between task_description and
        trigger_context.
        
        Returns:
            Patterns sorted by success_rate descending, limited.
        """

    def record_outcome(
        self,
        pattern_id: int,
        succeeded: bool,
    ) -> None:
        """Update success/failure counts for a pattern."""

    def get_stats(self) -> dict:
        """Return aggregate stats: total patterns, active patterns,
        average success rate."""
```

### `ExperiencePattern` dataclass

```python
@dataclass
class ExperiencePattern:
    id: int | None
    trigger_context: str
    tool_sequence: list[str]
    recommended_approach: str
    success_count: int
    failure_count: int
    sample_size: int
    first_observed: float
    last_applied: float | None
    is_active: bool
    
    @property
    def success_rate(self) -> float:
        """Return success ratio (0.0 to 1.0)."""
        if self.sample_size == 0:
            return 0.0
        return self.success_count / self.sample_size
```

## Integration Point

**Called from**: `ExperienceEngine.analyze_reflections()` during background cycles.

```
BackgroundCycle → Reflector.get_recent() 
                → ExperienceEngine.analyze_reflections()
                → store new patterns
                → Synthesizer.check_for_skill_proposals()
```

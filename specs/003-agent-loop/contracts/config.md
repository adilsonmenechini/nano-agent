# Configuration Contract: Agent Loop

## Loop Configuration Schema

### Configuration Source Hierarchy

1. CLI flags (highest priority)
2. Environment variables
3. Config file defaults
4. Code defaults (lowest priority)

### Environment Variables

| Variable | Type | Default | Maps To |
|----------|------|---------|---------|
| `NANOAGENT_MAX_STEPS` | int | `50` | `LoopConfig.max_steps_per_turn` |
| `NANOAGENT_TOOL_TIMEOUT` | float | `30.0` | `LoopConfig.tool_timeout_seconds` |
| `NANOAGENT_LLM_TIMEOUT` | float | `120.0` | `LoopConfig.llm_timeout_seconds` |
| `NANOAGENT_DIAGNOSTICS` | bool | `false` | `LoopConfig.diagnostics_enabled` |
| `NANOAGENT_STALL_THRESHOLD` | int | `5` | `LoopConfig.stall_threshold` |
| `NANOAGENT_COMPACTION_THRESHOLD` | float | `0.80` | `LoopConfig.compaction_threshold` |

### Config File (`~/.nanoagent/config.toml` or `.nanoagent.toml`)

```toml
[loop]
max_steps_per_turn = 50
tool_timeout_seconds = 30.0
llm_timeout_seconds = 120.0
diagnostics_enabled = false
stall_threshold = 5
oscillation_window = 3
compaction_threshold = 0.80
health_window_size = 20
```

### Python `LoopConfig` dataclass (source of truth)

```python
@dataclass
class LoopConfig:
    max_steps_per_turn: int = 50
    tool_timeout_seconds: float = 30.0
    llm_timeout_seconds: float = 120.0
    stall_threshold: int = 5
    oscillation_window: int = 3
    compaction_threshold: float = 0.80
    diagnostics_enabled: bool = False
    health_window_size: int = 20

    def __post_init__(self) -> None:
        assert 1 <= self.max_steps_per_turn <= 500
        assert self.tool_timeout_seconds > 0
        assert self.llm_timeout_seconds > 0
        assert self.stall_threshold >= 1
        assert self.oscillation_window >= 2
        assert 0.0 <= self.compaction_threshold <= 1.0
        assert self.health_window_size >= 5
```

### Existing Config Integration

The loop config will be added to the existing `nanoagent.config` module:

```python
# In config.py (additions)
from nanoagent.loop.constants import LoopConfig, DEFAULT_CONFIG

class NanoAgentConfig:
    # ... existing fields ...
    loop: LoopConfig = field(default_factory=lambda: DEFAULT_CONFIG.copy())
```

### Validation Rules

| Field | Rule | Error |
|-------|------|-------|
| `max_steps_per_turn` | 1 ≤ value ≤ 500 | `ValueError: max_steps_per_turn must be 1-500` |
| `tool_timeout_seconds` | > 0 | `ValueError: tool_timeout_seconds must be positive` |
| `llm_timeout_seconds` | > 0 | `ValueError: llm_timeout_seconds must be positive` |
| `stall_threshold` | ≥ 1 | `ValueError: stall_threshold must be >= 1` |
| `oscillation_window` | ≥ 2 | `ValueError: oscillation_window must be >= 2` |
| `compaction_threshold` | 0.0 ≤ value ≤ 1.0 | `ValueError: compaction_threshold must be 0.0-1.0` |
| `health_window_size` | ≥ 5 | `ValueError: health_window_size must be >= 5` |

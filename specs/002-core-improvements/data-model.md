# Data Model: Core Agent Improvements

## Entity: ProviderConfig

Configuration for an LLM provider connection.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | str | yes | Provider identifier (openai, anthropic, lm_studio) |
| `api_key` | str | no* | API key (from env var or config file) |
| `base_url` | str | no | Custom endpoint URL |
| `max_tokens` | int | no | Default: 4096 |
| `temperature` | float | no | Default: 0.7 |
| `retry_attempts` | int | no | Default: 3 |

*Marked as required if provider type requires authentication via API key.

## Entity: MemoryEntry

A stored memory with semantic search support.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `target` | str | yes | Namespace (memory, user, failure) |
| `scope` | str | yes | Scope (global, project) |
| `key` | str | yes | Lookup key |
| `value` | str | yes | Content text |
| `embedding` | bytes | no | Vector embedding (384-dim float32) |
| `importance` | float | no | Importance score 0.0–1.0 |
| `created_at` | datetime | auto | Timestamp of creation |
| `last_accessed` | datetime | auto | Timestamp of last retrieval |

**Validation Rules:**
- Embedding dimension must match model output (384 for all-MiniLM-L6-v2)
- Importance score defaults to 0.5 if not set
- `key` + `scope` + `target` must be unique

## Entity: SkillVersion

A versioned snapshot of a skill's code and metadata.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `skill_id` | str | yes | Unique skill identifier |
| `version` | int | yes | Monotonic version number |
| `name` | str | yes | Human-readable name |
| `description` | str | yes | Purpose description |
| `code` | str | yes | Python source code |
| `dependencies` | list[str] | no | Required tool names |
| `created_at` | datetime | auto | Version timestamp |
| `checksum` | str | auto | SHA256 of code |

**Validation Rules:**
- `version` starts at 1 and increments monotonically per skill_id
- `dependencies` must reference existing tool names at validation time
- `checksum` must match SHA256 of `code`

## Entity: AgentState

State machine lifecycle for the agent.

| State | Description | Valid Transitions |
|-------|-------------|-------------------|
| `IDLE` | Waiting for user input | THINKING |
| `THINKING` | LLM generating response | EXECUTING_TOOLS, AWAITING_INPUT, IDLE |
| `EXECUTING_TOOLS` | Running tool calls | THINKING, ERROR |
| `AWAITING_INPUT` | Waiting for user clarification | IDLE |
| `ERROR` | Recoverable error state | IDLE, THINKING |

**State Rules:**
- All transitions logged via callback
- Timeout in EXECUTING_TOOLS triggers ERROR after configurable duration
- ERROR state is always recoverable (returns to IDLE or THINKING)

## Entity: ToolPipeline

A directed acyclic graph of tool execution steps.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `pipeline_id` | str | yes | Unique pipeline identifier |
| `steps` | list[Step] | yes | Ordered list of tool calls |
| `parallel_groups` | list[list[str]] | no | Steps that can run in parallel |
| `dependencies` | dict[str, list[str]] | no | Step → [dependency step IDs] |

**Validation Rules:**
- Pipeline must be a valid DAG (no cycles)
- Parallel group members must have no interdependencies
- All dependency references must point to valid step IDs

## Entity: HealthStatus

Snapshot of system health at a point in time.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `timestamp` | datetime | auto | When check was performed |
| `providers` | dict[str, bool] | yes | Provider name → connected |
| `version` | str | yes | Agent version string |
| `python_version` | str | auto | Runtime Python version |
| `config_source` | str | auto | Where config was loaded from (env/file/both) |

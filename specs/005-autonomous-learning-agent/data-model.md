# Data Model: Autonomous Learning Agent

**Phase 1 output** — Entity definitions, relationships, and validation rules.

---

## Entity Relationship Diagram

```
┌──────────────────┐          ┌───────────────────────┐
│  Turn (existing) │          │  ReflectionRecord     │
├──────────────────┤          ├───────────────────────┤
│ messages[]       │ 1    0..N│ id: int (PK)          │
│ tool_calls[]     │──────────│ turn_id: str          │
│ errors[]         │          │ task_description      │
│ response         │          │ tool_calls: JSON[]    │
│ duration_ms      │          │ steps_taken: int      │
└──────────────────┘          │ errors: JSON[]        │
                              │ outcome: enum         │
                              │ duration_ms: int      │
                              │ lessons: JSON[]       │
                              │ created: float        │
                              └───────┬───────────────┘
                                      │
                         analyzes     │ 0..N
                                      ▼
                              ┌───────────────────────┐
                              │  ExperiencePattern    │
                              ├───────────────────────┤
                              │ id: int (PK)          │
                              │ trigger_context: JSON │
                              │ tool_sequence: JSON[] │
                              │ recommended_approach  │
                              │ success_count: int    │
                              │ failure_count: int    │
                              │ sample_size: int      │
                              │ first_observed: float │
                              │ last_applied: float   │
                              │ is_active: bool       │
                              └───────┬───────────────┘
                                      │
                         generates    │ 0..N
                                      ▼
                              ┌───────────────────────┐
                              │  SkillProposal        │
                              ├───────────────────────┤
                              │ (extends skills table) │
                              │ slug: str (PK)        │
                              │ name: str             │
                              │ description: str      │
                              │ code: str             │
                              │ scope: str            │
                              │ status: enum          │
                              │  → 'proposed'         │
                              │  → 'active'           │
                              │  → 'rejected'         │
                              │ created: float        │
                              │ updated: float        │
                              └───────────────────────┘

┌──────────────────┐
│  HarnessSnapshot │  (transient — computed on demand, not persisted)
├──────────────────┤
│ config: JSON     │
│ tools[]          │
│ permissions[]    │
│ memory_stats{}   │
│ loop_metrics{}   │
│ recommendations[]│
└──────────────────┘
```

---

## Entity Definitions

### ReflectionRecord

A structured analysis of a single agent turn, generated automatically after completion.

| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| `id` | int (PK) | Auto | Auto-incremented primary key | > 0 |
| `turn_id` | str | Yes | Unique identifier for the turn (UUID) | Non-empty, unique |
| `task_description` | str | Yes | Summary of the user's request | Max 500 chars |
| `tool_calls` | JSON[str] | Yes | List of tool names invoked during turn | Valid JSON array |
| `steps_taken` | int | Yes | Number of LLM+tool iterations | >= 0 |
| `errors` | JSON[obj] | No | List of errors with code and message | Valid JSON array or NULL |
| `outcome` | str | Yes | Overall result | One of: `success`, `partial`, `failure` |
| `duration_ms` | int | Yes | Total turn duration in milliseconds | >= 0 |
| `lessons_learned` | JSON[str] | No | Self-extracted lessons from this turn | Valid JSON array or NULL |
| `created` | float | Yes | Unix timestamp of record creation | > 0 |

### ExperiencePattern

A learned correlation between a task context and a recommended approach, derived from analyzing multiple reflection records.

| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| `id` | int (PK) | Auto | Auto-incremented primary key | > 0 |
| `trigger_context` | JSON | Yes | Description of conditions that match this pattern | Valid JSON |
| `tool_sequence` | JSON[str] | Yes | Ordered list of tools that form the pattern | Valid JSON array, non-empty |
| `recommended_approach` | str | Yes | Text description of the recommended strategy | Max 1000 chars |
| `success_count` | int | Yes | Times this pattern led to success | >= 0 |
| `failure_count` | int | Yes | Times this pattern led to failure | >= 0 |
| `sample_size` | int | Yes | Total observations (`success + failure`) | >= 1 for active patterns |
| `first_observed` | float | Yes | Unix timestamp of first observation | > 0 |
| `last_applied` | float | No | Unix timestamp of most recent use | NULL or > first_observed |
| `is_active` | bool | Yes | Whether pattern should be used for decision-making | Default: True |

### SkillProposal

A candidate skill created by the Synthesizer from detected repeated patterns. Extends the existing `skills` table with a `status` field.

| Field | Type | Required | Description | Values |
|-------|------|----------|-------------|--------|
| `slug` | str (PK) | Yes | Unique identifier for the skill | Auto-generated from pattern |
| `name` | str | Yes | Human-readable name | Derived from pattern |
| `description` | str | Yes | What the skill does | Auto-generated |
| `code` | str | Yes | Python source code | Generated by Synthesizer |
| `scope` | str | Yes | Skill visibility scope | `global` or `project` |
| `status` | str | Yes | Lifecycle state | `proposed` / `active` / `rejected` |
| `created` | float | Yes | Creation timestamp | Auto |
| `updated` | float | Yes | Last modification timestamp | Auto |

### HarnessSnapshot

A point-in-time diagnostic view of the agent's configuration and runtime state. Computed on demand — not stored in the database.

| Field | Type | Description |
|-------|------|-------------|
| `config` | JSON | Current AgentConfig values (loop settings, permissions, tools) |
| `tools` | JSON[] | List of registered tools with name, description, and call count |
| `permissions` | JSON[] | Active permission rules |
| `memory_stats` | JSON | Memory store statistics (total entries, by category, size) |
| `loop_metrics` | JSON | Turn budget stats, health history, error rates |
| `recommendations` | JSON[] | Auto-generated optimization suggestions |

---

## State Transitions

### SkillProposal State Machine

```
[proposed] ──user approves──▶ [active]
     │                            │
     └──user rejects────────────▶ [rejected]
     
     [active] ──user disables──▶ [rejected]  (future)
```

### Reflection Outcome

```
[success]  ← all tool calls completed, no errors
[partial]  ← some errors but task partially completed
[failure]  ← task failed or produced no useful result
```

---

## Validation Rules

| Rule | Description | Enforcement |
|------|-------------|-------------|
| R1 | Reflection records are immutable once written | No UPDATE allowed; only INSERT and SELECT |
| R2 | Experience patterns with `sample_size < 3` are not surfaced to the agent | Filtered in queries |
| R3 | Skill proposals with `status = 'proposed'` are not loaded by SkillsLoader | Filtered in `load_skills()` |
| R4 | HarnessSnapshot recommendations require `confidence > 0.5` to surface | Computed threshold |
| R5 | Background cycles skip if a user turn is in progress | Check via AgentState |

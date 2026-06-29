# Research: Autonomous Learning Agent

**Phase 0 output** — Technical research findings for design decisions.

---

## R1: Background Review Patterns (background_review.py)

**Source**: `src/nanoagent/memory/background_review.py`

### Decision
Extend the existing `BackgroundReview` pattern for background learning cycles.

### Rationale
- `BackgroundReview` already implements the scheduling pattern: it's instantiated in `_trigger_background_ops()` in `agent.py` and runs as a daemon thread
- It interacts with `SQLiteMemoryStore` for reading memories and storing review results
- The same threading + interval pattern can host reflection review cycles
- Background review is opt-in (configured in AgentConfig), matching our "opt-in" constraint

### Architecture Pattern
```
agent._trigger_background_ops()
  → BackgroundReview.start_if_due()
    → consolidates memories
    → (future) triggers reflection review
    → (future) triggers pattern detection
```

### Key Integration Points
- `agent.py` line ~490: `_trigger_background_ops()` called at end of `run()`
- `SQLiteMemoryStore.set_consolidator()` hooks the review cycle

---

## R2: Correction Detector Patterns (correction_detector.py)

**Source**: `src/nanoagent/memory/correction_detector.py`

### Decision
Model experience pattern detection on `CorrectionDetector`'s approach but generalize it.

### Rationale
- `CorrectionDetector` identifies failure → correction pairs in memory using string matching on content
- The same principle can be extended: instead of only detecting "failure → correction", detect any "context → outcome" pattern
- Current implementation is content-analysis based (scans memory entries), which is a good pattern for our experience matcher
- Integration with the memory store is well-established

### Architecture Pattern
```
correction_detector.is_correction(content) → bool (used in cli.py for real-time detection)
(proposed) experience.detect_pattern(reflection_records) → ExperiencePattern[]
```

---

## R3: Agent Loop Hooks for Reflection Trigger

**Source**: `src/nanoagent/agent/agent.py`, `src/nanoagent/loop/turn.py`

### Decision
Add post-turn reflection hook in `Agent.run()`, after the turn completes and before `_trigger_background_ops()`.

### Rationale
- The agent has 5 hook callbacks: `on_tool_call`, `on_tool_result`, `on_thinking`, `on_skill_call`, `on_paused`
- These are set externally (in `cli.py`) — we should follow the same pattern for `on_turn_complete`
- The `run()` method in `agent.py` is the single entry/exit point for all agent invocation
- Data available at completion: full message list, tool call results, response content, errors from the turn
- Adding `on_turn_complete` as a new hook follows the existing convention

### Hook Flow
```
run() →
  self.on_thinking()  # existing
  self.on_tool_call()  # existing
  self.on_tool_result()  # existing
  ...
  result = (response, messages)
  self.on_turn_complete(response, messages, tool_calls, errors, duration)  # NEW
  _trigger_background_ops()
  return result
```

### Key Files
- `agent.py` line ~490: `run()` method — add hook here
- `logging.py` line 74: `AgentLogger.tool_call()` — pattern for structured logging

---

## R4: SQLiteMemoryStore Schema Extensions

**Source**: `src/nanoagent/memory/sqlite_memory_store.py`

### Decision
Add two new tables to existing SQLite database: `reflection_records` and `experience_patterns`.

### Rationale
- Existing database at `~/.nanoagent/memory/global.db` already houses `memories` and `skills` tables
- No connection overhead — same database, same connection management
- Schema DDL follows existing patterns in `_create_tables()` method
- No migration needed — new tables are created on next startup via `CREATE TABLE IF NOT EXISTS`

### Existing Schema Patterns
```sql
CREATE TABLE IF NOT EXISTS memories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project TEXT, target TEXT, category TEXT, ...
    created REAL, last_referenced REAL
);
CREATE TABLE IF NOT EXISTS skills (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    slug TEXT UNIQUE, name TEXT, description TEXT, code TEXT, ...
    created REAL, updated REAL
);
```

### Proposed Table Schemas
```sql
CREATE TABLE IF NOT EXISTS reflection_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    turn_id TEXT NOT NULL,
    task_description TEXT,
    tool_calls TEXT,        -- JSON array
    steps_taken INTEGER,
    errors TEXT,            -- JSON array or NULL
    outcome TEXT,           -- 'success', 'partial', 'failure'
    duration_ms INTEGER,
    lessons_learned TEXT,   -- JSON array or NULL
    created REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS experience_patterns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trigger_context TEXT,   -- JSON: description of conditions
    tool_sequence TEXT,     -- JSON array of tool names
    recommended_approach TEXT,
    success_count INTEGER DEFAULT 0,
    failure_count INTEGER DEFAULT 0,
    sample_size INTEGER DEFAULT 0,
    first_observed REAL NOT NULL,
    last_applied REAL,
    is_active INTEGER DEFAULT 1
);
```

### Connection Management
- Reuse existing `SQLiteMemoryStore.conn` (single connection with WAL mode)
- Thread safety via `threading.Lock()` — same pattern as existing memory operations

---

## R5: CLI Command Patterns

**Source**: `src/nanoagent/cli.py` (~920 lines)

### Decision
Add new Click command groups `reflection` and `harness` following the `memory` group pattern.

### Rationale
- The `memory` command group at lines ~700-850 shows the established pattern:
  ```python
  @cli.group()
  def memory():
      """Inspect and manage agent memories."""
  
  @memory.command()
  @click.option(...)
  def list(...):
      ...
  ```
- Rich formatting with `Table` for list views, `Markdown` or `console.print()` for detail views
- Commands access the agent via `AgentJob` and `JobManager`
- New groups will sit at same level as `memory`, `chat`, `run`, `jobs`, `status`

### Proposed CLI Structure
```
nanoagent
├── chat
├── run
├── reflection       # NEW
│   ├── list         -- list recent reflections
│   ├── show         -- show reflection detail by ID
│   └── search       -- search reflections by keyword
├── harness          # NEW
│   ├── report       -- generate introspection report
│   └── analyze      -- run pattern detection on demand
├── memory
├── jobs
└── status
```

---

## R6: SkillStorage Patterns for Skill Creation

**Source**: `src/nanoagent/skills/skill_storage.py`, `src/nanoagent/skills/loader.py`

### Decision
Extend SkillStorage with a `propose_skill()` method that creates skill records with `status='proposed'` (new field). The SkillsLoader only loads skills with `status='active'`.

### Rationale
- `SkillStorage` stores skills in SQLite with fields: `slug, name, description, code, scope, created, updated`
- Skills are referenced by slug and loaded via `SkillsLoader.load_skills()` which queries all skills
- Adding a `status TEXT DEFAULT 'active'` field enables workflow: proposed → approved → active
- `SkillsLoader` filters by `status='active'`, so proposed skills don't affect runtime
- User-facing CLI command `nanoagent skill accept <slug>` changes status from 'proposed' to 'active'

### Skill Proposal Flow
```
1. Synthesizer detects pattern (3+ occurrences)
2. Generates skill code from pattern sequence
3. SkillStorage.add_skill(slug, name, desc, code, status='proposed')
4. User notified: "New skill proposed: summarize-python-files (nanoagent skill list --proposed)"
5. User runs: nanoagent skill accept summarize-python-files
6. SkillsLoader picks it up on next agent startup (or hot-reload)
```

### Existing Schema
```python
# skill_storage.py: stores in 'skills' table
slug: str           # unique identifier
name: str           # human-readable name
description: str    # what the skill does
code: str           # Python source code
scope: str          # 'global' or 'project'
created: float      # unix timestamp
updated: float      # unix timestamp
```

### Required Schema Change
```sql
-- Add status column (ALTER TABLE or CREATE IF NOT EXISTS with new schema)
ALTER TABLE skills ADD COLUMN status TEXT DEFAULT 'active';
-- Or for new DB:
CREATE TABLE IF NOT EXISTS skills (
    ..., status TEXT DEFAULT 'active'
);
```

---

## Consolidated Design Decisions

| Area | Decision | Rationale |
|------|----------|-----------|
| Reflection trigger | New `on_turn_complete` hook in `Agent.run()` | Follows existing hook pattern; single exit point |
| Reflector location | New `learning/reflector.py` module | Clean separation from existing memory/loop code |
| Pattern storage | New tables in existing SQLite DB | No new dependencies; reuses connection management |
| Pattern detection algorithm | Heuristic sequence matching (3+ occurrences) | Zero deps; sufficient for single-user agent |
| Background scheduling | Extend `BackgroundReview` threading pattern | Reuses existing infrastructure |
| Skill proposals | `status` field on skills table, filter by 'active' | Minimal schema change; clear workflow |
| CLI commands | `reflection` and `harness` groups | Follows `memory` group pattern |
| Opt-in learning | Disabled by default, enabled via config `[learning]` section | No surprises for existing users |

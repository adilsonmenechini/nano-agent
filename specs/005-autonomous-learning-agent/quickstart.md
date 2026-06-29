# Quickstart: Autonomous Learning Agent

**Validation guide** — runnable scenarios to verify the feature works end-to-end.

---

## Prerequisites

- Python 3.13+ with project dependencies installed (`pip install -e .`)
- Existing test suite passing (504 tests, 5 pre-existing failures)
- Working directory: project root

## Setup

No special setup required. All new tables are auto-created on first agent startup.

To enable learning (disabled by default):

```toml
# ~/.config/nanoagent/config.toml
[learning]
enabled = true
cycle_interval_turns = 5
```

---

## Validation Scenario 1: Post-Turn Reflection

**Objective**: Verify that the agent generates a reflection record after completing a task.

```bash
# Run a simple task
python -m nanoagent.cli run --provider openai --prompt "List Python files in current directory"

# Check the reflection was created
python -m nanoagent.cli reflection list --limit 5
```

**Expected outcome**: The `reflection list` command shows at least one entry with:
- Task description matching "List Python files..."
- Tool calls including `run_shell` or `glob_file`
- Outcome of "success" or "partial"
- Duration in milliseconds

**Automated test equivalent**:
```python
def test_reflection_created_after_turn():
    agent = create_test_agent()
    agent.on_turn_complete = mock.Mock()
    agent.run("hello")
    assert agent.on_turn_complete.called
    call_args = agent.on_turn_complete.call_args
    assert len(call_args[0]) == 4  # response, messages, tool_results, duration
```

---

## Validation Scenario 2: Reflection Retrieval

**Objective**: Verify reflection records are persistently stored and retrievable.

```bash
# Search reflections by keyword
python -m nanoagent.cli reflection search "Python files"

# Show specific reflection
python -m nanoagent.cli reflection show --turn-id <turn_id>
```

**Expected outcome**: Past reflections are searchable and displayable.

**Automated test equivalent**:
```python
def test_reflection_persistence():
    store = SQLiteMemoryStore(":memory:")
    reflector = Reflector(store)
    reflector.reflect(turn_id="test-1", messages=[], tool_results=[], duration_ms=100)
    records = reflector.get_recent(limit=10)
    assert len(records) == 1
    assert records[0].turn_id == "test-1"
```

---

## Validation Scenario 3: Harness Introspection

**Objective**: Verify the agent can analyze its own configuration and produce recommendations.

```bash
python -m nanoagent.cli harness report
```

**Expected outcome**: A structured report containing:
- Current agent configuration values
- List of registered built-in tools
- Permission rules (if configured)
- Memory statistics
- Optimization recommendations (may be empty for fresh install)

**Automated test equivalent**:
```python
def test_harness_snapshot():
    config = AgentConfig()
    registry = MockToolRegistry()
    analyzer = HarnessAnalyzer(config, registry)
    snapshot = analyzer.snapshot()
    assert "config" in snapshot
    assert "tools" in snapshot
    assert len(snapshot.tools) > 0  # built-in tools present
```

---

## Validation Scenario 4: Pattern Detection

**Objective**: Verify that repeated tool sequences are detected as experience patterns.

```python
# Automated test
def test_pattern_detection_after_multiple_similar_tasks():
    store = SQLiteMemoryStore(":memory:")
    reflector = Reflector(store)
    engine = ExperienceEngine(store)
    
    # Simulate 3 similar reflection records
    for i in range(3):
        reflector.reflect(
            turn_id=f"test-{i}",
            messages=[{"role": "user", "content": f"find files task {i}"}],
            tool_results=[
                ToolResult("glob_file", {"pattern": "*.py"}, ["a.py", "b.py"]),
                ToolResult("read_file", {"path": "a.py"}, "content..."),
            ],
            duration_ms=200,
        )
    
    # Run analysis
    reflections = reflector.get_recent(limit=10)
    patterns = engine.analyze_reflections(reflections)
    
    assert len(patterns) == 1  # One pattern detected
    assert patterns[0].sample_size == 3
    assert "glob_file" in patterns[0].tool_sequence
```

---

## Validation Scenario 5: Skill Proposal

**Objective**: Verify that repeated patterns lead to skill proposals.

```python
def test_skill_proposal_from_pattern():
    store = SQLiteMemoryStore(":memory:")
    skill_storage = SkillStorage(":memory:")
    synthesizer = Synthesizer(store, skill_storage)
    
    pattern = ExperiencePattern(
        trigger_context="find and read Python files",
        tool_sequence=["glob_file", "read_file"],
        recommended_approach="Use glob_file to find matching files, then read_file for each",
        success_count=3, failure_count=0, sample_size=3,
        ...
    )
    
    proposal = synthesizer.create_proposal(pattern)
    assert proposal.status == "proposed"
    
    # User should be able to accept
    skill_storage.activate_skill(proposal.slug)
    assert skill_storage.get_skill(proposal.slug).status == "active"
```

---

## Validation Scenario 6: Full Learning Cycle (Integration)

**Objective**: End-to-end verification that reflection → pattern → proposal flow works.

```bash
# Run multiple similar tasks
python -m nanoagent.cli run --prompt "Find all .py files in src/" --provider openai
python -m nanoagent.cli run --prompt "Find all .md files in docs/" --provider openai
python -m nanoagent.cli run --prompt "Find all .toml files in .specify/" --provider openai

# Check that a pattern was detected
python -m nanoagent.cli reflection list --limit 10
python -m nanoagent.cli harness analyze  # trigger pattern detection

# Check for skill proposals
python -m nanoagent.cli skill list --include-proposed
```

**Expected outcome**: After 3+ runs with similar tool sequences, the harness analyzer detects the pattern and creates a skill proposal.

---

## Running the Full Test Suite

```bash
# All new unit tests
python -m pytest tests/test_reflector.py tests/test_experience.py \
    tests/test_background.py tests/test_synthesizer.py \
    tests/test_introspection.py -v

# Memory integration tests  
python -m pytest tests/test_memory/test_reflections.py -v

# Full end-to-end
python -m pytest tests/integration/test_learning.py -v

# Smoke test — ensure no regressions
python -m pytest tests/ -q --tb=short
```

## Key Artifacts

| Artifact | Location | Description |
|----------|----------|-------------|
| Reflection records | `~/.nanoagent/memory/global.db` → `reflection_records` table | Per-turn analysis |
| Experience patterns | `~/.nanoagent/memory/global.db` → `experience_patterns` table | Learned correlations |
| Skill proposals | `~/.nanoagent/memory/global.db` → `skills` table with `status='proposed'` | Candidate skills |
| Harness snapshots | Computed in memory | Point-in-time config view |

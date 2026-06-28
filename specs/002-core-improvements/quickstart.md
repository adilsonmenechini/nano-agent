# Quickstart: Core Agent Improvements Validation

## Prerequisites

- Python 3.13+
- Dev dependencies installed: `pip install -e ".[dev]"`
- Provider API keys set in environment or config file (optional for mocked tests)

## Validation Scenarios

### 1. Streaming Response

```bash
# Run the agent with streaming enabled
echo "Tell me a story about a robot" | nanoagent --stream
```

**Expected**: Output appears token-by-token, not all at once.

**Test**:
```bash
pytest tests/test_streaming.py -v
```

---

### 2. Configurable Parameters

```bash
# Set a low max_tokens and observe truncation
NANOAGENT_MAX_TOKENS=50 echo "Write a very long essay about Python" | nanoagent
```

**Expected**: Response is short (~50 tokens), clearly truncated.

**Test**:
```bash
pytest tests/test_agent.py -v -k "test_max_tokens"
```

---

### 3. Semantic Memory

```bash
# Use the agent normally — semantic memory is automatically used for retrieval
# Memories stored during conversation are retrieved by meaning, not just keywords
pytest tests/test_embeddings.py -v
```

**Expected**: Embedding-based search returns semantically similar memories even with no keyword overlap.

**Test**:
```bash
pytest tests/test_embeddings.py -v
```

---

### 4. Skills Loaded from Database

```bash
# Add a skill, restart agent, invoke it
nanoagent --add-skill examples/my-skill.skill.md
nanoagent --run-skill my-skill
```

**Expected**: Skill executes even though it was never registered via code.

**Test**:
```bash
pytest tests/test_skills_db.py -v
```

---

### 5. State Machine Transitions

```bash
# Run the agent with verbose state logging
nanoagent --verbose --state-log
```

**Expected**: Output shows state transitions: IDLE → THINKING → (EXECUTING_TOOLS → THINKING)* → IDLE

**Test**:
```bash
pytest tests/test_state_machine.py -v
```

---

### 6. Health Check

```bash
nanoagent health
```

**Expected**: Table showing each provider and its connection status (✅ connected / ❌ disconnected).

---

### 7. CI Quality Checks

```bash
# Run all quality checks locally
ruff check src/ tests/
pyright src/
vulture src/nanoagent/ --min-confidence 65
pytest --cov=src/nanoagent/ --cov-fail-under=80
```

**Expected**: All commands pass without errors.

---

### 8. Config File

```bash
# Create a config file
cat > ~/.config/nanoagent/config.toml << EOF
[agent]
stream = true
retry_attempts = 5
EOF

# Run agent — should use config values
nanoagent --check-config
```

**Expected**: Agent reports "Config loaded from ~/.config/nanoagent/config.toml" with the correct values.

---

## Integration Test Suite

```bash
# Run all new integration tests
pytest tests/integration/ -v

# Run full suite with coverage
pytest --cov=src/nanoagent/ --cov-report=term-missing
```

## Reference

- [Data Model](data-model.md) — entity definitions and validation rules
- [Provider Contract](contracts/provider-interface.md) — LLM provider interface
- [Tool Contract](contracts/tool-interface.md) — tool decorator and registry
- [Skill Contract](contracts/skill-interface.md) — skill loading and execution
- [Config Contract](contracts/config-contract.md) — configuration file schema
- [State Machine](contracts/state-machine.md) — state transitions and callbacks

# Skill Interface Contract

## Skill Definition

A skill is stored in the database and loaded at runtime.

### Storage Schema

```yaml
# Stored as YAML frontmatter + code body in SQLite
name: my-skill
description: What this skill does
version: 1
dependencies:      # Optional: required tools
  - web_search
  - file_read
tools:             # Optional: tools this skill provides
  - my_custom_tool
---
def execute(context, **kwargs):
    """Main skill entry point.
    
    Args:
        context: SkillContext with access to tools and agent state
        **kwargs: Parameters from the skill invocation
    """
    result = context.tools.web_search(query=kwargs["query"])
    return result
```

### SkillContext (Runtime Injection)

Skills receive a `SkillContext` object with:

| Attribute | Type | Description |
|-----------|------|-------------|
| `tools` | `ToolRegistry` | All registered tools |
| `memory` | `SQLiteMemoryStore` | Memory access |
| `agent_state` | `AgentState` | Current agent state |
| `logger` | `Logger` | Structured logger |

### Execution Flow

1. Agent starts → `SkillLoader.load_all()` queries DB for all skills
2. Each skill's `dependencies` are validated against registered tools
3. Skills registered in agent's skill registry with `SkillWrapper`
4. When invoked, `SkillWrapper` creates `SkillContext` and calls `execute(context, **kwargs)`

### Versioning

- Each `save` creates a new version (monotonic integer)
- `list_versions(skill_id)` returns all versions with timestamps
- `rollback(skill_id, version)` restores a previous version
- Only the latest version is loaded at startup

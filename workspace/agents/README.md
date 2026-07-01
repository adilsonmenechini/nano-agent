# Agents Directory

Each file in this directory defines a **specialized agent personality** that can be invoked
with `@agent-name` in chat (e.g., `@sre-engineer investigate cpu spike`).

Agents extend the base `AGENT.md` instructions with role-specific system prompts,
restricted tool sets, and skill dependencies.

---

## Schema

```yaml
# workspace/agents/<name>.yaml

name: <string>                    # Required. Agent identifier (used as @name)
description: <string>             # Required. Short description of the agent's role
system_prompt: |                  # Required. The role-specific system prompt
  You are a ...
tools:                            # Optional. Allowed tools (default: all built-in)
  - run_shell
  - read_file
  - web_search
skills:                           # Optional. Skills to load into this agent's context
  - skill-drive
memory_scope: global | project    # Optional. Default: global
```

### Fields

| Field | Required | Description |
|-------|----------|-------------|
| `name` | ✅ | Used as `@name` in chat. Lowercase, hyphens recommended. |
| `description` | ✅ | Shown in `/agents` listing. |
| `system_prompt` | ✅ | The core personality + instructions for this agent. |
| `tools` | ❌ | Whitelist of tool names. Omit = all built-in tools. |
| `skills` | ❌ | Skill slugs to automatically load into context. |
| `memory_scope` | ❌ | `global` (default) or `project` — which memory to inject. |

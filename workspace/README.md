# NanoAgent Workspace

The `workspace/` directory is the **context and orchestration hub** for NanoAgent.
It follows a structure inspired by `.claude/` conventions, adapted for NanoAgent's
Python-based architecture.

---

## Directory Structure

```
workspace/
├── README.md           ← This file — entry point
├── AGENT.md            ← Global agent instructions (loaded for every turn)
├── USER.md             ← User preferences (name, timezone, etc.)
├── agents/             ← Specialized agent personalities (@name)
│   ├── README.md       ← Agent YAML schema documentation
│   ├── sre-engineer.yaml
│   └── architect.yaml
├── commands/           ← Deterministic workflow atalhos (/name)
│   ├── README.md       ← Command YAML schema documentation
│   ├── incident.yaml
│   └── review.yaml
├── skills/             ← Reusable skill packages (SKILL.md)
│   ├── skill-drive/
│   ├── skill-creator/
│   └── skill-smart/
├── memory/             ← SQLite database + session data
└── mcp.json            ← MCP server configuration
```

---

## How It Works

### AGENT.md + USER.md (always loaded)
- `AGENT.md`: Instructions for **all** agent interactions (project-wide context)
- `USER.md`: User-specific preferences and context

### @agents (specialized personalities)
Agents in `workspace/agents/` extend the base `AGENT.md` with:
- **Role-specific system prompt** (personality, expertise, behavior)
- **Tool whitelist** (which tools this agent may use)
- **Skill dependencies** (automatically loaded skills)
- **Memory scope** (global or project)

Invoke with `@agent-name <prompt>` — e.g., `@sre-engineer investigate cpu spike`.

### /commands (deterministic workflows)
Commands in `workspace/commands/` define multi-step orchestrations:
- **Steps** that call tools, run LLM prompts, or both
- **Dependencies** create execution DAGs (parallel where possible)
- **Variable interpolation** — `{step_name}` references previous step outputs
- **Arguments** — CLI-style parameters passed at invocation

Invoke with `/command-name <args>` — e.g., `/incident INC-2024-07-15`.

### skills/ (knowledge packages)
Skills follow the existing `SKILL.md` format with YAML frontmatter:
- **name** — Slug used for dependency resolution in agent YAMLs
- **description** — When the skill triggers
- **triggers** — Keywords for automatic activation

Skills are loaded from `workspace/skills/<name>/SKILL.md`.

---

## Quick Reference

| Type | Syntax | Example | Purpose |
|------|--------|---------|---------|
| Agent | `@name <prompt>` | `@sre-engineer check logs` | Specialized personality |
| Command | `/name <args>` | `/incident 12345` | Multi-step workflow |
| Skill | Auto-loaded | `skill-drive` | Reusable knowledge |
| Shell | `! <command>` | `! kubectl get pods` | One-off shell command |
| Memory | `/memory search <q>` | `/memory search deploy` | FTS5 memory search |

---

## Next Steps

Fases planejadas:
1. ✅ **Fase 1**: Schemas YAML para agents + commands (concluída)
2. ⏳ **Fase 2**: Workspace Engine — loader, router, executor (src/nanoagent/workspace/)
3. ⏳ **Fase 3**: Integração CLI + Web UI

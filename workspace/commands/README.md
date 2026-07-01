# Commands Directory

Each file in this directory defines a **deterministic workflow** that can be invoked
with `/command-name <args>` in chat (e.g., `/incident 12345`).

Commands are multi-step orchestrations. Each step can:
- Call a tool (shell, file, web, git, etc.)
- Run an LLM prompt
- Reference outputs from previous steps via `{step_name}` variables

---

## Schema

```yaml
# workspace/commands/<name>.yaml

name: <string>                    # Required. Command identifier (used as /name)
description: <string>             # Required. Shown in /commands listing
arguments:                        # Optional. CLI-style arguments
  - name: <string>
    type: string | int | bool
    required: true | false
    description: <string>
steps:                            # Required. Ordered list of execution steps
  - name: <string>                # Step ID, referenced by depends_on
    tool: <string>                # Tool to call (omit if using prompt)
    prompt: <string>              # LLM prompt (omit if using tool)
    args:                         # Arguments for the tool
      key: value                  # Supports {step_name} variable interpolation
    depends_on:                   # Optional. Steps that must complete first
      - <step_name>
    description: <string>         # Optional. Displayed during execution
```

### Variable Interpolation

Steps can reference outputs from previous steps using `{step_name}` syntax:

```yaml
steps:
  - name: fetch_logs
    tool: run_shell
    args:
      command: "kubectl logs pod/{pod_name}"
  - name: analyze
    prompt: "Analyze these logs: {fetch_logs}"
    depends_on:
      - fetch_logs
```

### Execution Rules

1. Steps without `depends_on` run in **parallel**
2. Steps with `depends_on` wait for all dependencies to complete
3. Step outputs are stored by `name` for variable interpolation
4. If a step has both `tool` and `prompt`, the tool result is passed to the LLM
5. Steps fail fast — if any step errors, the workflow stops

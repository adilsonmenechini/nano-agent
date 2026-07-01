# CLI Interface Contract: Agent Loop

## NanoAgent Command Interface

The agent loop adds new flags and display elements to the existing CLI.

### Existing Commands (Extended)

```
nanoagent [OPTIONS] [PROMPT]
```

### New Flags

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--diagnostics` / `-d` | flag | `False` | Enable diagnostics mode — shows per-phase timing and health metrics |
| `--max-steps` | int | `50` | Override maximum steps per turn |
| `--tool-timeout` | float | `30.0` | Override tool call timeout in seconds |
| `--health` / `-H` | flag | `False` | Show health indicator in prompt line (requires --diagnostics) |

### Interactive Mode Changes

In interactive (REPL) mode, the prompt line may include:

- **Health indicator** (when `--health` + `--diagnostics`): `[🟢 healthy] ›` or `[🟡 degraded] ›` or `[🟠 warning] ›` or `[🔴 critical] ›`
- **Phase indicator**: Visible during turn execution showing current phase

### Diagnostics Output Format

When `--diagnostics` is active, after each turn print a structured block:

```
━━━ Diagnostics ━━━
Phase Timing:
  explore:   0.042s
  execute:   1.237s
  verify:    0.018s
Total: 1.297s
Health: 0.92 (healthy)
Steps: 7/50
Tool calls: 5 (3 unique)
───────────────────
```

### Non-Interactive Mode

For single-prompt mode (`nanoagent "prompt"`), `--diagnostics` can be used for one-shot diagnostics output.

### Error Output

When `--diagnostics` is active and a healing action occurs:

```
━━━ Healing Action ━━━
Fault: OSCILLATION
Strategy: break_oscillation
Result: ✅ Success (0.003s)
━━━━━━━━━━━━━━━━━━━━━
```

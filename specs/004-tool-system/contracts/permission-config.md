# Permission Configuration Contract

**File**: `~/.config/nanoagent/config.toml`

**Section**: `[tools.permissions]`

## Schema

```toml
[tools.permissions]
# Default mode when no rule matches: "allow" or "deny"
default_mode = "allow"

# Optional: global truncation threshold in characters
max_output_chars = 10_240

# Rules: each key is a unique rule identifier
[tools.permissions.rules]
# Format: <rule_name> = { tool = "<tool>", type = "<match_type>", pattern = "<pattern>", mode = "<mode>" }

# Deny specific dangerous shell commands (prefix match)
deny_rm = { tool = "run_shell", type = "prefix", pattern = "rm -rf", mode = "deny" }
deny_sudo = { tool = "run_shell", type = "prefix", pattern = "sudo", mode = "ask" }
deny_dd = { tool = "run_shell", type = "prefix", pattern = "dd", mode = "deny" }
deny_chmod = { tool = "run_shell", type = "prefix", pattern = "chmod 777", mode = "deny" }

# Allow read operations (tool-level)
allow_read = { tool = "read_file", type = "exact", pattern = "*", mode = "allow" }
allow_glob = { tool = "glob_file", type = "exact", pattern = "*", mode = "allow" }
allow_grep = { tool = "grep_file", type = "exact", pattern = "*", mode = "allow" }

# Shell wildcard permission
allow_safe_shell = { tool = "run_shell", type = "prefix", pattern = "echo", mode = "allow" }
allow_shell_git = { tool = "run_shell", type = "prefix", pattern = "git", mode = "allow" }

# Block dangerous file writes
deny_overwrite_binaries = { tool = "write_file", type = "regex", pattern = "\\.(exe|dll|so|dylib|bin)$", mode = "ask" }
```

## Validation Rules

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| `tool` | `string` | ✅ | Must match a registered tool name or be `"*"` |
| `type` | `string` | ✅ | Must be one of: `"exact"`, `"prefix"`, `"regex"` |
| `pattern` | `string` | ✅ | Non-empty string |
| `mode` | `string` | ✅ | Must be one of: `"allow"`, `"deny"`, `"ask"` |
| `default_mode` | `string` | ✅ (in section) | Must be `"allow"` or `"deny"` |

## Error Handling

- Invalid mode value → raise `PermissionConfigError` at load time
- Missing `tool` field → skip rule with warning
- Unparseable TOML → existing config.py error handling (silent fallback to defaults)

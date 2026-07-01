# Configuration Contract

## Config File

Location: `~/.config/nanoagent/config.toml`

### Schema

```toml
# Provider configuration
[provider.openai]
api_key = "${OPENAI_API_KEY}"      # Env var reference
max_tokens = 4096
temperature = 0.7

[provider.anthropic]
api_key = "${ANTHROPIC_API_KEY}"
max_tokens = 4096
temperature = 0.7

[provider.lm_studio]
base_url = "http://localhost:1234/v1"
max_tokens = 4096
temperature = 0.0

# Agent behavior
[agent]
retry_attempts = 3
stream = true
default_provider = "openai"

# Memory
[memory]
embedding_model = "all-MiniLM-L6-v2"
importance_decay_days = 30
max_context_tokens = 8192
```

### Resolution Order

1. CLI argument (highest priority)
2. Environment variable (`NANOAGENT_*`)
3. Config file
4. Hardcoded default (lowest priority)

### Env Var Mapping

| Config Path | Env Var | Type |
|-------------|---------|------|
| `provider.openai.api_key` | `OPENAI_API_KEY` | str |
| `provider.anthropic.api_key` | `ANTHROPIC_API_KEY` | str |
| `provider.lm_studio.base_url` | `LM_STUDIO_BASE_URL` | str |
| `agent.retry_attempts` | `NANOAGENT_RETRY_ATTEMPTS` | int |
| `agent.stream` | `NANOAGENT_STREAM` | bool |
| `agent.default_provider` | `NANOAGENT_DEFAULT_PROVIDER` | str |

### Backward Compatibility

- All existing env-var-only configs continue to work
- Config file is optional — absence is not an error
- Mixing env vars and config file: env vars take precedence

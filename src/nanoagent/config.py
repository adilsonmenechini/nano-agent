import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List
from dotenv import load_dotenv
from nanoagent.loop.constants import DEFAULT_CONFIG, LoopConfig

# Load environment variables from .env file
load_dotenv()

_CONFIG_FILE_PATH = Path("~/.config/nanoagent/config.toml").expanduser()


def _load_toml_config(path: Path) -> dict:
    """Load config from TOML file, return empty dict on any failure."""
    try:
        import tomllib
    except ImportError:
        return {}
    if not path.exists():
        return {}
    try:
        with open(path, "rb") as f:
            return tomllib.load(f)
    except Exception:
        return {}


def _get_toml_str(toml: dict, *keys: str) -> str | None:
    """Safely traverse nested TOML keys."""
    val: dict | str | None = toml
    for k in keys:
        if not isinstance(val, dict):
            return None
        val = val.get(k)
    return val if isinstance(val, str) else None


def _get_toml_int(toml: dict, *keys: str, default: int = 0) -> int:
    val: dict | int | None = toml
    for k in keys:
        if not isinstance(val, dict):
            return default
        val = val.get(k)
    return val if isinstance(val, int) else default


def _get_toml_bool(toml: dict, *keys: str, default: bool = False) -> bool:
    val: dict | bool | None = toml
    for k in keys:
        if not isinstance(val, dict):
            return default
        val = val.get(k)
    return val if isinstance(val, bool) else default


def _get_toml_float(toml: dict, *keys: str, default: float = 0.0) -> float:
    val: dict | float | None = toml
    for k in keys:
        if not isinstance(val, dict):
            return default
        val = val.get(k)
    return val if isinstance(val, (int, float)) else default


@dataclass
class LLMProviderConfig:
    api_key: str
    base_url: str
    model: str


@dataclass
class AgentConfig:
    default_provider: str = ""
    project_path: Optional[str] = None
    review_enabled: bool = True
    flush_min_turns: int = 6
    nudge_interval: int = 10
    nudge_tool_calls: int = 15
    max_tokens: int = 4096
    temperature: float = 0.7
    retry_attempts: int = 3
    stream: bool = True
    providers: dict = field(default_factory=dict)
    mcp_servers: List[str] = field(default_factory=list)
    loop: LoopConfig = field(default_factory=lambda: DEFAULT_CONFIG)

    def __init__(self, config_path: str | None = None):
        toml = _load_toml_config(Path(config_path) if config_path else _CONFIG_FILE_PATH)

        self.default_provider = (
            os.getenv("NANOAGENT_DEFAULT_PROVIDER")
            or _get_toml_str(toml, "agent", "default_provider")
            or os.getenv("DEFAULT_PROVIDER", "openai")
        )
        self.project_path = (
            os.getenv("PROJECT_PATH")
            or _get_toml_str(toml, "agent", "project_path")
            or None
        )
        self.permissions_config = toml.get("tools", {}).get("permissions", {}) if isinstance(toml.get("tools"), dict) else {}
        self.max_output_chars = _get_toml_int(
            toml, "tools", "permissions", "max_output_chars", default=10_240
        )
        self.review_enabled = (
            os.getenv("MEMORY_REVIEW_ENABLED", str(
                _get_toml_bool(toml, "agent", "review_enabled", default=True)
            )).lower() == "true"
        )
        self.flush_min_turns = int(
            os.getenv("MEMORY_FLUSH_MIN_TURNS", str(
                _get_toml_int(toml, "agent", "flush_min_turns", default=6)
            ))
        )
        self.nudge_interval = int(
            os.getenv("MEMORY_NUDGE_INTERVAL", str(
                _get_toml_int(toml, "agent", "nudge_interval", default=10)
            ))
        )
        self.nudge_tool_calls = int(
            os.getenv("MEMORY_NUDGE_TOOL_CALLS", str(
                _get_toml_int(toml, "agent", "nudge_tool_calls", default=15)
            ))
        )
        self.max_tokens = int(
            os.getenv("NANOAGENT_MAX_TOKENS", str(
                _get_toml_int(toml, "agent", "max_tokens", default=4096)
            ))
        )
        self.temperature = float(
            os.getenv("NANOAGENT_TEMPERATURE", str(
                _get_toml_float(toml, "agent", "temperature", default=0.7)
            ))
        )
        self.retry_attempts = int(
            os.getenv("NANOAGENT_RETRY_ATTEMPTS", str(
                _get_toml_int(toml, "agent", "retry_attempts", default=3)
            ))
        )
        self.stream = (
            os.getenv("NANOAGENT_STREAM", str(
                _get_toml_bool(toml, "agent", "stream", default=True)
            )).lower() in ("true", "1", "yes")
        )

        # Build provider configs: TOML overrides defaults, env overrides everything
        base_providers = {
            "openai": LLMProviderConfig(
                api_key=(os.getenv("OPENAI_API_KEY")
                         or _get_toml_str(toml, "provider", "openai", "api_key")
                         or ""),
                base_url=(os.getenv("OPENAI_BASE_URL")
                          or os.getenv("OPENAI_API_URL")
                          or _get_toml_str(toml, "provider", "openai", "base_url")
                          or "https://api.openai.com/v1"),
                model=(os.getenv("OPENAI_MODEL")
                       or _get_toml_str(toml, "provider", "openai", "model")
                       or "gpt-4o"),
            ),
            "anthropic": LLMProviderConfig(
                api_key=(os.getenv("ANTHROPIC_API_KEY")
                         or _get_toml_str(toml, "provider", "anthropic", "api_key")
                         or ""),
                base_url=(os.getenv("ANTHROPIC_BASE_URL")
                          or os.getenv("ANTHROPIC_API_URL")
                          or _get_toml_str(toml, "provider", "anthropic", "base_url")
                          or "https://api.anthropic.com"),
                model=(os.getenv("ANTHROPIC_MODEL")
                       or _get_toml_str(toml, "provider", "anthropic", "model")
                       or "claude-3-5-sonnet-20241022"),
            ),
            "lmstudio": LLMProviderConfig(
                api_key=(os.getenv("LMSTUDIO_API_KEY")
                         or _get_toml_str(toml, "provider", "lmstudio", "api_key")
                         or "lmstudio"),
                base_url=(os.getenv("LMSTUDIO_BASE_URL")
                          or _get_toml_str(toml, "provider", "lmstudio", "base_url")
                          or "http://localhost:1234/v1"),
                model=(os.getenv("LMSTUDIO_MODEL")
                       or _get_toml_str(toml, "provider", "lmstudio", "model")
                       or "local-model"),
            ),
        }
        self.providers = base_providers

        mcp_val = os.getenv("MCP_SERVERS", "")
        if not mcp_val and toml:
            mcp_list = toml.get("agent", {}).get("mcp_servers", [])
            if isinstance(mcp_list, list):
                mcp_val = ",".join(str(s) for s in mcp_list)
        self.mcp_servers = [
            s.strip() for s in mcp_val.split(",") if s.strip()
        ]

        loop_section = toml.get("loop", {}) if isinstance(toml.get("loop"), dict) else {}
        self.loop = LoopConfig(
            max_steps_per_turn=int(
                os.getenv("NANOAGENT_MAX_STEPS", str(
                    _get_toml_int(loop_section, "max_steps_per_turn", default=50)
                ))
            ),
            tool_timeout_seconds=float(
                os.getenv("NANOAGENT_TOOL_TIMEOUT", str(
                    _get_toml_float(loop_section, "tool_timeout_seconds", default=30.0)
                ))
            ),
            llm_timeout_seconds=float(
                os.getenv("NANOAGENT_LLM_TIMEOUT", str(
                    _get_toml_float(loop_section, "llm_timeout_seconds", default=120.0)
                ))
            ),
            stall_threshold=int(
                os.getenv("NANOAGENT_STALL_THRESHOLD", str(
                    _get_toml_int(loop_section, "stall_threshold", default=5)
                ))
            ),
            oscillation_window=int(
                os.getenv("NANOAGENT_OSCILLATION_WINDOW", str(
                    _get_toml_int(loop_section, "oscillation_window", default=3)
                ))
            ),
            compaction_threshold=float(
                os.getenv("NANOAGENT_COMPACTION_THRESHOLD", str(
                    _get_toml_float(loop_section, "compaction_threshold", default=0.80)
                ))
            ),
            diagnostics_enabled=(
                os.getenv("NANOAGENT_DIAGNOSTICS", str(
                    _get_toml_bool(loop_section, "diagnostics_enabled", default=False)
                )).lower() in ("true", "1", "yes")
            ),
            health_window_size=int(
                os.getenv("NANOAGENT_HEALTH_WINDOW", str(
                    _get_toml_int(loop_section, "health_window_size", default=20)
                ))
            ),
        )

    def get_provider_config(self, provider_name: str) -> Optional[LLMProviderConfig]:
        return self.providers.get(provider_name)

    def set_provider_config(self, provider_name: str, config: LLMProviderConfig):
        self.providers[provider_name] = config

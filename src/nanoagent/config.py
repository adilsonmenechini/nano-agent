import os
from dataclasses import dataclass, field
from typing import Optional, List
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


@dataclass
class LLMProviderConfig:
    """Configuration for an LLM provider."""

    api_key: str
    base_url: str
    model: str
    # Additional provider-specific settings can be added here


@dataclass
class AgentConfig:
    default_provider: str = os.getenv("DEFAULT_PROVIDER", "openai")
    project_path: Optional[str] = os.getenv("PROJECT_PATH") or None
    review_enabled: bool = os.getenv("MEMORY_REVIEW_ENABLED", "true").lower() == "true"
    flush_min_turns: int = int(os.getenv("MEMORY_FLUSH_MIN_TURNS", "6"))
    nudge_interval: int = int(os.getenv("MEMORY_NUDGE_INTERVAL", "10"))
    nudge_tool_calls: int = int(os.getenv("MEMORY_NUDGE_TOOL_CALLS", "15"))
    providers: dict = field(
        default_factory=lambda: {
            "openai": LLMProviderConfig(
                api_key=os.getenv("OPENAI_API_KEY", ""),
                base_url=os.getenv("OPENAI_BASE_URL") or os.getenv("OPENAI_API_URL", "https://api.openai.com/v1"),
                model=os.getenv("OPENAI_MODEL", "gpt-4o"),
            ),
            "anthropic": LLMProviderConfig(
                api_key=os.getenv("ANTHROPIC_API_KEY", ""),
                base_url=os.getenv("ANTHROPIC_BASE_URL") or os.getenv("ANTHROPIC_API_URL", "https://api.anthropic.com"),
                model=os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022"),
            ),
            "lmstudio": LLMProviderConfig(
                api_key=os.getenv("LMSTUDIO_API_KEY", "lmstudio"),
                base_url=os.getenv("LMSTUDIO_BASE_URL", "http://localhost:1234/v1"),
                model=os.getenv("LMSTUDIO_MODEL", "local-model"),
            ),
        }
    )
    mcp_servers: List[str] = field(
        default_factory=lambda: [
            server.strip()
            for server in os.getenv("MCP_SERVERS", "").split(",")
            if server.strip()
        ]
    )

    def get_provider_config(self, provider_name: str) -> Optional[LLMProviderConfig]:
        """Get the configuration for a specific provider."""
        return self.providers.get(provider_name)

    def set_provider_config(self, provider_name: str, config: LLMProviderConfig):
        """Set or update the configuration for a provider."""
        self.providers[provider_name] = config

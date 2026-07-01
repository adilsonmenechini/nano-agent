from __future__ import annotations


class AgentError(Exception):
    """Base error for all nano-agent errors."""


class ProviderError(AgentError):
    """Base error for LLM provider communication issues."""


class ProviderRetryableError(ProviderError):
    """Transient error — safe to retry (timeout, 429, 5xx)."""


class ProviderFatalError(ProviderError):
    """Permanent error — do not retry (auth, 400, model not found)."""


class ConfigError(AgentError):
    """Configuration loading or validation error."""


class SkillError(AgentError):
    """Skill execution or loading error."""


class MemoryError(AgentError):
    """Memory storage or retrieval error."""


class StateTransitionError(AgentError):
    """Invalid state machine transition."""

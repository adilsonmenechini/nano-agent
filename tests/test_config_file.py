import os
import tempfile
from pathlib import Path

import pytest


def test_config_defaults():
    from nanoagent.config import AgentConfig
    config = AgentConfig(config_path="/nonexistent/config.toml")
    assert config.max_tokens == 4096
    assert config.temperature == 0.7
    assert config.retry_attempts == 3
    assert config.stream is True
    assert config.default_provider == "openai"


def test_config_env_var_overrides_default():
    import os
    os.environ["NANOAGENT_MAX_TOKENS"] = "512"
    try:
        from nanoagent.config import AgentConfig
        config = AgentConfig(config_path="/nonexistent/config.toml")
        assert config.max_tokens == 512
    finally:
        del os.environ["NANOAGENT_MAX_TOKENS"]


def test_config_file_overrides_default():
    content = """[agent]
max_tokens = 2048
temperature = 0.5
retry_attempts = 5
stream = false
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write(content)
        tmp_path = f.name
    try:
        from nanoagent.config import AgentConfig
        config = AgentConfig(config_path=tmp_path)
        assert config.max_tokens == 2048
        assert config.temperature == 0.5
        assert config.retry_attempts == 5
        assert config.stream is False
    finally:
        os.unlink(tmp_path)


def test_env_var_overrides_config_file():
    content = """[agent]
max_tokens = 9999
stream = false
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write(content)
        tmp_path = f.name
    os.environ["NANOAGENT_MAX_TOKENS"] = "500"
    os.environ["NANOAGENT_STREAM"] = "true"
    try:
        from nanoagent.config import AgentConfig
        config = AgentConfig(config_path=tmp_path)
        assert config.max_tokens == 500
        assert config.stream is True
    finally:
        del os.environ["NANOAGENT_MAX_TOKENS"]
        del os.environ["NANOAGENT_STREAM"]
        os.unlink(tmp_path)


def test_missing_config_file_not_an_error():
    from nanoagent.config import AgentConfig
    config = AgentConfig(config_path="/tmp/__nonexistent_nanoagent_config__/config.toml")
    assert config.max_tokens == 4096
    assert config.providers is not None


def test_provider_config_from_toml():
    content = """[provider.openai]
api_key = "test-key-123"
base_url = "https://custom.example.com/v1"
model = "gpt-4o-mini"
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write(content)
        tmp_path = f.name
    try:
        from nanoagent.config import AgentConfig
        config = AgentConfig(config_path=tmp_path)
        openai_cfg = config.get_provider_config("openai")
        assert openai_cfg is not None
        assert openai_cfg.api_key == "test-key-123"
        assert openai_cfg.base_url == "https://custom.example.com/v1"
    finally:
        os.unlink(tmp_path)

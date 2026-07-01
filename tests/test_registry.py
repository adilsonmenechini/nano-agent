"""Tests for ToolRegistry."""


import pytest

from nanoagent.registry import ToolRegistry
from nanoagent.tool import Tool


@pytest.fixture
def registry():
    return ToolRegistry()


class TestToolRegistry:
    def test_register_tool_instance(self, registry):
        t = Tool(lambda x: x, name="echo")
        result = registry.register(t)
        assert result.name == "echo"
        assert registry.get("echo") is t

    def test_register_callable(self, registry):
        def fn(x):
            return x

        t = registry.register(fn, name="callable_fn")
        assert t.name == "callable_fn"
        assert registry.get("callable_fn") is t

    def test_register_callable_no_name(self, registry):
        """Registering a function infers its name."""

        def my_func():
            pass

        t = registry.register(my_func)
        assert t.name == "my_func"

    def test_get_nonexistent(self, registry):
        assert registry.get("nope") is None

    def test_remove(self, registry):
        t = Tool(lambda x: x, name="temp")
        registry.register(t)
        assert registry.get("temp") is t
        registry.remove("temp")
        assert registry.get("temp") is None

    def test_remove_nonexistent(self, registry):
        registry.remove("nope")  # should not raise

    def test_all(self, registry):
        t1 = Tool(lambda: 1, name="one")
        t2 = Tool(lambda: 2, name="two")
        registry.register(t1)
        registry.register(t2)
        tools = registry.all()
        assert len(tools) == 2
        assert {t.name for t in tools} == {"one", "two"}

    def test_names(self, registry):
        t1 = Tool(lambda: 1, name="alpha")
        t2 = Tool(lambda: 2, name="beta")
        registry.register(t1)
        registry.register(t2)
        assert set(registry.names()) == {"alpha", "beta"}

    def test_openai_schemas(self, registry):
        t = Tool(lambda x: x, name="test_fn")
        registry.register(t)
        schemas = registry.openai_schemas()
        assert len(schemas) == 1
        assert schemas[0]["type"] == "function"

    def test_anthropic_schemas(self, registry):
        t = Tool(lambda x: x, name="test_fn")
        registry.register(t)
        schemas = registry.anthropic_schemas()
        assert len(schemas) == 1
        assert "name" in schemas[0]

    def test_execute(self, registry):
        t = Tool(lambda x: x * 2, name="double")
        registry.register(t)
        result = registry.execute("double", {"x": 5})
        assert result == "10"

    def test_execute_unknown_tool(self, registry):
        result = registry.execute("ghost", {})
        assert "unknown tool" in result

    def test_execute_error(self, registry):
        t = Tool(lambda: 1 / 0, name="broken")
        registry.register(t)
        result = registry.execute("broken", {})
        assert "Error executing" in result

    def test_execute_parallel(self, registry):
        t1 = Tool(lambda x: x, name="add")
        t2 = Tool(lambda y: y, name="mul")
        registry.register(t1)
        registry.register(t2)
        results = registry.execute_parallel([("add", {"x": 1}), ("mul", {"y": 2})])
        assert len(results) == 2
        assert results[0] == "1" or results[0] == "2"

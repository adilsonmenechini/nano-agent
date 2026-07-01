"""Tests for type-to-JSON-schema conversion and Tool class."""

from __future__ import annotations

from typing import Any, Optional, Union

from nanoagent.tool import Tool, infer_parameters_schema, py_to_json_schema, tool


class TestPyToJsonSchema:
    def test_str(self):
        assert py_to_json_schema(str) == {"type": "string"}

    def test_int(self):
        assert py_to_json_schema(int) == {"type": "integer"}

    def test_float(self):
        assert py_to_json_schema(float) == {"type": "number"}

    def test_bool(self):
        assert py_to_json_schema(bool) == {"type": "boolean"}

    def test_none_type(self):
        assert py_to_json_schema(type(None)) == {"type": "null"}

    def test_any(self):
        assert py_to_json_schema(Any) == {}

    def test_optional_str(self):
        result = py_to_json_schema(Optional[str])
        assert result["type"] == "string"
        assert result["nullable"] is True

    def test_optional_int(self):
        result = py_to_json_schema(Optional[int])
        assert result["type"] == "integer"
        assert result["nullable"] is True

    def test_list_str(self):
        result = py_to_json_schema(list[str])
        assert result["type"] == "array"
        assert result["items"]["type"] == "string"

    def test_list_mixed(self):
        result = py_to_json_schema(list)
        assert isinstance(result, dict)

    def test_dict_str_int(self):
        result = py_to_json_schema(dict[str, int])
        assert result["type"] == "object"
        assert "additionalProperties" in result

    def test_union_str_int(self):
        result = py_to_json_schema(Union[str, int])
        assert "anyOf" in result
        assert len(result["anyOf"]) == 2

    def test_literal(self):
        from typing import Literal

        result = py_to_json_schema(Literal["red", "green", "blue"])
        assert result["type"] == "string"
        assert result["enum"] == ["red", "green", "blue"]

    def test_fallback_unknown_type(self):
        class CustomType:
            pass

        result = py_to_json_schema(CustomType)
        assert result == {}


class TestToolDecorator:
    def test_tool_no_args(self):
        @tool
        def greet(name: str) -> str:
            return f"Hello {name}"

        assert isinstance(greet, Tool)
        assert greet.name == "greet"
        assert greet(name="world") == "Hello world"

    def test_tool_with_args(self):
        @tool(name="add_numbers", description="Add two numbers")
        def add(a: int, b: int) -> int:
            return a + b

        assert add.name == "add_numbers"
        assert add.description == "Add two numbers"
        assert add(a=3, b=4) == 7

    def test_tool_schema_openai(self):
        @tool
        def search(q: str, limit: int = 10) -> str:
            return f"Searching for {q}"

        schema = search.schema
        assert schema["type"] == "function"
        assert schema["function"]["name"] == "search"
        assert "parameters" in schema["function"]

    def test_tool_schema_anthropic(self):
        @tool
        def lookup(id: int) -> str:
            return f"Item {id}"

        schema = lookup.anthropic_schema
        assert "name" in schema
        assert "input_schema" in schema

    def test_tool_call(self):
        @tool
        def double(x: int) -> int:
            return x * 2

        result = double(x=5)
        assert result == 10

    def test_tool_to_openai_tool_call(self):
        @tool
        def fetch(url: str) -> str:
            return f"Fetched {url}"

        result = fetch.to_openai_tool_call({"url": "https://example.com"})
        assert result["role"] == "tool"
        assert "Fetched" in result["content"]


class TestInferParametersSchema:
    def test_basic_params(self):
        def fn(name: str, age: int) -> None:
            pass

        schema = infer_parameters_schema(fn)
        assert schema["type"] == "object"
        assert "name" in schema["properties"]
        assert "age" in schema["properties"]
        assert sorted(schema["required"]) == ["age", "name"]

    def test_params_with_defaults(self):
        def fn(name: str, age: int = 18) -> None:
            pass

        schema = infer_parameters_schema(fn)
        assert "age" not in (schema.get("required") or [])
        assert "default" in schema["properties"]["age"]

    def test_skips_return_and_private(self):
        def fn(x: int, _secret: str = "hidden") -> str:
            return str(x)

        schema = infer_parameters_schema(fn)
        assert "x" in schema["properties"]
        assert "_secret" not in schema["properties"]

    def test_empty_function(self):
        def fn() -> None:
            pass

        schema = infer_parameters_schema(fn)
        assert schema["type"] == "object"


class TestToolEdgeCases:
    def test_tool_empty_name_falls_back(self):
        t = Tool(lambda: 42)
        assert t.name == "<lambda>"

    def test_tool_parameters(self):
        @tool
        def add(a: int, b: int) -> int:
            return a + b

        assert isinstance(add.parameters, dict)
        assert "a" in add.parameters["properties"]
        assert "b" in add.parameters["properties"]

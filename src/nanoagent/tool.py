"""Lightweight tool system with automatic schema inference from type hints.

Usage:
    @tool
    def add(a: int, b: int) -> int:
        \"\"\"Add two numbers.\"\"\"
        return a + b

    print(add.schema)
    # -> {"type": "function", "function": {"name": "add", "description": "Add two numbers.", ...}}
"""

from __future__ import annotations

import inspect
import json
import typing
from collections.abc import Callable
from typing import Any, get_args, get_origin, get_type_hints

_SIMPLE_TYPES: dict[object, dict] = {
    str: {"type": "string"},
    int: {"type": "integer"},
    float: {"type": "number"},
    bool: {"type": "boolean"},
    Any: {},
    type(None): {"type": "null"},
}


def py_to_json_schema(tp: object) -> dict:
    """Convert a Python type annotation to a JSON Schema fragment."""
    if tp in _SIMPLE_TYPES:
        return dict(_SIMPLE_TYPES[tp])

    origin = get_origin(tp)
    args = get_args(tp)

    # Optional[X] == Union[X, None]
    if origin is type(None) or (origin is typing.Union and type(None) in args):
        non_none = [a for a in args if a is not type(None)]
        if len(non_none) == 1:
            inner = py_to_json_schema(non_none[0])
            inner["nullable"] = True
            return inner
        inner = py_to_json_schema(non_none[0]) if non_none else {"type": "null"}
        inner["nullable"] = True
        return inner

    # Union[X, Y]
    if origin is typing.Union:
        return {"anyOf": [py_to_json_schema(a) for a in args]}

    # Literal["a", "b"]
    if origin is typing.Literal:
        return {"type": "string", "enum": list(args)}

    # list[X]
    if origin is list:
        item = py_to_json_schema(args[0]) if args else {}
        return {"type": "array", "items": item}

    # dict[str, X]
    if origin is dict:
        addl = {}
        if args:
            addl["additionalProperties"] = (
                py_to_json_schema(args[1]) if len(args) > 1 else {}
            )
        return {"type": "object", **addl}

    # Fallback
    return {}


def infer_parameters_schema(fn: Callable) -> dict:
    """Build an OpenAI-compatible parameters schema from a function's signature.

    Returns {"type": "object", "properties": {...}, "required": [...]}.
    """
    sig = inspect.signature(fn)
    hints = get_type_hints(fn, globalns=getattr(fn, "__globals__", None), localns=None)
    properties = {}
    required = []

    for name, param in sig.parameters.items():
        if name == "return" or name.startswith("_"):
            continue
        tp = hints.get(name, str)
        prop = py_to_json_schema(tp)
        if param.default is inspect.Parameter.empty:
            required.append(name)
        elif param.default is not None:
            # set default value as schema default
            try:
                json.dumps(param.default)
                prop["default"] = param.default
            except (TypeError, ValueError):
                pass
        if param.default is not None and name not in required:
            prop["default"] = (
                param.default if param.default is not inspect.Parameter.empty else None
            )
        properties[name] = prop

    return {"type": "object", "properties": properties, "required": required}


class Tool:
    """A callable tool with an auto-generated OpenAI-compatible schema.

    Attributes:
        name: Tool name (used by the LLM to invoke it).
        description: What the tool does.
        fn: The underlying Python function.
        parameters: JSON Schema for the function parameters.
    """

    def __init__(
        self, fn: Callable, *, name: str | None = None, description: str | None = None
    ):
        self.name = name or fn.__name__
        self.description = description or (fn.__doc__ or "").strip()
        self.fn = fn
        self.parameters = infer_parameters_schema(fn)

    def __call__(self, **kwargs: Any) -> Any:
        return self.fn(**kwargs)

    @property
    def schema(self) -> dict:
        """OpenAI-compatible tool definition."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }

    @property
    def anthropic_schema(self) -> dict:
        """Anthropic-compatible tool definition."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.parameters,
        }

    def to_openai_tool_call(self, arguments: dict) -> dict:
        """Wrap execution result as an OpenAI-style tool call message."""
        result = self.fn(**arguments)
        return {
            "role": "tool",
            "tool_call_id": f"call_{self.name}",
            "content": str(result),
        }


def tool(
    fn: Callable | None = None,
    *,
    name: str | None = None,
    description: str | None = None,
) -> Callable | Tool:
    """Decorator that converts a function into a ``Tool`` with auto-generated schema.

    Can be used with or without arguments::

        @tool
        def add(a: int, b: int) -> int: ...

        @tool(name="multiply", description="Multiply two numbers")
        def mul(a: int, b: int) -> int: ...
    """
    if fn is not None:
        return Tool(fn, name=name, description=description)

    def _wrap(f: Callable) -> Tool:
        return Tool(f, name=name, description=description)

    return _wrap

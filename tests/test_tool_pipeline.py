"""Tests for DAG-based tool execution pipeline."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from nanoagent.tool_pipeline import (
    DAGValidationError,
    PipelineExecutionError,
    PipelineStep,
    ToolPipeline,
    create_pipeline,
)


@pytest.fixture
def registry():
    r = MagicMock()
    results_store: dict[str, str] = {}

    def execute(name, args):
        if name in results_store:
            return results_store[name]
        # Build result from all arg values
        arg_parts = []
        if args:
            for v in args.values():
                arg_parts.append(str(v) if not isinstance(v, (dict, list)) else str(v))
        arg_str = ":".join(arg_parts) if arg_parts else ""
        result = f"result:{name}:{arg_str}"
        results_store[name] = result
        return result

    r.execute.side_effect = execute
    return r


class TestToolPipeline:
    def test_single_step(self, registry):
        pipe = ToolPipeline(
            [
                PipelineStep("greet", "echo", {"input": "hello"}),
            ]
        )
        results = pipe.execute(registry)
        assert results["greet"] == "result:echo:hello"

    def test_linear_pipeline(self, registry):
        pipe = ToolPipeline(
            [
                PipelineStep("a", "tool_a", {"input": "start"}),
                PipelineStep(
                    "b", "tool_b", {"input": "{{a.result}}"}, depends_on=["a"]
                ),
                PipelineStep(
                    "c", "tool_c", {"input": "{{b.result}}"}, depends_on=["b"]
                ),
            ]
        )
        results = pipe.execute(registry)
        assert results["a"] == "result:tool_a:start"
        assert results["b"] == "result:tool_b:result:tool_a:start"
        assert results["c"] == "result:tool_c:result:tool_b:result:tool_a:start"

    def test_parallel_steps(self, registry):
        pipe = ToolPipeline(
            [
                PipelineStep("a", "tool_a", {"input": "x"}),
                PipelineStep("b", "tool_b", {"input": "y"}),
                PipelineStep(
                    "c", "tool_c", {"input": "{{a.result}}"}, depends_on=["a"]
                ),
            ]
        )
        results = pipe.execute(registry)
        assert results["a"] == "result:tool_a:x"
        assert results["b"] == "result:tool_b:y"
        # c depends on a — must have a's result
        assert "result:tool_a:x" in results["c"]

    def test_diamond_dag(self, registry):
        """Diamond: a -> b, a -> c, b&c -> d"""
        pipe = ToolPipeline(
            [
                PipelineStep("a", "tool_a", {"input": "base"}),
                PipelineStep(
                    "b", "tool_b", {"input": "{{a.result}}"}, depends_on=["a"]
                ),
                PipelineStep(
                    "c", "tool_c", {"input": "{{a.result}}"}, depends_on=["a"]
                ),
                PipelineStep(
                    "d",
                    "tool_d",
                    {"input": "{{b.result}}|{{c.result}}"},
                    depends_on=["b", "c"],
                ),
            ]
        )
        results = pipe.execute(registry)
        assert results["a"] == "result:tool_a:base"
        assert "result:tool_b" in results["b"]
        assert "result:tool_c" in results["c"]
        assert results["b"] in results["d"]
        assert results["c"] in results["d"]

    def test_cycle_detected(self):
        pipe = ToolPipeline(
            [
                PipelineStep("a", "t1", depends_on=["c"]),
                PipelineStep("b", "t2", depends_on=["a"]),
                PipelineStep("c", "t3", depends_on=["b"]),
            ]
        )
        with pytest.raises(DAGValidationError, match="Cycle detected"):
            pipe.validate()

    def test_missing_dependency(self):
        pipe = ToolPipeline(
            [
                PipelineStep("a", "t1", depends_on=["nonexistent"]),
            ]
        )
        with pytest.raises(DAGValidationError, match="nonexistent"):
            pipe.validate()

    def test_no_args_pipeline(self, registry):
        pipe = ToolPipeline(
            [
                PipelineStep("a", "tool_a"),
                PipelineStep("b", "tool_b", depends_on=["a"]),
            ]
        )
        results = pipe.execute(registry)
        assert results["a"] == "result:tool_a:"
        assert results["b"] == "result:tool_b:"

    def test_static_args_no_templates(self, registry):
        pipe = ToolPipeline(
            [
                PipelineStep("a", "calc", {"x": 42, "y": "hello"}),
            ]
        )
        results = pipe.execute(registry)
        assert "42" in results["a"]

    def test_execute_sequential(self, registry):
        pipe = ToolPipeline(
            [
                PipelineStep("a", "ta", {"input": "1"}),
                PipelineStep("b", "tb", {"input": "{{a.result}}"}, depends_on=["a"]),
            ]
        )
        results = pipe.execute_sequential(registry)
        assert results["a"] == "result:ta:1"
        assert results["b"] == "result:tb:result:ta:1"

    def test_create_pipeline_from_dicts(self, registry):
        pipe = create_pipeline(
            [
                {"name": "a", "tool_name": "ta", "arguments": {"input": "hi"}},
                {
                    "name": "b",
                    "tool_name": "tb",
                    "arguments": {"input": "{{a.result}}"},
                    "depends_on": ["a"],
                },
            ]
        )
        results = pipe.execute(registry)
        assert results["a"] == "result:ta:hi"
        assert "hi" in results["b"]

    def test_validation_on_valid_dag(self):
        pipe = ToolPipeline(
            [
                PipelineStep("a", "t1"),
                PipelineStep("b", "t2", depends_on=["a"]),
            ]
        )
        pipe.validate()  # should not raise

    def test_validate_on_empty_pipeline(self):
        with pytest.raises(DAGValidationError):
            ToolPipeline([])

    def test_multiple_independent_chains(self, registry):
        """Two independent chains run in parallel."""
        pipe = ToolPipeline(
            [
                PipelineStep("a1", "t1", {"input": "chain1"}),
                PipelineStep("a2", "t2", {"input": "{{a1.result}}"}, depends_on=["a1"]),
                PipelineStep("b1", "t3", {"input": "chain2"}),
                PipelineStep("b2", "t4", {"input": "{{b1.result}}"}, depends_on=["b1"]),
            ]
        )
        results = pipe.execute(registry)
        assert "chain1" in results["a2"]
        assert "chain2" in results["b2"]

    def test_step_error_bubbles_up(self, registry):
        registry.execute.side_effect = ValueError("tool failed")
        pipe = ToolPipeline(
            [
                PipelineStep("a", "failing_tool"),
            ]
        )
        with pytest.raises(PipelineExecutionError):
            pipe.execute(registry)

    def test_nested_dict_args(self, registry):
        pipe = ToolPipeline(
            [
                PipelineStep("a", "ta", {"input": "hello"}),
                PipelineStep(
                    "b",
                    "tb",
                    {
                        "nested": {"key": "{{a.result}}"},
                        "list": ["{{a.result}}", "static"],
                    },
                    depends_on=["a"],
                ),
            ]
        )
        results = pipe.execute(registry)
        assert "hello" in results["b"]

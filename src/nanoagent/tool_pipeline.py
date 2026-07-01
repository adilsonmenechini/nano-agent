"""DAG-based tool execution pipeline.

Allows defining tool steps with dependency ordering. Steps without dependencies
execute in parallel; steps with dependencies wait for their prerequisites.

Usage:
    pipe = ToolPipeline([
        PipelineStep("fetch", "web_fetch", {"url": "https://example.com"}),
        PipelineStep("parse", "html_parse", {"html": "{{fetch.result}}"}, depends_on=["fetch"]),
        PipelineStep("summarize", "llm_summarize", {"text": "{{parse.result}}"}, depends_on=["parse"]),
    ])
    results = pipe.execute(registry)
"""

from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any


class DAGValidationError(Exception):
    """Raised when the pipeline DAG has cycles or missing dependencies."""


class PipelineExecutionError(Exception):
    """Raised when a step in the pipeline fails execution."""


@dataclass
class PipelineStep:
    """A single step in a tool pipeline.

    Attributes:
        name: Unique step identifier.
        tool_name: Name of the tool to execute (must be registered in ToolRegistry).
        arguments: Arguments to pass to the tool. Can reference prior step
            results via ``{{step_name.result}}`` syntax.
        depends_on: Names of steps that must complete before this one.
    """

    name: str
    tool_name: str
    arguments: dict[str, Any] | None = None
    depends_on: list[str] | None = None


_TEMPLATE_RE = re.compile(r"\{\{(\w+)\.result\}\}")


def _resolve_templates(value: str, step_results: dict[str, str]) -> str:
    """Replace ``{{step.result}}`` placeholders with actual step outputs."""

    def _replacer(m: re.Match) -> str:
        step_name = m.group(1)
        if step_name not in step_results:
            raise PipelineExecutionError(
                f"Cannot resolve template '{{{step_name}.result}}': "
                f"step '{step_name}' has no result yet"
            )
        return step_results[step_name]

    return _TEMPLATE_RE.sub(_replacer, value)


def _resolve_args(
    args: dict[str, Any],
    step_results: dict[str, str],
) -> dict[str, Any]:
    """Recursively resolve template references in arguments."""
    resolved: dict[str, Any] = {}
    for key, val in args.items():
        if isinstance(val, str):
            resolved[key] = _resolve_templates(val, step_results)
        elif isinstance(val, dict):
            resolved[key] = _resolve_args(val, step_results)
        elif isinstance(val, list):
            resolved[key] = [
                _resolve_templates(item, step_results)
                if isinstance(item, str)
                else item
                for item in val
            ]
        else:
            resolved[key] = val
    return resolved


def _topological_sort(
    steps: list[PipelineStep],
) -> list[PipelineStep]:
    """Topologically sort steps using Kahn's algorithm.

    Returns steps in execution order (dependencies first).
    Raises DAGValidationError if a cycle is detected.
    """
    names = {s.name for s in steps}
    # Validate all dependency names exist
    for s in steps:
        if s.depends_on:
            for dep in s.depends_on:
                if dep not in names:
                    raise DAGValidationError(
                        f"Step '{s.name}' depends on '{dep}' which is not a defined step. "
                        f"Available steps: {sorted(names)}"
                    )

    # Build adjacency list and in-degree counts
    in_degree: dict[str, int] = {s.name: 0 for s in steps}
    adjacency: dict[str, list[str]] = {s.name: [] for s in steps}

    for s in steps:
        if s.depends_on:
            for dep in s.depends_on:
                adjacency[dep].append(s.name)
                in_degree[s.name] = in_degree.get(s.name, 0) + 1

    # Kahn's algorithm
    queue = [s.name for s in steps if in_degree.get(s.name, 0) == 0]
    sorted_names: list[str] = []
    step_map = {s.name: s for s in steps}

    while queue:
        name = queue.pop(0)
        sorted_names.append(name)
        for neighbor in adjacency.get(name, []):
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    if len(sorted_names) != len(steps):
        cycle_steps = [s.name for s in steps if s.name not in sorted_names]
        raise DAGValidationError(
            f"Cycle detected in pipeline involving steps: {cycle_steps}"
        )

    return [step_map[name] for name in sorted_names]


class ToolPipeline:
    """A DAG-based tool execution pipeline.

    Steps declare dependencies; the pipeline resolves execution order,
    runs independent steps in parallel, and passes results downstream.
    """

    def __init__(self, steps: list[PipelineStep]):
        if not steps:
            raise DAGValidationError("Pipeline must contain at least one step")
        self.steps = list(steps)

    def validate(self) -> None:
        """Validate the DAG: check dependencies and detect cycles."""
        _topological_sort(self.steps)

    def _execute_step(
        self,
        step: PipelineStep,
        registry: Any,
        step_results: dict[str, str],
    ) -> tuple[str, str]:
        """Execute a single step and return (step_name, result)."""
        args = _resolve_args(step.arguments or {}, step_results)
        try:
            result = registry.execute(step.tool_name, args)
        except Exception as exc:
            raise PipelineExecutionError(
                f"Step '{step.name}' (tool: {step.tool_name}) failed: {exc}"
            ) from exc
        return step.name, result

    def execute(
        self,
        registry: Any,
        parallel: bool = True,
    ) -> dict[str, str]:
        """Execute all steps respecting dependency ordering.

        Args:
            registry: ToolRegistry instance with registered tools.
            parallel: If True, steps with no unfulfilled dependencies run concurrently.

        Returns:
            Dict mapping step name to result string.

        Raises:
            DAGValidationError: If the DAG is invalid.
            PipelineExecutionError: If a step fails.
        """
        sorted_steps = _topological_sort(self.steps)
        step_results: dict[str, str] = {}
        completed: set[str] = set()

        if parallel:
            return self._execute_parallel(
                sorted_steps, registry, step_results, completed
            )
        return self._execute_sequential(sorted_steps, registry, step_results)

    def _execute_sequential(
        self,
        sorted_steps: list[PipelineStep],
        registry: Any,
        step_results: dict[str, str],
    ) -> dict[str, str]:
        """Execute steps one at a time in dependency order."""
        for step in sorted_steps:
            name, result = self._execute_step(step, registry, step_results)
            step_results[name] = result
        return step_results

    def _execute_parallel(
        self,
        sorted_steps: list[PipelineStep],
        registry: Any,
        step_results: dict[str, str],
        completed: set[str],
    ) -> dict[str, str]:
        """Execute steps with parallel execution where dependencies allow."""
        remaining = {s.name: s for s in sorted_steps}

        while remaining:
            # Find steps whose dependencies are all satisfied
            ready = []
            for name, step in list(remaining.items()):
                deps = step.depends_on or []
                if all(d in completed for d in deps):
                    ready.append(step)
                    del remaining[name]

            if not ready and remaining:
                # Shouldn't happen if topological sort is correct
                raise DAGValidationError(
                    f"Deadlock: no ready steps but {len(remaining)} remain"
                )

            if len(ready) == 1:
                name, result = self._execute_step(ready[0], registry, step_results)
                step_results[name] = result
                completed.add(name)
            else:
                with ThreadPoolExecutor(max_workers=min(len(ready), 4)) as pool:
                    fut_map = {
                        pool.submit(
                            self._execute_step, step, registry, step_results
                        ): step.name
                        for step in ready
                    }
                    for fut in as_completed(fut_map):
                        name, result = fut.result()
                        step_results[name] = result
                        completed.add(name)

        return step_results

    def execute_sequential(self, registry: Any) -> dict[str, str]:
        """Execute all steps one at a time in dependency order."""
        return self.execute(registry, parallel=False)


def create_pipeline(steps: list[dict]) -> ToolPipeline:
    """Create a ToolPipeline from a list of dict configs.

    Each dict should have keys: name, tool_name, arguments (optional), depends_on (optional).

    Example::

        pipe = create_pipeline([
            {"name": "fetch", "tool_name": "web_fetch", "arguments": {"url": "..."}},
            {"name": "parse", "tool_name": "html_parse",
             "arguments": {"html": "{{fetch.result}}"}, "depends_on": ["fetch"]},
        ])
    """
    pipeline_steps = [
        PipelineStep(
            name=s["name"],
            tool_name=s["tool_name"],
            arguments=s.get("arguments"),
            depends_on=s.get("depends_on"),
        )
        for s in steps
    ]
    return ToolPipeline(pipeline_steps)

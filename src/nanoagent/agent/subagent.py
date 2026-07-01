"""Multi-agent delegation — spawn child Agent instances for independent tasks.

Each subagent runs its own `Agent.run()` loop with a filtered toolset
and shares the parent's memory store.
"""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from threading import Lock
from typing import Any


@dataclass
class SubAgentTask:
    """Definition of a task to be executed by a child agent.

    Attributes:
        name: Unique name for this task.
        prompt: User prompt to send to the child agent.
        system_prompt: Optional system prompt override.
        max_iterations: Max iterations for the child agent loop.
        tools: Tool names to expose to the child. None = all parent tools.
    """

    name: str
    prompt: str
    system_prompt: str | None = None
    max_iterations: int = 5
    tools: list[str] | None = None


@dataclass
class SubAgentResult:
    """Outcome of a delegated sub-agent task.

    Attributes:
        name: Task name this result corresponds to.
        success: Whether execution completed without error.
        response: The response text from the agent.
        messages: Full message list from the agent run.
        error: Error message if execution failed.
        duration_ms: Wall-clock time in milliseconds.
    """

    name: str
    success: bool
    response: str = ""
    messages: list[dict] | None = None
    error: str | None = None
    duration_ms: float = 0.0


def _copy_tools(source: Any, target: Any, tool_names: list[str] | None) -> None:
    """Copy tools from source agent to target agent.

    Copies both ToolRegistry tools and legacy tools.
    If tool_names is provided, only copies those tools.
    """
    all_tools = dict(source.tools)
    for tname, tool_obj in all_tools.items():
        if tool_names is not None and tname not in tool_names:
            continue
        target.register_tool(tname, tool_obj)


class SubAgentManager:
    """Manages spawning and coordination of child agent instances.

    Each child agent shares the parent's memory store and project path
    but runs its own independent execution loop.
    """

    def __init__(
        self,
        parent_agent: Any,
        llm_provider: Any = None,
    ):
        self._parent = parent_agent
        self._llm_provider = llm_provider
        self._results: dict[str, SubAgentResult] = {}
        self._lock = Lock()

    def _create_child(self, task: SubAgentTask) -> Any:
        """Create a new Agent instance configured for the sub-task."""
        from nanoagent.agent.agent import Agent

        child = Agent(
            project_path=self._parent.project_path,
            db_path=self._parent.memory.db_path
            if hasattr(self._parent.memory, "db_path")
            else None,
            llm_provider=self._llm_provider or self._parent.llm_provider,
        )
        _copy_tools(self._parent, child, task.tools)
        return child

    def _run_single(self, task: SubAgentTask) -> SubAgentResult:
        """Execute a single sub-task and return its result."""
        start = time.perf_counter()
        try:
            child = self._create_child(task)
            response, messages = child.run(
                prompt=task.prompt,
                system_prompt=task.system_prompt,
                max_iterations=task.max_iterations,
            )
            elapsed = (time.perf_counter() - start) * 1000
            return SubAgentResult(
                name=task.name,
                success=True,
                response=response,
                messages=messages,
                duration_ms=elapsed,
            )
        except Exception as exc:
            elapsed = (time.perf_counter() - start) * 1000
            return SubAgentResult(
                name=task.name,
                success=False,
                error=str(exc),
                duration_ms=elapsed,
            )

    def delegate(self, task: SubAgentTask) -> SubAgentResult:
        """Spawn a child agent for a single task and wait for completion."""
        result = self._run_single(task)
        with self._lock:
            self._results[task.name] = result
        return result

    def delegate_all(
        self,
        tasks: list[SubAgentTask],
        parallel: bool = True,
    ) -> list[SubAgentResult]:
        """Spawn child agents for multiple tasks.

        If parallel=True, tasks run concurrently using a thread pool.
        Returns results in the same order as ``tasks``.
        """
        if not tasks:
            return []

        if not parallel:
            return [self.delegate(t) for t in tasks]

        results: list[SubAgentResult | None] = [None] * len(tasks)
        with ThreadPoolExecutor(max_workers=min(len(tasks), 4)) as pool:
            fut_map = {
                pool.submit(self._run_single, tasks[i]): i for i in range(len(tasks))
            }
            for fut in as_completed(fut_map):
                idx = fut_map[fut]
                results[idx] = fut.result()

        # Store results
        with self._lock:
            for r in results:
                if r:
                    self._results[r.name] = r

        return results  # type: ignore[return-value]

    def delegate_sequential(self, tasks: list[SubAgentTask]) -> list[SubAgentResult]:
        """Run tasks one at a time in order."""
        return self.delegate_all(tasks, parallel=False)

    def get_result(self, name: str) -> SubAgentResult | None:
        """Retrieve a stored result by task name."""
        with self._lock:
            return self._results.get(name)

    def all_results(self) -> dict[str, SubAgentResult]:
        """Return all stored results."""
        with self._lock:
            return dict(self._results)

    def clear_results(self) -> None:
        """Clear all stored results."""
        with self._lock:
            self._results.clear()

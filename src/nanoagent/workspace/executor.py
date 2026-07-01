"""Command workflow executor — runs DAG of steps using agent's tools and LLM.

Supports:
- Tool steps: call a registered tool
- Prompt steps: send a prompt to the LLM
- Variable interpolation: {step_name} in args and prompts
- DAG ordering: steps without dependencies run first
- Parallel execution where possible

Note: The DAG execution logic here mirrors tool_pipeline.py's topological
sort and parallel execution, but extends it to support both tool and prompt
steps. A future refactor could unify the two executors.
"""

from __future__ import annotations

import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any

from .models import CommandStep, CommandWorkflow

# Variable interpolation: {step_name} or {arg_name}
_VAR_RE = re.compile(r"\{(\w+)\}")


@dataclass
class StepResult:
    """Result of executing a single step."""

    name: str
    success: bool
    output: str = ""
    error: str = ""
    duration_ms: float = 0.0


@dataclass
class WorkflowResult:
    """Result of executing a complete command workflow."""

    command_name: str
    success: bool
    step_results: dict[str, StepResult] = field(default_factory=dict)
    final_output: str = ""
    duration_ms: float = 0.0
    error: str | None = None

    @property
    def output(self) -> str:
        """Return the last step's output as the final result."""
        if self.final_output:
            return self.final_output
        if self.step_results:
            last_step = list(self.step_results.values())[-1]
            return last_step.output
        return ""


def _resolve_vars(text: str, variables: dict[str, str]) -> str:
    """Replace {var_name} placeholders with values from variables dict."""

    def _replacer(m: re.Match) -> str:
        key = m.group(1)
        return variables.get(key, f"{{{key}}}")

    return _VAR_RE.sub(_replacer, text)


def _resolve_args(args: dict[str, Any], variables: dict[str, str]) -> dict[str, Any]:
    """Recursively resolve variable references in step arguments."""
    resolved: dict[str, Any] = {}
    for key, val in args.items():
        if isinstance(val, str):
            resolved[key] = _resolve_vars(val, variables)
        elif isinstance(val, dict):
            resolved[key] = _resolve_args(val, variables)
        elif isinstance(val, list):
            resolved[key] = [
                _resolve_vars(item, variables) if isinstance(item, str) else item
                for item in val
            ]
        else:
            resolved[key] = val
    return resolved


class WorkflowExecutor:
    """Executes command workflows by orchestrating tool calls and LLM prompts.

    Bridges between the workspace command system and the agent's existing
    tool registry and LLM provider.

    Example::

        executor = WorkflowExecutor(agent)
        result = executor.execute(workflow, {"incident_id": "INC-123"})
        print(result.output)
    """

    def __init__(self, agent: Any) -> None:
        self._agent = agent

    def execute(
        self,
        workflow: CommandWorkflow,
        args: dict[str, str] | None = None,
        on_step_start: Any = None,
        on_step_complete: Any = None,
    ) -> WorkflowResult:
        """Execute a command workflow.

        Args:
            workflow: The command workflow to execute.
            args: Arguments to pass to the workflow.
            on_step_start: Optional callback(step_name, description) called before each step.
            on_step_complete: Optional callback(step_name, result) called after each step.

        Returns:
            WorkflowResult with all step outputs and final result.
        """
        # Validate arguments before execution
        workflow.validate_args(args or {})

        start_time = time.monotonic()
        variables = dict(args or {})
        step_outputs: dict[str, str] = {}
        step_results: dict[str, StepResult] = {}

        # Build dependency graph
        remaining: dict[str, CommandStep] = {s.name: s for s in workflow.steps}

        while remaining:
            # Find steps whose deps are satisfied
            batch: list[CommandStep] = []
            for name, step in list(remaining.items()):
                deps_met = all(d in step_outputs for d in step.depends_on)
                if deps_met:
                    batch.append(step)
                    del remaining[name]

            if not batch:
                return WorkflowResult(
                    command_name=workflow.name,
                    success=False,
                    step_results=step_results,
                    error=f"Deadlock: remaining steps {list(remaining.keys())} have unsatisfied dependencies",
                    duration_ms=(time.monotonic() - start_time) * 1000,
                )

            # Execute batch (parallel if multiple)
            if len(batch) == 1:
                self._run_step(
                    batch[0],
                    variables,
                    step_outputs,
                    step_results,
                    on_step_start,
                    on_step_complete,
                )
            else:
                self._run_parallel(
                    batch,
                    variables,
                    step_outputs,
                    step_results,
                    on_step_start,
                    on_step_complete,
                )

            # Merge new outputs into variables for next round
            variables.update(step_outputs)

        elapsed = (time.monotonic() - start_time) * 1000
        all_success = all(r.success for r in step_results.values())
        last_output = list(step_outputs.values())[-1] if step_outputs else ""

        return WorkflowResult(
            command_name=workflow.name,
            success=all_success,
            step_results=step_results,
            final_output=last_output,
            duration_ms=elapsed,
        )

    def _run_step(
        self,
        step: CommandStep,
        variables: dict[str, str],
        outputs: dict[str, str],
        results: dict[str, StepResult],
        on_start: Any = None,
        on_complete: Any = None,
    ) -> None:
        if on_start:
            on_start(step.name, step.description)

        start = time.monotonic()
        try:
            if step.tool:
                output = self._execute_tool_step(step, variables)
            elif step.prompt:
                output = self._execute_prompt_step(step, variables)
            else:
                output = ""

            elapsed = (time.monotonic() - start) * 1000
            outputs[step.name] = output
            results[step.name] = StepResult(
                name=step.name,
                success=True,
                output=output,
                duration_ms=elapsed,
            )
        except Exception as exc:
            elapsed = (time.monotonic() - start) * 1000
            error_msg = str(exc)
            outputs[step.name] = f"Error: {error_msg}"
            results[step.name] = StepResult(
                name=step.name,
                success=False,
                error=error_msg,
                duration_ms=elapsed,
            )

        if on_complete:
            on_complete(step.name, results[step.name])

    def _run_parallel(
        self,
        steps: list[CommandStep],
        variables: dict[str, str],
        outputs: dict[str, str],
        results: dict[str, StepResult],
        on_start: Any = None,
        on_complete: Any = None,
    ) -> None:
        lock = threading.Lock()

        def _task(step: CommandStep) -> None:
            self._run_step(step, variables, outputs, results, on_start, on_complete)
            # Thread-safe update of shared variables
            with lock:
                variables.update(outputs)

        with ThreadPoolExecutor(max_workers=min(len(steps), 4)) as pool:
            futures = [pool.submit(_task, s) for s in steps]
            for fut in as_completed(futures):
                # Re-raise any unhandled exception
                fut.result()

    def _execute_tool_step(
        self,
        step: CommandStep,
        variables: dict[str, str],
    ) -> str:
        """Execute a step that calls a registered tool."""
        resolved_args = _resolve_args(step.args, variables)
        return self._agent.execute_tool(step.tool, resolved_args)

    def _execute_prompt_step(
        self,
        step: CommandStep,
        variables: dict[str, str],
    ) -> str:
        """Execute a step that sends a prompt to the LLM.

        NOTE: This uses Agent._chat_with_retry (private method coupling).
        If the Agent API changes, this may need updating.
        """
        resolved_prompt = _resolve_vars(step.prompt or "", variables)

        if not self._agent.llm_provider:
            return f"[No LLM provider available for prompt step '{step.name}']"

        # Build messages with accumulated context
        messages: list[dict[str, str]] = [
            {"role": "user", "content": resolved_prompt},
        ]

        response = self._agent._chat_with_retry(
            messages=messages,
            system_prompt=self._agent.build_system_prompt(query=resolved_prompt),
        )

        return response.content or ""

"""Workspace engine — loads agents, commands, and routes user input.

This module provides the orchestration layer for NanoAgent's workspace-based
agent and command system, inspired by .claude/ conventions.

Usage::

    from nanoagent.workspace import WorkspaceLoader, InputRouter, WorkflowExecutor

    # Load agents and commands from workspace/
    loader = WorkspaceLoader(Path("workspace"))

    # Route user input
    router = InputRouter(loader)
    route = router.parse("@sre-engineer check cpu spike")
    # route.is_agent == True

    # Execute a command workflow
    executor = WorkflowExecutor(agent)
    result = executor.execute(workflow, {"incident_id": "INC-123"})
"""

from .models import AgentProfile, CommandArgument, CommandStep, CommandWorkflow
from .loader import WorkspaceLoader
from .router import InputRouter, Route, AgentRoute, CommandRoute
from .executor import WorkflowExecutor, WorkflowResult, StepResult

__all__ = [
    "AgentProfile",
    "CommandArgument",
    "CommandStep",
    "CommandWorkflow",
    "WorkspaceLoader",
    "InputRouter",
    "Route",
    "AgentRoute",
    "CommandRoute",
    "WorkflowExecutor",
    "WorkflowResult",
    "StepResult",
]

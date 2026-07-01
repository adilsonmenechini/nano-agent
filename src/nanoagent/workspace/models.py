"""Data models for workspace agents and commands.

These match the YAML schemas defined in workspace/agents/ and workspace/commands/.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentProfile:
    """A specialized agent personality loaded from YAML.

    Attributes:
        name: Agent identifier (used as @name in chat).
        description: Short description of the agent's role.
        system_prompt: The role-specific system prompt.
        tools: Whitelist of allowed tool names. Empty = all tools.
        skills: Skill slugs to load into context.
        memory_scope: 'global' or 'project'.
    """

    name: str
    description: str = ""
    system_prompt: str = ""
    tools: list[str] = field(default_factory=list)
    skills: list[str] = field(default_factory=list)
    memory_scope: str = "global"

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("AgentProfile requires a non-empty name")


@dataclass
class CommandArgument:
    """A single argument for a command workflow.

    Attributes:
        name: Argument identifier.
        type: Value type (string, int, bool).
        required: Whether this argument must be provided.
        description: Human-readable description.
    """

    name: str
    type: str = "string"
    required: bool = True
    description: str = ""


@dataclass
class CommandStep:
    """A single step in a command workflow.

    Attributes:
        name: Unique step identifier for DAG references.
        tool: Tool name to call (mutually exclusive with prompt).
        prompt: LLM prompt to execute (mutually exclusive with tool).
        args: Arguments for the tool. Supports {step_name} interpolation.
        depends_on: Steps that must complete before this one.
        description: Human-readable description shown during execution.
    """

    name: str
    tool: str | None = None
    prompt: str | None = None
    args: dict[str, Any] = field(default_factory=dict)
    depends_on: list[str] = field(default_factory=list)
    description: str = ""

    def __post_init__(self) -> None:
        if not self.tool and not self.prompt:
            raise ValueError(f"Step '{self.name}' must have either 'tool' or 'prompt'")
        if self.tool and self.prompt:
            raise ValueError(f"Step '{self.name}' cannot have both 'tool' and 'prompt'")


@dataclass
class CommandWorkflow:
    """A deterministic workflow loaded from YAML.

    Attributes:
        name: Command identifier (used as /name in chat).
        description: Human-readable description.
        arguments: CLI-style arguments with types and validation.
        steps: Ordered list of execution steps forming a DAG.
    """

    name: str
    description: str = ""
    arguments: list[CommandArgument] = field(default_factory=list)
    steps: list[CommandStep] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("CommandWorkflow requires a non-empty name")
        if not self.steps:
            raise ValueError(f"Command '{self.name}' must have at least one step")

    def validate_args(self, provided: dict[str, str]) -> None:
        """Validate provided arguments against the command's argument schema.

        Raises ValueError if required arguments are missing.
        """
        for arg in self.arguments:
            if arg.required and arg.name not in provided:
                raise ValueError(
                    f"Missing required argument '{arg.name}' for /{self.name}. "
                    f"Usage: /{self.name} {self._usage_hint()}"
                )

    def _usage_hint(self) -> str:
        parts = []
        for arg in self.arguments:
            if arg.required:
                parts.append(f"<{arg.name}>")
            else:
                parts.append(f"[{arg.name}]")
        return " ".join(parts)

"""Input router — detects @agent and /command patterns in user input.

Routes parsed input to the appropriate handler:
- @agent-name <prompt> → agent dispatch
- /command-name <args> → command execution
- Regular text → normal agent flow
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from .loader import WorkspaceLoader
from .models import AgentProfile, CommandWorkflow

logger = logging.getLogger("nanoagent.workspace.router")

# Pattern: @agent-name <prompt> — captures group(1)=name, group(2)=prompt
_AGENT_RE = re.compile(r"^@(\w[\w-]*)\s+(.+)$", re.DOTALL)

# Pattern: /command-name [args] — captures group(1)=name, group(2)=args
_COMMAND_RE = re.compile(r"^/(\w[\w-]*)\s*(.*)$", re.DOTALL)


@dataclass
class AgentRoute:
    """Result of routing to a specialized agent."""

    agent: AgentProfile
    prompt: str


@dataclass
class CommandRoute:
    """Result of routing to a command workflow."""

    command: CommandWorkflow
    args: dict[str, str]


@dataclass
class Route:
    """Unified routing result. Check which field is set."""

    agent: AgentProfile | None = None
    prompt: str = ""
    command: CommandWorkflow | None = None
    command_args: dict[str, str] | None = None
    is_agent: bool = False
    is_command: bool = False
    is_regular: bool = False


class InputRouter:
    """Routes user input to the appropriate handler.

    Example::

        loader = WorkspaceLoader(Path("workspace"))
        router = InputRouter(loader)

        route = router.parse("@sre-engineer check cpu spike")
        # route.is_agent == True, route.agent.name == "sre-engineer"

        route = router.parse("/incident INC-123")
        # route.is_command == True, route.command.name == "incident"

        route = router.parse("hello there")
        # route.is_regular == True
    """

    def __init__(self, loader: WorkspaceLoader) -> None:
        self._loader = loader

    def parse(self, text: str) -> Route:
        """Parse user input and return a routing decision.

        Returns a Route with the appropriate field set:
        - is_agent → agent + prompt
        - is_command → command + command_args
        - is_regular → plain text (no special routing)
        """
        if not text:
            return Route(is_regular=True)

        text = text.strip()

        # Try @agent pattern
        agent_match = _AGENT_RE.match(text)
        if agent_match:
            name = agent_match.group(1)
            prompt = agent_match.group(2).strip()
            agent = self._loader.get_agent(name)
            if agent:
                return Route(agent=agent, prompt=prompt, is_agent=True)
            # Unknown agent — fall through to regular

        # Try /command pattern
        cmd_match = _COMMAND_RE.match(text)
        if cmd_match:
            name = cmd_match.group(1)
            raw_args = cmd_match.group(2).strip()
            command = self._loader.get_command(name)
            if command:
                args = self._parse_command_args(command, raw_args)
                return Route(
                    command=command,
                    command_args=args,
                    is_command=True,
                )
            # Unknown command — fall through to regular

        return Route(is_regular=True, prompt=text)

    def _parse_command_args(
        self,
        command: CommandWorkflow,
        raw_args: str,
    ) -> dict[str, str]:
        """Parse raw argument string into a dict based on the command's argument schema.

        Simple positional parsing: first arg goes to first argument, etc.
        Supports --flag value and --flag=value syntax.
        """
        result: dict[str, str] = {}
        if not raw_args:
            return result

        tokens = self._tokenize(raw_args)
        positional_idx = 0

        i = 0
        while i < len(tokens):
            token = tokens[i]
            if token.startswith("--"):
                # Named argument: --name value or --name=value
                if "=" in token:
                    key, value = token[2:].split("=", 1)
                    result[key] = value
                elif i + 1 < len(tokens):
                    key = token[2:]
                    result[key] = tokens[i + 1]
                    i += 1
            else:
                # Positional argument
                if positional_idx < len(command.arguments):
                    arg_def = command.arguments[positional_idx]
                    result[arg_def.name] = token
                    positional_idx += 1
                else:
                    logger.warning(
                        "Extra positional arg ignored: '%s' for /%s",
                        token,
                        command.name,
                    )
            i += 1

        return result

    def _tokenize(self, text: str) -> list[str]:
        """Simple tokenizer that respects double quotes."""
        tokens: list[str] = []
        current: list[str] = []
        in_quotes = False

        for char in text:
            if char == '"':
                in_quotes = not in_quotes
            elif char == " " and not in_quotes:
                if current:
                    tokens.append("".join(current))
                    current = []
            else:
                current.append(char)

        if current:
            tokens.append("".join(current))

        return tokens

    def list_agents(self) -> list[str]:
        """List available agent names for display."""
        return self._loader.agent_names()

    def list_commands(self) -> list[str]:
        """List available command names for display."""
        return self._loader.command_names()

    def get_agent(self, name: str) -> AgentProfile | None:
        """Get an agent profile by name."""
        return self._loader.get_agent(name)

    def get_command(self, name: str) -> CommandWorkflow | None:
        """Get a command workflow by name."""
        return self._loader.get_command(name)

"""YAML loader for workspace agents and commands.

Scans workspace/agents/ and workspace/commands/ directories,
parses YAML files, and returns typed dataclasses.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from .models import AgentProfile, CommandArgument, CommandStep, CommandWorkflow

logger = logging.getLogger("nanoagent.workspace.loader")


def _load_yaml(path: Path) -> dict[str, Any]:
    """Load a YAML file and return the parsed dict."""
    try:
        import yaml

        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except ImportError:
        logger.warning("pyyaml not installed, cannot load YAML files")
        return {}
    except Exception as exc:
        logger.error("Failed to load YAML from %s: %s", path, exc)
        return {}


class WorkspaceLoader:
    """Loads and manages workspace agents and commands from YAML files.

    Scans the workspace directory for agents/ and commands/ subdirectories,
    parsing each YAML file into typed dataclass instances.

    Example::

        loader = WorkspaceLoader(Path("workspace"))
        agents = loader.agents
        commands = loader.commands
        sre = loader.get_agent("sre-engineer")
        incident = loader.get_command("incident")
    """

    def __init__(self, workspace_path: Path | str) -> None:
        self.workspace = Path(workspace_path).expanduser().resolve()
        self._agents: dict[str, AgentProfile] = {}
        self._commands: dict[str, CommandWorkflow] = {}
        self._load_all()

    def _load_all(self) -> None:
        """Scan and load all agents and commands from the workspace."""
        self._load_agents()
        self._load_commands()

    def _load_from_dir(
        self,
        directory: Path,
        parse_fn: Any,  # Callable[[Path], T | None]
        store: dict[str, Any],
    ) -> None:
        """Generic loader: scan a directory for YAML files and parse each."""
        if not directory.is_dir():
            return
        for pattern in ("*.yaml", "*.yml"):
            for path in sorted(directory.glob(pattern)):
                item = parse_fn(path)
                if item is not None:
                    store[item.name] = item

    def _load_agents(self) -> None:
        agents_dir = self.workspace / "agents"
        self._load_from_dir(agents_dir, self._parse_agent, self._agents)
        logger.info("Loaded %d agents from %s", len(self._agents), agents_dir)

    def _parse_agent(self, path: Path) -> AgentProfile | None:
        data = _load_yaml(path)
        if not data:
            return None
        try:
            return AgentProfile(
                name=data.get("name", path.stem),
                description=data.get("description", ""),
                system_prompt=data.get("system_prompt", ""),
                tools=data.get("tools") or [],
                skills=data.get("skills") or [],
                memory_scope=data.get("memory_scope", "global"),
            )
        except (ValueError, KeyError) as exc:
            logger.warning("Failed to parse agent %s: %s", path.name, exc)
            return None

    def _load_commands(self) -> None:
        commands_dir = self.workspace / "commands"
        self._load_from_dir(commands_dir, self._parse_command, self._commands)
        logger.info("Loaded %d commands from %s", len(self._commands), commands_dir)

    def _parse_command(self, path: Path) -> CommandWorkflow | None:
        data = _load_yaml(path)
        if not data:
            return None
        try:
            arguments = []
            for arg in data.get("arguments", []):
                arguments.append(
                    CommandArgument(
                        name=arg.get("name", ""),
                        type=arg.get("type", "string"),
                        required=arg.get("required", True),
                        description=arg.get("description", ""),
                    )
                )

            steps = []
            for step in data.get("steps", []):
                steps.append(
                    CommandStep(
                        name=step.get("name", ""),
                        tool=step.get("tool"),
                        prompt=step.get("prompt"),
                        args=step.get("args") or {},
                        depends_on=step.get("depends_on") or [],
                        description=step.get("description", ""),
                    )
                )

            return CommandWorkflow(
                name=data.get("name", path.stem),
                description=data.get("description", ""),
                arguments=arguments,
                steps=steps,
            )
        except (ValueError, KeyError) as exc:
            logger.warning("Failed to parse command %s: %s", path.name, exc)
            return None

    # ─── Public API ──────────────────────────────────────────────────────

    @property
    def agents(self) -> dict[str, AgentProfile]:
        """All loaded agent profiles, keyed by name."""
        return dict(self._agents)

    @property
    def commands(self) -> dict[str, CommandWorkflow]:
        """All loaded command workflows, keyed by name."""
        return dict(self._commands)

    def get_agent(self, name: str) -> AgentProfile | None:
        """Get an agent profile by name."""
        return self._agents.get(name)

    def get_command(self, name: str) -> CommandWorkflow | None:
        """Get a command workflow by name."""
        return self._commands.get(name)

    def agent_names(self) -> list[str]:
        """List all available agent names."""
        return sorted(self._agents.keys())

    def command_names(self) -> list[str]:
        """List all available command names."""
        return sorted(self._commands.keys())

    def reload(self) -> None:
        """Reload all agents and commands from disk."""
        self._agents.clear()
        self._commands.clear()
        self._load_all()

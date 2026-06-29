"""Permission-based tool access control.

Provides PermissionManager and PermissionRule for evaluating
whether a tool invocation is allowed, denied, or requires human approval.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Literal


class PermissionMode(Enum):
    ALLOW = "allow"
    DENY = "deny"
    ASK = "ask"


MatchType = Literal["exact", "prefix", "regex"]


@dataclass
class PermissionRule:
    """A single access control rule for tool invocations."""

    tool_name: str
    match_type: MatchType = "exact"
    pattern: str = "*"
    mode: PermissionMode = PermissionMode.ALLOW


# Priority ordering for match types (lower = higher priority)
_MATCH_TYPE_PRIORITY = {"exact": 0, "prefix": 1, "regex": 2}


class PermissionManager:
    """Evaluates tool invocations against configured permission rules."""

    def __init__(self, default_mode: str = "allow"):
        self.rules: list[PermissionRule] = []
        if default_mode not in ("allow", "deny"):
            raise ValueError(f"default_mode must be 'allow' or 'deny', got {default_mode!r}")
        self.default_mode = PermissionMode(default_mode)

    def add_rule(self, rule: PermissionRule) -> None:
        """Add a permission rule.

        Args:
            rule: The PermissionRule to add.
        """
        self.rules.append(rule)

    def check(self, tool_name: str, command: str = "") -> PermissionMode:
        """Check if a tool invocation is permitted.

        Evaluates rules in priority order:
        1. Exact matches before prefix before regex
        2. Tool-specific rules before wildcard (*)
        3. First matching rule wins

        Args:
            tool_name: Name of the tool being invoked.
            command: The command/argument string (for shell tools).

        Returns:
            PermissionMode: ALLOW, DENY, or ASK.
        """
        # Sort matching rules by priority
        matching = [r for r in self.rules if _rule_matches(r, tool_name, command)]
        matching.sort(
            key=lambda r: (
                _MATCH_TYPE_PRIORITY.get(r.match_type, 99),
                0 if r.tool_name == tool_name else 1,
            )
        )

        if not matching:
            return self.default_mode

        return matching[0].mode

    @classmethod
    def load_from_config(cls, config_dict: dict | None) -> PermissionManager:
        """Create a PermissionManager from a TOML config dict.

        Expects the ``[tools.permissions]`` section structure:

        .. code-block:: toml

            [tools.permissions]
            default_mode = "allow"

            [tools.permissions.rules]
            rule_name = { tool = "run_shell", type = "prefix", pattern = "rm", mode = "deny" }

        Args:
            config_dict: The parsed ``[tools.permissions]`` dict, or None.

        Returns:
            A configured PermissionManager instance.
        """
        if not config_dict:
            return cls()

        pm = cls(default_mode=config_dict.get("default_mode", "allow"))
        rules_dict = config_dict.get("rules", {})
        for _name, rule_cfg in rules_dict.items():
            if not isinstance(rule_cfg, dict):
                continue
            tool_name = rule_cfg.get("tool", "*")
            match_type = rule_cfg.get("type", "exact")
            pattern = rule_cfg.get("pattern", "*")
            mode_str = rule_cfg.get("mode", "allow")
            try:
                mode = PermissionMode(mode_str)
            except ValueError:
                continue
            if match_type not in ("exact", "prefix", "regex"):
                match_type = "exact"
            pm.add_rule(PermissionRule(
                tool_name=tool_name,
                match_type=match_type,  # type: ignore[arg-type]
                pattern=pattern,
                mode=mode,
            ))
        return pm


def _rule_matches(rule: PermissionRule, tool_name: str, command: str) -> bool:
    """Check if a rule applies to the given tool invocation."""
    # Tool name filter
    if rule.tool_name != "*" and rule.tool_name != tool_name:
        return False

    # Pattern matching (only for non-empty commands)
    if not command:
        return rule.pattern == "*" or rule.pattern == ""

    if rule.match_type == "exact":
        return command == rule.pattern
    elif rule.match_type == "prefix":
        return command.startswith(rule.pattern)
    elif rule.match_type == "regex":
        try:
            return bool(re.match(rule.pattern, command))
        except re.error:
            return False

    return False


__all__ = [
    "PermissionMode",
    "PermissionRule",
    "PermissionManager",
]

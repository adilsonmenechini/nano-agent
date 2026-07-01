from __future__ import annotations


from nanoagent.config import AgentConfig


class HarnessAnalyzer:
    def __init__(
        self,
        config=None,
        tool_registry=None,
        permission_manager=None,
        memory_store=None,
    ):
        self.config = config or AgentConfig()
        self.tool_registry = tool_registry
        self.permission_manager = permission_manager
        self.memory_store = memory_store

    def snapshot(self) -> dict:
        config_vals = {
            "default_provider": self.config.default_provider,
            "review_enabled": self.config.review_enabled,
            "flush_min_turns": self.config.flush_min_turns,
            "nudge_interval": self.config.nudge_interval,
            "nudge_tool_calls": self.config.nudge_tool_calls,
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
            "retry_attempts": self.config.retry_attempts,
            "stream": self.config.stream,
            "max_iterations": getattr(self.config, "max_iterations", 10),
        }
        tools_list = []
        if self.tool_registry:
            for t in self.tool_registry.all():
                tools_list.append(
                    {
                        "name": t.name,
                        "description": t.description[:80] if t.description else "",
                        "param_count": len(
                            getattr(t, "parameters", {}).get("properties", {})
                        ),
                    }
                )
        permissions_list = []
        if self.permission_manager:
            rules = getattr(self.permission_manager, "_rules", [])
            for r in rules:
                permissions_list.append(
                    {
                        "tool_pattern": getattr(r, "tool_pattern", ""),
                        "mode": getattr(r, "mode", "allow"),
                    }
                )
        memory_stats = {}
        if self.memory_store:
            try:
                memory_stats = {
                    "memories": self.memory_store.char_count("memory"),
                    "users": self.memory_store.char_count("user"),
                    "failures": self.memory_store.char_count("failure"),
                }
            except Exception:
                memory_stats = {"error": "could not compute"}
        return {
            "config": config_vals,
            "tools": tools_list,
            "permissions": permissions_list,
            "memory_stats": memory_stats,
            "recommendations": [],
        }

    def analyze(self, snapshot_data=None) -> list[dict]:
        data = snapshot_data if snapshot_data is not None else self.snapshot()
        recommendations = []
        tools = data.get("tools", [])
        if not tools:
            recommendations.append(
                {
                    "type": "NO_TOOLS_REGISTERED",
                    "severity": "high",
                    "message": "No tools are registered. Agent cannot perform any actions.",
                    "confidence": 1.0,
                }
            )
        config = data.get("config", {})
        max_iter = config.get("max_iterations", 10)
        if max_iter < 5:
            recommendations.append(
                {
                    "type": "TIMEOUT_SHORT",
                    "severity": "medium",
                    "message": f"Max iterations is only {max_iter}. Complex tasks may timeout.",
                    "confidence": 0.7,
                }
            )
        mem = data.get("memory_stats", {})
        if mem.get("memories", 0) > 50_000:
            recommendations.append(
                {
                    "type": "MEMORY_HIGH",
                    "severity": "low",
                    "message": f"Memory usage is high ({mem['memories']} chars). Consider consolidation.",
                    "confidence": 0.5,
                }
            )
        if not config.get("review_enabled", True):
            recommendations.append(
                {
                    "type": "REVIEW_DISABLED",
                    "severity": "medium",
                    "message": "Background review is disabled. Agent will not auto-consolidate memories.",
                    "confidence": 0.9,
                }
            )
        return recommendations

    def report(self) -> str:
        snap = self.snapshot()
        recs = self.analyze(snap)
        lines = ["=== Harness Introspection Report ===", ""]
        lines.append("Configuration:")
        for k, v in snap.get("config", {}).items():
            lines.append(f"  {k}: {v}")
        lines.append("")
        lines.append(f"Tools ({len(snap.get('tools', []))}):")
        for t in snap.get("tools", []):
            lines.append(f"  - {t['name']} ({t['param_count']} params)")
        lines.append("")
        lines.append(f"Permissions ({len(snap.get('permissions', []))}):")
        for p in snap.get("permissions", []):
            lines.append(f"  - {p['tool_pattern']}: {p['mode']}")
        lines.append("")
        if recs:
            lines.append("Recommendations:")
            for r in recs:
                lines.append(f"  [{r['severity'].upper()}] {r['type']}: {r['message']}")
        else:
            lines.append("No recommendations.")
        return "\n".join(lines)

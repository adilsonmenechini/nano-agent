from __future__ import annotations

import json

from nanoagent.learning import ExperiencePattern, SkillStatus
from nanoagent.memory.sqlite_memory_store import SQLiteMemoryStore
from nanoagent.skills.skill_storage import SkillStorage


class Synthesizer:
    def __init__(self, store: SQLiteMemoryStore):
        self.store = store
        self.skill_storage = SkillStorage(store=store)

    def create_proposal(self, pattern: ExperiencePattern) -> dict | None:
        if not pattern.tool_sequence:
            return None
        tool_names = [t.get("name", "tool") for t in pattern.tool_sequence]
        slug = self._generate_slug(tool_names)
        existing = self.skill_storage.get_skill(slug)
        if existing:
            return None
        name = self._generate_name(tool_names)
        description = (
            pattern.recommended_approach
            or f"Run {', '.join(tool_names)} based on learned pattern"
        )
        code = self._generate_code(tool_names, description)
        try:
            skill_id = self.skill_storage.add_skill(
                slug=slug,
                name=name,
                description=description,
                code=code,
                scope="global",
            )
            self.store.conn.execute(
                "UPDATE skills SET status = ? WHERE id = ?",
                (SkillStatus.PROPOSED.value, skill_id),
            )
            self.store.conn.commit()
            return {
                "slug": slug,
                "name": name,
                "description": description,
                "status": SkillStatus.PROPOSED.value,
            }
        except Exception:
            return None

    def check_for_proposals(self) -> list[dict]:
        cursor = self.store.conn.execute(
            """SELECT * FROM experience_patterns
               WHERE sample_size >= 3 AND success_count > 0
               ORDER BY success_count DESC"""
        )
        proposals = []
        for row in cursor.fetchall():
            d = dict(row)
            pattern = ExperiencePattern(
                id=d["id"],
                trigger_context=json.loads(d["trigger_context"])
                if isinstance(d["trigger_context"], str)
                else d["trigger_context"],
                tool_sequence=json.loads(d["tool_sequence"])
                if isinstance(d["tool_sequence"], str)
                else d["tool_sequence"],
                recommended_approach=d["recommended_approach"],
                success_count=d["success_count"],
                failure_count=d["failure_count"],
                sample_size=d["sample_size"],
                first_observed=d["first_observed"],
                last_applied=d["last_applied"],
                is_active=bool(d["is_active"]),
            )
            proposal = self.create_proposal(pattern)
            if proposal:
                proposals.append(proposal)
        return proposals

    def get_pending_proposals(self) -> list[dict]:
        return [
            s
            for s in self.skill_storage.list_skills()
            if s.get("status") == SkillStatus.PROPOSED.value
        ]

    def _generate_slug(self, tool_names: list[str]) -> str:
        base = "_".join(tool_names[:3]).lower().replace(" ", "_")
        return f"auto_{base}" if base else "auto_unknown"

    def _generate_name(self, tool_names: list[str]) -> str:
        return " + ".join(n.replace("_", " ").title() for n in tool_names[:3])

    def _generate_code(self, tool_names: list[str], description: str) -> str:
        return f'"""Auto-generated skill: {description}"""\n\n' + "\n".join(
            f"# {n}: auto-generated tool call" for n in tool_names
        )

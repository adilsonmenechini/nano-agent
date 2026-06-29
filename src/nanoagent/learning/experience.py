from __future__ import annotations

import json
import time

from nanoagent.learning import ExperiencePattern
from nanoagent.memory.sqlite_memory_store import SQLiteMemoryStore


class ExperienceEngine:
    def __init__(self, store: SQLiteMemoryStore):
        self.store = store

    def analyze_reflections(self, reflections: list[dict]) -> list[ExperiencePattern]:
        if not reflections:
            return []
        tool_signatures: dict[str, list[dict]] = {}
        for r in reflections:
            tc_raw = r.get("tool_calls", "[]")
            tcs = json.loads(tc_raw) if isinstance(tc_raw, str) else tc_raw
            if not tcs:
                continue
            sig = self._signature(tcs)
            if sig not in tool_signatures:
                tool_signatures[sig] = []
            tool_signatures[sig].append(r)
        patterns = []
        for sig, records in tool_signatures.items():
            if len(records) >= 2:
                sample = records[0]
                tc_raw = sample.get("tool_calls", "[]")
                tcs = json.loads(tc_raw) if isinstance(tc_raw, str) else tc_raw
                successes = sum(1 for r in records if r.get("outcome") in ("success", "partial"))
                failures = sum(1 for r in records if r.get("outcome") in ("failure", "error"))
                times = [r.get("created", 0) for r in records if r.get("created")]
                pattern = ExperiencePattern(
                    trigger_context={"task_hint": sample.get("task_description", "")[:120], "tool_signature": sig},
                    tool_sequence=tcs,
                    recommended_approach=self._describe_pattern(tcs),
                    success_count=successes,
                    failure_count=failures,
                    sample_size=len(records),
                    first_observed=min(times) if times else time.time(),
                    last_applied=max(times) if times else time.time(),
                )
                patterns.append(pattern)
        self._persist_patterns(patterns)
        return patterns

    def match(self, context: str, limit: int = 5) -> list[ExperiencePattern]:
        cursor = self.store.conn.execute(
            "SELECT * FROM experience_patterns WHERE is_active = 1 ORDER BY success_count DESC, sample_size DESC LIMIT ?",
            (limit,),
        )
        results = []
        for row in cursor.fetchall():
            ctx_str = (dict(row)).get("trigger_context", "{}")
            ctx = json.loads(ctx_str) if isinstance(ctx_str, str) else ctx_str
            hint = ctx.get("task_hint", "") if isinstance(ctx, dict) else ""
            if not context or not hint or any(w in hint.lower() for w in context.lower().split()):
                results.append(self._row_to_pattern(row))
        return results

    def get_stats(self) -> dict:
        cursor = self.store.conn.execute(
            """SELECT
               COUNT(*) as total_patterns,
               SUM(CASE WHEN is_active = 1 THEN 1 ELSE 0 END) as active_patterns,
               COALESCE(SUM(sample_size), 0) as total_samples,
               COALESCE(SUM(success_count), 0) as total_successes
               FROM experience_patterns"""
        )
        row = cursor.fetchone()
        return dict(row) if row else {}

    def _signature(self, tool_calls: list[dict]) -> str:
        return "+".join(sorted(set(t.get("name", "") for t in tool_calls)))

    def _describe_pattern(self, tool_calls: list[dict]) -> str:
        names = [t.get("name", "?") for t in tool_calls]
        return "Use " + " then ".join(names)

    def _persist_patterns(self, patterns: list[ExperiencePattern]) -> None:
        for p in patterns:
            self.store.conn.execute(
                """INSERT OR REPLACE INTO experience_patterns
                   (trigger_context, tool_sequence, recommended_approach,
                    success_count, failure_count, sample_size,
                    first_observed, last_applied, is_active)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    json.dumps(p.trigger_context),
                    json.dumps(p.tool_sequence),
                    p.recommended_approach,
                    p.success_count,
                    p.failure_count,
                    p.sample_size,
                    p.first_observed,
                    p.last_applied,
                    1 if p.is_active else 0,
                ),
            )
        self.store.conn.commit()

    def _row_to_pattern(self, row) -> ExperiencePattern:
        d = dict(row)
        return ExperiencePattern(
            id=d["id"],
            trigger_context=json.loads(d["trigger_context"]) if isinstance(d["trigger_context"], str) else d["trigger_context"],
            tool_sequence=json.loads(d["tool_sequence"]) if isinstance(d["tool_sequence"], str) else d["tool_sequence"],
            recommended_approach=d["recommended_approach"],
            success_count=d["success_count"],
            failure_count=d["failure_count"],
            sample_size=d["sample_size"],
            first_observed=d["first_observed"],
            last_applied=d["last_applied"],
            is_active=bool(d["is_active"]),
        )

from __future__ import annotations

import json
import time
from typing import Any

from nanoagent.memory.sqlite_memory_store import SQLiteMemoryStore


def _ensure_str_dicts(val: Any) -> str:
    if isinstance(val, str):
        return val
    return json.dumps(val, default=str)


class Reflector:
    def __init__(self, store: SQLiteMemoryStore):
        self.store = store

    def reflect(
        self,
        turn_id: str,
        task_description: str = "",
        tool_calls: list[dict] | None = None,
        steps_taken: int = 0,
        errors: list[dict] | None = None,
        outcome: str = "success",
        duration_ms: int = 0,
        lessons: list[str] | None = None,
    ) -> dict | None:
        now = time.time()
        cursor = self.store.conn.execute(
            """INSERT OR IGNORE INTO reflection_records
               (turn_id, task_description, tool_calls, steps_taken, errors, outcome, duration_ms, lessons, created)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                turn_id,
                task_description,
                _ensure_str_dicts(tool_calls or []),
                steps_taken,
                _ensure_str_dicts(errors or []),
                outcome,
                duration_ms,
                _ensure_str_dicts(lessons or []),
                now,
            ),
        )
        self.store.conn.commit()
        if cursor.lastrowid is None:
            return self.get_by_turn_id(turn_id)
        row = self.store.conn.execute(
            "SELECT * FROM reflection_records WHERE id = ?", (cursor.lastrowid,)
        ).fetchone()
        return dict(row) if row else None

    def get_recent(self, limit: int = 10) -> list[dict]:
        cursor = self.store.conn.execute(
            "SELECT * FROM reflection_records ORDER BY created DESC LIMIT ?",
            (limit,),
        )
        return [dict(row) for row in cursor.fetchall()]

    def get_by_turn_id(self, turn_id: str) -> dict | None:
        cursor = self.store.conn.execute(
            "SELECT * FROM reflection_records WHERE turn_id = ?",
            (turn_id,),
        )
        row = cursor.fetchone()
        return dict(row) if row else None

    def search(self, query: str, limit: int = 10) -> list[dict]:
        cursor = self.store.conn.execute(
            "SELECT * FROM reflection_records WHERE task_description LIKE ? ORDER BY created DESC LIMIT ?",
            (f"%{query}%", limit),
        )
        return [dict(row) for row in cursor.fetchall()]

    def get_stats(self) -> dict:
        cursor = self.store.conn.execute(
            """SELECT
               COUNT(*) as total,
               SUM(CASE WHEN outcome = 'success' THEN 1 ELSE 0 END) as success_count,
               SUM(CASE WHEN outcome = 'failure' THEN 1 ELSE 0 END) as failure_count,
               SUM(CASE WHEN outcome = 'error' THEN 1 ELSE 0 END) as error_count,
               COALESCE(AVG(duration_ms), 0) as avg_duration_ms
               FROM reflection_records"""
        )
        row = cursor.fetchone()
        return dict(row) if row else {}

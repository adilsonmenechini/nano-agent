from ..memory.sqlite_memory_store import SQLiteMemoryStore


class SkillStorage:
    """Persistent skill storage using the SQLite skills table.

    Ported from pi-hermes-memory SkillStore — stores skills as
    executable code with slug-based lookup, scope, and metadata.
    """

    def __init__(
        self, db_path: str | None = None, store: SQLiteMemoryStore | None = None
    ):
        if store is not None:
            self._store_ref = store
        else:
            self._store_ref = SQLiteMemoryStore(db_path=db_path)

    @property
    def _store(self) -> SQLiteMemoryStore:
        return self._store_ref

    def add_skill(
        self,
        slug: str,
        name: str,
        description: str,
        code: str,
        scope: str = "global",
        project_path: str | None = None,
    ) -> int:
        entry = self._store.add_skill(
            slug, name, description, code, scope=scope, project_path=project_path
        )
        return entry.id

    def get_skill(
        self, slug: str, scope: str = "global", project_path: str | None = None
    ) -> dict | None:
        entry = self._store.get_skill(slug, scope=scope, project_path=project_path)
        if entry is None:
            return None
        return {
            "name": entry.name,
            "description": entry.description,
            "code": entry.code,
            "slug": entry.slug,
            "scope": entry.scope,
            "status": getattr(entry, "status", "active"),
            "created_at": entry.created,
            "updated_at": entry.updated,
        }

    def list_skills(
        self, scope: str = "global", project_path: str | None = None
    ) -> list[dict]:
        entries = self._store.list_skills(scope=scope, project_path=project_path)
        return [
            {
                "name": e.name,
                "description": e.description,
                "code": e.code,
                "slug": e.slug,
                "scope": e.scope,
                "status": getattr(e, "status", "active"),
                "created_at": e.created,
                "updated_at": e.updated,
            }
            for e in entries
        ]

    def update_skill(
        self,
        slug: str,
        description: str | None = None,
        code: str | None = None,
        scope: str = "global",
        project_path: str | None = None,
    ) -> bool:
        entry = self._store.get_skill(slug, scope=scope, project_path=project_path)
        if entry is None:
            return False
        old_code = entry.code
        old_desc = entry.description
        import time
        now = time.time()
        self._save_version(entry.id, old_code, old_desc)
        if scope == "project" and project_path:
            self._store._get_project_id(project_path)
        where, params = self._store._project_filter(scope, project_path)
        where = where.replace("project", "project_id")
        self._store.conn.execute(
            f"UPDATE skills SET code = ?, description = ?, updated = ?"
            f" WHERE slug = ? AND scope = ? AND {where}",
            [
                code if code is not None else old_code,
                description if description is not None else old_desc,
                now, slug, scope,
            ] + params,
        )
        self._store.conn.commit()
        return True

    def _save_version(self, skill_id: int, code: str, description: str) -> None:
        import time
        max_ver = self._store.conn.execute(
            "SELECT COALESCE(MAX(version), 0) FROM skill_versions WHERE skill_id = ?",
            (skill_id,),
        ).fetchone()[0]
        self._store.conn.execute(
            """INSERT INTO skill_versions (skill_id, version, code, description, created)
               VALUES (?, ?, ?, ?, ?)""",
            (skill_id, max_ver + 1, code, description, time.time()),
        )
        self._store.conn.commit()

    def list_versions(
        self, slug: str, scope: str = "global", project_path: str | None = None
    ) -> list[dict]:
        entry = self._store.get_skill(slug, scope=scope, project_path=project_path)
        if entry is None:
            return []
        cursor = self._store.conn.execute(
            """SELECT version, code, description, created
               FROM skill_versions WHERE skill_id = ?
               ORDER BY version DESC""",
            (entry.id,),
        )
        return [dict(row) for row in cursor.fetchall()]

    def rollback(
        self, slug: str, version: int, scope: str = "global", project_path: str | None = None
    ) -> bool:
        entry = self._store.get_skill(slug, scope=scope, project_path=project_path)
        if entry is None:
            return False
        project_id: str | None = None
        if scope == "project" and project_path:
            project_id = self._store._get_project_id(project_path)
        cursor = self._store.conn.execute(
            """SELECT sv.code, sv.description FROM skill_versions sv
               JOIN skills s ON sv.skill_id = s.id
               WHERE s.slug = ? AND s.scope = ? AND sv.version = ?
               AND (? IS NULL OR s.project_id = ?)""",
            [slug, scope, version, project_id, project_id],
        )
        row = cursor.fetchone()
        if row is None:
            return False
        self.update_skill(
            slug,
            description=row["description"],
            code=row["code"],
            scope=scope,
            project_path=project_path,
        )
        return True

    def activate_skill(self, slug: str, scope: str = "global", project_path: str | None = None) -> bool:
        where, params = self._store._project_filter(scope, project_path)
        where = where.replace("project", "project_id")
        cursor = self._store.conn.execute(
            f"UPDATE skills SET status = 'active' WHERE slug = ? AND scope = ? AND {where}",
            [slug, scope] + params,
        )
        self._store.conn.commit()
        return cursor.rowcount > 0

    def reject_skill(self, slug: str, scope: str = "global", project_path: str | None = None) -> bool:
        where, params = self._store._project_filter(scope, project_path)
        where = where.replace("project", "project_id")
        cursor = self._store.conn.execute(
            f"UPDATE skills SET status = 'rejected' WHERE slug = ? AND scope = ? AND {where}",
            [slug, scope] + params,
        )
        self._store.conn.commit()
        return cursor.rowcount > 0

    def list_proposed_skills(self) -> list[dict]:
        return [s for s in self.list_skills() if s.get("status") == "proposed"]

    def delete_skill(
        self, slug: str, scope: str = "global", project_path: str | None = None
    ) -> bool:
        return self._store.delete_skill(slug, scope=scope, project_path=project_path)

    def _get_project_id(self, project_path: str) -> str:
        return self._store._get_project_id(project_path)

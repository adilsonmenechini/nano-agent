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
        self._store.delete_skill(slug, scope=scope, project_path=project_path)
        name = entry.name
        desc = description if description is not None else entry.description
        new_code = code if code is not None else entry.code
        self._store.add_skill(
            slug, name, desc, new_code, scope=scope, project_path=project_path
        )
        return True

    def delete_skill(
        self, slug: str, scope: str = "global", project_path: str | None = None
    ) -> bool:
        return self._store.delete_skill(slug, scope=scope, project_path=project_path)

    def _get_project_id(self, project_path: str) -> str:
        return self._store._get_project_id(project_path)

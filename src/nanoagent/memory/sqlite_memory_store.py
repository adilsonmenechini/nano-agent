import sqlite3
import hashlib
import time
from pathlib import Path
from dataclasses import dataclass

from .content_scanner import scan_content
from .constants import FAILURE_CATEGORIES


@dataclass
class SqliteMemoryEntry:
    id: int
    project: str | None
    target: str
    category: str | None
    key: str | None
    content: str
    failure_reason: str | None
    tool_state: str | None
    corrected_to: str | None
    created: float
    last_referenced: float


@dataclass
class SqliteSkillEntry:
    id: int
    slug: str
    name: str
    description: str
    code: str
    scope: str
    created: float
    updated: float


class SQLiteMemoryStore:
    """SQLite store for memories and skills.

    Ported from pi-hermes-memory src/store/sqlite-memory-store.ts
    and src/store/db.ts — schema with failure_reason, tool_state,
    corrected_to, last_referenced columns.
    """

    def __init__(self, db_path: str | None = None):
        if db_path is None:
            home = Path.home()
            self.db_dir = home / ".nanoagent" / "memory"
            self.db_dir.mkdir(parents=True, exist_ok=True)
            db_path = str(self.db_dir / "global.db")
        self.db_path = db_path
        self.conn: sqlite3.Connection | None = None
        self._connect()
        self._create_tables()

    def _connect(self):
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode = WAL")
        self.conn.execute("PRAGMA foreign_keys = ON")

    def _create_tables(self):
        """Create memories table with full Hermes schema + skills table."""
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project TEXT,
                target TEXT NOT NULL CHECK(target IN ('memory', 'user', 'failure')),
                category TEXT,
                key TEXT,
                content TEXT NOT NULL,
                failure_reason TEXT,
                tool_state TEXT,
                corrected_to TEXT,
                created REAL NOT NULL,
                last_referenced REAL NOT NULL
            )
        """)
        self.conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts
            USING fts5(content, content='memories', content_rowid='id')
        """)
        self._create_fts_triggers()
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS skills (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                slug TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                code TEXT NOT NULL,
                scope TEXT NOT NULL DEFAULT 'global' CHECK(scope IN ('global', 'project')),
                project_id TEXT,
                created REAL NOT NULL,
                updated REAL NOT NULL
            )
        """)
        self.conn.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_skills_slug_scope
            ON skills(slug, scope, project_id)
        """)
        self.conn.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_skills_global_unique
            ON skills(slug, scope) WHERE project_id IS NULL
        """)
        # Index for memory queries (handle stale schema gracefully)
        try:
            self.conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_memories_target_scope
                ON memories(target, project)
            """)
        except sqlite3.OperationalError:
            self.conn.execute("DROP TABLE IF EXISTS memories_fts")
            self.conn.execute("DROP TABLE IF EXISTS memories")
            self.conn.execute("""
                CREATE TABLE memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project TEXT,
                    target TEXT NOT NULL CHECK(target IN ('memory', 'user', 'failure')),
                    category TEXT,
                    key TEXT,
                    content TEXT NOT NULL,
                    failure_reason TEXT,
                    tool_state TEXT,
                    corrected_to TEXT,
                    created REAL NOT NULL,
                    last_referenced REAL NOT NULL
                )
            """)
            self.conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_memories_target_scope
                ON memories(target, project)
            """)
            self._create_fts_triggers()
        self.conn.commit()

    def _create_fts_triggers(self):
        self.conn.execute("""
            CREATE TRIGGER IF NOT EXISTS memories_ai AFTER INSERT ON memories BEGIN
                INSERT INTO memories_fts(rowid, content) VALUES (new.id, new.content);
            END
        """)
        self.conn.execute("""
            CREATE TRIGGER IF NOT EXISTS memories_ad AFTER DELETE ON memories BEGIN
                INSERT INTO memories_fts(memories_fts, rowid, content) VALUES('delete', old.id, old.content);
            END
        """)
        self.conn.execute("""
            CREATE TRIGGER IF NOT EXISTS memories_au AFTER UPDATE ON memories BEGIN
                INSERT INTO memories_fts(memories_fts, rowid, content) VALUES('delete', old.id, old.content);
                INSERT INTO memories_fts(rowid, content) VALUES (new.id, new.content);
            END
        """)

    def _get_project_id(self, project_path: str) -> str:
        return hashlib.sha256(project_path.encode()).hexdigest()[:16]

    def _map_row(self, row: sqlite3.Row) -> SqliteMemoryEntry:
        return SqliteMemoryEntry(
            id=row["id"],
            project=row["project"],
            target=row["target"],
            category=row["category"],
            key=row["key"],
            content=row["content"],
            failure_reason=row["failure_reason"],
            tool_state=row["tool_state"],
            corrected_to=row["corrected_to"],
            created=row["created"],
            last_referenced=row["last_referenced"],
        )

    # ─── Backward-compatible API ───

    def add(self, target: str, scope: str, key: str, value: str,
            category: str | None = None, project_path: str | None = None):
        """Add a memory entry (backward-compatible signature).

        Args:
            target: 'memory', 'user', or 'failure'
            scope: 'global' or 'project'
            key: lookup key
            value: content
            category: failure category
            project_path: for project scope
        """
        result = scan_content(value)
        if result.blocked:
            raise ValueError(f"Content blocked: {result.reason}")

        project_id: str | None = None
        if scope == "project" and project_path:
            project_id = self._get_project_id(project_path)
        elif scope != "global":
            raise ValueError("Scope must be 'global' or 'project' with project_path")

        now = time.time()
        self.conn.execute(
            """INSERT INTO memories (project, target, category, key, content,
               failure_reason, tool_state, corrected_to, created, last_referenced)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (project_id, target, category, key, value, None, None, None, now, now),
        )
        self.conn.commit()

    def get(self, target: str, scope: str, key: str,
            project_path: str | None = None) -> str | None:
        """Retrieve memory by exact key match (backward-compatible).

        In Hermes, memories are §-delimited and key-based lookup maps
        to content search. We use FTS5 as the primary lookup, with key
        stored as a content prefix for backward compatibility.
        """
        project_id: str | None = None
        if scope == "project" and project_path:
            project_id = self._get_project_id(project_path)

        if project_id is not None:
            cursor = self.conn.execute(
                """SELECT id, content FROM memories
                   WHERE target = ? AND project = ? AND key = ?
                   ORDER BY last_referenced DESC LIMIT 1""",
                (target, project_id, key),
            )
        else:
            cursor = self.conn.execute(
                """SELECT id, content FROM memories
                   WHERE target = ? AND project IS NULL AND key = ?
                   ORDER BY last_referenced DESC LIMIT 1""",
                (target, key),
            )
        row = cursor.fetchone()
        if row is None:
            return None
        # Update last_referenced
        self.conn.execute(
            "UPDATE memories SET last_referenced = ? WHERE id = ?",
            (time.time(), row["id"]),
        )
        self.conn.commit()
        return row["content"]

    def search(self, query: str, target: str | None = None,
               limit: int = 10) -> list[SqliteMemoryEntry]:
        """FTS5 search across memories. Ported from Hermes sqlite-memory-store.ts."""
        # Sanitize FTS5 query
        clean_query = query.replace('"', '""')
        sql = """SELECT m.* FROM memories m
                 JOIN memories_fts f ON m.id = f.rowid
                 WHERE memories_fts MATCH ?"""
        params: list = [clean_query]
        if target:
            sql += " AND m.target = ?"
            params.append(target)
        sql += " ORDER BY m.last_referenced DESC LIMIT ?"
        params.append(limit)
        cursor = self.conn.execute(sql, params)
        return [self._map_row(row) for row in cursor.fetchall()]

    def remove(self, target: str, scope: str, key: str,
               project_path: str | None = None):
        """Remove memory by exact key match."""
        project_id: str | None = None
        if scope == "project" and project_path:
            project_id = self._get_project_id(project_path)

        if project_id is not None:
            self.conn.execute(
                "DELETE FROM memories WHERE target = ? AND project = ? AND key = ?",
                (target, project_id, key),
            )
        else:
            self.conn.execute(
                "DELETE FROM memories WHERE target = ? AND project IS NULL AND key = ?",
                (target, key),
            )
        self.conn.commit()

    def replace(self, target: str, scope: str, old_text: str, new_text: str,
                category: str | None = None, project_path: str | None = None):
        """Replace old_text with new_text in matching memories."""
        result = scan_content(new_text)
        if result.blocked:
            raise ValueError(f"Content blocked: {result.reason}")

        project_id: str | None = None
        if scope == "project" and project_path:
            project_id = self._get_project_id(project_path)

        now = time.time()
        if project_id is not None:
            self.conn.execute(
                """UPDATE memories SET content = REPLACE(content, ?, ?),
                   created = ?, last_referenced = ?
                   WHERE target = ? AND project = ? AND content LIKE ?""",
                (old_text, new_text, now, now, target, project_id, f"%{old_text}%"),
            )
        else:
            self.conn.execute(
                """UPDATE memories SET content = REPLACE(content, ?, ?),
                   created = ?, last_referenced = ?
                   WHERE target = ? AND project IS NULL AND content LIKE ?""",
                (old_text, new_text, now, now, target, f"%{old_text}%"),
            )
        self.conn.commit()

    def delete_all(self, target: str | None = None) -> int:
        """Delete all memories, optionally filtered by target. Returns count removed."""
        if target:
            cursor = self.conn.execute("DELETE FROM memories WHERE target = ?", (target,))
        else:
            cursor = self.conn.execute("DELETE FROM memories")
        self.conn.commit()
        return cursor.rowcount

    def find_duplicates(self, target: str | None = None
                        ) -> list[dict]:
        """Find exact duplicate content entries per target.

        Returns list of {target, content, count, keep_id} for groups
        with 2+ identical entries.
        """
        where = "WHERE m.target = ?" if target else ""
        params = [target] if target else []
        rows = self.conn.execute(
            f"""SELECT m.target, m.content, COUNT(*) as cnt,
                       (SELECT m2.id FROM memories m2
                        WHERE m2.target = m.target AND m2.content = m.content
                        ORDER BY m2.created DESC LIMIT 1) as keep_id
                FROM memories m
                {where}
                GROUP BY m.target, m.content
                HAVING cnt > 1""",
            params,
        ).fetchall()
        return [dict(r) for r in rows]

    def consolidate_dedup(self, target: str | None = None) -> int:
        """Remove exact duplicate content, keeping the newest entry per content group.

        Returns total rows removed.
        """
        removed = 0
        for dup in self.find_duplicates(target):
            keep_id = dup["keep_id"]
            tgt = dup["target"]
            content = dup["content"]
            cursor = self.conn.execute(
                "DELETE FROM memories WHERE target = ? AND content = ? AND id != ?",
                (tgt, content, keep_id),
            )
            removed += cursor.rowcount
        self.conn.commit()
        return removed

    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None

    # ─── Hermes-style failure memory API ───

    def add_failure(self, content: str, category: str,
                    failure_reason: str | None = None,
                    tool_state: str | None = None,
                    corrected_to: str | None = None,
                    project_path: str | None = None) -> SqliteMemoryEntry:
        """Add a categorized failure memory. Ported from Hermes syncMemoryEntry()."""
        if category not in FAILURE_CATEGORIES:
            raise ValueError(f"Invalid failure category '{category}'. "
                             f"Must be one of {sorted(FAILURE_CATEGORIES)}")

        result = scan_content(content)
        if result.blocked:
            raise ValueError(f"Content blocked: {result.reason}")

        project_id: str | None = None
        if project_path:
            project_id = self._get_project_id(project_path)

        now = time.time()
        cursor = self.conn.execute(
            """INSERT INTO memories (project, target, category, content,
               failure_reason, tool_state, corrected_to, created, last_referenced)
               VALUES (?, 'failure', ?, ?, ?, ?, ?, ?, ?)""",
            (project_id, category, content, failure_reason,
             tool_state, corrected_to, now, now),
        )
        self.conn.commit()
        return SqliteMemoryEntry(
            id=cursor.lastrowid,
            project=project_id,
            target="failure",
            category=category,
            content=content,
            failure_reason=failure_reason,
            tool_state=tool_state,
            corrected_to=corrected_to,
            created=now,
            last_referenced=now,
        )

    def search_failures(self, category: str | None = None,
                        project_path: str | None = None,
                        limit: int = 10) -> list[SqliteMemoryEntry]:
        """Search failure memories. Ported from Hermes."""
        sql = "SELECT * FROM memories WHERE target = 'failure'"
        params: list = []
        if category:
            sql += " AND category = ?"
            params.append(category)
        if project_path:
            sql += " AND project = ?"
            params.append(self._get_project_id(project_path))
        else:
            sql += " AND project IS NULL"
        sql += " ORDER BY last_referenced DESC LIMIT ?"
        params.append(limit)
        cursor = self.conn.execute(sql, params)
        return [self._map_row(row) for row in cursor.fetchall()]

    def get_stale_failures(self, max_age_days: int = 7,
                           limit: int = 5) -> list[SqliteMemoryEntry]:
        """Get old, rarely-referenced failures. Ported from Hermes failure injection."""
        cutoff = time.time() - (max_age_days * 86400)
        cursor = self.conn.execute(
            """SELECT * FROM memories
               WHERE target = 'failure' AND last_referenced < ?
               ORDER BY last_referenced ASC LIMIT ?""",
            (cutoff, limit),
        )
        return [self._map_row(row) for row in cursor.fetchall()]

    # ─── Hermes-style skill API ───

    def add_skill(self, slug: str, name: str, description: str, code: str,
                  scope: str = "global", project_path: str | None = None) -> SqliteSkillEntry:
        """Add a skill to the skills table."""
        result = scan_content(code)
        if result.blocked:
            raise ValueError(f"Content blocked: {result.reason}")

        project_id: str | None = None
        if scope == "project" and project_path:
            project_id = self._get_project_id(project_path)

        now = time.time()
        cursor = self.conn.execute(
            """INSERT OR IGNORE INTO skills (slug, name, description, code, scope, project_id, created, updated)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (slug, name, description, code, scope, project_id, now, now),
        )
        if cursor.lastrowid is None:
            return self.get_skill(slug, scope=scope, project_path=project_path)
        self.conn.commit()
        return SqliteSkillEntry(
            id=cursor.lastrowid,
            slug=slug,
            name=name,
            description=description,
            code=code,
            scope=scope,
            created=now,
            updated=now,
        )

    def get_skill(self, slug: str, scope: str = "global",
                  project_path: str | None = None) -> SqliteSkillEntry | None:
        """Get a skill by slug."""
        project_id: str | None = None
        if scope == "project" and project_path:
            project_id = self._get_project_id(project_path)

        if project_id is not None:
            cursor = self.conn.execute(
                "SELECT * FROM skills WHERE slug = ? AND scope = ? AND project_id = ?",
                (slug, scope, project_id),
            )
        else:
            cursor = self.conn.execute(
                "SELECT * FROM skills WHERE slug = ? AND scope = ? AND project_id IS NULL",
                (slug, scope),
            )
        row = cursor.fetchone()
        if row is None:
            return None
        return SqliteSkillEntry(
            id=row["id"], slug=row["slug"], name=row["name"],
            description=row["description"], code=row["code"],
            scope=row["scope"], created=row["created"], updated=row["updated"],
        )

    def list_skills(self, scope: str = "global",
                    project_path: str | None = None) -> list[SqliteSkillEntry]:
        """List all skills."""
        project_id: str | None = None
        if scope == "project" and project_path:
            project_id = self._get_project_id(project_path)

        if project_id is not None:
            cursor = self.conn.execute(
                "SELECT * FROM skills WHERE scope = ? AND project_id = ? ORDER BY slug",
                (scope, project_id),
            )
        else:
            cursor = self.conn.execute(
                "SELECT * FROM skills WHERE scope = ? AND project_id IS NULL ORDER BY slug",
                (scope,),
            )
        return [
            SqliteSkillEntry(
                id=row["id"], slug=row["slug"], name=row["name"],
                description=row["description"], code=row["code"],
                scope=row["scope"], created=row["created"], updated=row["updated"],
            )
            for row in cursor.fetchall()
        ]

    def delete_skill(self, slug: str, scope: str = "global",
                     project_path: str | None = None) -> bool:
        """Delete a skill."""
        project_id: str | None = None
        if scope == "project" and project_path:
            project_id = self._get_project_id(project_path)

        if project_id is not None:
            cursor = self.conn.execute(
                "DELETE FROM skills WHERE slug = ? AND scope = ? AND project_id = ?",
                (slug, scope, project_id),
            )
        else:
            cursor = self.conn.execute(
                "DELETE FROM skills WHERE slug = ? AND scope = ? AND project_id IS NULL",
                (slug, scope),
            )
        self.conn.commit()
        return cursor.rowcount > 0

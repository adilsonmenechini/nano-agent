import json
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
    embedding: bytes | None = None


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
    status: str = "active"


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
        self._consolidator = None

    def set_consolidator(self, fn) -> None:
        self._consolidator = fn

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
        # Add embedding column if not present (schema migration)
        try:
            self.conn.execute("ALTER TABLE memories ADD COLUMN embedding BLOB")
        except sqlite3.OperationalError:
            pass  # column already exists
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS skill_versions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                skill_id INTEGER NOT NULL,
                version INTEGER NOT NULL,
                code TEXT NOT NULL,
                description TEXT,
                created REAL NOT NULL,
                FOREIGN KEY (skill_id) REFERENCES skills(id) ON DELETE CASCADE
            )
        """)
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_skill_versions_skill
            ON skill_versions(skill_id)
        """)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                project TEXT,
                messages TEXT NOT NULL DEFAULT '[]',
                status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active', 'paused', 'completed', 'cancelled')),
                created REAL NOT NULL,
                updated REAL NOT NULL
            )
        """)
        # Add status column to skills table if not present (schema migration)
        try:
            self.conn.execute("ALTER TABLE skills ADD COLUMN status TEXT DEFAULT 'active'")
        except sqlite3.OperationalError:
            pass

        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS reflection_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                turn_id TEXT NOT NULL UNIQUE,
                task_description TEXT,
                tool_calls TEXT NOT NULL DEFAULT '[]',
                steps_taken INTEGER DEFAULT 0,
                errors TEXT NOT NULL DEFAULT '[]',
                outcome TEXT NOT NULL DEFAULT 'success' CHECK(outcome IN ('success','partial','failure','error')),
                duration_ms INTEGER DEFAULT 0,
                lessons TEXT NOT NULL DEFAULT '[]',
                created REAL NOT NULL
            )
        """)
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_reflection_created
            ON reflection_records(created)
        """)
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_reflection_outcome
            ON reflection_records(outcome)
        """)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS experience_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trigger_context TEXT NOT NULL DEFAULT '{}',
                tool_sequence TEXT NOT NULL DEFAULT '[]',
                recommended_approach TEXT NOT NULL DEFAULT '',
                success_count INTEGER DEFAULT 0,
                failure_count INTEGER DEFAULT 0,
                sample_size INTEGER DEFAULT 0,
                first_observed REAL NOT NULL,
                last_applied REAL NOT NULL,
                is_active INTEGER DEFAULT 1
            )
        """)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS evolution_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                skill_slug TEXT NOT NULL,
                iteration INTEGER NOT NULL,
                baseline_fitness REAL,
                evolved_fitness REAL,
                accepted INTEGER DEFAULT 0,
                created REAL NOT NULL
            )
        """)
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

    def _project_filter(
        self, scope: str = "global", project_path: str | None = None
    ) -> tuple[str, list]:
        """Return (where_clause, params) for scoped queries."""
        if scope == "project" and project_path:
            return "project = ?", [self._get_project_id(project_path)]
        return "project IS NULL", []

    def _map_row(self, row: sqlite3.Row) -> SqliteMemoryEntry:
        return SqliteMemoryEntry(**{k: row[k] for k in row.keys()})

    def _char_limit(self, target: str) -> int:
        from .constants import (
            DEFAULT_MEMORY_CHAR_LIMIT,
            DEFAULT_USER_CHAR_LIMIT,
            DEFAULT_FAILURE_CHAR_LIMIT,
        )

        if target == "failure":
            return DEFAULT_FAILURE_CHAR_LIMIT
        elif target == "user":
            return DEFAULT_USER_CHAR_LIMIT
        return DEFAULT_MEMORY_CHAR_LIMIT

    def char_count(
        self, target: str, scope: str = "global", project_path: str | None = None
    ) -> int:
        """Get total character count of entries for target and scope/project."""
        project_id = None
        if scope == "project" and project_path:
            project_id = self._get_project_id(project_path)

        if project_id is not None:
            cursor = self.conn.execute(
                "SELECT SUM(LENGTH(content)) FROM memories WHERE target = ? AND project = ?",
                (target, project_id),
            )
        else:
            cursor = self.conn.execute(
                "SELECT SUM(LENGTH(content)) FROM memories WHERE target = ? AND project IS NULL",
                (target,),
            )
        row = cursor.fetchone()
        return row[0] if row and row[0] is not None else 0

    def _format_entries(
        self, target: str, where: str, params: list, char_limit: int
    ) -> str:
        """Select and join memory entries respecting char_limit."""
        from .constants import ENTRY_DELIMITER

        cursor = self.conn.execute(
            f"SELECT content FROM memories WHERE target = ? AND {where} ORDER BY last_referenced DESC",
            [target] + params,
        )
        result, length = [], 0
        for entry in (row["content"] for row in cursor.fetchall()):
            needed = len(entry) + (len(ENTRY_DELIMITER) if result else 0)
            if length + needed > char_limit:
                break
            result.append(entry)
            length += needed
        return ENTRY_DELIMITER.join(result)

    def format_for_system_prompt(self, target: str, char_limit: int = 5000) -> str:
        """Format global entries of a target with ENTRY_DELIMITER, respecting char_limit."""
        return self._format_entries(target, "project IS NULL", [], char_limit)

    def format_project_block(
        self, target: str, project_path: str, char_limit: int = 5000
    ) -> str:
        """Format project-scoped entries for the given project path, respecting char_limit."""
        pid = self._get_project_id(project_path)
        return self._format_entries(target, "project = ?", [pid], char_limit)

    # ─── Backward-compatible API ───

    def add(
        self,
        target: str,
        scope: str,
        key: str,
        value: str,
        category: str | None = None,
        project_path: str | None = None,
    ):
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

        if scope == "project" and project_path:
            project_id: str | None = self._get_project_id(project_path)
        elif scope == "global":
            project_id = None
        else:
            raise ValueError("Scope must be 'global' or 'project' with project_path")

        limit = self._char_limit(target)
        current_count = self.char_count(target, scope, project_path)
        if current_count + len(value) > limit:
            if self._consolidator:
                self._consolidator(target)
                current_count = self.char_count(target, scope, project_path)
            if current_count + len(value) > limit:
                raise ValueError(
                    f"Memory full for target '{target}'. "
                    f"Limit: {limit}, current: {current_count}, needed: {len(value)}"
                )

        now = time.time()
        embedding_blob: bytes | None = None
        try:
            from .embeddings import compute_embedding
            emb = compute_embedding(value)
            import struct
            embedding_blob = struct.pack(f"{len(emb)}d", *emb)
        except Exception:
            embedding_blob = None
        self.conn.execute(
            """INSERT INTO memories (project, target, category, key, content,
               failure_reason, tool_state, corrected_to, created, last_referenced, embedding)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (project_id, target, category, key, value, None, None, None, now, now, embedding_blob),
        )
        self.conn.commit()

    def get(
        self, target: str, scope: str, key: str, project_path: str | None = None
    ) -> str | None:
        """Retrieve memory by exact key match (backward-compatible)."""
        where, params = self._project_filter(scope, project_path)
        cursor = self.conn.execute(
            f"SELECT id, content FROM memories WHERE target = ? AND {where} AND key = ?"
            " ORDER BY last_referenced DESC LIMIT 1",
            [target] + params + [key],
        )
        row = cursor.fetchone()
        if row is None:
            return None
        self.conn.execute(
            "UPDATE memories SET last_referenced = ? WHERE id = ?",
            (time.time(), row["id"]),
        )
        self.conn.commit()
        return row["content"]

    def search(
        self, query: str, target: str | None = None, limit: int = 10
    ) -> list[SqliteMemoryEntry]:
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

    def semantic_search(
        self, query: str, target: str | None = None, limit: int = 10, alpha: float = 0.5
    ) -> list[SqliteMemoryEntry]:
        """Hybrid search: FTS5 keyword match ranked by cosine similarity.

        alpha=1.0 → pure semantic, alpha=0.0 → pure FTS5
        """
        from .embeddings import compute_embedding, cosine_similarity
        import struct

        query_emb = compute_embedding(query)

        fts_results = self.search(query, target=target, limit=limit * 2)

        scored: list[tuple[float, SqliteMemoryEntry]] = []
        for entry in fts_results:
            cursor = self.conn.execute(
                "SELECT embedding FROM memories WHERE id = ?", (entry.id,)
            )
            row = cursor.fetchone()
            if row and row["embedding"]:
                stored = list(struct.unpack(f"{len(row['embedding']) // 8}d", row["embedding"]))
                sim = cosine_similarity(query_emb, stored)
            else:
                sim = 0.0
            scored.append((alpha * sim + (1 - alpha), entry))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [entry for _, entry in scored[:limit]]

    def remove(
        self, target: str, scope: str, key: str, project_path: str | None = None
    ):
        """Remove memory by exact key match."""
        where, params = self._project_filter(scope, project_path)
        self.conn.execute(
            f"DELETE FROM memories WHERE target = ? AND {where} AND key = ?",
            [target] + params + [key],
        )
        self.conn.commit()

    def replace(
        self,
        target: str,
        scope: str,
        old_text: str,
        new_text: str,
        category: str | None = None,
        project_path: str | None = None,
    ):
        """Replace old_text with new_text in matching memories."""
        result = scan_content(new_text)
        if result.blocked:
            raise ValueError(f"Content blocked: {result.reason}")
        where, params = self._project_filter(scope, project_path)
        now = time.time()
        self.conn.execute(
            f"""UPDATE memories SET content = REPLACE(content, ?, ?),
               created = ?, last_referenced = ?
               WHERE target = ? AND {where} AND content LIKE ?""",
            [old_text, new_text, now, now, target] + params + [f"%{old_text}%"],
        )
        self.conn.commit()

    def delete_all(self, target: str | None = None) -> int:
        """Delete all memories, optionally filtered by target. Returns count removed."""
        if target:
            cursor = self.conn.execute(
                "DELETE FROM memories WHERE target = ?", (target,)
            )
        else:
            cursor = self.conn.execute("DELETE FROM memories")
        self.conn.commit()
        return cursor.rowcount

    def find_duplicates(self, target: str | None = None) -> list[dict]:
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

    # ─── Session API ───

    def save_session(
        self,
        session_id: str,
        messages: list[dict],
        project: str | None = None,
        status: str = "active",
    ) -> None:
        now = time.time()
        messages_json = json.dumps(messages, ensure_ascii=False)
        self.conn.execute(
            """INSERT INTO sessions (id, project, messages, status, created, updated)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(id) DO UPDATE SET
                   messages = excluded.messages,
                   status = excluded.status,
                   updated = excluded.updated""",
            (session_id, project, messages_json, status, now, now),
        )
        self.conn.commit()

    def load_session(self, session_id: str) -> dict | None:
        cursor = self.conn.execute(
            "SELECT id, project, messages, status, created, updated FROM sessions WHERE id = ?",
            (session_id,),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return {
            "id": row["id"],
            "project": row["project"],
            "messages": json.loads(row["messages"]),
            "status": row["status"],
            "created": row["created"],
            "updated": row["updated"],
        }

    def list_sessions(self, project: str | None = None, limit: int = 20) -> list[dict]:
        if project:
            cursor = self.conn.execute(
                "SELECT id, project, messages, status, created, updated FROM sessions WHERE project = ? ORDER BY updated DESC LIMIT ?",
                (project, limit),
            )
        else:
            cursor = self.conn.execute(
                "SELECT id, project, messages, status, created, updated FROM sessions ORDER BY updated DESC LIMIT ?",
                (limit,),
            )
        return [
            {
                "id": r["id"],
                "project": r["project"],
                "messages": json.loads(r["messages"]),
                "status": r["status"],
                "created": r["created"],
                "updated": r["updated"],
            }
            for r in cursor.fetchall()
        ]

    def update_session_status(self, session_id: str, status: str) -> None:
        self.conn.execute(
            "UPDATE sessions SET status = ?, updated = ? WHERE id = ?",
            (status, time.time(), session_id),
        )
        self.conn.commit()

    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None

    # ─── Hermes-style failure memory API ───

    def add_failure(
        self,
        content: str,
        category: str,
        failure_reason: str | None = None,
        tool_state: str | None = None,
        corrected_to: str | None = None,
        project_path: str | None = None,
    ) -> SqliteMemoryEntry:
        """Add a categorized failure memory. Ported from Hermes syncMemoryEntry()."""
        if category not in FAILURE_CATEGORIES:
            raise ValueError(
                f"Invalid failure category '{category}'. "
                f"Must be one of {sorted(FAILURE_CATEGORIES)}"
            )

        result = scan_content(content)
        if result.blocked:
            raise ValueError(f"Content blocked: {result.reason}")

        project_id: str | None = None
        if project_path:
            project_id = self._get_project_id(project_path)

        limit = self._char_limit("failure")
        current_count = self.char_count(
            "failure",
            scope="project" if project_path else "global",
            project_path=project_path,
        )

        if current_count + len(content) > limit:
            raise ValueError(
                f"Failure memory full. Limit: {limit}, current: {current_count}, needed: {len(content)}"
            )

        now = time.time()
        cursor = self.conn.execute(
            """INSERT INTO memories (project, target, category, content,
               failure_reason, tool_state, corrected_to, created, last_referenced)
               VALUES (?, 'failure', ?, ?, ?, ?, ?, ?, ?)""",
            (
                project_id,
                category,
                content,
                failure_reason,
                tool_state,
                corrected_to,
                now,
                now,
            ),
        )
        self.conn.commit()
        return SqliteMemoryEntry(
            id=cursor.lastrowid,
            project=project_id,
            target="failure",
            category=category,
            key=None,
            content=content,
            failure_reason=failure_reason,
            tool_state=tool_state,
            corrected_to=corrected_to,
            created=now,
            last_referenced=now,
        )

    def search_failures(
        self,
        category: str | None = None,
        project_path: str | None = None,
        limit: int = 10,
    ) -> list[SqliteMemoryEntry]:
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

    def get_stale_failures(
        self, max_age_days: int = 7, limit: int = 5
    ) -> list[SqliteMemoryEntry]:
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

    def add_skill(
        self,
        slug: str,
        name: str,
        description: str,
        code: str,
        scope: str = "global",
        project_path: str | None = None,
    ) -> SqliteSkillEntry:
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

    def get_skill(
        self, slug: str, scope: str = "global", project_path: str | None = None
    ) -> SqliteSkillEntry | None:
        """Get a skill by slug."""
        where, params = self._project_filter(scope, project_path)
        where = where.replace("project", "project_id")
        cursor = self.conn.execute(
            f"SELECT * FROM skills WHERE slug = ? AND scope = ? AND {where}",
            [slug, scope] + params,
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return SqliteSkillEntry(
            id=row["id"],
            slug=row["slug"],
            name=row["name"],
            description=row["description"],
            code=row["code"],
            scope=row["scope"],
            status=row["status"] if "status" in row.keys() else "active",
            created=row["created"],
            updated=row["updated"],
        )

    def list_skills(
        self, scope: str = "global", project_path: str | None = None
    ) -> list[SqliteSkillEntry]:
        """List all skills."""
        where, params = self._project_filter(scope, project_path)
        where = where.replace("project", "project_id")
        cursor = self.conn.execute(
            f"SELECT * FROM skills WHERE scope = ? AND {where} ORDER BY slug",
            [scope] + params,
        )
        return [
            SqliteSkillEntry(
                id=row["id"],
                slug=row["slug"],
                name=row["name"],
                description=row["description"],
                code=row["code"],
                scope=row["scope"],
                status=row["status"] if "status" in row.keys() else "active",
                created=row["created"],
                updated=row["updated"],
            )
            for row in cursor.fetchall()
        ]

    def delete_skill(
        self, slug: str, scope: str = "global", project_path: str | None = None
    ) -> bool:
        """Delete a skill and its version history."""
        where, params = self._project_filter(scope, project_path)
        where = where.replace("project", "project_id")
        # Delete FK-referencing versions first (safe even with CASCADE)
        self.conn.execute(
            f"DELETE FROM skill_versions WHERE skill_id IN "
            f"(SELECT id FROM skills WHERE slug = ? AND scope = ? AND {where})",
            [slug, scope] + params,
        )
        cursor = self.conn.execute(
            f"DELETE FROM skills WHERE slug = ? AND scope = ? AND {where}",
            [slug, scope] + params,
        )
        self.conn.commit()
        return cursor.rowcount > 0

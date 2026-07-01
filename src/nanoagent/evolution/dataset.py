from __future__ import annotations


from nanoagent.memory.sqlite_memory_store import SQLiteMemoryStore


class DatasetBuilder:
    def __init__(self, store: SQLiteMemoryStore | None = None):
        self.store = store

    def build_from_reflections(self, limit: int = 100) -> list[dict]:
        if not self.store:
            return []
        cursor = self.store.conn.execute(
            "SELECT task_description, tool_calls, outcome FROM reflection_records WHERE outcome IN ('success','failure') ORDER BY created DESC LIMIT ?",
            (limit,),
        )
        return [dict(row) for row in cursor.fetchall()]

    def build_synthetic(self, skill_domain: str, count: int = 10) -> list[dict]:
        examples = {
            "file": [
                {
                    "task_description": "List all files in directory",
                    "expected_tools": ["run_shell", "glob_file"],
                    "outcome": "success",
                },
                {
                    "task_description": "Read configuration file",
                    "expected_tools": ["read_file"],
                    "outcome": "success",
                },
            ],
            "git": [
                {
                    "task_description": "Check git status",
                    "expected_tools": ["git_status", "git_diff"],
                    "outcome": "success",
                },
                {
                    "task_description": "View recent commits",
                    "expected_tools": ["git_log"],
                    "outcome": "success",
                },
            ],
            "search": [
                {
                    "task_description": "Find files containing pattern",
                    "expected_tools": ["grep_file"],
                    "outcome": "success",
                },
                {
                    "task_description": "Search for function definition",
                    "expected_tools": ["grep_file", "read_file"],
                    "outcome": "success",
                },
            ],
        }
        domain_key = "file"
        for key in examples:
            if key in skill_domain.lower():
                domain_key = key
                break
        base = examples.get(domain_key, examples["file"])
        result = []
        for i in range(count):
            item = base[i % len(base)]
            result.append(dict(item))
        return result

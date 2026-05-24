import os
import tempfile
from pathlib import Path
from dataclasses import dataclass
from typing import Callable

from .content_scanner import scan_content
from .constants import (
    ENTRY_DELIMITER,
    DEFAULT_MEMORY_CHAR_LIMIT,
    DEFAULT_USER_CHAR_LIMIT,
    DEFAULT_FAILURE_CHAR_LIMIT,
    FAILURE_CATEGORIES,
    MEMORY_FILE,
    USER_FILE,
    FAILURES_FILE,
)


@dataclass
class MemorySnapshot:
    memory: str = ""
    user: str = ""
    failure: str = ""


MemoryTarget = str


class MemoryStore:
    """File-backed persistent memory store.

    Ported from pi-hermes-memory — §-delimited entries,
    atomic writes, content scanning, frozen snapshot.
    """

    def __init__(self, memory_dir: str | None = None,
                 memory_char_limit: int = DEFAULT_MEMORY_CHAR_LIMIT,
                 user_char_limit: int = DEFAULT_USER_CHAR_LIMIT,
                 failure_char_limit: int = DEFAULT_FAILURE_CHAR_LIMIT):
        if memory_dir is None:
            memory_dir = str(Path.home() / ".nanoagent" / "memory")
        self._memory_dir = memory_dir
        self._memory_char_limit = memory_char_limit
        self._user_char_limit = user_char_limit
        self._failure_char_limit = failure_char_limit

        self._memory_entries: list[str] = []
        self._user_entries: list[str] = []
        self._failure_entries: list[str] = []
        self._snapshot = MemorySnapshot()
        self._consolidator: Callable | None = None

        os.makedirs(self._memory_dir, exist_ok=True)
        self._load()

    def set_consolidator(self, fn: Callable) -> None:
        self._consolidator = fn

    @property
    def memory_dir(self) -> str:
        return self._memory_dir

    def _path_for(self, target: MemoryTarget) -> str:
        if target == "user":
            return os.path.join(self._memory_dir, USER_FILE)
        elif target == "failure":
            return os.path.join(self._memory_dir, FAILURES_FILE)
        return os.path.join(self._memory_dir, MEMORY_FILE)

    def _entries_for(self, target: MemoryTarget) -> list[str]:
        if target == "user":
            return self._user_entries
        elif target == "failure":
            return self._failure_entries
        return self._memory_entries

    def _set_entries(self, target: MemoryTarget, entries: list[str]) -> None:
        if target == "user":
            self._user_entries = entries
        elif target == "failure":
            self._failure_entries = entries
        else:
            self._memory_entries = entries

    def _char_limit(self, target: MemoryTarget) -> int:
        if target == "failure":
            return self._failure_char_limit
        elif target == "user":
            return self._user_char_limit
        return self._memory_char_limit

    def _char_count(self, target: MemoryTarget) -> int:
        return sum(len(e) for e in self._entries_for(target))

    def _load(self) -> None:
        for target in ("memory", "user", "failure"):
            filepath = self._path_for(target)
            if os.path.exists(filepath):
                with open(filepath, encoding="utf-8") as f:
                    raw = f.read()
                entries = [e.strip() for e in raw.split(ENTRY_DELIMITER) if e.strip()]
                self._set_entries(target, entries)
            else:
                self._set_entries(target, [])
        self._freeze_snapshot()

    def _freeze_snapshot(self) -> None:
        self._snapshot = MemorySnapshot(
            memory="\n".join(self._memory_entries),
            user="\n".join(self._user_entries),
            failure="\n".join(self._failure_entries),
        )

    def get_snapshot(self) -> MemorySnapshot:
        return self._snapshot

    def get_entries(self, target: MemoryTarget) -> list[str]:
        return list(self._entries_for(target))

    def _atomic_write(self, filepath: str, content: str) -> None:
        dirpath = os.path.dirname(filepath)
        fd, tmp = tempfile.mkstemp(dir=dirpath, prefix=".tmp_", suffix=".md")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(content)
            os.replace(tmp, filepath)
        except BaseException:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise

    def _save(self, target: MemoryTarget) -> None:
        entries = self._entries_for(target)
        content = ENTRY_DELIMITER.join(entries)
        filepath = self._path_for(target)
        self._atomic_write(filepath, content)

    def add(self, target: MemoryTarget, content: str) -> None:
        result = scan_content(content)
        if result.blocked:
            raise ValueError(f"Content blocked: {result.reason}")

        limit = self._char_limit(target)
        current_count = self._char_count(target)
        entries = self._entries_for(target)

        if current_count + len(content) > limit:
            if self._consolidator:
                self._consolidator(target)
                self._load()
            current_count = self._char_count(target)
            if current_count + len(content) > limit:
                raise ValueError(f"Memory full for target '{target}'. "
                                 f"Limit: {limit}, current: {current_count}, "
                                 f"needed: {len(content)}")

        entries.append(content)
        self._set_entries(target, entries)
        self._save(target)
        self._freeze_snapshot()

    def add_failure(self, content: str, category: str,
                    failure_reason: str | None = None,
                    corrected_to: str | None = None) -> None:
        """Add a categorized failure entry."""
        if category not in FAILURE_CATEGORIES:
            raise ValueError(f"Invalid failure category '{category}'")
        entry = f"[{category}]"
        if failure_reason:
            entry += f" reason: {failure_reason}"
        if corrected_to:
            entry += f" corrected: {corrected_to}"
        entry += f"\n{content}"
        self.add("failure", entry)

    def search(self, target: MemoryTarget, term: str) -> list[str]:
        """Simple linear search across entries."""
        return [e for e in self._entries_for(target) if term.lower() in e.lower()]

    def remove(self, target: MemoryTarget, index: int) -> bool:
        """Remove entry by index."""
        entries = self._entries_for(target)
        if 0 <= index < len(entries):
            entries.pop(index)
            self._set_entries(target, entries)
            self._save(target)
            self._freeze_snapshot()
            return True
        return False

    def clear(self, target: MemoryTarget) -> None:
        """Clear all entries for a target."""
        self._set_entries(target, [])
        self._save(target)
        self._freeze_snapshot()

"""Shared memory utilities."""

from __future__ import annotations

import hashlib


def parse_category_content(text: str) -> list[tuple[str, str]]:
    """Parse LLM output with CATEGORY:/CONTENT: format.

    Returns a list of (category, content) tuples.
    """
    entries: list[tuple[str, str]] = []
    current: str | None = None
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.upper().startswith("CATEGORY:"):
            current = line[9:].strip().lower()
        elif line.upper().startswith("CONTENT:") and current:
            entries.append((current, line[8:].strip()))
            current = None
    return entries


def persist_entries(entries: list[tuple[str, str]], agent, prefix: str) -> None:
    """Persist parsed CATEGORY/CONTENT entries into the agent memory."""
    for category, content in entries:
        if category in ("user", "memory"):
            key_hash = hashlib.sha256(content.encode()).hexdigest()[:8]
            agent.remember(
                key=f"{prefix}-{category}-{key_hash}",
                value=content,
                target=category,
                scope="project" if agent.project_path else "global",
            )
        elif category == "failure":
            agent.memory.add_failure(
                content=content,
                category="failure",
                project_path=agent.project_path,
            )

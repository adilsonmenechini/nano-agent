from __future__ import annotations

import re
from pathlib import Path
from typing import NamedTuple


class SkillMeta(NamedTuple):
    name: str
    description: str
    path: str
    source: str


_FRONTMATTER_RE = re.compile(r"^---\s*\r?\n(.*?)\r?\n---\s*\r?\n?", re.DOTALL)


class SkillsLoader:

    def __init__(self, sources: list[str | tuple[str, str]]):
        self._skills: dict[str, SkillMeta] = {}
        for entry in sources:
            if isinstance(entry, tuple):
                path, label = entry
            else:
                path = entry
                label = Path(path).name.replace("_", " ").title()
            self._scan(Path(path).expanduser(), label)

    def _scan(self, base: Path, label: str):
        if not base.is_dir():
            return
        for child in sorted(base.iterdir()):
            if not child.is_dir():
                continue
            skill_file = child / "SKILL.md"
            if not skill_file.exists():
                continue
            meta = self._parse(child.name, skill_file, label)
            if meta:
                self._skills[meta.name] = meta

    def _parse(self, dirname: str, path: Path, label: str) -> SkillMeta | None:
        raw = path.read_text(encoding="utf-8")
        m = _FRONTMATTER_RE.match(raw)
        if m:
            try:
                import yaml  # noqa: F811
                data = yaml.safe_load(m.group(1)) or {}
            except Exception:
                data = {}
            name = data.get("name") or dirname
            desc = data.get("description") or ""
        else:
            name = dirname
            desc = ""
        return SkillMeta(name=str(name), description=str(desc), path=str(path), source=label)

    @property
    def catalog(self) -> str:
        lines = []
        for skill in self._skills.values():
            lines.append(f"- {skill.name}: {skill.description}  ({skill.source})")
        return "\n".join(lines)

    def get(self, name: str) -> SkillMeta | None:
        return self._skills.get(name)

    def load_content(self, name: str) -> str | None:
        meta = self._skills.get(name)
        if not meta:
            return None
        path = Path(meta.path)
        if not path.exists():
            return None
        raw = path.read_text(encoding="utf-8")
        stripped = _FRONTMATTER_RE.sub("", raw)
        return stripped.strip()

    @property
    def names(self) -> list[str]:
        return list(self._skills.keys())

import re
from pathlib import Path

from nanoagent.tool import tool


def _get_project_root() -> Path:
    """Determine the project root directory."""
    return Path.cwd().resolve()


def _validate_path(path: str) -> Path:
    """Resolve and validate that a path is within the project directory."""
    resolved = Path(path).resolve()
    project_root = _get_project_root()
    if not str(resolved).startswith(str(project_root)):
        raise PermissionError(
            f"Access denied: path '{path}' is outside the project directory"
        )
    return resolved


@tool
def read_file(path: str) -> str:
    """Read a file's contents from an absolute path."""
    filepath = Path(path).resolve()
    if not filepath.exists():
        raise FileNotFoundError(f"File not found: {path}")
    if not filepath.is_file():
        raise IsADirectoryError(f"Path is a directory: {path}")
    try:
        return filepath.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return filepath.read_bytes().hex()


@tool
def write_file(path: str, content: str) -> str:
    """Write content to a file at an absolute path. Validates path is within project directory."""
    filepath = _validate_path(path)
    filepath.parent.mkdir(parents=True, exist_ok=True)
    filepath.write_text(content, encoding="utf-8")
    return f"OK: wrote {len(content)} bytes to {path}"


@tool
def glob_file(pattern: str, path: str = ".") -> str:
    """Find files matching a glob pattern."""
    search_dir = Path(path).resolve()
    if not search_dir.is_dir():
        return f"Error: directory not found: {path}"
    matches = list(search_dir.glob(pattern))
    if not matches:
        return "No matches found"
    return "\n".join(str(m.relative_to(search_dir)) for m in sorted(matches))


@tool
def grep_file(pattern: str, path: str = ".", context: int = 0) -> str:
    """Search file contents for a regex pattern."""
    search_dir = Path(path).resolve()
    if not search_dir.is_dir():
        return f"Error: directory not found: {path}"
    try:
        compiled = re.compile(pattern, re.MULTILINE)
    except re.error as e:
        return f"Error: invalid regex pattern: {e}"

    results: list[str] = []
    for filepath in search_dir.rglob("*"):
        if not filepath.is_file():
            continue
        try:
            text = filepath.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        lines = text.split("\n")
        rel_path = filepath.relative_to(search_dir)
        for i, line in enumerate(lines):
            if compiled.search(line):
                if context > 0:
                    start = max(0, i - context)
                    end = min(len(lines), i + context + 1)
                    results.append(f"{rel_path}:{i + 1}: ...")
                    for j in range(start, end):
                        prefix = ">" if j == i else " "
                        results.append(f"{prefix} {lines[j]}")
                    results.append("---")
                else:
                    results.append(f"{rel_path}:{i + 1}: {line}")

    if not results:
        return f"No matches found for pattern: {pattern}"
    return "\n".join(results)

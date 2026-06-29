import subprocess
from pathlib import Path

from nanoagent.tool import tool


def _git_cmd(args: list[str], path: str = ".") -> str:
    """Run a git command and return its output.

    Args:
        args: Git arguments (e.g., ["status", "--short"]).
        path: Repository path.

    Returns:
        Command stdout, or an error message prefixed with 'Error:'.
    """
    try:
        result = subprocess.run(
            ["git"] + args,
            capture_output=True,
            text=True,
            timeout=30,
            cwd=Path(path).resolve(),
        )
        if result.returncode != 0:
            error_msg = result.stderr.strip() or f"git exited with code {result.returncode}"
            return f"Error: {error_msg}"
        return result.stdout.rstrip("\n")
    except FileNotFoundError:
        return "Error: git not found. Is git installed?"
    except subprocess.TimeoutExpired:
        return "Error: git command timed out"
    except Exception as e:
        return f"Error: {e}"


@tool
def git_status(path: str = ".") -> str:
    """Show the working tree status (equivalent to 'git status --short')."""
    return _git_cmd(["status", "--short"], path=path)


@tool
def git_diff(path: str = ".") -> str:
    """Show unstaged changes (equivalent to 'git diff')."""
    return _git_cmd(["diff"], path=path)


@tool
def git_log(path: str = ".", max_count: int = 10) -> str:
    """Show recent commit history."""
    return _git_cmd(
        ["log", f"--max-count={max_count}", "--oneline", "--decorate"],
        path=path,
    )

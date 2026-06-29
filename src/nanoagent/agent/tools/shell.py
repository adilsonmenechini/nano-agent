import subprocess
from pathlib import Path

from nanoagent.tool import tool


@tool
def run_shell(command: str, timeout: int = 30, workdir: str = "") -> str:
    """Execute a shell command and return stdout, stderr, and exit code."""
    if not command or not command.strip():
        return "Error: empty command"

    cwd = None
    if workdir:
        cwd = Path(workdir).resolve()
        if not cwd.is_dir():
            return f"Error: working directory does not exist: {workdir}"

    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
        )
        parts = []
        if result.stdout:
            parts.append(result.stdout.rstrip("\n"))
        if result.stderr:
            parts.append(result.stderr.rstrip("\n"))
        if result.returncode != 0:
            parts.append(f"exit code: {result.returncode}")
        return "\n".join(parts)
    except subprocess.TimeoutExpired:
        return f"Error: command timed out after {timeout}s"
    except FileNotFoundError:
        return "Error: shell not found"
    except Exception as e:
        return f"Error: {e}"

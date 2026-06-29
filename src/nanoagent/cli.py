from __future__ import annotations

import select
import subprocess
import sys
import threading
import uuid
from dataclasses import dataclass, field
from pathlib import Path

import click
from rich.console import Console
from rich.markdown import Markdown
from rich.table import Table

from .agent import Agent
from .config import AgentConfig
from .llm.anthropic import AnthropicProvider
from .llm.base import BaseLLMProvider
from .llm.lmstudio import LMStudioProvider
from .llm.openai import OpenAIProvider
from .mcp import MCPManager
from .memory.correction_detector import is_correction
from .memory.session_flush import SessionFlush
from .learning.reflector import Reflector
from .introspection import HarnessAnalyzer
from .memory.sqlite_memory_store import SQLiteMemoryStore
from .skills.loader import SkillsLoader
from .tool import Tool

_PROVIDER_FACTORY: dict[str, type[BaseLLMProvider]] = {
    "openai": OpenAIProvider,
    "anthropic": AnthropicProvider,
    "lmstudio": LMStudioProvider,
}

console = Console()


# ─── Agent Job Tracking ────────────────────────────────────────────────────────


@dataclass
class AgentJob:
    job_id: str
    agent: Agent
    status: str
    thread: threading.Thread | None = None
    session_id: str | None = None
    messages: list[dict] = field(default_factory=list)
    system_prompt: str | None = None
    prompt: str | None = None
    result: tuple[str, list[dict]] | None = None
    error: str | None = None


class JobManager:
    def __init__(self):
        self._jobs: dict[str, AgentJob] = {}
        self._lock = threading.Lock()

    def add(self, job: AgentJob) -> None:
        with self._lock:
            self._jobs[job.job_id] = job

    def get(self, job_id: str) -> AgentJob | None:
        with self._lock:
            return self._jobs.get(job_id)

    def remove(self, job_id: str) -> None:
        with self._lock:
            self._jobs.pop(job_id, None)

    def list(self) -> list[AgentJob]:
        with self._lock:
            return list(self._jobs.values())

    def latest(self) -> AgentJob | None:
        with self._lock:
            if not self._jobs:
                return None
            return max(self._jobs.values(), key=lambda j: j.job_id)


_job_manager = JobManager()


def _stdin_ready(timeout: float = 0.05) -> bool:
    if sys.platform == "win32" or not sys.stdin.isatty():
        return False
    try:
        return select.select([sys.stdin], [], [], timeout) == ([sys.stdin], [], [])
    except (ValueError, TypeError, OSError):
        return False


def _fmt_time(t: float) -> str:
    from datetime import datetime

    return datetime.fromtimestamp(t).strftime("%Y-%m-%d %H:%M")


def _read_file(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return ""


def _build_system_prompt(project_path: str | None) -> str | None:
    if not project_path:
        return None
    base = Path(project_path).expanduser().resolve()
    parts = [_read_file(base / fname) for fname in ("AGENT.md", "USER.md")]
    parts = [p for p in parts if p]
    return "\n\n".join(parts) if parts else None


def _resolve_provider(provider_name: str | None) -> BaseLLMProvider | None:
    config = AgentConfig()
    name = provider_name or config.default_provider
    if not name:
        return None
    pc = config.get_provider_config(name)
    if not pc:
        click.echo(f"Error: Provider '{name}' not configured.", err=True)
        return None
    cls = _PROVIDER_FACTORY.get(name)
    if not cls:
        click.echo(f"Error: Unknown provider '{name}'.", err=True)
        return None
    return cls(api_key=pc.api_key, base_url=pc.base_url, model=pc.model)


def _find_mcp_json(candidate: str | None) -> Path | None:
    dirs = [Path(p).expanduser().resolve() for p in ([candidate] if candidate else [])]
    dirs.append(Path.cwd())
    for d in dirs:
        p = d / "mcp.json"
        if p.exists():
            return p
    return None


def _load_mcp_tools(project_path: str | None) -> list[Tool]:
    mcp_json = _find_mcp_json(project_path)
    if not mcp_json:
        return []
    manager = MCPManager()
    try:
        manager.load_json_config(str(mcp_json))
        tools = manager.discover_tools()
        if tools:
            console.print(f"[dim]Loaded {len(tools)} MCP tools[/dim]")
        return tools
    except Exception as e:
        console.print(f"[yellow]MCP load skipped: {e}[/yellow]")
        return []


def _load_skills(project_path: str | None) -> list[dict]:
    if not project_path:
        return []
    skills_dir = Path(project_path) / "skills"
    if not skills_dir.is_dir():
        return []
    loader = SkillsLoader([str(skills_dir)])
    loaded = [
        {"name": meta.name, "description": meta.description}
        for name in loader.names
        if (meta := loader.get(name))
    ]
    if loaded:
        console.print(f"[dim]Loaded {len(loaded)} skills from {skills_dir.name}/[/dim]")
    return loaded


def _run_consolidation(agent: Agent, target: str) -> None:
    store = agent.memory
    store.consolidate_dedup(target=target)
    llm_provider = agent.llm_provider
    if llm_provider is None:
        return

    entries = store.conn.execute(
        "SELECT content, key FROM memories WHERE target = ? ORDER BY created",
        (target,),
    ).fetchall()
    if len(entries) < 3:
        return

    contents = "\n\n".join(
        f"--- Entry #{i} (key: {e['key'] or '(none)'}) ---\n{e['content']}"
        for i, e in enumerate(entries, 1)
    )
    from .memory.constants import CONSOLIDATION_PROMPT

    cprompt = f"{CONSOLIDATION_PROMPT}\n\nTarget category: {target}\n\nEntries to consolidate:\n\n{contents}"
    try:
        response_text = llm_provider.generate(
            prompt=cprompt,
            system_prompt="You are a memory consolidation system. Output only the consolidated text.",
        )
        parts = [p.strip() for p in response_text.split("§") if p.strip()]
        if parts:
            store.conn.execute("DELETE FROM memories WHERE target = ?", (target,))
            for idx, part in enumerate(parts):
                store.add(
                    target=target,
                    scope="project" if agent.project_path else "global",
                    key=f"consolidated-{target}-{idx + 1}",
                    value=part,
                    project_path=agent.project_path,
                )
    except Exception:
        pass


def _check_config(output_json: bool = False) -> None:
    """Print current config sources and values."""
    import json as _json
    config = AgentConfig()
    info = {
        "default_provider": config.default_provider,
        "project_path": config.project_path,
        "max_tokens": config.max_tokens,
        "temperature": config.temperature,
        "retry_attempts": config.retry_attempts,
        "stream": config.stream,
        "review_enabled": config.review_enabled,
        "providers": {k: {"model": v.model, "base_url": v.base_url} for k, v in config.providers.items()},
    }
    if output_json:
        click.echo(_json.dumps(info, indent=2))
    else:
        for k, v in info.items():
            click.echo(f"{k}: {v}")


def _make_agent(provider_name: str | None, project_path: str | None) -> Agent:
    config = AgentConfig()
    project_path = project_path or config.project_path
    db_path = None
    if project_path:
        project_path = str(Path(project_path).expanduser().resolve())
        db_dir = Path(project_path) / "memory"
        db_dir.mkdir(parents=True, exist_ok=True)
        db_path = str(db_dir / "memory.db")
    llm = _resolve_provider(provider_name)
    agent = Agent(project_path=project_path, llm_provider=llm, db_path=db_path)
    agent.memory.set_consolidator(lambda target: _run_consolidation(agent, target))

    # Register local tools
    from .agent.tools.web_tool import WebTool
    from .agent.tools.todo import TodoTool

    agent.register_tool("web", WebTool())

    todo_file = "todos.json"
    if project_path:
        todo_file = str(Path(project_path) / "memory" / "todos.json")
    agent.register_tool("todo", TodoTool(storage_file=todo_file))

    for t in _load_mcp_tools(project_path):
        agent._tools.register(t)

    for s in _load_skills(project_path):
        slug = s["name"].lower().replace(" ", "-")
        if not agent.skill_storage.get_skill(slug, scope="global"):
            agent.skill_storage.add_skill(
                slug=slug,
                name=s["name"],
                description=s["description"],
                code="",
            )

    return agent


def _print_banner() -> None:
    console.print("""[bold green]
        ┌──────────────────┐
        │   ⚡ NanoAgent   │
        └──────────────────┘
    [/bold green]""")
    console.print("[dim]v0.1.0[/dim]")


def _print_welcome() -> None:
    _print_banner()
    console.print("[dim]/help - show commands | /exit - quit[/dim]")
    console.print()


def _print_full_help() -> None:
    _print_banner()
    console.print("\n[bold]Commands:[/bold]")
    commands = [
        ("/help", "Show available commands"),
        ("/clear", "Clear the screen"),
        ("/history", "Show conversation history"),
        ("/history -session <id>", "Load a saved session"),
        ("/tools", "List registered tools"),
        ("/skills", "List loaded skills"),
        ("/jobs", "List agent jobs"),
        ("/pause", "Pause the running agent job"),
        ("/resume", "Resume a paused agent job"),
        ("/cancel", "Cancel the running agent job"),
        ("/memory-insights", "Show memory stats"),
        ("/memory-search <q>", "FTS5 search across memories"),
        ("/memory-forget <key>", "Remove memory by key"),
        ("/memory-forget --all", "Remove all memories"),
        ("/memory-forget --target <t>", "Remove all memories for a target"),
        ("/memory-consolidate", "Dedup and consolidate memories"),
        ("!<cmd>", "Run a shell command"),
        ("/exit", "Exit the chat"),
    ]
    table = Table(show_header=False, box=None, pad_edge=False)
    table.add_column("Cmd", style="cyan", no_wrap=True)
    table.add_column("Description", style="white")
    for cmd, desc in commands:
        table.add_row(cmd, desc)
    console.print(table)
    console.print()


# ─── REPL command handlers ───────────────────────────────────────────────────


def _handle_history(messages: list[dict]) -> None:
    if not messages:
        console.print("[dim]No messages yet.[/dim]")
        return
    console.print(f"[bold]Conversation history[/bold] ({len(messages)} messages)")
    for i, msg in enumerate(messages, 1):
        role = msg.get("role", "?")
        content = msg.get("content", "")
        if content:
            console.print(f"  [dim]{i}.[/dim] [bold]{role}:[/bold] {content[:200]}")
        elif "tool_calls" in msg:
            for tc in msg["tool_calls"]:
                fn = tc.get("function", {})
                console.print(
                    f"  [dim]{i}.[/dim] [yellow]tool:[/yellow] {fn.get('name', '?')}"
                )
        elif msg.get("role") == "tool":
            console.print(f"  [dim]{i}.[/dim] [green]tool result[/green]")


def _handle_tools(agent: Agent) -> None:
    all_tools = agent.tools
    if not all_tools:
        console.print("[dim]No tools registered[/dim]")
        return
    table = Table(title=f"Tools ({len(all_tools)})", box=None)
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Description")
    for name, t in sorted(all_tools.items()):
        table.add_row(name, (getattr(t, "description", "") or "")[:120])
    console.print(table)


def _handle_skills(agent: Agent) -> None:
    db_skills = agent.skill_storage.list_skills(scope="global")
    if not db_skills:
        console.print("[dim]No skills stored[/dim]")
        return
    table = Table(title=f"Skills ({len(db_skills)})", box=None)
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Description")
    for s in sorted(db_skills, key=lambda x: x["name"]):
        table.add_row(s["name"], s["description"][:120])
    console.print(table)


def _handle_memory_search(query: str, agent: Agent) -> None:
    if not query:
        console.print("[yellow]Usage: /memory-search <query>[/yellow]")
        return
    results = agent.memory.search(query, limit=20)
    if not results:
        console.print(f"[dim]No results for '{query}'[/dim]")
        return
    table = Table(title=f"Memory search: '{query}' ({len(results)} results)", box=None)
    table.add_column("Target", style="cyan")
    table.add_column("Content")
    table.add_column("Key", style="yellow")
    for r in results:
        table.add_row(r.target, r.content[:150], r.key or "")
    console.print(table)


def _handle_memory_insights(agent: Agent) -> None:
    rows = agent.memory.conn.execute(
        "SELECT target, COUNT(*) as cnt, MIN(created) as oldest, MAX(created) as newest FROM memories GROUP BY target"
    ).fetchall()
    if not rows:
        console.print("[dim]No memories stored[/dim]")
        return
    total = sum(r["cnt"] for r in rows)
    table = Table(title=f"Memory ({total} total)", box=None)
    table.add_column("Target", style="cyan")
    table.add_column("Count", style="yellow")
    table.add_column("Oldest")
    table.add_column("Newest")
    for r in rows:
        table.add_row(
            r["target"], str(r["cnt"]), _fmt_time(r["oldest"]), _fmt_time(r["newest"])
        )
    console.print(table)


def _handle_memory_forget(raw: str, agent: Agent) -> None:
    if raw == "/memory-forget --all":
        count = agent.memory.delete_all()
        console.print(f"[green]Removed all {count} memories[/green]")
        return
    if raw.startswith("/memory-forget --target "):
        target = raw[len("/memory-forget --target ") :].strip()
        count = agent.memory.delete_all(target=target)
        console.print(f"[green]Removed all {count} '{target}' memories[/green]")
        return
    key = raw[len("/memory-forget ") :].strip()
    if not key:
        console.print(
            "[yellow]Usage: /memory-forget <key> | --all | --target <user|memory|failure>[/yellow]"
        )
        return
    conn = agent.memory.conn
    rows = conn.execute(
        "SELECT id, target, key, content FROM memories WHERE key = ? LIMIT 20", (key,)
    ).fetchall()
    if not rows:
        console.print(f"[dim]No memory found with key '{key}'[/dim]")
        return
    for r in rows:
        conn.execute("DELETE FROM memories WHERE id = ?", (r["id"],))
    conn.commit()
    console.print(f"[green]Removed {len(rows)} memory(ies) with key '{key}'[/green]")


def _handle_memory_consolidate(agent: Agent) -> None:
    store = agent.memory
    removed = store.consolidate_dedup()
    if removed:
        console.print(f"[dim]Dedup removed {removed} duplicate entries[/dim]")

    targets_with_counts = store.conn.execute(
        "SELECT target, COUNT(*) as cnt FROM memories GROUP BY target"
    ).fetchall()
    if not targets_with_counts:
        console.print("[yellow]No memories to consolidate[/yellow]")
        return

    llm_provider = agent.llm_provider
    if llm_provider is None:
        console.print(
            "[dim]No LLM provider — exact dedup only. Set a provider for semantic consolidation.[/dim]"
        )
        return

    from .memory.constants import CONSOLIDATION_PROMPT

    for row in targets_with_counts:
        target = row["target"]
        entries = store.conn.execute(
            "SELECT content, key FROM memories WHERE target = ? ORDER BY created",
            (target,),
        ).fetchall()
        if len(entries) < 3:
            continue
        contents = "\n\n".join(
            f"--- Entry #{i} (key: {e['key'] or '(none)'}) ---\n{e['content']}"
            for i, e in enumerate(entries, 1)
        )
        cprompt = f"{CONSOLIDATION_PROMPT}\n\nTarget category: {target}\n\nEntries to consolidate:\n\n{contents}"
        try:
            response_text = llm_provider.generate(
                prompt=cprompt,
                system_prompt="You are a memory consolidation system. Output only the consolidated text.",
            )
            parts = [p.strip() for p in response_text.split("§") if p.strip()]
            if parts:
                store.conn.execute("DELETE FROM memories WHERE target = ?", (target,))
                for idx, part in enumerate(parts):
                    store.add(
                        target=target,
                        scope="project" if agent.project_path else "global",
                        key=f"consolidated-{target}-{idx + 1}",
                        value=part,
                        project_path=agent.project_path,
                    )
                console.print(
                    f"[green]Consolidated {target}: {len(entries)} entries → {len(parts)}[/green]"
                )
            else:
                console.print(
                    f"[yellow]Consolidation returned empty result for {target}[/yellow]"
                )
        except Exception as e:
            console.print(f"[yellow]Consolidation failed for {target}: {e}[/yellow]")
    store.conn.commit()


def _handle_shell(cmd: str) -> None:
    if not cmd:
        return
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=30
        )
        if result.stdout:
            console.print(result.stdout.rstrip())
        if result.stderr:
            console.print(f"[red]{result.stderr.rstrip()}[/red]")
    except subprocess.TimeoutExpired:
        console.print("[red]Command timed out (30s)[/red]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


def _maybe_flush(messages: list[dict], agent: Agent) -> None:
    flusher = SessionFlush(flush_min_turns=agent.flush_min_turns)
    repl_turns = sum(1 for m in messages if m.get("role") == "user")
    if flusher.should_flush(repl_turns):
        console.print("[dim italic green]Flushing session memory...[/dim italic green]")
        flusher.flush(messages, agent)


def _run_with_status(
    agent: Agent,
    prompt: str,
    system_prompt: str | None,
    messages: list[dict],
    session_id: str | None = None,
) -> tuple[str, list[dict]]:
    result: list = [None, None]
    exc: list = [None]
    status_text: list[str] = ["thinking..."]

    def on_thinking() -> None:
        status_text[0] = "thinking..."

    def on_tool_call(name: str, _args: dict) -> None:
        label = name.removeprefix("mcp_").replace("_", " ")
        status_text[0] = f"tool: {label}"

    def on_skill_call(name: str, _kwargs: dict) -> None:
        label = name.replace("_", " ")
        status_text[0] = f"skill: {label}"

    def on_paused() -> None:
        status_text[0] = "paused"

    agent.on_thinking = on_thinking
    agent.on_tool_call = on_tool_call
    agent.on_skill_call = on_skill_call
    agent.on_paused = on_paused

    job_id = str(uuid.uuid4())[:8]
    job = AgentJob(
        job_id=job_id,
        agent=agent,
        status="running",
        session_id=session_id,
        messages=messages,
        system_prompt=system_prompt,
        prompt=prompt,
    )
    _job_manager.add(job)

    def _target() -> None:
        try:
            result[0], result[1] = agent.run(
                prompt,
                system_prompt=system_prompt,
                messages=messages,
                session_id=session_id,
            )
        except Exception as e:
            exc[0] = e

    thread = threading.Thread(target=_target, daemon=True)
    job.thread = thread
    thread.start()

    with console.status("", spinner="dots") as status:
        while thread.is_alive():
            status.update(f"[dim]{status_text[0]}[/dim]")
            if _stdin_ready(0.05):
                raw_cmd = sys.stdin.readline().strip().lower()
                if raw_cmd == "/pause":
                    agent.pause_event.clear()
                    job.status = "paused"
                    if session_id:
                        agent.memory.update_session_status(session_id, "paused")
                    console.print(
                        "\n[yellow]Paused. Type /resume to continue or /cancel to stop.[/yellow]"
                    )
                elif raw_cmd == "/cancel":
                    agent.cancelled = True
                    job.status = "cancelled"
                    if session_id:
                        agent.memory.update_session_status(session_id, "cancelled")
                    console.print("\n[red]Cancelling...[/red]")
                elif raw_cmd == "/resume":
                    agent.pause_event.set()
                    job.status = "running"
                    if session_id:
                        agent.memory.update_session_status(session_id, "active")
                    console.print("\n[green]Resumed.[/green]")
                elif raw_cmd == "/jobs":
                    _handle_jobs(_job_manager)
            thread.join(timeout=0.05)

    if agent.cancelled:
        job.status = "cancelled"
        if session_id:
            agent.memory.update_session_status(session_id, "cancelled")
    elif not agent.pause_event.is_set():
        job.status = "paused"
    else:
        job.status = "completed"

    if exc[0]:
        job.error = str(exc[0])
        raise exc[0]
    job.result = (result[0], result[1])
    return result[0], result[1]


# ─── Job command handlers ──────────────────────────────────────────────────────


def _handle_jobs(job_manager: JobManager) -> None:
    jobs = job_manager.list()
    if not jobs:
        console.print("[dim]No jobs.[/dim]")
        return
    table = Table(title="Jobs", box=None)
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Status", style="yellow")
    table.add_column("Prompt")
    for j in jobs[-10:]:
        prompt_preview = (j.prompt or "")[:60]
        table.add_row(j.job_id, j.status, prompt_preview)
    console.print(table)


def _handle_pause(job_manager: JobManager) -> None:
    job = job_manager.latest()
    if not job or job.status != "running":
        console.print("[yellow]No running job to pause.[/yellow]")
        return
    job.agent.pause_event.clear()
    job.status = "paused"
    if job.session_id:
        job.agent.memory.update_session_status(job.session_id, "paused")
    console.print("[yellow]Pause requested.[/yellow]")


def _handle_resume(job_manager: JobManager) -> None:
    job = job_manager.latest()
    if not job:
        console.print("[yellow]No jobs found.[/yellow]")
        return
    if job.status == "paused":
        job.agent.pause_event.set()
        job.status = "running"
        if job.session_id:
            job.agent.memory.update_session_status(job.session_id, "active")
        console.print("[green]Resumed.[/green]")
    else:
        console.print("[yellow]No paused job to resume.[/yellow]")


def _handle_cancel(job_manager: JobManager) -> None:
    job = job_manager.latest()
    if not job or job.status not in ("running", "paused"):
        console.print("[yellow]No active job to cancel.[/yellow]")
        return
    job.agent.cancelled = True
    job.agent.pause_event.set()
    job.status = "cancelled"
    if job.session_id:
        job.agent.memory.update_session_status(job.session_id, "cancelled")
    console.print("[red]Cancellation requested.[/red]")


# ─── CLI commands ─────────────────────────────────────────────────────────────


@click.group()
@click.version_option(version="0.1.0")
def cli():
    pass


@cli.command()
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def check_config(output_json):
    """Show current configuration sources and values."""
    _check_config(output_json=output_json)


@cli.command()
@click.option("--provider", "-pr", default=None, help="Provider to check (default: all)")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def health(provider, output_json):
    """Check provider connectivity status."""
    import json as _json
    config = AgentConfig()
    providers_to_check: list[tuple[str, type[BaseLLMProvider]]] = []
    if provider and provider in _PROVIDER_FACTORY:
        providers_to_check = [(provider, _PROVIDER_FACTORY[provider])]
    elif provider:
        click.echo(f"Unknown provider: {provider}")
        return
    else:
        providers_to_check = list(_PROVIDER_FACTORY.items())

    results: dict[str, str] = {}
    for name, factory in providers_to_check:
        try:
            provider_config = config.providers.get(name)
            if provider_config:
                inst = factory(
                    api_key=provider_config.api_key,
                    base_url=provider_config.base_url,
                    model=provider_config.model,
                )
            else:
                inst = factory()
            inst.chat(messages=[{"role": "user", "content": "ping"}], max_tokens=1)
            results[name] = "connected"
        except Exception as e:
            results[name] = f"error: {e}"

    if output_json:
        click.echo(_json.dumps(results, indent=2))
    else:
        for name, status in results.items():
            color = "green" if status == "connected" else "red"
            click.echo(click.style(f"  {name}: {status}", fg=color))


@cli.command()
@click.option("--prompt", "-p", prompt="Enter your prompt")
@click.option("--provider", "-pr", default=None)
@click.option("--project-path", "-pp", default=None)
@click.option("--diagnostics", is_flag=True, help="Show turn diagnostics")
def run(prompt, provider, project_path, diagnostics):
    agent = _make_agent(provider, project_path)
    system_prompt = _build_system_prompt(agent.project_path)
    diagnostics_collector = None
    if diagnostics:
        from nanoagent.loop.diagnostics import DiagnosticsCollector
        diagnostics_collector = DiagnosticsCollector(enabled=True)
    response, _ = agent.run(prompt, system_prompt=system_prompt)
    click.echo(response)
    if diagnostics and diagnostics_collector is not None:
        rendered = diagnostics_collector.render()
        if rendered:
            console.print(rendered)


@cli.command()
@click.option("--provider", "-pr", default=None)
@click.option("--project-path", "-pp", default=None)
@click.option("--diagnostics", is_flag=True, help="Show turn diagnostics")
@click.option("--health", is_flag=True, help="Show health indicator in prompt")
def chat(provider, project_path, diagnostics, health):
    agent = _make_agent(provider, project_path)
    system_prompt = _build_system_prompt(agent.project_path)
    messages: list[dict] = []
    session_id: str | None = str(uuid.uuid4())[:12]

    diagnostics_collector = None
    if diagnostics or health:
        from nanoagent.loop.diagnostics import DiagnosticsCollector
        diagnostics_collector = DiagnosticsCollector(enabled=diagnostics)

    _print_welcome()

    _repl_completer = None
    try:
        from prompt_toolkit import PromptSession
        from prompt_toolkit.completion import WordCompleter
        from prompt_toolkit.formatted_text import HTML
        _repl_words = [
            "help", "clear", "history", "tools", "skills", "jobs",
            "pause", "resume", "cancel", "memory-search", "memory-insights",
            "memory-forget", "memory-consolidate", "shell", "exit", "quit",
        ]
        _repl_completer = WordCompleter(_repl_words, ignore_case=True)
        _repl_session = PromptSession(completer=_repl_completer)
        _use_pt = True
    except ImportError:
        _use_pt = False

    while True:
        try:
            if _use_pt and _repl_completer is not None:
                prompt_text = "<b><style fg='green'>you</style></b> <style fg='gray'>›</style> "
                if health and diagnostics_collector is not None:
                    report = diagnostics_collector.report()
                    if report.health_snapshots:
                        last = report.health_snapshots[-1]
                        level = last.get("level", "healthy")
                        color = "green" if level == "healthy" else "yellow" if level == "warning" else "red"
                        prompt_text = f"<b><style fg='green'>you</style></b> <b><style fg='{color}'>{level[0]}</style></b> <style fg='gray'>›</style> "
                raw = _repl_session.prompt(HTML(prompt_text)).strip()
            else:
                prompt_suffix = ""
                if health and diagnostics_collector is not None:
                    report = diagnostics_collector.report()
                    if report.health_snapshots:
                        last = report.health_snapshots[-1]
                        level = last.get("level", "healthy")
                        colors = {"healthy": "green", "warning": "yellow", "degraded": "yellow", "critical": "red"}
                        color = colors.get(level, "green")
                        prompt_suffix = f" [{color}]{level[0]}[/{color}]"
                raw = console.input(f"[bold green]you[/bold green]{prompt_suffix} [dim]›[/dim] ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print()
            if session_id and messages:
                agent.memory.save_session(session_id, messages, status="completed")
            _maybe_flush(messages, agent)
            break

        if raw in ("exit", "quit", "/exit", "/quit"):
            if session_id and messages:
                agent.memory.save_session(session_id, messages, status="completed")
            _maybe_flush(messages, agent)
            break

        if not raw:
            continue

        if raw in ("/help", "help"):
            _print_full_help()
        elif raw in ("/clear", "clear"):
            console.clear()
            _print_welcome()
        elif raw.startswith("/history"):
            parts = raw.split(maxsplit=2)
            if len(parts) == 3 and parts[1] == "-session":
                sid = parts[2]
                stored = agent.memory.load_session(sid)
                if stored:
                    messages = list(stored["messages"])
                    session_id = sid
                    console.print(
                        f"[green]Loaded session {sid} ({len(messages)} messages)[/green]"
                    )
                else:
                    console.print(f"[yellow]Session {sid} not found.[/yellow]")
            else:
                _handle_history(messages)
        elif raw in ("/tools", "tools"):
            _handle_tools(agent)
        elif raw in ("/skills", "skills"):
            _handle_skills(agent)
        elif raw == "/jobs":
            _handle_jobs(_job_manager)
        elif raw == "/pause":
            _handle_pause(_job_manager)
        elif raw == "/resume":
            _handle_resume(_job_manager)
        elif raw == "/cancel":
            _handle_cancel(_job_manager)
        elif raw.startswith("/memory-search "):
            _handle_memory_search(raw[len("/memory-search ") :].strip(), agent)
        elif raw == "/memory-insights":
            _handle_memory_insights(agent)
        elif raw.startswith("/memory-forget"):
            _handle_memory_forget(raw, agent)
        elif raw == "/memory-consolidate":
            _handle_memory_consolidate(agent)
        elif raw in ("/memory-preview-context", "memory-preview-context"):
            injected_sys = agent.build_system_prompt(system_prompt)
            console.print(
                "[bold cyan]--- Injected System Prompt Preview ---[/bold cyan]"
            )
            console.print(injected_sys)
            console.print(
                "[bold cyan]----------------------------------------[/bold cyan]"
            )
        elif raw.startswith("!"):
            _handle_shell(raw[1:])
        else:
            if is_correction(raw):
                try:
                    agent.memory.add_failure(
                        content=raw,
                        category="correction",
                        project_path=agent.project_path,
                    )
                    console.print(
                        "[dim italic green]Saved correction feedback to failure memories.[/dim italic green]"
                    )
                except Exception as e:
                    console.print(
                        f"[dim yellow]Could not auto-save correction feedback: {e}[/dim yellow]"
                    )
            try:
                response, messages = _run_with_status(
                    agent, raw, system_prompt, messages, session_id=session_id
                )
            except RuntimeError as e:
                console.print(f"[red]{e}[/red]")
                continue
            if response:
                console.print("[bold purple]nano[/bold purple] [dim]›[/dim]")
                console.print(Markdown(response))
            if diagnostics and diagnostics_collector is not None:
                rendered = diagnostics_collector.render()
                if rendered:
                    console.print(rendered)


# ─── Skill CLI ─────────────────────────────────────────────────────────


@cli.group()
def skill():
    """Manage agent skills."""


@skill.command("list-proposals")
def skill_list_proposals():
    """List proposed skills awaiting approval."""
    store = SQLiteMemoryStore()
    from nanoagent.skills.skill_storage import SkillStorage
    ss = SkillStorage(store=store)
    proposals = ss.list_proposed_skills()
    if not proposals:
        console.print("[yellow]No proposed skills.[/yellow]")
        return
    table = Table(title=f"Proposed Skills ({len(proposals)})")
    table.add_column("Slug")
    table.add_column("Name")
    table.add_column("Description")
    for p in proposals:
        table.add_row(p["slug"], p["name"], p["description"][:60])
    console.print(table)


@skill.command("accept")
@click.argument("slug")
def skill_accept(slug):
    """Accept a proposed skill and make it active."""
    store = SQLiteMemoryStore()
    from nanoagent.skills.skill_storage import SkillStorage
    ss = SkillStorage(store=store)
    if ss.activate_skill(slug):
        console.print(f"[green]Skill '{slug}' activated.[/green]")
    else:
        console.print(f"[red]Skill '{slug}' not found or already active.[/red]")


@skill.command("reject")
@click.argument("slug")
def skill_reject(slug):
    """Reject a proposed skill."""
    store = SQLiteMemoryStore()
    from nanoagent.skills.skill_storage import SkillStorage
    ss = SkillStorage(store=store)
    if ss.reject_skill(slug):
        console.print(f"[yellow]Skill '{slug}' rejected.[/yellow]")
    else:
        console.print(f"[red]Skill '{slug}' not found.[/red]")


@skill.command("evolve")
@click.argument("slug")
@click.option("--iterations", default=5, help="Number of evolution iterations")
@click.option("--eval-source", default="synthetic", help="synthetic or reflection_records")
def skill_evolve(slug, iterations, eval_source):
    """Evolve a skill using DSPy-style optimization."""
    store = SQLiteMemoryStore()
    from nanoagent.evolution.pipeline import EvolutionPipeline
    from nanoagent.evolution.config import EvolutionConfig
    config = EvolutionConfig(iterations=iterations, eval_source=eval_source)
    pipeline = EvolutionPipeline(store=store, config=config)
    console.print(f"[bold]Evolving skill '{slug}'...[/bold]")
    result = pipeline.evolve(slug, iterations=iterations)
    if not result.get("success"):
        console.print(f"[red]Evolution failed: {result.get('error', 'unknown error')}[/red]")
        return
    baseline = result.get("baseline", {})
    best = result.get("best_fitness", {})
    console.print(f"[bold]Baseline fitness:[/bold] {baseline.get('fitness_score', 0):.3f}")
    console.print(f"[bold]Evolved fitness:[/bold] {best.get('fitness_score', 0):.3f}")
    improved = result.get("improved", False)
    if improved:
        console.print("[green]✓ Evolution improved the skill![/green]")
        if click.confirm("Accept the evolved variant?"):
            evolved_code = result.get("best_variant", "")
            if pipeline.accept_evolution(slug, evolved_code):
                console.print(f"[green]Skill '{slug}' updated with evolved version.[/green]")
            else:
                console.print("[red]Failed to update skill.[/red]")
    else:
        console.print("[yellow]Evolution did not improve baseline. Keeping current version.[/yellow]")


# ─── Harness CLI ───────────────────────────────────────────────────────


@cli.group()
def harness():
    """Introspect agent configuration and state."""


@harness.command("report")
def harness_report():
    """Generate full harness introspection report."""
    config = AgentConfig()
    store = SQLiteMemoryStore()
    analyzer = HarnessAnalyzer(config=config, memory_store=store)
    console.print(analyzer.report())


@harness.command("analyze")
def harness_analyze():
    """Analyze harness for optimization recommendations."""
    config = AgentConfig()
    store = SQLiteMemoryStore()
    analyzer = HarnessAnalyzer(config=config, memory_store=store)
    recs = analyzer.analyze()
    if not recs:
        console.print("[green]No recommendations — harness looks healthy.[/green]")
        return
    console.print("[bold]Optimization Recommendations:[/bold]")
    for r in recs:
        severity_color = {"high": "red", "medium": "yellow", "low": "dim"}.get(r["severity"], "white")
        console.print(f"  [{severity_color}][{r['severity'].upper()}][/] {r['type']}")
        console.print(f"       {r['message']} (confidence: {r['confidence']:.0%})")


# ─── Reflection CLI ────────────────────────────────────────────────────


@cli.group()
def reflection():
    """Inspect agent reflections."""


@reflection.command("list")
@click.option("--limit", default=10, help="Number of reflections to show")
def reflection_list(limit):
    """Show recent reflections."""
    store = SQLiteMemoryStore()
    reflector = Reflector(store)
    records = reflector.get_recent(limit=limit)
    if not records:
        console.print("[yellow]No reflections found.[/yellow]")
        return
    table = Table(title=f"Recent Reflections (last {len(records)})")
    table.add_column("Turn ID", style="dim")
    table.add_column("Task")
    table.add_column("Outcome")
    table.add_column("Steps")
    table.add_column("Duration")
    for r in records:
        table.add_row(
            r["turn_id"][:8],
            r["task_description"][:50],
            r["outcome"],
            str(r["steps_taken"]),
            f"{r['duration_ms']}ms",
        )
    console.print(table)


@reflection.command("show")
@click.argument("turn_id")
def reflection_show(turn_id):
    """Show a specific reflection."""
    store = SQLiteMemoryStore()
    reflector = Reflector(store)
    record = reflector.get_by_turn_id(turn_id)
    if not record:
        console.print(f"[red]Reflection not found: {turn_id}[/red]")
        return
    console.print(f"[bold]Turn ID:[/bold] {record['turn_id']}")
    console.print(f"[bold]Task:[/bold] {record['task_description']}")
    console.print(f"[bold]Outcome:[/bold] {record['outcome']}")
    console.print(f"[bold]Steps:[/bold] {record['steps_taken']}")
    console.print(f"[bold]Duration:[/bold] {record['duration_ms']}ms")
    errors_raw = record.get("errors", "[]")
    if errors_raw and errors_raw != "[]":
        import json as _json
        errors = _json.loads(errors_raw) if isinstance(errors_raw, str) else errors_raw
        if errors:
            console.print("[red]Errors:[/red]")
            for e in errors:
                console.print(f"  - {e}")
    lessons_raw = record.get("lessons", "[]")
    if lessons_raw and lessons_raw != "[]":
        import json as _json
        lessons = _json.loads(lessons_raw) if isinstance(lessons_raw, str) else lessons_raw
        if lessons:
            console.print("[bold]Lessons:[/bold]")
            for lesson in lessons:
                console.print(f"  - {lesson}")


@reflection.command("search")
@click.argument("query")
@click.option("--limit", default=10)
def reflection_search(query, limit):
    """Search reflections by keyword."""
    store = SQLiteMemoryStore()
    reflector = Reflector(store)
    records = reflector.search(query, limit=limit)
    if not records:
        console.print(f"[yellow]No reflections matching '{query}'[/yellow]")
        return
    console.print(f"[bold]Found {len(records)} reflection(s):[/bold]")
    for r in records:
        console.print(f"  {r['turn_id'][:8]} — {r['task_description'][:60]} [{r['outcome']}]")


@reflection.command("stats")
def reflection_stats():
    """Show reflection statistics."""
    store = SQLiteMemoryStore()
    reflector = Reflector(store)
    stats = reflector.get_stats()
    console.print("[bold]Reflection Statistics[/bold]")
    console.print(f"  Total turns: {stats.get('total', 0)}")
    console.print(f"  Success: {stats.get('success_count', 0)}")
    console.print(f"  Failures: {stats.get('failure_count', 0)}")
    console.print(f"  Errors: {stats.get('error_count', 0)}")
    console.print(f"  Avg duration: {stats.get('avg_duration_ms', 0):.0f}ms")


if __name__ == "__main__":
    cli()

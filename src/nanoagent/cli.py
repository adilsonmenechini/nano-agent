from __future__ import annotations

import subprocess
import threading
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
from .skills.loader import SkillsLoader
from .tool import Tool

_PROVIDER_FACTORY: dict[str, type[BaseLLMProvider]] = {
    "openai": OpenAIProvider,
    "anthropic": AnthropicProvider,
    "lmstudio": LMStudioProvider,
}

console = Console()


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
                    key=f"consolidated-{target}-{idx+1}",
                    value=part,
                    project_path=agent.project_path,
                )
    except Exception:
        pass


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
                slug=slug, name=s["name"], description=s["description"], code="",
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
        ("/tools", "List registered tools"),
        ("/skills", "List loaded skills"),
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
                console.print(f"  [dim]{i}.[/dim] [yellow]tool:[/yellow] {fn.get('name', '?')}")
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
        table.add_row(r["target"], str(r["cnt"]), _fmt_time(r["oldest"]), _fmt_time(r["newest"]))
    console.print(table)


def _handle_memory_forget(raw: str, agent: Agent) -> None:
    if raw == "/memory-forget --all":
        count = agent.memory.delete_all()
        console.print(f"[green]Removed all {count} memories[/green]")
        return
    if raw.startswith("/memory-forget --target "):
        target = raw[len("/memory-forget --target "):].strip()
        count = agent.memory.delete_all(target=target)
        console.print(f"[green]Removed all {count} '{target}' memories[/green]")
        return
    key = raw[len("/memory-forget "):].strip()
    if not key:
        console.print("[yellow]Usage: /memory-forget <key> | --all | --target <user|memory|failure>[/yellow]")
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
        console.print("[dim]No LLM provider — exact dedup only. Set a provider for semantic consolidation.[/dim]")
        return

    from .memory.constants import CONSOLIDATION_PROMPT
    for row in targets_with_counts:
        target = row["target"]
        entries = store.conn.execute(
            "SELECT content, key FROM memories WHERE target = ? ORDER BY created", (target,)
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
                        target=target, scope="project" if agent.project_path else "global",
                        key=f"consolidated-{target}-{idx+1}", value=part,
                        project_path=agent.project_path,
                    )
                console.print(f"[green]Consolidated {target}: {len(entries)} entries → {len(parts)}[/green]")
            else:
                console.print(f"[yellow]Consolidation returned empty result for {target}[/yellow]")
        except Exception as e:
            console.print(f"[yellow]Consolidation failed for {target}: {e}[/yellow]")
    store.conn.commit()


def _handle_shell(cmd: str) -> None:
    if not cmd:
        return
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
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
) -> tuple[str, list[dict]]:
    """Run agent.run() in a background thread with a live Rich spinner.

    The spinner text updates dynamically:
    - "✦ thinking..." while waiting for the LLM
    - "⚙ <tool_name>" while a tool executes
    """
    result: list = [None, None]
    exc: list = [None]
    status_text: list[str] = ["✦ thinking..."]

    def on_thinking() -> None:
        status_text[0] = "✦ thinking..."

    def on_tool_call(name: str, _args: dict) -> None:
        label = name.removeprefix("mcp_").replace("_", " ")
        status_text[0] = f"⚙  {label}"

    def on_skill_call(name: str, _kwargs: dict) -> None:
        label = name.replace("_", " ")
        status_text[0] = f"⚡  {label}"

    agent.on_thinking = on_thinking
    agent.on_tool_call = on_tool_call
    agent.on_skill_call = on_skill_call


    def _target() -> None:
        try:
            result[0], result[1] = agent.run(
                prompt, system_prompt=system_prompt, messages=messages
            )
        except Exception as e:  # noqa: BLE001
            exc[0] = e

    thread = threading.Thread(target=_target, daemon=True)
    thread.start()
    with console.status("", spinner="dots") as status:
        while thread.is_alive():
            status.update(f"[dim]{status_text[0]}[/dim]")
            thread.join(timeout=0.1)

    if exc[0]:
        raise exc[0]  # type: ignore[misc]
    return result[0], result[1]


# ─── CLI commands ─────────────────────────────────────────────────────────────

@click.group()
@click.version_option(version="0.1.0")
def cli():
    pass


@cli.command()
@click.option("--prompt", "-p", prompt="Enter your prompt")
@click.option("--provider", "-pr", default=None)
@click.option("--project-path", "-pp", default=None)
def run(prompt, provider, project_path):
    agent = _make_agent(provider, project_path)
    system_prompt = _build_system_prompt(agent.project_path)
    response, _ = agent.run(prompt, system_prompt=system_prompt)
    click.echo(response)


@cli.command()
@click.option("--provider", "-pr", default=None)
@click.option("--project-path", "-pp", default=None)
def chat(provider, project_path):
    agent = _make_agent(provider, project_path)
    system_prompt = _build_system_prompt(agent.project_path)
    messages: list[dict] = []

    _print_welcome()

    while True:
        try:
            raw = console.input("[bold green]you[/bold green] [dim]›[/dim] ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print()
            _maybe_flush(messages, agent)
            break

        if raw in ("exit", "quit", "/exit", "/quit"):
            _maybe_flush(messages, agent)
            break

        if not raw:
            continue

        if raw in ("/help", "help"):
            _print_full_help()
        elif raw in ("/clear", "clear"):
            console.clear()
            _print_welcome()
        elif raw in ("/history", "history"):
            _handle_history(messages)
        elif raw in ("/tools", "tools"):
            _handle_tools(agent)
        elif raw in ("/skills", "skills"):
            _handle_skills(agent)
        elif raw.startswith("/memory-search "):
            _handle_memory_search(raw[len("/memory-search "):].strip(), agent)
        elif raw == "/memory-insights":
            _handle_memory_insights(agent)
        elif raw.startswith("/memory-forget"):
            _handle_memory_forget(raw, agent)
        elif raw == "/memory-consolidate":
            _handle_memory_consolidate(agent)
        elif raw in ("/memory-preview-context", "memory-preview-context"):
            injected_sys = agent.build_system_prompt(system_prompt)
            console.print("[bold cyan]--- Injected System Prompt Preview ---[/bold cyan]")
            console.print(injected_sys)
            console.print("[bold cyan]----------------------------------------[/bold cyan]")
        elif raw.startswith("!"):
            _handle_shell(raw[1:])
        else:
            if is_correction(raw):
                try:
                    agent.memory.add_failure(
                        content=raw, category="correction", project_path=agent.project_path
                    )
                    console.print("[dim italic green]Saved correction feedback to failure memories.[/dim italic green]")
                except Exception as e:
                    console.print(f"[dim yellow]Could not auto-save correction feedback: {e}[/dim yellow]")
            try:
                response, messages = _run_with_status(
                    agent, raw, system_prompt, messages
                )
            except RuntimeError as e:
                console.print(f"[red]{e}[/red]")
                continue
            if response:
                console.print("[bold purple]nano[/bold purple] [dim]›[/dim]")
                console.print(Markdown(response))



if __name__ == "__main__":
    cli()

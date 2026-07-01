// Command handler — intercepts /commands and !shell in the chat, same as CLI
// Routes to local frontend actions or backend API calls

class CommandRouter {
  constructor(app) {
    this.app = app;
  }

  /** Check if text is a command, handle it, return true if handled */
  async handle(text, chat) {
    if (!text || typeof text !== 'string') return false;

    const trimmed = text.trim();

    // Shell commands: !<command>
    if (trimmed.startsWith('!')) {
      const cmd = trimmed.slice(1).trim();
      if (cmd) {
        await this._handleShell(cmd, chat);
        return true;
      }
      return false;
    }

    // Slash commands: /command [args]
    if (!trimmed.startsWith('/')) return false;

    const parts = trimmed.split(/\s+/);
    const command = parts[0].toLowerCase();
    const args = parts.slice(1).join(' ');
    const argArr = parts.slice(1);

    switch (command) {
      case '/help':
      case 'help':
        this._handleHelp(chat);
        return true;

      case '/clear':
      case 'clear':
        this._handleClear(chat);
        return true;

      case '/history':
        this._handleHistory(chat);
        return true;

      case '/tools':
        await this._handleTools(chat);
        return true;

      case '/skills':
        await this._handleSkills(chat);
        return true;

      case '/jobs':
        chat.addSystemMessage('Job management is not available in the web UI. Use the CLI for /jobs.');
        return true;

      case '/pause':
        chat.addSystemMessage('Pause is handled automatically. Use the Cancel button to stop the current response.');
        return true;

      case '/resume':
        chat.addSystemMessage('Resume is handled automatically. Start a new message to continue.');
        return true;

      case '/cancel':
        this.app.cancelMessage();
        chat.addSystemMessage('Operation cancelled.');
        return true;

      case '/agents':
        await this._handleAgents(chat);
        return true;

      case '/commands':
        await this._handleCommands(chat);
        return true;

      case '/memory':
        await this._handleMemory(args, chat);
        return true;

      case '/exit':
      case '/quit':
        chat.addSystemMessage('Closing the tab will end the session.');
        return true;

      default:
        return false;
    }
  }

  // ─── Help ────────────────────────────────────────────────────────────

  _handleHelp(chat) {
    const commands = [
      { cmd: '/help', desc: 'Show available commands' },
      { cmd: '/clear', desc: 'Clear the chat' },
      { cmd: '/history', desc: 'Show conversation history' },
      { cmd: '/tools', desc: 'List registered tools' },
      { cmd: '/skills', desc: 'List loaded skills' },
      { cmd: '/cancel', desc: 'Cancel the current response' },
      { cmd: '/memory', desc: 'Memory: search, insights, consolidate, forget' },
      { cmd: '/agents', desc: 'List workspace agents' },
      { cmd: '/commands', desc: 'List workspace commands' },
      { cmd: '@agent <prompt>', desc: 'Use a specialized agent' },
      { cmd: '!<command>', desc: 'Run a shell command' },
    ];

    let html = '<strong>Available Commands</strong><br><br>';
    html += '<table style="width:100%; border-collapse: collapse;">';
    for (const { cmd, desc } of commands) {
      html += `<tr><td style="padding: 4px 12px 4px 0; font-family: monospace; color: #8b5cf6; white-space: nowrap;">${cmd}</td><td style="padding: 4px 0; color: #9ca3af;">${desc}</td></tr>`;
    }
    html += '</table>';

    chat.addCommandMessage('help', html);
  }

  // ─── Clear ───────────────────────────────────────────────────────────

  _handleClear(chat) {
    chat.clear();
  }

  // ─── History ─────────────────────────────────────────────────────────

  _handleHistory(chat) {
    const messages = chat._getAllMessages();
    if (!messages || messages.length === 0) {
      chat.addSystemMessage('No messages yet.');
      return;
    }

    const count = messages.length;
    const userCount = messages.filter(m => m.role === 'user').length;
    const agentCount = messages.filter(m => m.role === 'assistant').length;

    const lastFew = messages.slice(-5);
    let html = `<strong>Conversation History</strong> — ${count} messages total (${userCount} user, ${agentCount} agent)<br><br>`;
    html += '<div style="font-size: 13px;">';
    for (const m of lastFew) {
      const role = m.role === 'user' ? 'You' : 'NanoAgent';
      const content = (m.content || '').slice(0, 100);
      const color = m.role === 'user' ? '#8b5cf6' : '#34d399';
      html += `<div style="margin-bottom: 6px;"><span style="color: ${color}; font-weight: 600;">${role}:</span> <span style="color: #9ca3af;">${this._escapeHtml(content)}</span></div>`;
    }
    if (count > 5) {
      html += `<div style="color: #6b7280; margin-top: 4px;">… and ${count - 5} more messages</div>`;
    }
    html += '</div>';

    chat.addCommandMessage('history', html);
  }

  // ─── Tools ───────────────────────────────────────────────────────────

  async _handleTools(chat) {
    try {
      const resp = await fetch('/api/tools');
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data = await resp.json();
      const tools = data.tools || [];

      if (tools.length === 0) {
        chat.addSystemMessage('No tools registered.');
        return;
      }

      let html = `<strong>Tools (${tools.length})</strong><br><br>`;
      html += '<table style="width:100%; border-collapse: collapse;">';
      for (const t of tools) {
        const desc = (t.description || '—').slice(0, 100);
        html += `<tr><td style="padding: 6px 12px 6px 0; font-family: monospace; color: #3b82f6; white-space: nowrap;">${t.name}</td><td style="padding: 6px 0; color: #9ca3af;">${this._escapeHtml(desc)}</td></tr>`;
      }
      html += '</table>';

      chat.addCommandMessage('tools', html);
    } catch (e) {
      chat.addSystemMessage(`Error loading tools: ${e.message}`);
    }
  }

  // ─── Skills ──────────────────────────────────────────────────────────

  async _handleSkills(chat) {
    try {
      const resp = await fetch('/api/skills');
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data = await resp.json();
      const skills = data.skills || [];

      if (skills.length === 0) {
        chat.addSystemMessage('No skills loaded.');
        return;
      }

      let html = `<strong>Skills (${skills.length})</strong><br><br>`;
      html += '<table style="width:100%; border-collapse: collapse;">';
      for (const s of skills) {
        const desc = (s.description || '—').slice(0, 100);
        const status = s.enabled ? '<span style="color: #34d399;">Active</span>' : '<span style="color: #6b7280;">Disabled</span>';
        html += `<tr><td style="padding: 6px 12px 6px 0; font-family: monospace; color: #fbbf24;">${this._escapeHtml(s.name)}</td><td style="padding: 6px 12px 6px 0; color: #9ca3af;">${this._escapeHtml(desc)}</td><td style="padding: 6px 0;">${status}</td></tr>`;
      }
      html += '</table>';

      chat.addCommandMessage('skills', html);
    } catch (e) {
      chat.addSystemMessage(`Error loading skills: ${e.message}`);
    }
  }

  // ─── Memory (unified: /memory search|insights|consolidate|forget) ─────

  async _handleMemory(args, chat) {
    const parts = args.split(/\s+/);
    const sub = (parts[0] || '').toLowerCase();
    const rest = parts.slice(1).join(' ');

    switch (sub) {
      case 'search':
        if (!rest) {
          chat.addSystemMessage('Usage: /memory search <query>');
          return;
        }
        await this._memorySearch(rest, chat);
        break;

      case 'insights':
      case 'stats':
        await this._memoryInsights(chat);
        break;

      case 'consolidate':
        await this._memoryConsolidate(chat);
        break;

      case 'forget':
      case 'delete':
      case 'rm':
        await this._memoryForget(rest, chat);
        break;

      default:
        chat.addCommandMessage('memory',
          '<strong>/memory &lt;subcommand&gt; [args]</strong><br><br>' +
          '<table style="width:100%; border-collapse: collapse;">' +
          '<tr><td style="padding: 4px 12px 4px 0; font-family: monospace; color: #8b5cf6; white-space: nowrap;">/memory search &lt;q&gt;</td><td style="padding: 4px 0; color: #9ca3af;">Search memories</td></tr>' +
          '<tr><td style="padding: 4px 12px 4px 0; font-family: monospace; color: #8b5cf6; white-space: nowrap;">/memory insights</td><td style="padding: 4px 0; color: #9ca3af;">Show memory statistics</td></tr>' +
          '<tr><td style="padding: 4px 12px 4px 0; font-family: monospace; color: #8b5cf6; white-space: nowrap;">/memory consolidate</td><td style="padding: 4px 0; color: #9ca3af;">Consolidate memories</td></tr>' +
          '<tr><td style="padding: 4px 12px 4px 0; font-family: monospace; color: #8b5cf6; white-space: nowrap;">/memory forget &lt;key&gt;</td><td style="padding: 4px 0; color: #9ca3af;">Remove memory by key</td></tr>' +
          '<tr><td style="padding: 4px 12px 4px 0; font-family: monospace; color: #8b5cf6; white-space: nowrap;">/memory forget --all</td><td style="padding: 4px 0; color: #9ca3af;">Remove all memories</td></tr>' +
          '<tr><td style="padding: 4px 12px 4px 0; font-family: monospace; color: #8b5cf6; white-space: nowrap;">/memory forget --target &lt;t&gt;</td><td style="padding: 4px 0; color: #9ca3af;">Remove by target type</td></tr>' +
          '</table>'
        );
    }
  }

  async _memorySearch(query, chat) {
    try {
      const resp = await fetch(`/api/memory/search?q=${encodeURIComponent(query)}&limit=15`);
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data = await resp.json();
      const results = data.results || [];

      if (results.length === 0) {
        chat.addSystemMessage(`No memory results for '${query}'`);
        return;
      }

      let html = `<strong>Memory search: '${this._escapeHtml(query)}' (${results.length} results)</strong><br><br>`;
      for (const r of results) {
        const time = new Date(r.created * 1000).toLocaleString();
        html += `<div style="margin-bottom: 10px; padding: 8px 12px; background: rgba(255,255,255,0.03); border-radius: 8px; border: 1px solid rgba(255,255,255,0.06);">`;
        html += `<div style="display: flex; gap: 8px; margin-bottom: 4px; font-size: 12px;">`;
        html += `<span style="color: #8b5cf6;">${r.target}</span>`;
        if (r.key) html += `<span style="color: #fbbf24;">${this._escapeHtml(r.key)}</span>`;
        html += `<span style="color: #6b7280;">${time}</span>`;
        html += `</div>`;
        html += `<div style="color: #d1d5db; font-size: 13px;">${this._escapeHtml(r.content)}</div>`;
        html += `</div>`;
      }

      chat.addCommandMessage('/memory search', html);
    } catch (e) {
      chat.addSystemMessage(`Error searching memory: ${e.message}`);
    }
  }

  async _memoryInsights(chat) {
    try {
      const resp = await fetch('/api/memory/insights');
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data = await resp.json();
      const stats = data.stats || [];

      if (stats.length === 0) {
        chat.addSystemMessage('No memories stored.');
        return;
      }

      let html = `<strong>Memory (${data.total} total)</strong><br><br>`;
      html += '<table style="width:100%; border-collapse: collapse;">';
      html += '<tr style="color: #6b7280; font-size: 12px;"><th style="text-align: left; padding: 4px 12px 4px 0;">Target</th><th style="text-align: left; padding: 4px 12px 4px 0;">Count</th><th style="text-align: left; padding: 4px 0;">Period</th></tr>';
      for (const s of stats) {
        const oldest = new Date(s.oldest * 1000).toLocaleDateString();
        const newest = new Date(s.newest * 1000).toLocaleDateString();
        html += `<tr><td style="padding: 6px 12px 6px 0; color: #8b5cf6;">${s.target}</td><td style="padding: 6px 12px 6px 0; color: #fbbf24;">${s.count}</td><td style="padding: 6px 0; color: #9ca3af;">${oldest} → ${newest}</td></tr>`;
      }
      html += '</table>';

      chat.addCommandMessage('/memory insights', html);
    } catch (e) {
      chat.addSystemMessage(`Error getting memory stats: ${e.message}`);
    }
  }

  async _memoryConsolidate(chat) {
    chat.addSystemMessage('Consolidating memories...');
    try {
      const resp = await fetch('/api/memory/consolidate', { method: 'POST' });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data = await resp.json();
      if (data.duplicates_removed > 0) {
        chat.addSystemMessage(`Consolidation complete. Removed ${data.duplicates_removed} duplicate entries.`);
      } else {
        chat.addSystemMessage('Consolidation complete. No duplicates found.');
      }
    } catch (e) {
      chat.addSystemMessage(`Error consolidating: ${e.message}`);
    }
  }

  async _memoryForget(args, chat) {
    if (!args) {
      chat.addSystemMessage('Usage: /memory forget <key> | --all | --target <memory|user|failure>');
      return;
    }
    if (args === '--all') {
      chat.addSystemMessage('This action will delete ALL memories. Not implemented via web UI for safety — use the CLI.');
    } else if (args.startsWith('--target ')) {
      const target = args.slice(9).trim();
      chat.addSystemMessage(`Memory deletion for target '${target}' is not available in the web UI. Use the CLI.`);
    } else {
      const key = args.trim();
      chat.addSystemMessage(`Memory deletion by key '${key}' is not available in the web UI. Use the CLI.`);
    }
  }

  // ─── Agents ──────────────────────────────────────────────────────────

  async _handleAgents(chat) {
    try {
      const resp = await fetch('/api/agents');
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data = await resp.json();
      const agents = data.agents || [];

      if (agents.length === 0) {
        chat.addSystemMessage('No workspace agents loaded.');
        return;
      }

      let html = `<strong>Workspace Agents (${agents.length})</strong><br><br>`;
      html += '<table style="width:100%; border-collapse: collapse;">';
      for (const a of agents) {
        const desc = (a.description || '—').slice(0, 100);
        html += `<tr><td style="padding: 6px 12px 6px 0; font-family: monospace; color: #8b5cf6; white-space: nowrap;">@${this._escapeHtml(a.name)}</td><td style="padding: 6px 0; color: #9ca3af;">${this._escapeHtml(desc)}</td></tr>`;
      }
      html += '</table>';
      html += '<br><div style="color: #6b7280; font-size: 12px;">Use @agent-name &lt;prompt&gt; to invoke a specialized agent</div>';

      chat.addCommandMessage('agents', html);
    } catch (e) {
      chat.addSystemMessage(`Error loading agents: ${e.message}`);
    }
  }

  // ─── Commands List ────────────────────────────────────────────────────

  async _handleCommands(chat) {
    try {
      const resp = await fetch('/api/commands');
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data = await resp.json();
      const cmds = data.commands || [];

      if (cmds.length === 0) {
        chat.addSystemMessage('No workspace commands loaded.');
        return;
      }

      let html = `<strong>Workspace Commands (${cmds.length})</strong><br><br>`;
      html += '<table style="width:100%; border-collapse: collapse;">';
      for (const c of cmds) {
        const desc = (c.description || '—').slice(0, 100);
        let usage = `/${c.name}`;
        if (c.arguments && c.arguments.length > 0) {
          for (const arg of c.arguments) {
            usage += arg.required ? ` &lt;${arg.name}&gt;` : ` [${arg.name}]`;
          }
        }
        html += `<tr><td style="padding: 6px 12px 6px 0; font-family: monospace; color: #fbbf24; white-space: nowrap;">${this._escapeHtml(usage)}</td><td style="padding: 6px 0; color: #9ca3af;">${this._escapeHtml(desc)}</td></tr>`;
      }
      html += '</table>';
      html += '<br><div style="color: #6b7280; font-size: 12px;">Use /command-name &lt;args&gt; to run a workflow</div>';

      chat.addCommandMessage('commands', html);
    } catch (e) {
      chat.addSystemMessage(`Error loading commands: ${e.message}`);
    }
  }

  // ─── Shell ───────────────────────────────────────────────────────────

  async _handleShell(command, chat) {
    chat.addSystemMessage(`Running: ! ${command}`);
    try {
      const resp = await fetch('/api/shell', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ command }),
      });
      const data = await resp.json();

      if (data.exit_code === -1) {
        chat.showError(`Shell error: ${data.error || 'Command failed'}`);
        return;
      }

      let html = `<strong>$ ${this._escapeHtml(command)}</strong><br>`;
      if (data.stdout) {
        html += `<pre style="margin: 8px 0 0; padding: 10px; background: rgba(0,0,0,0.3); border-radius: 8px; font-size: 12px; line-height: 1.5; overflow-x: auto; color: #d1d5db;">${this._escapeHtml(data.stdout)}</pre>`;
      }
      if (data.stderr) {
        html += `<pre style="margin: 8px 0 0; padding: 10px; background: rgba(30,10,10,0.3); border-radius: 8px; font-size: 12px; line-height: 1.5; overflow-x: auto; color: #f87171;">${this._escapeHtml(data.stderr)}</pre>`;
      }
      html += `<div style="margin-top: 6px; font-size: 12px; color: ${data.exit_code === 0 ? '#34d399' : '#f87171'};">Exit code: ${data.exit_code}</div>`;

      chat.addCommandMessage('shell', html);
    } catch (e) {
      chat.showError(`Shell error: ${e.message}`);
    }
  }

  // ─── Utils ───────────────────────────────────────────────────────────

  _escapeHtml(text) {
    if (typeof text !== 'string') return '';
    return text
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }
}

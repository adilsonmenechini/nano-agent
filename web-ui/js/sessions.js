// Modern SessionManager — search, inline rename, delete, optimistic UI, AbortController cleanup

const toasts = {
  show(message, kind = 'info') {
    let root = document.getElementById('toast-root');
    if (!root) {
      root = document.createElement('div');
      root.id = 'toast-root';
      root.className = 'toast-root';
      document.body.appendChild(root);
    }
    const t = document.createElement('div');
    t.className = `toast toast-${kind}`;
    t.setAttribute('role', 'status');
    t.textContent = message;
    root.appendChild(t);
    requestAnimationFrame(() => t.classList.add('visible'));
    setTimeout(() => {
      t.classList.remove('visible');
      t.addEventListener('transitionend', () => t.remove(), { once: true });
    }, 2600);
  }
};

class SessionManager {
  constructor(listContainer) {
    this.container = listContainer;
    this.items = [];
    this.onSessionSelected = null;
    this.activeId = null;
    this._searchTerm = '';
    this._abortController = null;
  }

  async fetchSessions() {
    this._abortController?.abort();
    this._abortController = new AbortController();
    try {
      const req = fetch('/api/sessions', { signal: this._abortController.signal });
      const resp = await req;
      if (!resp.ok) throw new Error(`HTTP ${resp.status}: ${resp.statusText}`);
      const data = await resp.json();
      return data.sessions || [];
    } catch (e) {
      if (e.name === 'AbortError') return null;
      toasts.show('Failed to load sessions', 'error');
      return null;
    }
  }

  async loadSessions() {
    const fresh = await this.fetchSessions();
    if (fresh) {
      this.items = fresh;
      this.render();
    }
  }

  async createSession() {
    try {
      const resp = await fetch('/api/sessions', { method: 'POST' });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const json = await resp.json();
      const session = json.session;
      const entry = {
        id: session.id,
        name: 'New session',
        message_count: 0,
        created_at: session.created_at,
        updated_at: session.updated_at,
      };
      this.items.unshift(entry);
      this.activeId = entry.id;
      this.render();
      toasts.show('Session created');
      return entry.id;
    } catch (e) {
      toasts.show('Failed to create session', 'error');
      return null;
    }
  }

  async deleteSession(id) {
    this.items = this.items.filter(s => s.id !== id);
    if (this.activeId === id) this.activeId = null;
    this.render();
    try {
      const resp = await fetch(`/api/sessions/${encodeURIComponent(id)}`, { method: 'DELETE' });
      if (resp.status === 404) return; // already gone
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      toasts.show('Session deleted');
    } catch (e) {
      toasts.show('Failed to delete session', 'error');
    }
  }

  async renameSession(id, newName) {
    const trimmed = (newName || '').trim();
    if (!trimmed) return;
    const item = this.items.find(s => s.id === id);
    if (item) item.name = trimmed;
    this.render();
    try {
      const resp = await fetch(`/api/sessions/${encodeURIComponent(id)}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: trimmed }),
      });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      toasts.show('Renamed');
    } catch (e) {
      toasts.show('Failed to rename session', 'error');
      this.render();
    }
  }

  setActive(id) {
    this.activeId = id;
    this._updateActiveClass();
  }

  setSearchTerm(term) {
    this._searchTerm = term.trim().toLowerCase();
    this.render();
  }

  _notify(id) { if (typeof this.onSessionSelected === 'function') this.onSessionSelected(id); }

  _updateActiveClass() {
    this.container.querySelectorAll('.session-item').forEach(el => {
      el.classList.toggle('active', el.dataset.id === this.activeId);
    });
  }

  _select(id) {
    this.setActive(id);
    this._notify(id);
  }

  _formatRelativeTime(updatedAt) {
    const ts = typeof updatedAt === 'number' ? updatedAt : Date.parse(updatedAt) / 1000;
    const ms = Math.abs(Date.now() - ts * 1000);
    if (ms < 60_000) return 'just now';
    if (ms < 60 * 60_000) return `${Math.floor(ms / 60_000)}m ago`;
    if (ms < 24 * 60 * 60_000) return `${Math.floor(ms / 60 * 60_000)}h ago`;
    return new Date(ts * 1000).toLocaleDateString();
  }

  _renderItem(s) {
    const wrap = document.createElement('div');
    wrap.className = 'session-item' + (s.id === this.activeId ? ' active' : '');
    wrap.dataset.id = s.id;

    const select = document.createElement('button');
    select.className = 'session-main';
    select.type = 'button';

    const name = document.createElement('span');
    name.className = 'session-name';
    name.textContent = s.name || `Session ${String(s.id).slice(0, 8)}`;

    const time = document.createElement('time');
    time.className = 'session-time';
    time.textContent = this._formatRelativeTime(s.updated_at);
    try { time.setAttribute('datetime', new Date(s.updated_at * 1000).toISOString()); } catch {}

    select.appendChild(name);
    select.appendChild(time);

    const actions = document.createElement('div');
    actions.className = 'session-actions';

    const renameBtn = document.createElement('button');
    renameBtn.className = 'icon-btn';
    renameBtn.type = 'button';
    renameBtn.title = 'Rename';
    renameBtn.setAttribute('aria-label', 'Rename session');
    renameBtn.textContent = '✎';

    const renameInput = document.createElement('input');
    renameInput.className = 'session-rename-input';
    renameInput.type = 'text';
    renameInput.value = name.textContent;
    renameInput.style.display = 'none';

    const deleteBtn = document.createElement('button');
    deleteBtn.className = 'icon-btn icon-btn--danger';
    deleteBtn.type = 'button';
    deleteBtn.title = 'Delete';
    deleteBtn.setAttribute('aria-label', 'Delete session');
    deleteBtn.textContent = '🗑';

    renameBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      renameInput.style.display = '';
      renameInput.focus();
      renameInput.select();
    });

    renameInput.addEventListener('blur', async () => {
      renameInput.style.display = 'none';
      await this.renameSession(s.id, renameInput.value);
    });

    renameInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') renameInput.blur();
      if (e.key === 'Escape') {
        renameInput.value = name.textContent;
        renameInput.blur();
      }
    });

    deleteBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      if (confirm('Delete this session?')) this.deleteSession(s.id);
    });

    actions.appendChild(renameBtn);
    actions.appendChild(deleteBtn);

    wrap.appendChild(select);
    wrap.appendChild(actions);
    wrap.appendChild(renameInput);

    select.addEventListener('click', () => this._select(s.id));
    return wrap;
  }

  render() {
    this.container.innerHTML = '';
    const filtered = this._searchTerm
      ? this.items.filter(s => (s.name || '').toLowerCase().includes(this._searchTerm))
      : this.items;

    const grouped = new Map();
    for (const s of filtered) {
      const ts = typeof s.updated_at === 'number' ? s.updated_at : Date.parse(s.updated_at) / 1000;
      const dateKey = new Date(ts * 1000).toLocaleDateString();
      const today = new Date().toLocaleDateString();
      const yesterday = new Date(Date.now() - 86400e3).toLocaleDateString();
      const label = dateKey === today ? 'Today' : dateKey === yesterday ? 'Yesterday' : dateKey;
      const list = grouped.get(label) || [];
      list.push(s);
      grouped.set(label, list);
    }

    for (const [label, list] of grouped) {
      const header = document.createElement('div');
      header.className = 'session-group-label';
      header.textContent = label;
      this.container.appendChild(header);
      for (const s of list) this.container.appendChild(this._renderItem(s));
    }

    if (filtered.length === 0) {
      const empty = document.createElement('div');
      empty.className = 'sessions-empty';
      empty.textContent = this._searchTerm ? 'No matches' : 'No sessions yet';
      this.container.appendChild(empty);
    }
  }
}
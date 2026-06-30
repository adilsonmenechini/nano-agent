// Modern App controller — neighborhood-safe modules, hash-based routing, resilient lifecycle, AI-assisted UX hints

class App {
  constructor() {
    this.bridge = null;
    this.chat = null;
    this.sessions = null;
    this.skills = null;
    this.currentSessionId = null;

    this.chatMessages = document.getElementById('chat-messages');
    this.indicator = document.getElementById('indicator');
    this.chatInput = document.getElementById('chat-input');
    this.sendBtn = document.getElementById('send-btn');
    this.cancelBtn = document.getElementById('cancel-btn');
    this.newSessionBtn = document.getElementById('new-session-btn');
    this.sessionList = document.getElementById('session-list');
    this.skillList = document.getElementById('skill-list');
    this.sidebarLinks = document.querySelectorAll('.sidebar-nav a');
    this.sidebarPanels = document.querySelectorAll('.sidebar-panel');
    this.sidebarNav = document.getElementById('sidebar-nav');
    this.mainContent = document.querySelector('.main-content');

    this._onRetry = this._handleRetry.bind(this);
    document.addEventListener('agent:retry', this._onRetry);
  }

  init() {
    this.chat = new ChatPanel(this.chatMessages, this.indicator);
    this.sessions = new SessionManager(this.sessionList);
    this.skills = new SkillManager(this.skillList);

    this.sessions.onSessionSelected = (id) => this.loadSession(id);
    this.setupEventListeners();
    this.setupSidebar();
    this.setupShortcuts();
    this.setupResize();

    this.sessions.loadSessions().then(() => this.startNewSession());
    this.skills.loadSkills();
  }

  setupEventListeners() {
    this.sendBtn.addEventListener('click', () => this.sendMessage());
    this.cancelBtn.addEventListener('click', () => this.cancelMessage());
    this.newSessionBtn.addEventListener('click', () => this.startNewSession());

    this.chatInput.addEventListener('keydown', (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
        e.preventDefault();
        this.sendMessage();
        return;
      }
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        this.sendMessage();
      }
    });

    this.chatInput.addEventListener('input', () => {
      this.sendBtn.disabled = !this.chatInput.value.trim();
    });
  }

  setupSidebar() {
    for (const link of this.sidebarLinks) {
      link.addEventListener('click', (e) => {
        e.preventDefault();
        const panel = link.dataset.panel;
        if (!panel) return;
        
        if (panel === 'chat') {
          this.chatInput.focus();
          if (window.innerWidth <= 768) {
            document.getElementById('sidebar').classList.remove('open');
          }
          return;
        }

        this.sidebarLinks.forEach(l => l.classList.remove('active'));
        link.classList.add('active');
        this.sidebarPanels.forEach(p => p.classList.remove('active'));
        const target = document.getElementById(`${panel}-panel`);
        if (target) target.classList.add('active');
      });
    }

    const searchInputs = document.querySelectorAll('.panel-search');
    for (const input of searchInputs) {
      input.addEventListener('input', (e) => {
        const target = e.target.dataset.target;
        if (target === 'sessions') this.sessions.setSearchTerm(e.target.value);
        if (target === 'skills') this.skills.setSearch(e.target.value);
      });
    }
  }

  setupShortcuts() {
    document.addEventListener('keydown', (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'n') {
        e.preventDefault();
        this.startNewSession();
      }
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        this.chatInput.focus();
      }
    });
  }

  setupResize() {
    if (matchMedia('(min-width: 768px)').matches) return;
    this.sidebarLinks.forEach(a => a.addEventListener('click', () => {
      this.sidebarNav.classList.remove('open');
    }));
  }

  async startNewSession() {
    this.disconnectBridge();
    this.chat.clear();
    this.chat.showIndicator('thinking');
    this.chatInput.disabled = true;
    this.sendBtn.disabled = true;

    const sessionId = await this.sessions.createSession();
    if (!sessionId) {
      this.chat.hideIndicator();
      this.chat.showError('Failed to create session');
      return;
    }

    this.currentSessionId = sessionId;
    this.sessions.setActive(sessionId);
    this.connectBridge(sessionId);
    this.chat.hideIndicator();
    this.chatInput.disabled = false;
    this.chatInput.focus();
  }

  async loadSession(sessionId) {
    this.disconnectBridge();
    this.chat.clear();
    this.currentSessionId = sessionId;
    this.sessions.setActive(sessionId);

    try {
      const resp = await fetch(`/api/sessions/${sessionId}`);
      if (!resp.ok) throw new Error('Not found');
      const data = await resp.json();
      this.renderHistory(data.session?.conversation?.messages || []);
    } catch (e) {
      const history = this.getStoredHistory(sessionId);
      this.renderHistory(history);
    }

    this.connectBridge(sessionId);
    this.chatInput.disabled = false;
  }

  getStoredHistory(sessionId) {
    try {
      const raw = sessionStorage.getItem(`chat_${sessionId}`);
      return raw ? JSON.parse(raw) : [];
    } catch {
      return [];
    }
  }

  storeMessage(sessionId, msg) {
    const history = this.getStoredHistory(sessionId);
    history.push(msg);
    try {
      sessionStorage.setItem(`chat_${sessionId}`, JSON.stringify(history));
    } catch {}
  }

  renderHistory(messages) {
    for (const msg of messages) {
      if (msg.role === 'user') {
        this.chat.addUserMessage(msg.content);
      } else if (msg.role === 'assistant') {
        let text = msg.content || '';
        if (Array.isArray(text)) text = text.map(t => t.text || '').join('\n');
        else if (typeof text === 'object') text = JSON.stringify(text);

        if (text) {
          this._renderHistoryAgent(text);
        }
      }
      // tool messages are visual detail; skip for history
    }
  }

  /** Render a completed agent message directly (no streaming pipeline). */
  _renderHistoryAgent(text) {
    const div = document.createElement('div');
    div.className = 'message agent';

    const header = document.createElement('div');
    header.className = 'message-header';
    header.textContent = 'NanoAgent';

    const bubble = document.createElement('div');
    bubble.className = 'message-bubble';
    bubble.innerHTML = MarkdownLite.format(text);

    div.appendChild(header);
    div.appendChild(bubble);
    this.chat.container.appendChild(div);
    this.chat.scrollToBottom();
  }

  connectBridge(sessionId) {
    this.bridge = new Bridge();
    const onStateChange = ({ state }) => {
      console.debug('[app] bridge state:', state);
      if (state === 'connected') this.chatInput.disabled = false;
    };

    this.bridge.on('state_change', onStateChange);
    this.bridge.on('message_chunk', (payload) => {
      console.debug('[app] message_chunk', payload);
      this.chat.showIndicator('thinking');
      if (payload.message_id && payload.message_id !== this.chat.currentMessageId) {
        this.chat.startAgentMessage(payload.message_id);
      }
      this.chat.appendChunk(payload.delta);
    });

    this.bridge.on('message_complete', () => {
      this.chat.completeAgentMessage();
      this.sendBtn.disabled = false;
      this.cancelBtn.classList.add('hidden');
      this.chatInput.disabled = false;
      this.chatInput.focus();
    });

    this.bridge.on('tool_call_start', (payload) => {
      this.chat.showIndicator('executing_tools');
      this.chat.showToolCall(payload.tool_name, payload.arguments);
    });

    this.bridge.on('tool_call_result', (payload) => {
      this.chat.showToolResult(payload.tool_name, payload.result);
    });

    this.bridge.on('agent_state_change', (payload) => {
      this.chat.showIndicator(payload.state);
    });

    this.bridge.on('session_updated', () => {
      if (!this.chat.currentMessageId) this.chat.hideIndicator();
    });

    this.bridge.on('error', (payload) => {
      this.chat.showError(payload.message || 'An error occurred');
      this.chat.hideIndicator();
      this.sendBtn.disabled = false;
      this.cancelBtn.classList.add('hidden');
      this.chatInput.disabled = false;
    });

    this.bridge.on('reconnect_failed', () => {
      this.chat.showError('Connection lost. Please refresh the page.');
    });

    this.bridge.connect(sessionId);
  }

  disconnectBridge() {
    if (this.bridge) {
      this.bridge.disconnect();
      this.bridge = null;
    }
  }

  sendMessage() {
    const text = this.chatInput.value.trim();
    if (!text || !this.bridge || !this.currentSessionId) return;

    this.chat.addUserMessage(text);
    this.storeMessage(this.currentSessionId, { role: 'user', content: text });
    this.bridge.sendMessage(text);

    this.chatInput.value = '';
    this.sendBtn.disabled = true;
    this.cancelBtn.classList.remove('hidden');
    this.chatInput.disabled = true;
    this.chat.showIndicator('thinking');
  }

  cancelMessage() {
    if (this.bridge) this.bridge.cancel();
    this.cancelBtn.classList.add('hidden');
    this.sendBtn.disabled = false;
    this.chatInput.disabled = false;
    this.chat.hideIndicator();
  }

  _handleRetry({ messageId }) {
    if (messageId) {
      this.chat.showError('Retry is not supported yet for individual messages.');
    }
  }

  _msgId() {
    const ts = performance.now().toString(36).replace(/\./g, '');
    const rand = Math.random().toString(36).slice(2, 7);
    return `msg_${ts}_${rand}`;
  }

  destroy() {
    this.disconnectBridge();
    document.removeEventListener('agent:retry', this._onRetry);
  }
}

window.app = null;
document.addEventListener('DOMContentLoaded', () => {
  window.app = new App();
  window.app.init();
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible' && window.app?.bridge?.state === 'disconnected') {
      window.app.connectBridge(window.app.currentSessionId);
    }
  });
});
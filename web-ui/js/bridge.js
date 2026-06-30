// Modern WebSocket bridge — typed events, AbortController cleanup, jittered backoff, disposal-safe

const EventBus = {
  create() {
    const listeners = new Map();
    return {
      on(event, fn) {
        if (!listeners.has(event)) listeners.set(event, new Set());
        listeners.get(event).add(fn);
        return () => listeners.get(event)?.delete(fn);
      },
      off(event, fn) {
        listeners.get(event)?.delete(fn);
      },
      emit(event, payload) {
        const set = listeners.get(event);
        if (!set) return;
        for (const fn of set) {
          try { fn(payload); } catch (err) {
            console.error(`Event error [${event}]`, err);
          }
        }
      },
      removeAll() { listeners.clear(); }
    };
  }
};

class Bridge {
  static RECONNECT_BASE_DELAY = 1000;
  static RECONNECT_MAX_ATTEMPTS = 8;
  static PENDING_BUFFER_LIMIT = 50;

  constructor() {
    this.ws = null;
    this.sessionId = null;
    this.listeners = EventBus.create();
    this.reconnectAttempts = 0;
    this._reconnectTimeout = null;
    this.pendingMessages = [];
    this.connectionState = 'disconnected';
    this._abortController = null;
    this._disposed = false;
  }

  get state() {
    return this.connectionState;
  }

  connect(sessionId) {
    if (this._disposed) return Promise.resolve();
    this.disconnect(false);

    this.sessionId = sessionId;
    this.connectionState = 'connecting';
    this.reconnectAttempts = 0;
    this.listeners.emit('state_change', { state: 'connecting' });
    this._abortController = new AbortController();

    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
    const url = `${protocol}//${location.host}/ws/chat?session_id=${sessionId}`;

    try {
      this.ws = new WebSocket(url);
    } catch (err) {
      this.connectionState = 'failed';
      this._scheduleReconnect();
      return Promise.resolve();
    }

    this.ws.addEventListener('open', () => {
      this._flushPending();
      this.connectionState = 'connected';
      this.listeners.emit('state_change', { state: 'connected' });
      this.listeners.emit('connected', { sessionId: this.sessionId });
    }, { signal: this._abortController.signal });

    this.ws.addEventListener('message', (event) => {
      try {
        const msg = JSON.parse(event.data);
        console.debug('[bridge] ws msg:', msg.type, msg.payload);
        this.emit(msg.type, msg.payload);
      } catch (e) {
        console.error('Bridge: failed to parse message', e);
      }
    }, { signal: this._abortController.signal });

    this.ws.addEventListener('close', () => {
      if (this._disposed) return;
      this.connectionState = 'disconnected';
      this.listeners.emit('disconnected', {});
      this._scheduleReconnect();
    }, { signal: this._abortController.signal });

    this.ws.addEventListener('error', (err) => {
      console.error('Bridge: socket error', err);
    }, { signal: this._abortController.signal });

    return Promise.resolve();
  }

  _scheduleReconnect() {
    if (this.reconnectAttempts >= Bridge.RECONNECT_MAX_ATTEMPTS) {
      this.listeners.emit('reconnect_failed', {
        attempts: this.reconnectAttempts
      });
      return;
    }
    clearTimeout(this._reconnectTimeout);
    const base = Bridge.RECONNECT_BASE_DELAY;
    const jitter = Math.random() * 500;
    const delay = Math.min(base * 2 ** this.reconnectAttempts + jitter, 30000);
    this.reconnectAttempts++;
    this._reconnectTimeout = setTimeout(() => {
      if (this.sessionId && !this._disposed) this.connect(this.sessionId);
    }, delay);
  }

  _flushPending() {
    while (
      this.pendingMessages.length > 0 &&
      this.ws?.readyState === WebSocket.OPEN
    ) {
      const msg = this.pendingMessages.shift();
      this.ws.send(JSON.stringify(msg));
    }
  }

  send(type, payload) {
    if (this._disposed) return;
    const msg = { type, payload };
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(msg));
    } else {
      if (this.pendingMessages.length < Bridge.PENDING_BUFFER_LIMIT) {
        this.pendingMessages.push(msg);
      }
    }
  }

  sendMessage(content) {
    this.send('user_message', { content, session_id: this.sessionId });
  }

  cancel() {
    this.pendingMessages = [];
    this.send('cancel', {});
  }

  on(event, callback) {
    return this.listeners.on(event, callback);
  }

  off(event, callback) {
    this.listeners.off(event, callback);
  }

  emit(event, payload) {
    this.listeners.emit(event, payload);
  }

  disconnect(shouldClear = true) {
    if (shouldClear) {
      this._disposed = true;
      this.pendingMessages = [];
    }
    clearTimeout(this._reconnectTimeout);
    this._abortController?.abort();
    this.connectionState = 'disconnected';
    if (this.ws) {
      try { this.ws.close(); } catch {}
      this.ws = null;
    }
    this._abortController = null;
  }
}
// Modern ChatPanel — streaming UX improvements, copy/retry actions, accessible tool blocks, throttled renders

const MarkdownLite = {
  format(text) {
    if (typeof text !== 'string') return '';
    let html = text
      .replace(/&/g, '&')
      .replace(/</g, '<')
      .replace(/>/g, '>');

    html = html
      .replace(/`{1,3}([\s\S]*?)`{1,3}/g, (_, code) => {
        const escaped = code.replace(/[<>]/g, '');
        return `<code>${escaped}</code>`;
      })
      .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>')
      .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
      .replace(/\*([^*]+)\*/g, '<em>$1</em>')
      .replace(/^#{1,6}\s+(.+)$/gm, (_, line) => `<h4>${line}</h4>`)
      .replace(/^[-*]\s+(.+)$/gm, '<li>$1</li>');

    html = html
      .replace(/((?:<li>.*<\/li>\n?)+)/g, '<ul>$1</ul>')
      .replace(/((?:<h4>.*<\/h4>\n?)+)/g, '<div>$1</div>');

    return html;
  }
};

const StreamingRenderer = {
  _rafId: null,
  schedule(callback) {
    cancelAnimationFrame(this._rafId);
    this._rafId = requestAnimationFrame(() => {
      callback();
      this._rafId = null;
    });
  },
  cancel() {
    cancelAnimationFrame(this._rafId);
    this._rafId = null;
  }
};

class ChatPanel {
  constructor(container, indicator) {
    this.container = container;
    this.indicator = indicator;
    this.indicatorText = indicator.querySelector('#indicator-text');

    this.currentMessageId = null;
    this.currentBubble = null;
    this.accumulated = '';
    this._queuedAppend = '';
    this._streaming = false;

    this._agentActions = new Map();
    this._toolCallIndexes = new Map();
  }

  _handleAgentClick(messageId, bubbleEl) {
    const actions = document.createElement('div');
    actions.className = 'message-actions';
    const copy = document.createElement('button');
    copy.className = 'icon-btn';
    copy.type = 'button';
    copy.title = 'Copy';
    copy.setAttribute('aria-label', 'Copy message');
    copy.textContent = '📋';

    const retry = document.createElement('button');
    retry.className = 'icon-btn';
    retry.type = 'button';
    retry.title = 'Retry';
    retry.setAttribute('aria-label', 'Retry message');
    retry.textContent = '↻';

    copy.addEventListener('click', async () => {
      try {
        await navigator.clipboard.writeText(bubbleEl.textContent || '');
        copy.textContent = '✓';
        setTimeout(() => copy.textContent = '📋', 1200);
      } catch {}
    });

    retry.addEventListener('click', () => {
      document.dispatchEvent(new CustomEvent('agent:retry', { detail: { messageId } }));
    });

    actions.appendChild(copy);
    actions.appendChild(retry);
    bubbleEl.appendChild(actions);
  }

  showIndicator(state) {
    this.indicator.classList.remove('hidden');
    const dot = this.indicator.querySelector('.indicator-dot');
    const text = String(state || '').toLowerCase();
    dot.style.background = 'var(--accent)';
    if (text.includes('tool')) {
      this.indicatorText.textContent = 'Running tools…';
      dot.style.background = 'var(--warning)';
    } else if (text.includes('error') || text.includes('fail')) {
      this.indicatorText.textContent = 'Error';
      dot.style.background = 'var(--error)';
    } else if (text.includes('think') || text.includes('process')) {
      this.indicatorText.textContent = 'Thinking…';
      dot.style.background = 'var(--accent)';
    } else if (text === 'idle' || text === 'done' || text === 'complete') {
      this.hideIndicator();
      return;
    } else {
      this.indicatorText.textContent = 'Processing…';
      dot.style.background = 'var(--accent)';
    }
  }

  _markdownRender(text) {
    return MarkdownLite.format(text);
  }

  addUserMessage(content) {
    const div = document.createElement('div');
    div.className = 'message user';

    const header = document.createElement('div');
    header.className = 'message-header';
    header.textContent = 'You';

    const bubble = document.createElement('div');
    bubble.className = 'message-bubble';
    bubble.textContent = content;

    const ts = document.createElement('div');
    ts.className = 'message-timestamp';
    const now = new Date();
    ts.textContent = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    ts.setAttribute('datetime', now.toISOString());

    div.appendChild(header);
    div.appendChild(bubble);
    div.appendChild(ts);
    this.container.appendChild(div);
    this.scrollToBottom();
  }

  startAgentMessage(messageId) {
    const prevId = this.currentMessageId;
    if (prevId && prevId !== messageId) this.completeAgentMessage();

    this.currentMessageId = messageId;
    this._streaming = true;
    this.accumulated = '';
    this._queuedAppend = '';

    const div = document.createElement('div');
    div.className = 'message agent streaming';
    div.dataset.messageId = messageId;

    const header = document.createElement('div');
    header.className = 'message-header';
    header.textContent = 'NanoAgent';

    const bubble = document.createElement('div');
    bubble.className = 'message-bubble';
    bubble.id = `msg-${messageId}`;
    bubble.setAttribute('role', 'region');
    bubble.setAttribute('aria-live', 'polite');
    bubble.setAttribute('aria-atomic', 'false');

    const streamText = document.createElement('span');
    streamText.className = 'stream-text';

    const streamCursor = document.createElement('span');
    streamCursor.className = 'stream-cursor';
    streamCursor.setAttribute('aria-hidden', 'true');
    streamCursor.textContent = '▊';

    bubble.appendChild(streamText);
    bubble.appendChild(streamCursor);
    header.appendChild(document.createElement('span'));
    div.appendChild(header);
    div.appendChild(bubble);
    this.container.appendChild(div);
    this.currentBubble = bubble;
    this.scrollToBottom();
  }

  appendChunk(delta) {
    if (!this.currentBubble || !this._streaming) this.startAgentMessage(this._msgId());
    this._queuedAppend += delta || '';
    StreamingRenderer.schedule(() => {
      if (!this._streaming) return;
      this.accumulated += this._queuedAppend;
      this._queuedAppend = '';
      const textSpan = this.currentBubble.querySelector('.stream-text');
      if (textSpan) {
        textSpan.textContent = this.accumulated;
      } else {
        this.currentBubble.textContent = this.accumulated;
      }
      this.scrollToBottom();
    });
  }

  completeAgentMessage() {
    StreamingRenderer.cancel();
    if (this._queuedAppend) {
      this.accumulated += this._queuedAppend;
      this._queuedAppend = '';
    }
    if (this.currentBubble) {
      const rendered = this._markdownRender(this.accumulated);
      const actions = document.createElement('div');
      actions.className = 'message-actions';
      const copy = document.createElement('button');
      copy.className = 'icon-btn';
      copy.type = 'button';
      copy.title = 'Copy';
      copy.setAttribute('aria-label', 'Copy message');
      copy.textContent = '📋';
      const retry = document.createElement('button');
      retry.className = 'icon-btn';
      retry.type = 'button';
      retry.title = 'Retry';
      retry.setAttribute('aria-label', 'Retry message');
      retry.textContent = '↻';
      copy.addEventListener('click', async () => {
        try {
          await navigator.clipboard.writeText(this.accumulated || '');
          copy.textContent = '✓';
          setTimeout(() => copy.textContent = '📋', 1200);
        } catch {}
      });
      retry.addEventListener('click', () => {
        document.dispatchEvent(new CustomEvent('agent:retry', {
          detail: { messageId: this.currentMessageId }
        }));
      });
      actions.appendChild(copy);
      actions.appendChild(retry);
      this.currentBubble.innerHTML = rendered;
      this.currentBubble.appendChild(actions);

      const msgDiv = this.currentBubble.closest('.message');
      if (msgDiv) {
        msgDiv.classList.remove('streaming');
        const ts = document.createElement('div');
        ts.className = 'message-timestamp';
        const now = new Date();
        ts.textContent = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        ts.setAttribute('datetime', now.toISOString());
        msgDiv.appendChild(ts);
      }
    }
    this.currentMessageId = null;
    this.currentBubble = null;
    this._streaming = false;
    this.accumulated = '';
    this._queuedAppend = '';
    this.hideIndicator();
  }

  showToolCall(toolName, args) {
    if (!this.currentBubble) return;
    const container = this.currentBubble.closest('.message');
    const toolDiv = document.createElement('details');
    toolDiv.className = 'tool-call';
    toolDiv.open = false;

    const summary = document.createElement('summary');
    summary.className = 'tool-call-header';
    summary.textContent = `🔧 ${toolName}`;

    const argsPre = document.createElement('pre');
    argsPre.className = 'tool-call-args';
    argsPre.textContent = JSON.stringify(args, null, 2);

    toolDiv.appendChild(summary);
    toolDiv.appendChild(argsPre);
    container.insertAdjacentElement('afterend', toolDiv);
    this.scrollToBottom();
  }

  showToolResult(toolName, result) {
    const toolCalls = Array.from(this.container.querySelectorAll('.tool-call'));
    const last = toolCalls.at(-1);
    if (last) {
      const header = last.querySelector('.tool-call-header');
      const matches = header?.textContent?.includes(toolName);
      if (matches) {
        const out = document.createElement('div');
        out.className = 'tool-call-result';
        const pre = document.createElement('pre');
        pre.textContent = typeof result === 'string' ? result : JSON.stringify(result, null, 2);
        out.appendChild(pre);
        last.appendChild(out);
        this.scrollToBottom();
      }
    }
  }

  showError(message) {
    const div = document.createElement('div');
    div.className = 'message agent error';

    const header = document.createElement('div');
    header.className = 'message-header';
    header.textContent = 'System';

    const bubble = document.createElement('div');
    bubble.className = 'message-bubble';
    bubble.setAttribute('role', 'alert');
    bubble.textContent = message;

    div.appendChild(header);
    div.appendChild(bubble);
    this.container.appendChild(div);
    this.scrollToBottom();
  }

  hideIndicator() {
    this.indicator.classList.add('hidden');
  }

  clear() {
    StreamingRenderer.cancel();
    this.container.innerHTML = '';
    this.currentMessageId = null;
    this.currentBubble = null;
    this._streaming = false;
    this.accumulated = '';
    this._queuedAppend = '';
    this._toolCallIndexes.clear();
    this.hideIndicator();
  }

  scrollToBottom() {
    const peak = this.container.scrollHeight - this.container.clientHeight;
    const atBottom = this.container.scrollTop + this.container.clientHeight >= peak - 64;
    if (atBottom || this._streaming) {
      this.container.scrollTop = this.container.scrollHeight;
    }
  }

  /** Add a formatted command result message in the chat */
  addCommandMessage(command, htmlContent) {
    const div = document.createElement('div');
    div.className = 'message command';

    const header = document.createElement('div');
    header.className = 'message-header';
    header.textContent = `Command: ${command}`;

    const bubble = document.createElement('div');
    bubble.className = 'message-bubble command-bubble';
    bubble.innerHTML = htmlContent;

    const ts = document.createElement('div');
    ts.className = 'message-timestamp';
    const now = new Date();
    ts.textContent = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    ts.setAttribute('datetime', now.toISOString());

    div.appendChild(header);
    div.appendChild(bubble);
    div.appendChild(ts);
    this.container.appendChild(div);
    this.scrollToBottom();
  }

  /** Add a simple system notification message */
  addSystemMessage(text) {
    const div = document.createElement('div');
    div.className = 'message system';

    const bubble = document.createElement('div');
    bubble.className = 'message-bubble system-bubble';
    bubble.textContent = text;

    div.appendChild(bubble);
    this.container.appendChild(div);
    this.scrollToBottom();
  }

  /** Get all parsed messages from the DOM (for history) */
  _getAllMessages() {
    const msgDivs = this.container.querySelectorAll('.message');
    const messages = [];
    for (const el of msgDivs) {
      if (el.classList.contains('user')) {
        const bubble = el.querySelector('.message-bubble');
        const content = bubble ? bubble.textContent || '' : '';
        if (content) messages.push({ role: 'user', content });
      } else if (el.classList.contains('agent')) {
        const bubble = el.querySelector('.message-bubble');
        const content = bubble ? bubble.textContent || '' : '';
        if (content) messages.push({ role: 'assistant', content });
      }
    }
    return messages;
  }

  _msgId() {
    const ts = performance.now().toString(36).replace(/\./g, '');
    const rand = Math.random().toString(36).slice(2, 7);
    return `msg_${ts}_${rand}`;
  }
}
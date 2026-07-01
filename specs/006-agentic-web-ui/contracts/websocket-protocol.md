# WebSocket Protocol: Real-time Chat

**Version**: 1.0
**Date**: 2026-06-29
**Endpoint**: `ws://localhost:PORT/ws/chat?session_id={session_id}`

---

## Overview

The WebSocket connection handles real-time bidirectional communication for the chat feature. The client connects to a specific session, sends user messages, and receives streaming agent responses.

**Protocol**: JSON messages over a single persistent WebSocket connection.

---

## Client → Server Messages

### `user_message`

Send a user message to the agent.

```json
{
  "type": "user_message",
  "payload": {
    "content": "What is the weather in Tokyo?",
    "session_id": "uuid-of-session"
  }
}
```

---

### `cancel`

Cancel the currently running agent response.

```json
{
  "type": "cancel"
}
```

---

## Server → Client Messages

### `message_chunk`

A partial chunk of the agent's streaming response.

```json
{
  "type": "message_chunk",
  "payload": {
    "message_id": "uuid-of-message",
    "delta": "What is the wea",
    "session_id": "uuid-of-session"
  }
}
```

The client accumulates `delta` values until a `message_complete` signal is received.

---

### `message_complete`

Indicates the agent has finished generating a message.

```json
{
  "type": "message_complete",
  "payload": {
    "message_id": "uuid-of-message",
    "session_id": "uuid-of-session",
    "full_content": "What is the weather in Tokyo? Let me check...",
    "timestamp": "2026-06-29T10:00:05Z"
  }
}
```

---

### `tool_call_start`

Indicates the agent is about to execute a tool.

```json
{
  "type": "tool_call_start",
  "payload": {
    "tool_name": "web_search",
    "arguments": {"query": "Tokyo weather 2026"},
    "tool_call_id": "tc-uuid",
    "session_id": "uuid-of-session"
  }
}
```

---

### `tool_call_result`

The result of a completed tool execution.

```json
{
  "type": "tool_call_result",
  "payload": {
    "tool_name": "web_search",
    "tool_call_id": "tc-uuid",
    "result": {"snippet": "Tokyo weather: 22°C, partly cloudy..."},
    "status": "success",
    "session_id": "uuid-of-session"
  }
}
```

---

### `agent_state_change`

The agent's state has changed.

```json
{
  "type": "agent_state_change",
  "payload": {
    "state": "executing_tools",
    "previous_state": "thinking",
    "session_id": "uuid-of-session"
  }
}
```

---

### `error`

An error occurred during processing.

```json
{
  "type": "error",
  "payload": {
    "code": "agent_error",
    "message": "The agent encountered an error processing your request.",
    "session_id": "uuid-of-session"
  }
}
```

**Error Codes**:

| Code | Meaning |
|------|---------|
| `agent_error` | Agent execution error |
| `invalid_session` | Session ID not found |
| `rate_limit` | Too many requests |
| `internal_error` | Unexpected server error |
| `connection_error` | Backend agent unavailable |

---

### `session_updated`

Session metadata has changed (e.g., new message added to history).

```json
{
  "type": "session_updated",
  "payload": {
    "session_id": "uuid-of-session",
    "message_count": 13,
    "updated_at": "2026-06-29T10:00:06Z"
  }
}
```

---

## Connection Lifecycle

1. Client opens WebSocket to `/ws/chat?session_id={id}`
2. Server validates session exists, sends `session_updated` as confirmation
3. Client sends `user_message` to start chat interaction
4. Server streams response chunks and state changes
5. Server sends `message_complete` when done
6. Client can send another `user_message`
7. Either party may close the connection

**Error Handling**:
- If the session_id is invalid, server closes with close code 4000 and reason "Invalid session"
- If the backend agent fails mid-response, server sends `error` then `message_complete` with error content
- If the client disconnects mid-response, the server cancels the agent task

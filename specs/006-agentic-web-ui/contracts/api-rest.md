# API Contract: REST Endpoints

**Version**: 1.0
**Date**: 2026-06-29
**Base URL**: `http://localhost:PORT` (port configurable, default 8080)
**Content-Type**: `application/json`

---

## Sessions

### `GET /api/sessions`

List all sessions.

**Response** `200`:
```json
{
  "sessions": [
    {
      "id": "uuid-string",
      "name": "Chat about Python",
      "message_count": 12,
      "created_at": "2026-06-29T10:00:00Z",
      "updated_at": "2026-06-29T10:30:00Z",
      "is_active": false
    }
  ]
}
```

---

### `GET /api/sessions/{id}`

Get a single session with full conversation history.

**Response** `200`:
```json
{
  "session": {
    "id": "uuid-string",
    "name": "Chat about Python",
    "conversation": {
      "messages": [
        {
          "id": "msg-uuid",
          "role": "user",
          "content": "Hello!",
          "timestamp": "2026-06-29T10:00:00Z",
          "tool_calls": null,
          "agent_state": null,
          "metadata": {}
        },
        {
          "id": "msg-uuid",
          "role": "agent",
          "content": "Hi! How can I help you?",
          "timestamp": "2026-06-29T10:00:02Z",
          "tool_calls": [
            {
              "tool_name": "calculator",
              "arguments": {"expr": "2+2"},
              "result": {"value": 4},
              "status": "success",
              "started_at": "2026-06-29T10:00:01Z",
              "completed_at": "2026-06-29T10:00:01Z"
            }
          ],
          "agent_state": "executing_tools",
          "metadata": {}
        }
      ]
    },
    "created_at": "2026-06-29T10:00:00Z",
    "updated_at": "2026-06-29T10:30:00Z",
    "is_active": false
  }
}
```

**Response** `404`:
```json
{
  "error": "Session not found",
  "session_id": "uuid-string"
}
```

---

### `POST /api/sessions`

Create a new session.

**Request** (optional body):
```json
{
  "name": "Optional session name"
}
```

**Response** `201`:
```json
{
  "session": {
    "id": "uuid-string",
    "name": "Optional session name",
    "conversation": {
      "messages": []
    },
    "created_at": "2026-06-29T11:00:00Z",
    "updated_at": "2026-06-29T11:00:00Z",
    "is_active": true
  }
}
```

---

### `DELETE /api/sessions/{id}`

Delete a session.

**Response** `200`:
```json
{
  "status": "deleted",
  "session_id": "uuid-string"
}
```

---

## Skills

### `GET /api/skills`

List all available skills.

**Response** `200`:
```json
{
  "skills": [
    {
      "name": "web_search",
      "description": "Search the web for information",
      "enabled": true,
      "details": "Uses DuckDuckGo search API to find recent information.",
      "updated_at": "2026-06-29T10:00:00Z"
    }
  ]
}
```

---

### `PATCH /api/skills/{name}`

Toggle a skill's enabled status.

**Request**:
```json
{
  "enabled": false
}
```

**Response** `200`:
```json
{
  "skill": {
    "name": "web_search",
    "description": "Search the web for information",
    "enabled": false,
    "updated_at": "2026-06-29T11:05:00Z"
  }
}
```

**Response** `404`:
```json
{
  "error": "Skill not found",
  "skill_name": "unknown_skill"
}
```

---

## Health

### `GET /api/health`

Server health check.

**Response** `200`:
```json
{
  "status": "ok",
  "version": "0.1.0",
  "uptime_seconds": 3600
}
```

---

## Error Format (all endpoints)

```json
{
  "error": "Human-readable error message",
  "detail": "Optional additional context"
}
```

**HTTP Status Codes**:
| Code | Meaning |
|------|---------|
| 200 | Success |
| 201 | Created |
| 400 | Bad request |
| 404 | Not found |
| 500 | Internal server error |

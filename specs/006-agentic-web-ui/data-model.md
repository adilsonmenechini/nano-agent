# Data Model: Agentic Web UI

**Phase**: 1 — Design & Contracts
**Date**: 2026-06-29
**Source**: [spec.md](file:///Users/adilsonmenechini/SRE/AI/nano-agent/specs/006-agentic-web-ui/spec.md)

---

## 1. Conversation

Represents a single chat conversation within a session.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | `string` (UUID) | Yes | Unique identifier |
| `session_id` | `string` (UUID) | Yes | Parent session |
| `messages` | `Message[]` | Yes | Ordered list of messages |
| `created_at` | `datetime` | Yes | Creation timestamp |
| `updated_at` | `datetime` | Yes | Last activity timestamp |

**Validation Rules**:
- `messages` must be ordered by `created_at` ascending
- A conversation must have at least one message after first user interaction

---

## 2. Message

A single exchange unit in a conversation.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | `string` (UUID) | Yes | Unique identifier |
| `role` | `enum(user, agent)` | Yes | Who sent the message |
| `content` | `string` | Yes | Message text content |
| `timestamp` | `datetime` | Yes | When the message was sent |
| `tool_calls` | `ToolCall[]` | No | Tool calls made by the agent |
| `agent_state` | `enum(idle, thinking, executing_tools, awaiting_input, error)` | No | Agent state when message was produced |
| `metadata` | `object` | No | Additional metadata (token count, model, etc.) |

**Validation Rules**:
- `content` max length: 100,000 characters (display-side truncation handled by UI)
- `role` must be one of the two enumerated values

---

## 3. Session

Represents a discrete conversational context.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | `string` (UUID) | Yes | Unique identifier |
| `name` | `string` | Yes | Human-readable label (auto-generated or user-set) |
| `conversation` | `Conversation` | Yes | The conversation data |
| `created_at` | `datetime` | Yes | Creation timestamp |
| `updated_at` | `datetime` | Yes | Last activity |
| `is_active` | `boolean` | Yes | Whether this is the currently active session |

**State Transitions**:
```
created → active (user opens session)
active → archived (user switches to another session)
archived → active (user reopens session)
any → deleted (user deletes session)
```

---

## 4. Skill

A modular capability registered with the agent.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | `string` | Yes | Unique skill identifier |
| `description` | `string` | Yes | Human-readable description |
| `enabled` | `boolean` | Yes | Whether the skill is currently active |
| `details` | `string` | No | Expanded description or documentation |
| `updated_at` | `datetime` | Yes | Last modified timestamp |

**Validation Rules**:
- `name` must be unique across all skills
- `description` max length: 500 characters

---

## 5. Agent State

The current operational state of the agent, exposed to the UI.

| Value | Description | Display |
|-------|-------------|---------|
| `idle` | Ready for input | "Ready" indicator |
| `thinking` | LLM is generating a response | Spinner + "Thinking..." |
| `executing_tools` | Agent is running one or more tools | "Running tool: {tool_name}" |
| `awaiting_input` | Agent needs user input to continue | Input prompt |
| `error` | An error occurred | Error message with details |

**State Machine** (from existing [agent.py](file:///Users/adilsonmenechini/SRE/AI/nano-agent/src/nanoagent/agent/agent.py#L22-L36)):
```
IDLE → THINKING
THINKING → EXECUTING_TOOLS | AWAITING_INPUT | IDLE | ERROR
EXECUTING_TOOLS → THINKING | AWAITING_INPUT | ERROR
AWAITING_INPUT → IDLE
ERROR → IDLE | THINKING
```

---

## 6. Tool Call

Represents a tool invocation by the agent during a response.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `tool_name` | `string` | Yes | Name of the tool called |
| `arguments` | `object` | Yes | Arguments passed to the tool |
| `result` | `object` | No | Result returned by the tool |
| `status` | `enum(running, success, error)` | Yes | Execution status |
| `started_at` | `datetime` | Yes | When execution started |
| `completed_at` | `datetime` | No | When execution completed |

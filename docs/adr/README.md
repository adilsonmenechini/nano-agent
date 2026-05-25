# Architecture Decision Records (ADRs)

This directory contains [Architecture Decision Records](https://adr.github.io/) for the NanoAgent project.

## What is an ADR?

An Architecture Decision Record is a document that captures an important architectural decision made along with its context and consequences.

## List of ADRs

| Number | Title | Status |
|--------|-------|--------|
| [0001](0001-modular-agent-architecture.md) | Modular Agent Architecture with Pluggable Components | Accepted |
| [0002](0002-sqlite-memory-with-fts5.md) | SQLite Memory Store with FTS5 Full-Text Search | Accepted |

## Adding New ADRs

When making an architectural decision:
1. Create a new file named `NNNN-descriptive-title.md` where NNNN is the next sequential number
2. Follow the template used in existing ADRs
3. Update this README with the new entry

## Template

Each ADR should include:
- **Status**: Proposed, Accepted, Superseded, or Deprecated
- **Context**: The situation motivating the decision
- **Decision**: What we decided to do
- **Consequences**: Positive and negative outcomes of the decision
- **Alternatives Considered**: Other options we evaluated
- **Related Decisions**: How this connects to other ADRs
- **References**: Links to resources that informed the decision
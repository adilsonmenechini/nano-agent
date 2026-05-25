# 0002: SQLite Memory Store with FTS5 Full-Text Search

## Status
Accepted

## Context
The NanoAgent framework requires a persistent memory system to store agent experiences, user interactions, and learned patterns. The memory system needs to support efficient storage, retrieval, and searching of textual content while being lightweight and dependency-free where possible.

## Decision
We will use SQLite as the memory backend with FTS5 (Full-Text Search) extension for efficient text search capabilities. The memory store will:

1. Use SQLite for ACID transactions and persistent storage
2. Implement FTS5 virtual table for full-text search on memory content
3. Store memories with metadata including project, target, category, key, and timestamps
4. Support failure tracking with failure_reason, tool_state, and corrected_to fields
5. Provide a clean abstraction layer via SQLiteMemoryStore class

This approach is inspired by the pi-hermes-memory project but adapted for the NanoAgent framework's specific needs.

## Consequences

### Positive
- **Zero External Dependencies**: SQLite is part of Python's standard library
- **ACID Compliance**: Reliable transaction handling for memory operations
- **Efficient Search**: FTS5 provides fast full-text search capabilities
- **Portability**: Single file database that's easy to backup and transfer
- **Maturity**: Well-established technology with good performance characteristics
- **Flexibility**: Easy to query and extend with additional metadata fields

### Negative
- **Limited Concurrency**: SQLite has restrictions on concurrent writers
- **File-Based**: Not ideal for distributed systems requiring network-accessible storage
- **Size Limitations**: Practical limits on database size compared to server-based solutions

## Alternatives Considered
1. **PostgreSQL/MySQL**: More robust concurrency and scaling
   - Rejected because it adds external dependencies and complexity unsuitable for a lightweight framework

2. **Redis**: In-memory with persistence options
   - Rejected because it requires external service and doesn't provide the same querying capabilities

3. **JSON Files**: Simple file-based storage
   - Rejected because it lacks ACID properties and efficient search capabilities

4. **MongoDB**: Document-based NoSQL storage
   - Rejected because it adds external dependency and over-engineering for the use case

## Related Decisions
- This decision works in conjunction with the modular agent architecture (ADR 0001)
- Influences how we implement skill storage (which also uses SQLite)
- Affects background memory processing and consolidation strategies

## References
- [SQLite FTS5 Documentation](https://www.sqlite.org/fts5.html)
- [pi-hermes-memory project](https://github.com/chandra447/pi-hermes-memory)
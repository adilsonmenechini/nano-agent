# Entry delimiter — same as Hermes
ENTRY_DELIMITER = "\n\u00a7\n"

# File names
MEMORY_FILE = "MEMORY.md"
USER_FILE = "USER.md"
FAILURES_FILE = "failures.md"

# Character limits (not tokens)
DEFAULT_MEMORY_CHAR_LIMIT = 5000
DEFAULT_USER_CHAR_LIMIT = 5000
DEFAULT_FAILURE_CHAR_LIMIT = 10000

# Failure memory
DEFAULT_FAILURE_INJECTION_MAX_AGE_DAYS = 7
DEFAULT_FAILURE_INJECTION_MAX_ENTRIES = 5

# Allowed failure categories
# Ported from pi-hermes-memory
FAILURE_CATEGORIES = frozenset({
    "failure",
    "correction",
    "insight",
    "preference",
    "convention",
    "tool-quirk",
})

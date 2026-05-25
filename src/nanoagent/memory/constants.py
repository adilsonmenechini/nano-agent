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
FAILURE_CATEGORIES = frozenset(
    {
        "failure",
        "correction",
        "insight",
        "preference",
        "convention",
        "tool-quirk",
    }
)

# Memory loop constants
DEFAULT_NUDGE_INTERVAL = 10
DEFAULT_FLUSH_MIN_TURNS = 6
DEFAULT_NUDGE_TOOL_CALLS = 15

# XML prompts for memory policy and operations
MEMORY_POLICY_PROMPT = """<memory-policy>
You are equipped with a memory system to persist key facts across conversations.
Your memory targets are:
1. 'user': Information about the user's preferences, style, rules, constraints, background, and environment.
2. 'memory': Key project facts, design decisions, architectural agreements, and notable domain facts.
3. 'failure': Past mistakes, bugs, tool quirks, and how they were corrected.

Guidelines:
- DO NOT store transient information, chat history details, or generic pleasantries.
- DO store lasting preferences ("prefers HSL colors", "uses mac OS", "never use Tailwind").
- DO store project decisions ("decided to use SQLite with WAL for concurrency").
- DO store failures/corrections ("run command failed because python wasn't python3, resolved by calling python3").
</memory-policy>"""

CONSOLIDATION_PROMPT = """You are a memory consolidation expert. 
Your task is to merge, deduplicate, and clean up the list of memory entries below.
Consolidate redundant items, resolve any direct contradictions (favoring more recent entries), and format the consolidated result as a list of distinct, high-quality entries separated by the § symbol.
Keep all crucial details, key constraints, and user preferences intact. Do not lose specific technical terms, commands, or paths.

Format the output exactly as a sequence of consolidated entries separated by:

§

Do not include any conversational preamble, intro, or markdown fences in your response."""

COMBINED_REVIEW_PROMPT = """You are an expert review agent. Analyze the recent conversation turns and tool calls below.
Identify any notable new facts, user preferences, project decisions, or tool execution failures that occurred.
Extract them and format them as new memory entries.

Categorize each entry as one of:
- 'user': A lasting preference, constraint, or fact about the user.
- 'memory': A lasting fact, design decision, or project context.
- 'failure': A tool quirk, error, or mistake with its correction.

Return a structured list of new entries to save. Format your response exactly as:

CATEGORY: <target>
CONTENT: <factual description of the memory/failure/preference>

Separated by double newlines. Do not add any extra preamble, intro, or markdown fences."""

FLUSH_PROMPT = """Analyze the current active conversation session.
Before we lose the context of this session, identify and extract the most important facts, decisions, and lessons learned.
For any tool execution failures or developer corrections, document them with their specific reasons and corrections.

Format your response exactly as:

CATEGORY: <target>
CONTENT: <factual description>"""

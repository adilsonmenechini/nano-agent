import re

# Ported from pi-hermes-memory correction-detector.ts
# Two-pass filter: strong patterns always trigger, weak need directive words

CORRECTION_STRONG_PATTERNS: list[re.Pattern] = [
    re.compile(
        r"\b(no|wrong|incorrect|that'?s\s+not\s+(right|correct|what\s+I\s+meant))\b",
        re.I,
    ),
    re.compile(
        r"\b(don'?t|do\s+not|stop|never)\s+(do|use|run|call|assume|make)\b", re.I
    ),
    re.compile(r"\b(actually|correction|instead|rather)\s*,", re.I),
    re.compile(r"\bI\s+(said|told\s+you|meant)\s", re.I),
    re.compile(r"\b(not|no)\s+\w+\s*,\s*(use|try|run|do|the)\b", re.I),
]

CORRECTION_WEAK_PATTERNS: list[re.Pattern] = [
    re.compile(r"\b(no|nope|nah)\b", re.I),
    re.compile(r"\b(wait|hold\s+on|hang\s+on)\b", re.I),
    re.compile(r"\b(actually|um\s+actually)\b", re.I),
    re.compile(r"\b(I\s+think|maybe|perhaps)\s+(you|it'?s)\b", re.I),
]

CORRECTION_NEGATIVE_PATTERNS: list[re.Pattern] = [
    re.compile(r"\b(no\s+(worries|problem|issue|biggie|need))\b", re.I),
    re.compile(r"\b(no\s+(thank|thanks))\b", re.I),
    re.compile(r"\b(no\s+(way|chance))\b", re.I),
    re.compile(r"\bnot\s+(bad|wrong|terrible)\b", re.I),
]

CORRECTION_DIRECTIVE_WORDS: list[str] = [
    "use",
    "run",
    "do",
    "make",
    "try",
    "call",
    "set",
    "write",
    "create",
    "add",
    "remove",
    "change",
    "update",
    "install",
    "instead",
    "not",
    "the",
    "a",
    "with",
    "without",
]


def is_correction(text: str) -> bool:
    """Two-pass correction detection.

    Returns True if the user message is a correction that should
    trigger an immediate memory save.
    """
    for pattern in CORRECTION_NEGATIVE_PATTERNS:
        if pattern.search(text):
            return False

    for pattern in CORRECTION_STRONG_PATTERNS:
        if pattern.search(text):
            return True

    for pattern in CORRECTION_WEAK_PATTERNS:
        if pattern.search(text):
            remainder = re.sub(
                r"^(no|nope|nah|wait|hold\s+on|actually|um\s+actually)\s*[,!.]*\s*",
                "",
                text,
                flags=re.I,
            ).strip()
            for word in CORRECTION_DIRECTIVE_WORDS:
                if re.search(rf"\b{re.escape(word)}\b", remainder, re.I):
                    return True

    return False

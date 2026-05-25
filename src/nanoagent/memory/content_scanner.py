import re
from dataclasses import dataclass


@dataclass
class ScanResult:
    blocked: bool
    reason: str = ""
    pattern_id: str = ""
    severity: str = ""


# Threat patterns — prompt injection, role hijack, exfiltration
# Ported from pi-hermes-memory src/store/content-scanner.ts
MEMORY_THREAT_PATTERNS: list[dict] = [
    {
        "pattern": re.compile(
            r"ignore\s+(previous|all|above|prior)\s+instructions", re.I
        ),
        "id": "prompt_injection",
    },
    {"pattern": re.compile(r"you\s+are\s+now\s+", re.I), "id": "role_hijack"},
    {
        "pattern": re.compile(r"do\s+not\s+tell\s+the\s+user", re.I),
        "id": "deception_hide",
    },
    {
        "pattern": re.compile(r"system\s+prompt\s+override", re.I),
        "id": "sys_prompt_override",
    },
    {
        "pattern": re.compile(
            r"disregard\s+(your|all|any)\s+(instructions|rules|guidelines)", re.I
        ),
        "id": "disregard_rules",
    },
    {
        "pattern": re.compile(
            r"act\s+as\s+(if|though)\s+you\s+(have\s+no|don\'?t\s+have)\s+(restrictions|limits|rules)",
            re.I,
        ),
        "id": "bypass_restrictions",
    },
    {"pattern": re.compile(r"curl\s+[^\n]*\$", re.I), "id": "exfil_curl"},
    {"pattern": re.compile(r"wget\s+[^\n]*\$", re.I), "id": "exfil_wget"},
    {
        "pattern": re.compile(
            r"cat\s+[^\n]*(\.env|credentials|\.netrc|\.pgpass|\.npmrc|\.pypirc)", re.I
        ),
        "id": "read_secrets",
    },
    {"pattern": re.compile(r"authorized_keys", re.I), "id": "ssh_backdoor"},
    {"pattern": re.compile(r"\$HOME\/\.ssh|~\/\.ssh", re.I), "id": "ssh_access"},
]

# Secret detection patterns — API keys, tokens, SSH keys, env var leaks
SECRET_PATTERNS: list[dict] = [
    {
        "pattern": re.compile(r"\bsk-ant-api\S{10,}\b"),
        "id": "anthropic_api_key",
        "severity": "high",
    },
    {
        "pattern": re.compile(r"\bsk-or-v1-\S{10,}\b"),
        "id": "openrouter_api_key",
        "severity": "high",
    },
    {
        "pattern": re.compile(r"\bsk-\S{20,}\b"),
        "id": "openai_api_key",
        "severity": "high",
    },
    {
        "pattern": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
        "id": "aws_access_key",
        "severity": "high",
    },
    {
        "pattern": re.compile(r"\bghp_\S{10,}\b"),
        "id": "github_personal_token",
        "severity": "high",
    },
    {
        "pattern": re.compile(r"\bghu_\S{10,}\b"),
        "id": "github_user_token",
        "severity": "high",
    },
    {
        "pattern": re.compile(r"\bxoxb-\S{10,}\b"),
        "id": "slack_bot_token",
        "severity": "high",
    },
    {
        "pattern": re.compile(r"\bxapp-\S{10,}\b"),
        "id": "slack_app_token",
        "severity": "high",
    },
    {
        "pattern": re.compile(r"\bntn_\S{10,}\b"),
        "id": "notion_token",
        "severity": "high",
    },
    {
        "pattern": re.compile(r"\bBearer\s+\S{20,}\b"),
        "id": "bearer_auth_token",
        "severity": "high",
    },
    {
        "pattern": re.compile(r"-----BEGIN\s+(?:RSA\s+)?PRIVATE\sKEY-----"),
        "id": "private_key_block",
        "severity": "high",
    },
    {
        "pattern": re.compile(r"\b(?:sk_live|sk_test)_[0-9a-zA-Z]{10,}\b"),
        "id": "stripe_api_key",
        "severity": "high",
    },
    {
        "pattern": re.compile(r"\bAC[a-zA-Z0-9]{32}\b"),
        "id": "twilio_account_sid",
        "severity": "high",
    },
    {
        "pattern": re.compile(r"\bANTHROPIC_API_KEY\b"),
        "id": "env_anthropic_key",
        "severity": "medium",
    },
    {
        "pattern": re.compile(r"\bOPENAI_API_KEY\b"),
        "id": "env_openai_key",
        "severity": "medium",
    },
    {
        "pattern": re.compile(r"\bOPENROUTER_API_KEY\b"),
        "id": "env_openrouter_key",
        "severity": "medium",
    },
    {
        "pattern": re.compile(r"\bGITHUB_TOKEN\b"),
        "id": "env_github_token",
        "severity": "medium",
    },
    {
        "pattern": re.compile(r"\bAWS_SECRET_ACCESS_KEY\b"),
        "id": "env_aws_secret",
        "severity": "medium",
    },
    {
        "pattern": re.compile(r"\b[A-Za-z0-9+/]{60,}\b"),
        "id": "high_entropy_string",
        "severity": "low",
    },
]


def scan_content(text: str) -> ScanResult:
    """Scan text for both injection threats and secrets.

    Ported from pi-hermes-memory scanContent().
    Returns ScanResult indicating if content is blocked and why.
    """
    # Check threats first (block immediately)
    for entry in MEMORY_THREAT_PATTERNS:
        if entry["pattern"].search(text):
            return ScanResult(
                blocked=True,
                reason=f"Threat detected: {entry['id']}",
                pattern_id=entry["id"],
                severity="high",
            )

    # Check secrets (block on high/medium, warn on low)
    for entry in SECRET_PATTERNS:
        m = entry["pattern"].search(text)
        if m:
            return ScanResult(
                blocked=True,
                reason=f"Secret detected: {entry['id']}",
                pattern_id=entry["id"],
                severity=entry.get("severity", "high"),
            )

    return ScanResult(blocked=False)

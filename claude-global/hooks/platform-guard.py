"""PreToolUse guard for the must-never rules of the platform global assets.

Reads the hook JSON on stdin. Prints a deny decision when a rule is broken,
otherwise prints nothing (normal permission flow). Stdlib only. Advisory rules
live in rules/*.md; this file enforces only what must never happen.
"""
import json
import re
import sys

# Mutating broker/order tools exposed by MCP connectors (create/cancel/modify...).
# Read tools (get_*, search_*) never match.
ORDER_TOOL = re.compile(
    r"^(create|place|submit|modify|cancel|delete|update|replace|transmit)_\w*order", re.I
)
BROKER_REST = re.compile(r"iserver/account/\S*/orders?\b", re.I)

SECRET_WORDS = r"(TOKEN|SECRET|PASSWORD|PASSWD|API_?KEY|PRIVATE_KEY|WEBHOOK_SECRET)"
SECRET_RULES = [
    (re.compile(r"(^|[;&|]\s*)(printenv|env|export\s+-p|set)\s*($|[;&|>])"),
     "dumping the environment can print secrets"),
    (re.compile(r"printenv\s+\w*" + SECRET_WORDS, re.I), "printing a secret variable"),
    (re.compile(r"\b(echo|printf)\b[^\n;&|]*\$\{?\w*" + SECRET_WORDS, re.I),
     "echoing a secret variable"),
    (re.compile(r"\b(cat|type|less|more|head|tail|bat|Get-Content)\b[^\n;&|]*(^|[\s/\\])\.env(\.(?!example|sample|template)\w+)?(\s|$)"),
     "reading a .env file"),
    (re.compile(r"\bgh\s+auth\s+(token|status\s+.*(-t\b|--show-token))"), "printing the gh token"),
    (re.compile(r"\.ssh[/\\]id_\w+(?!\.pub)\b"), "reading an SSH private key"),
    (re.compile(r"(?<!\d)\d{8,10}:[A-Za-z0-9_-]{35}(?![A-Za-z0-9_-])"), "a Telegram bot token in a command"),
    (re.compile(r"\b(sk-ant-[A-Za-z0-9_-]{10,}|ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})"),
     "a literal token in a command"),
]

GITHUB_RULES = [
    (re.compile(r"\bgh\s+repo\s+delete\b"), "deleting a repo needs the owner's explicit ask"),
    (re.compile(r"\bgh\s+repo\s+edit\b[^\n;&|]*--visibility"), "changing visibility needs the owner's explicit ask"),
    (re.compile(r"\bgh\s+pr\s+merge\b[^\n;&|]*--(auto|admin)\b"), "auto/admin merge is not allowed"),
    (re.compile(r"\bgit\s+push\b[^\n;&|]*(--force(?!-with-lease)\b|\s-f\b)"), "force-push is not allowed"),
    (re.compile(r"\bgit\s+(commit|push)\b[^\n;&|]*--no-verify\b"), "skipping hooks is not allowed"),
]


def decide(tool_name, tool_input):
    """Return a reason string if the call must be denied, else None."""
    name = tool_name or ""
    if name.startswith("mcp__"):
        short = name.split("__")[-1]
        if ORDER_TOOL.match(short):
            return "no-broker-orders: " + short + " would place or change an order"
        return None
    if name == "Bash":
        cmd = (tool_input or {}).get("command", "") or ""
        if BROKER_REST.search(cmd):
            return "no-broker-orders: broker order endpoint in a command"
        for rx, why in SECRET_RULES:
            if rx.search(cmd):
                return "secrets: " + why
        for rx, why in GITHUB_RULES:
            if rx.search(cmd):
                return "github-workflow: " + why
    return None


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    reason = decide(data.get("tool_name"), data.get("tool_input"))
    if reason:
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": "platform guard: " + reason,
        }}))
    return 0


if __name__ == "__main__":
    sys.exit(main())

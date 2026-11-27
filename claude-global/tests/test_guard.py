import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

GUARD = Path(__file__).resolve().parents[1] / "hooks" / "platform-guard.py"
spec = importlib.util.spec_from_file_location("platform_guard", GUARD)
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)

BROKER_DENY = [
    "mcp__abc__create_order_instruction",
    "mcp__abc__delete_order_instruction",
    "mcp__abc__place_order",
    "mcp__abc__modify_order",
    "mcp__abc__cancel_order",
]
BROKER_ALLOW = [
    "mcp__abc__get_account_orders",
    "mcp__abc__get_order_instructions",
    "mcp__abc__get_account_trades",
    "mcp__abc__create_alert",
    "mcp__abc__update_watchlist",
    "Read",
]


@pytest.mark.parametrize("tool", BROKER_DENY)
def test_broker_order_tools_denied(tool):
    assert "no-broker-orders" in guard.decide(tool, {})


@pytest.mark.parametrize("tool", BROKER_ALLOW)
def test_read_and_other_tools_allowed(tool):
    assert guard.decide(tool, {}) is None


def bash(cmd):
    return guard.decide("Bash", {"command": cmd})


@pytest.mark.parametrize("cmd", [
    "printenv",
    "env",
    "env | sort",
    "echo $TELEGRAM_BOT_TOKEN",
    'echo "token=${GH_TOKEN}"',
    "printenv API_KEY",
    "cat .env",
    "cat ../app/.env.production",
    "gh auth token",
    "cat ~/.ssh/id_ed25519",
    "curl https://api.telegram.org/bot1234567890:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA/getMe",
    "curl -H 'x-api-key: sk-ant-abcdefghijklmnop'",
    "curl -X POST https://x/iserver/account/U1/orders",
])
def test_secret_and_broker_bash_denied(cmd):
    assert bash(cmd) is not None


@pytest.mark.parametrize("cmd", [
    "gh repo delete owner/x --yes",
    "gh repo edit owner/x --visibility public",
    "gh pr merge 5 --squash --auto",
    "gh pr merge 5 --admin",
    "git push --force origin main",
    "git push -f origin main",
    "git commit --no-verify -m x",
])
def test_github_bash_denied(cmd):
    assert "github-workflow" in bash(cmd)


@pytest.mark.parametrize("cmd", [
    "git status",
    "git push -u origin claude/topic",
    "git push --force-with-lease origin claude/topic",
    "gh pr merge 5 --squash --delete-branch",
    "cat .env.example",
    "echo hello",
    '[ -n "$TELEGRAM_BOT_TOKEN" ] && echo set',
    "python -m pytest -q",
    "ls -a .claude",
])
def test_normal_bash_allowed(cmd):
    assert bash(cmd) is None


def run_hook(payload, raw=None):
    p = subprocess.run([sys.executable, str(GUARD)],
                       input=raw if raw is not None else json.dumps(payload),
                       capture_output=True, text=True)
    return p.returncode, p.stdout


def test_hook_prints_deny_json():
    code, out = run_hook({"tool_name": "mcp__x__create_order_instruction", "tool_input": {}})
    assert code == 0
    d = json.loads(out)["hookSpecificOutput"]
    assert d["permissionDecision"] == "deny" and d["hookEventName"] == "PreToolUse"


def test_hook_silent_when_allowed_and_on_bad_input():
    assert run_hook({"tool_name": "Bash", "tool_input": {"command": "git status"}}) == (0, "")
    assert run_hook(None, raw="not json") == (0, "")

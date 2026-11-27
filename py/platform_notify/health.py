"""Shared building blocks for healthchecks (stdlib only).

One result model, two renderers, one policy knob and one Telegram probe, so every
repo's healthcheck reports the same way.

    results = [Result("schedule", PASS, "ok"), probe_telegram(token, chat, require_chat=True)]
    if should_report(results, silent_when_ok=True): ...   # only on failure
    sys.exit(exit_code(results))                          # 1 when any FAIL

Policy (`silent_when_ok`): False reports every run (a daily "OK" heartbeat);
True reports only when something FAILs. WARN never counts as a failure.
Nothing here ever includes a token in its output.
"""
import json
from dataclasses import dataclass

from .telegram import TelegramError, get_chat, get_me

PASS, WARN, FAIL = "PASS", "WARN", "FAIL"
_STATUSES = (PASS, WARN, FAIL)


@dataclass(frozen=True)
class Result:
    name: str
    status: str
    detail: str = ""

    def __post_init__(self):
        if self.status not in _STATUSES:
            raise ValueError("status must be one of %s, got %r" % (_STATUSES, self.status))

    @classmethod
    def from_passed(cls, name, passed, detail=""):
        return cls(name, PASS if passed else FAIL, detail)

    @property
    def passed(self):
        """True unless FAIL (a WARN still counts as passed)."""
        return self.status != FAIL

    def to_dict(self):
        """{check, passed, detail}: the JSON shape Claude commands already read."""
        return {"check": self.name, "passed": self.passed, "detail": self.detail}


def has_failure(results):
    return any(r.status == FAIL for r in results)


def exit_code(results):
    return 1 if has_failure(results) else 0


def should_report(results, *, silent_when_ok):
    """Report on failure always; on success only when not silent_when_ok."""
    return has_failure(results) or not silent_when_ok


def render_text(results, *, prefix="HEALTHCHECK", suffix="", ok_footer="", fail_footer=""):
    """Human/Telegram text: a head line, one `STATUS name: detail` line per result, a footer."""
    failed = has_failure(results)
    head = "%s %s" % (prefix, "FAILED" if failed else "OK")
    if suffix:
        head += " " + suffix
    lines = [head, ""] + ["%-4s %s: %s" % (r.status, r.name, r.detail) for r in results]
    footer = fail_footer if failed else ok_footer
    if footer:
        lines += ["", footer]
    return "\n".join(lines)


def render_json(results):
    return json.dumps([r.to_dict() for r in results], indent=2)


def probe_telegram(token, chat=None, *, require_chat=False, opener=None):
    """Validate the bot token (getMe) and, when `chat` is given, that the chat is reachable."""
    if not token or (require_chat and not chat):
        need = "TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID" if require_chat else "TELEGRAM_BOT_TOKEN"
        return Result("telegram", FAIL, "%s not set" % need)
    kwargs = {"opener": opener} if opener is not None else {}
    try:
        me = get_me(token=token, **kwargs)
        if chat:
            get_chat(chat, token=token, **kwargs)
    except TelegramError as exc:
        return Result("telegram", FAIL, str(exc))
    name = me.get("username") or "?"
    return Result("telegram", PASS, "bot @%s reaches chat" % name if chat else "bot username=%s" % name)

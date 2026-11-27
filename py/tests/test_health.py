import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from platform_notify import TelegramError, get_chat  # noqa: E402
from platform_notify import health as h  # noqa: E402


class FakeResp:
    def __init__(self, status=200, payload=None):
        self.status = status
        self._raw = json.dumps(payload if payload is not None else {"ok": True, "result": {"username": "bot"}}).encode()

    def read(self):
        return self._raw

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def opener_for(seen, per_method=None):
    per_method = per_method or {}

    def op(req, timeout=None):
        method = req.full_url.rsplit("/", 1)[1]
        seen.append((method, json.loads(req.data)))
        return per_method.get(method, FakeResp())
    return op


def test_result_validates_status_and_passed():
    with pytest.raises(ValueError):
        h.Result("x", "MAYBE")
    assert h.Result("x", h.WARN).passed is True
    assert h.Result("x", h.FAIL).passed is False
    assert h.Result.from_passed("x", True, "d") == h.Result("x", h.PASS, "d")
    assert h.Result.from_passed("x", False).status == h.FAIL


def test_to_dict_keeps_investment_json_shape():
    assert h.Result("yfinance", h.FAIL, "rate limited").to_dict() == {
        "check": "yfinance", "passed": False, "detail": "rate limited"}
    assert list(h.Result("a", h.WARN, "w").to_dict()) == ["check", "passed", "detail"]


def test_policy_and_exit_code():
    ok = [h.Result("a", h.PASS), h.Result("b", h.WARN)]
    bad = [h.Result("a", h.PASS), h.Result("b", h.FAIL)]
    assert h.exit_code(ok) == 0 and h.exit_code(bad) == 1
    assert h.should_report(ok, silent_when_ok=False) is True
    assert h.should_report(ok, silent_when_ok=True) is False
    assert h.should_report(bad, silent_when_ok=True) is True
    assert h.should_report([], silent_when_ok=True) is False


def test_render_text_matches_carry_format():
    text = h.render_text([h.Result("a", h.PASS, "x"), h.Result("b", h.WARN, "y")],
                         suffix="2026-10-08", ok_footer="armed")
    assert text == "HEALTHCHECK OK 2026-10-08\n\nPASS a: x\nWARN b: y\n\narmed"
    bad = h.render_text([h.Result("a", h.FAIL, "x")], suffix="d", fail_footer="fix it")
    assert bad.startswith("HEALTHCHECK FAILED d\n\nFAIL a: x") and bad.endswith("\n\nfix it")
    assert h.render_text([h.Result("a", h.PASS)], prefix="P") == "P OK\n\nPASS a: "


def test_render_json_roundtrip():
    out = json.loads(h.render_json([h.Result("a", h.PASS, "x"), h.Result("b", h.FAIL, "y")]))
    assert out == [{"check": "a", "passed": True, "detail": "x"}, {"check": "b", "passed": False, "detail": "y"}]


def test_probe_telegram_unset():
    r = h.probe_telegram(None, None)
    assert r.status == h.FAIL and "TELEGRAM_BOT_TOKEN not set" in r.detail
    r = h.probe_telegram("T", None, require_chat=True)
    assert r.status == h.FAIL and "TELEGRAM_CHAT_ID" in r.detail


def test_probe_telegram_ok_with_and_without_chat():
    seen = []
    r = h.probe_telegram("TOK", "42", opener=opener_for(seen))
    assert r == h.Result("telegram", h.PASS, "bot @bot reaches chat")
    assert [m for m, _ in seen] == ["getMe", "getChat"] and seen[1][1] == {"chat_id": "42"}
    seen.clear()
    r = h.probe_telegram("TOK", None, opener=opener_for(seen))
    assert r == h.Result("telegram", h.PASS, "bot username=bot")
    assert [m for m, _ in seen] == ["getMe"]


def test_probe_telegram_failure_never_leaks_token():
    r = h.probe_telegram("SECRETTOK", "42", opener=opener_for([], {"getMe": FakeResp(401)}))
    assert r.status == h.FAIL and "HTTP 401" in r.detail and "SECRETTOK" not in r.detail
    r = h.probe_telegram("SECRETTOK", "42", opener=opener_for([], {"getChat": FakeResp(400)}))
    assert r.status == h.FAIL and "getChat" in r.detail and "SECRETTOK" not in r.detail


def test_get_chat_errors():
    with pytest.raises(TelegramError):
        get_chat("1", token=None)  # no env token
    with pytest.raises(TelegramError) as e:
        get_chat("1", token="SECRETTOK", opener=opener_for([], {"getChat": FakeResp(200, {"ok": False})}))
    assert "SECRETTOK" not in str(e.value)

import io
import json
import sys
import urllib.error
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from platform_notify import TelegramError, get_me, send_message  # noqa: E402


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


def opener_returning(resp, seen=None):
    def op(req, timeout=None):
        if seen is not None:
            seen.append((req.full_url, json.loads(req.data)))
        return resp
    return op


def test_skips_when_unset(monkeypatch, capsys):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    assert send_message("hi", opener=lambda *a, **k: pytest.fail("must not call")) is False
    assert "skipping" in capsys.readouterr().out


def test_sends_with_env(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "TOK")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "42")
    seen = []
    assert send_message("hi", parse_mode="HTML", reply_markup={"inline_keyboard": []},
                        opener=opener_returning(FakeResp(), seen)) is True
    url, body = seen[0]
    assert url == "https://api.telegram.org/botTOK/sendMessage"
    assert body == {"chat_id": "42", "text": "hi", "parse_mode": "HTML", "reply_markup": {"inline_keyboard": []}}


def test_explicit_args_override_env(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "ENV")
    seen = []
    send_message("x", token="ARG", chat_id="7", opener=opener_returning(FakeResp(), seen))
    assert seen[0][0].startswith("https://api.telegram.org/botARG/")
    assert seen[0][1]["chat_id"] == "7"


def test_ok_false_raises():
    with pytest.raises(TelegramError, match="ok=false"):
        send_message("x", token="T", chat_id="1", opener=opener_returning(FakeResp(payload={"ok": False})))


def test_non_200_raises():
    with pytest.raises(TelegramError, match="HTTP 500"):
        send_message("x", token="T", chat_id="1", opener=opener_returning(FakeResp(status=500)))


def test_http_error_message_has_no_token():
    def op(req, timeout=None):
        raise urllib.error.HTTPError(req.full_url, 401, "Unauthorized", {}, io.BytesIO(b""))
    with pytest.raises(TelegramError) as ei:
        send_message("x", token="SECRETTOKEN", chat_id="1", opener=op)
    assert "SECRETTOKEN" not in str(ei.value)
    assert "401" in str(ei.value)


def test_network_error_message_is_redacted():
    def op(req, timeout=None):
        raise OSError("cannot reach https://api.telegram.org/botSECRETTOKEN/sendMessage")
    with pytest.raises(TelegramError) as ei:
        send_message("x", token="SECRETTOKEN", chat_id="1", opener=op)
    assert "SECRETTOKEN" not in str(ei.value)


def test_get_me(monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    assert get_me(token="T", opener=opener_returning(FakeResp()))["username"] == "bot"
    with pytest.raises(TelegramError, match="token not set"):
        get_me(token="")

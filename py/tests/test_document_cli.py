import io
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from platform_notify import TelegramError, send_document  # noqa: E402
from platform_notify.__main__ import main  # noqa: E402


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


def capture(seen, resp=None):
    def op(req, timeout=None):
        seen.append((req.full_url, dict(req.header_items()), req.data))
        return resp or FakeResp()
    return op


def test_document_multipart(tmp_path):
    f = tmp_path / "event.ics"
    f.write_bytes(b"BEGIN:VCALENDAR\r\nEND:VCALENDAR\r\n")
    seen = []
    assert send_document(f, caption="due", parse_mode="Markdown", token="TOK", chat_id="42",
                         opener=capture(seen)) is True
    url, headers, body = seen[0]
    assert url == "https://api.telegram.org/botTOK/sendDocument"
    ctype = headers["Content-type"]
    assert ctype.startswith("multipart/form-data; boundary=")
    boundary = ctype.split("boundary=")[1].encode()
    assert body.count(b"--" + boundary) == 5  # 3 fields + file + closing
    assert b'name="chat_id"\r\n\r\n42' in body
    assert b'name="caption"\r\n\r\ndue' in body
    assert b'name="parse_mode"\r\n\r\nMarkdown' in body
    assert b'name="document"; filename="event.ics"' in body
    assert b"BEGIN:VCALENDAR\r\nEND:VCALENDAR\r\n" in body
    assert b"TOK" not in body


def test_document_skips_when_unset(monkeypatch, capsys, tmp_path):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    f = tmp_path / "a.ics"
    f.write_bytes(b"x")
    assert send_document(f, opener=lambda *a, **k: pytest.fail("must not call")) is False
    assert "skipping" in capsys.readouterr().out


def test_document_missing_file_error_has_no_token(tmp_path):
    with pytest.raises(TelegramError) as e:
        send_document(tmp_path / "nope.ics", token="SECRETTOK", chat_id="1", opener=capture([]))
    assert "SECRETTOK" not in str(e.value) and "nope.ics" in str(e.value)


def test_document_http_error_has_no_token(tmp_path):
    f = tmp_path / "a.ics"
    f.write_bytes(b"x")
    with pytest.raises(TelegramError) as e:
        send_document(f, token="SECRETTOK", chat_id="1", opener=capture([], FakeResp(500)))
    assert "SECRETTOK" not in str(e.value)


def test_filename_is_sanitised():
    from platform_notify.telegram import _multipart
    body, _ = _multipart({}, "document", 'we"ird\r\n.ics', b"x")
    assert b'filename="we_ird__.ics"' in body


def test_cli_message_text_and_parse_mode():
    seen = []
    code = main(["message", "--text", "hi *there*", "--parse-mode", "Markdown"],
                token="TOK", chat_id="42",
                opener=lambda req, timeout=None: (seen.append(json.loads(req.data)), FakeResp())[1])
    assert code == 0
    assert seen == [{"chat_id": "42", "text": "hi *there*", "parse_mode": "Markdown"}]


def test_cli_message_stdin_and_file(tmp_path):
    seen = []

    def op(req, timeout=None):
        seen.append(json.loads(req.data)["text"])
        return FakeResp()

    assert main(["message", "--text", "-"], stdin=io.StringIO("from stdin\nline2"),
                token="T", chat_id="1", opener=op) == 0
    f = tmp_path / "n.md"
    f.write_text("from file", encoding="utf-8")
    assert main(["message", "--text-file", str(f)], token="T", chat_id="1", opener=op) == 0
    assert seen == ["from stdin\nline2", "from file"]


def test_cli_document(tmp_path):
    f = tmp_path / "e.ics"
    f.write_bytes(b"x")
    seen = []
    assert main(["document", str(f), "--caption", "c"], token="T", chat_id="1", opener=capture(seen)) == 0
    assert seen[0][0].endswith("/sendDocument")


def test_cli_failure_exit_1_without_token(capsys):
    code = main(["message", "--text", "x"], token="SECRETTOK", chat_id="1",
                opener=lambda req, timeout=None: FakeResp(500))
    assert code == 1
    err = capsys.readouterr().err
    assert "SECRETTOK" not in err and "HTTP 500" in err


def test_cli_get_me(capsys):
    assert main(["get-me"], token="T", opener=lambda req, timeout=None: FakeResp()) == 0
    assert "bot username=bot" in capsys.readouterr().out


def test_cli_requires_text():
    with pytest.raises(SystemExit) as e:
        main(["message"])
    assert e.value.code == 2

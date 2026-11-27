import json
import os
import urllib.error
import urllib.request
import uuid
from pathlib import Path

API = "https://api.telegram.org"


class TelegramError(RuntimeError):
    """Raised on a failed Bot API call. Message never contains the token."""


def _redact(text, token):
    return str(text).replace(token, "<token>") if token else str(text)


def _call(method, body, token, timeout, opener):
    req = urllib.request.Request(
        f"{API}/bot{token}/{method}",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    return _send_raw(req, method, token, timeout, opener)


def _send_raw(req, method, token, timeout, opener):
    try:
        with opener(req, timeout=timeout) as resp:
            status = resp.status
            raw = resp.read()
    except urllib.error.HTTPError as exc:
        raise TelegramError(f"{method} failed: HTTP {exc.code}") from None
    except Exception as exc:  # network, DNS, timeout
        raise TelegramError(f"{method} failed: {_redact(type(exc).__name__ + ': ' + str(exc), token)}") from None
    if status != 200:
        raise TelegramError(f"{method} failed: HTTP {status}")
    try:
        data = json.loads(raw)
    except ValueError:
        raise TelegramError(f"{method} failed: non-JSON response") from None
    if not data.get("ok"):
        raise TelegramError(f"{method} failed: ok=false")
    return data


def send_message(
    text,
    *,
    token=None,
    chat_id=None,
    parse_mode=None,
    reply_markup=None,
    timeout=15,
    opener=urllib.request.urlopen,
):
    """Send a message. Returns True if sent, False if token/chat id are unset
    (skipped, with a one-line note on stdout). Raises TelegramError on failure."""
    token = token or os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = chat_id or os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID not set - skipping Telegram notification.")
        return False
    body = {"chat_id": chat_id, "text": text}
    if parse_mode:
        body["parse_mode"] = parse_mode
    if reply_markup is not None:
        body["reply_markup"] = reply_markup
    _call("sendMessage", body, token, timeout, opener)
    return True


def _multipart(fields, file_field, filename, content):
    """Build a multipart/form-data body. Returns (body_bytes, content_type)."""
    boundary = "platformnotify" + uuid.uuid4().hex
    parts = []
    for name, value in fields.items():
        parts.append(
            (f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"\r\n\r\n{value}\r\n").encode("utf-8")
        )
    safe_name = filename.replace('"', "_").replace("\r", "_").replace("\n", "_")
    parts.append(
        (f"--{boundary}\r\nContent-Disposition: form-data; name=\"{file_field}\"; filename=\"{safe_name}\"\r\n"
         "Content-Type: application/octet-stream\r\n\r\n").encode("utf-8")
    )
    parts.append(content)
    parts.append(f"\r\n--{boundary}--\r\n".encode("utf-8"))
    return b"".join(parts), f"multipart/form-data; boundary={boundary}"


def send_document(
    path,
    *,
    caption=None,
    token=None,
    chat_id=None,
    parse_mode=None,
    timeout=30,
    opener=urllib.request.urlopen,
):
    """Send a file (for example an .ics calendar event). Same skip/raise rules
    as send_message."""
    token = token or os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = chat_id or os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID not set - skipping Telegram notification.")
        return False
    p = Path(path)
    try:
        content = p.read_bytes()
    except OSError as exc:
        raise TelegramError(f"sendDocument failed: cannot read {p.name}: {type(exc).__name__}") from None
    fields = {"chat_id": chat_id}
    if caption:
        fields["caption"] = caption
    if parse_mode:
        fields["parse_mode"] = parse_mode
    body, ctype = _multipart(fields, "document", p.name, content)
    req = urllib.request.Request(
        f"{API}/bot{token}/sendDocument", data=body, headers={"Content-Type": ctype}
    )
    _send_raw(req, "sendDocument", token, timeout, opener)
    return True


def get_me(*, token=None, timeout=15, opener=urllib.request.urlopen):
    """Validate the token. Returns the bot's 'result' dict, raises TelegramError."""
    token = token or os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise TelegramError("getMe failed: token not set")
    return _call("getMe", {}, token, timeout, opener)["result"]

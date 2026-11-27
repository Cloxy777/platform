import json
import os
import urllib.error
import urllib.request

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


def get_me(*, token=None, timeout=15, opener=urllib.request.urlopen):
    """Validate the token. Returns the bot's 'result' dict, raises TelegramError."""
    token = token or os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise TelegramError("getMe failed: token not set")
    return _call("getMe", {}, token, timeout, opener)["result"]

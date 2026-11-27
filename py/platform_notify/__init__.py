"""platform_notify: stdlib-only Telegram sender for scripts and Actions jobs.

Reads TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID from the environment unless given.
Never includes the token in an exception message or log line.
"""

from .telegram import TelegramError, get_me, send_message

__all__ = ["TelegramError", "get_me", "send_message"]

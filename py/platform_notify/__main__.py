"""Command line for Routines, slash commands and shell steps.

    python -m platform_notify message --text "hello" [--parse-mode Markdown]
    python -m platform_notify message --text-file note.md
    python -m platform_notify message --text -            (read stdin)
    python -m platform_notify document event.ics [--caption "..."]
    python -m platform_notify get-me

Reads TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID from the environment. Exit codes:
0 sent or skipped (unset secrets are reported on stdout), 1 Telegram failure,
2 usage error. Failure messages never contain the token.
"""
import argparse
import sys

from .telegram import TelegramError, get_me, send_document, send_message


def build_parser():
    ap = argparse.ArgumentParser(prog="python -m platform_notify")
    sub = ap.add_subparsers(dest="cmd", required=True)

    m = sub.add_parser("message", help="send a text message")
    g = m.add_mutually_exclusive_group(required=True)
    g.add_argument("--text", help="message text, or - to read stdin")
    g.add_argument("--text-file", help="read the message text from a file")
    m.add_argument("--parse-mode", choices=["Markdown", "MarkdownV2", "HTML"])

    d = sub.add_parser("document", help="send a file")
    d.add_argument("path")
    d.add_argument("--caption")
    d.add_argument("--parse-mode", choices=["Markdown", "MarkdownV2", "HTML"])

    sub.add_parser("get-me", help="validate the bot token")
    return ap


def main(argv=None, stdin=None, **kwargs):
    """`kwargs` are passed to the library calls (tests inject opener/token/chat_id)."""
    args = build_parser().parse_args(argv)
    stdin = stdin if stdin is not None else sys.stdin
    try:
        if args.cmd == "message":
            if args.text_file:
                with open(args.text_file, encoding="utf-8") as fh:
                    text = fh.read()
            elif args.text == "-":
                text = stdin.read()
            else:
                text = args.text
            send_message(text, parse_mode=args.parse_mode, **kwargs)
        elif args.cmd == "document":
            send_document(args.path, caption=args.caption, parse_mode=args.parse_mode, **kwargs)
        else:
            info = get_me(**kwargs)
            print("bot username=%s" % info.get("username"))
    except TelegramError as exc:
        print("ERROR: %s" % exc, file=sys.stderr)
        return 1
    except OSError as exc:
        print("ERROR: %s" % type(exc).__name__, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

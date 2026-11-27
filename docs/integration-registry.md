# Integration registry (template)

Copy this file into a **private** repo (for example the one holding HANDOFF.md) and fill it in.
Never record secret values, only where each one lives and how to rotate it. This public copy stays empty
on purpose: no chat ids, account ids, tokens or hostnames.

| Integration | Kind | Owner repo | Secret (name only) | Lives in | Rotation | Healthcheck |
|---|---|---|---|---|---|---|
| (example) carry bot | Telegram bot | ua-carry-trade | TELEGRAM_BOT_TOKEN | Worker secret, Actions secret, Routine env | docs/operations.md, bot rotation | tools/healthcheck.py |
| (example) gateway | Cloudflare Worker | life-gateway | CLOUDFLARE_API_TOKEN, REGISTRY | Actions secret, Worker secret | docs/operations.md | gateway /health digest |
| (example) Routine 1 | Routine | investment-framework | none | claude.ai | n/a | `routines/routine_drift.py check` |

One row per instance. Kinds: Telegram bot, Cloudflare Worker, KV namespace, cron, GitHub token, connector, Routine.
Review the table whenever a row is added to a repo's CI secrets, and after every rotation.

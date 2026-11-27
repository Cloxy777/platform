# Platform architecture (current state)

Status as of 2026-11-27. This file describes what **exists and works today**.
What is designed but not built is in [design.md](design.md); what to do next is
in [roadmap.md](roadmap.md); why choices were made is in
[decisions.md](decisions.md); how to operate it is in
[operations.md](operations.md).

Read this file fully before changing anything in this repo or in a consumer's
use of it.

## 1. Purpose

One owner (GitHub user `Cloxy777`) runs about ten personal repos. Each repo is
a *domain* (investments, sports-court booking, a credit carry-trade tracker,
health/car/sport records, trading, career). The goal of `platform` is to hold
everything that is **the same across domains** so each domain repo keeps only
what is specific to it:

- shared CI (reusable GitHub Actions workflows),
- shared Telegram code (JS for Cloudflare Workers, Python for scripts),
- later: shared Claude Code rules/skills/agents (a plugin), a domain contract,
  a template repo, a gateway Worker (see [design.md](design.md)).

`platform` is **public** and must contain **no personal data, ids, tokens or
secrets**. Private repos consume it without any token (public reusable
workflows and public git dependencies need no credentials).

## 2. Repository map

| Repo | Visibility | Domain | Uses platform for |
|---|---|---|---|
| `platform` | public | shared code | (this repo) |
| `investment-framework` | private | quality-value investing, runs as Claude Code Routines + slash commands | CI (`test-py`), Telegram `getMe` probe (`platform_notify`) |
| `automation-framework` | private | municipal sports-court booking (Playwright on Actions) + Telegram bot on a Cloudflare Worker | CI (`test-node`, `test-py`), Worker uses vendored `telegram-kit`, Python sender uses `platform_notify` |
| `ua-carry-trade` | private | credit carry-trade tracker, daily reminders | CI (`test-py`), Telegram sender via `platform_notify` |
| `life-sport`, `life-health`, `life-car`, `life-context` | private | personal records | nothing yet |
| `trading-framework`, `career-hub` | private | dormant / static | nothing yet |
| `game-scripts` | private | AutoHotkey save backups | nothing |

## 3. What is in this repo

```
.github/workflows/
  test-py.yml        reusable: pytest
  test-node.yml      reusable: npm ci + npm test
  deploy-worker.yml  reusable: wrangler deploy
  check-claude-sync.yml  reusable: fail if a consumer's generated Claude files drift
  ci.yml             this repo's own CI (calls the reusable ones via ./)
claude-global/           global Claude assets (rules, guard hook, settings fragment)
                         and sync.py that renders them into a consumer repo (3.4)
packages/telegram-kit/   JS, zero dependencies (Cloudflare Workers / Node 22+)
py/platform_notify/      Python, stdlib only (3.9+)
docs/                    this documentation
renovate.json            Renovate config (bumps pinned tags in consumers)
```

### 3.1 Reusable workflows (tag `v0.1.0`)

Call with `uses: Cloxy777/platform/.github/workflows/<file>@v0.1.0`.

`test-py.yml` inputs: `python-version` (default 3.12), `test-path` (default
`tests`), `requirements-file` (default empty = skip install),
`working-directory` (default `.`). Installs `pytest`, runs
`python -m pytest <test-path> -q`.

`test-node.yml` inputs: `node-version` (22), `working-directory` (`.`). Runs
`npm ci` then `npm test --if-present`. **The caller must commit a
`package-lock.json`** (`npm ci` fails without one).

`deploy-worker.yml` inputs: `working-directory`, `node-version`; secret
`CLOUDFLARE_API_TOKEN` (required). Runs `npm ci` then `npx wrangler deploy`.
Not used by any consumer yet (the booking repo still has its own
`deploy-webhook.yml`).

All three declare `permissions: contents: read` and short `timeout-minutes`.
Verified: a **private** repo can call these public workflows with no token.

### 3.2 `packages/telegram-kit` (tag `telegram-kit-v0.1.0`)

ES module, no dependencies, uses only Web APIs (`fetch`, `crypto.subtle`,
`TextEncoder`, `Headers`). Exports:

| Function | Behaviour |
|---|---|
| `timingSafeEqual(a, b)` | Constant-time compare of UTF-8 bytes; loops over the longer length; unequal length -> false; null/undefined treated as "" |
| `verifyWebhook(request, secret)` | True only if `X-Telegram-Bot-Api-Secret-Token` equals `secret` (constant time). Empty/unset secret never verifies. Missing header -> false |
| `parseAllowlist(csv)` | `"1, 2,,3"` -> `Set{"1","2","3"}` (ids are strings) |
| `isAllowed(set, chatId)` | String compare; empty id never matches |
| `parseCommand(text)` | `"/Cmd@Bot a b"` -> `{name:"/cmd", args:"a b"}` |
| `firstSeen(kv, updateId, ttl=86400)` | KV dedup of `update_id` (`upd:<id>`). True first time, false on repeat. Missing kv or id -> true (never drops updates). Best-effort: KV is eventually consistent |
| `sign(secret, data, bytes=8)` | HMAC-SHA256, hex, truncated |
| `verifySignature(secret, data, sig, bytes=8)` | constant-time check of `sign` output |
| `createClient({token, fetchImpl, parseMode="HTML"})` | `send(chatId,text,markup)` throws on non-2xx; `answerCallback`, `editText`, `editMarkup` are best-effort (never throw on HTTP errors). `fetchImpl` is injectable for tests |

`sign`/`verifySignature` are built and tested but **no consumer uses them
yet** (they exist for the future confirm-before-execute callback flow, see
design.md).

### 3.3 `py/platform_notify` (tags `py-v0.1.0`; `py-v0.2.0` adds `send_document` and the CLI)

Stdlib only. `send_message(text, *, token=None, chat_id=None, parse_mode=None,
reply_markup=None, timeout=15, opener=urlopen) -> bool`. Reads
`TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` from the environment unless passed.
Returns `False` (prints a note) when either is unset, `True` when sent, raises
`TelegramError` (a `RuntimeError`) on failure. `get_me(*, token=None,
timeout=15, opener=urlopen)` returns the bot's `result` dict. **Error messages
never contain the token** (HTTP errors give only the code; other exceptions are
redacted). `opener` is injectable for tests.

From `py-v0.2.0`: `send_document(path, *, caption=None, token=None,
chat_id=None, parse_mode=None, timeout=30, opener=urlopen) -> bool` (multipart,
same skip/raise rules), and a CLI so Routines and slash commands need no curl:

```
python -m platform_notify message --text "..." [--parse-mode Markdown]   # or --text - (stdin) / --text-file F
python -m platform_notify document event.ics [--caption "..."]
python -m platform_notify get-me
```
Exit codes: 0 sent or skipped (unset secrets), 1 Telegram failure, 2 usage.

### 3.4 `claude-global` (not tagged yet; first use is the carry pilot)

Single source of the global Claude layer (design.md section 3, decisions D13):
- `rules/*.md`: github-workflow, secrets, no-broker-orders, cite-sources.
- `hooks/platform-guard.py`: PreToolUse guard that denies broker order tools
  (MCP tool names like `create_order_instruction`, `cancel_order`; read tools are
  untouched), secret-printing shell commands, and risky `gh`/`git` commands
  (repo delete, visibility change, auto/admin merge, force-push, `--no-verify`).
  Plain `gh pr merge --squash` stays allowed: Routine 2 merges its own PRs, and
  the owner's yes for merges is a rule, not a hook.
- `settings.fragment.json`: the hook wiring.
- `sync.py <repo> --tag <tag> [--check]`: writes `.claude/rules/platform-*.md`,
  `.claude/hooks/platform-guard.py`, merges the hook entry into
  `.claude/settings.json` (consumer's own settings and hooks are preserved), and
  maintains a marked block of `@.claude/rules/platform-*.md` imports in the
  consumer's `CLAUDE.md`. Files named `platform-*` are owned by the script.
- `check-claude-sync.yml` (reusable) runs `sync.py --check` in the consumer's CI.

Consumer flow: run sync with the release tag, commit, PR. Bump = re-run with the
new tag. The consumer `CLAUDE.md` keeps only domain rules above the block.

## 4. How consumers use it

Claude global assets (3.4), synced at `v0.2.0` with CI job `claude-sync`: `ua-carry-trade` (#59, pilot), `investment-framework` (#999), `automation-framework` (#115), `life-sport` (#14), `life-health` (#1), `life-car` (#3), `life-context` (#1). The three AGENTS.md-only life repos got a `CLAUDE.md` that imports `@AGENTS.md` plus the platform block. Not yet: dormant repos (`trading-framework`, `career-hub`, `game-scripts`).

| Consumer | CI | Telegram |
|---|---|---|
| `ua-carry-trade` | `ci.yml` -> `test-py.yml@v0.1.0` (`tests`, `requirements.txt`) | `tools/daily_reminder.py` `send()` calls `platform_notify.send_message`; Actions jobs `pip install -r requirements.txt` (git-tag pin) |
| `automation-framework` | `ci.yml`: `test-node.yml` for `webhook/`, `test-py.yml` for `tests/` | Worker: vendored `webhook/src/vendor/telegram-kit.js`; Python: `scripts/notify_telegram.py` is a shim over `platform_notify` (keeps `send_message(text, reply_markup=None)` and HTML mode) |
| `investment-framework` | `ci.yml` -> `test-py.yml@v0.1.0` (`scripts/tests`, `scripts/requirements.txt`) | Routine/command text sends via `python -m platform_notify message|document` (pin `py-v0.2.0`); `scripts/healthcheck.py` `check_telegram_bot` uses `platform_notify.get_me` (test seam `fetch(url)->str` kept) |

Pinning styles in use:
- Workflows: `@v0.1.0` tag.
- Python: `platform-notify @ git+https://github.com/Cloxy777/platform@py-v0.1.0#subdirectory=py` in a `requirements.txt`.
- JS: **vendored copy** (see decisions.md D2). The copy's first lines name the
  source tag; `webhook/test/vendor-sync.test.js` checks that header and, when a
  sibling `platform` checkout exists locally, checks byte-for-byte drift.

## 5. Telegram topology today

- Three separate bots exist, one per domain (investment, carry-trade, booking).
  Tokens are never shared between domains.
- Inbound (webhook) exists **only** for the booking bot: a Cloudflare Worker
  (`telegram-bookings-bot`, KV namespace for state, `*/5` cron). It now checks
  the secret header in constant time, drops repeated `update_id`s, enforces a
  chat-id allowlist (unknown chats silently ignored) and an owner-only gate for
  cancel/confirm commands.
- Investment and carry-trade bots are **outbound only** (scripts or Claude
  Routines call the Bot API directly).
- There is no gateway, no per-domain contract, no shared bot for a group of
  repos yet (designed in design.md).

## 6. Conventions that apply to every repo

- Work on `claude/*` branches, open PRs, merge only on the owner's explicit yes.
  Private repos on the free plan have no branch protection, so this is process,
  not enforcement.
- Merge with a direct squash merge (`gh pr merge --squash --delete-branch`).
  Do not rely on GitHub auto-merge (decision recorded in
  `investment-framework/decisions/2026-11-25-direct-merge-no-auto-merge.md`).
- Commits end with `Co-Authored-By: Claude ... <noreply@anthropic.com>`; PR
  bodies end with the Claude Code line.
- Never print secret values. Tokens live in Worker secrets, Actions secrets or
  the Routine environment, never in git.
- No tool in any repo may place, modify or cancel broker orders.
- Tests must pass in CI before merge; pure helpers are exported for tests
  (`export { ... }` at the end of a Worker entry file is fine).

## 7. Known constraints and gotchas

- **Private-repo Actions minutes** are limited on the free plan; keep jobs
  short (current CI jobs run 10-35 s).
- **`clujLocalToUtcMs`** (booking Worker) re-parses `toLocaleString()` in the
  runtime timezone, so it is only correct when `TZ=UTC` (always true on
  Workers). Its tests pin `process.env.TZ = "UTC"`.
- **`node --test`** in Node 24 treats a directory argument as a file; use bare
  `node --test` (auto-discovers `test/`).
- **npm cannot install a git subdirectory**, hence vendoring for JS.
- **Claude Code Routine environments** (claude.ai): the setup script runs
  before the session, from a directory that is *not* the repo root, and its
  result is cached until the script text changes. `python` may resolve to a
  different interpreter than `pip`. The working setup installs into both
  interpreters using an absolute path (see operations.md).
- GitHub cron is unreliable (measured 1.5-4.5 h late). Time-critical triggers
  belong on Cloudflare cron, which dispatches `workflow_dispatch`.
- Booking dispatch in the booking Worker is currently **suspended** (commit
  4d6d4ce); that is a product decision, not a bug.

# Operations runbook

## Releasing a change to platform

1. Branch `claude/<topic>` from `main`, change, run the suites locally:
   - Python: `cd py && python -m pytest tests -q`
   - JS: `cd packages/telegram-kit && npm test`
   - Claude assets: `python -m pytest claude-global/tests -q`; scripts: `python -m pytest scripts/tests -q`
   - If a released path changed, add a line under `## Unreleased` in `CHANGELOG.md`
     (`python scripts/check_changelog.py origin/main` shows what CI will say).
2. Open a PR. `ci.yml` runs both suites through the repo's own reusable
   workflows. Merge with `gh pr merge <n> --squash --delete-branch` after the
   owner says yes.
3. Tag only the thing that changed, from `main` (and move the Unreleased lines in
   `CHANGELOG.md` under a heading for the tag, in the same or the next PR):
   - workflows and `claude-global`: `v<major>.<minor>.<patch>`
   - JS kit: `telegram-kit-v<...>`; Python: `py-v<...>`
   - `git tag <name> && git push origin <name>`. Never move or delete a pushed tag;
     cut a new one.
4. Bump consumers (below). Renovate (`renovate.json`) can propose tag bumps for
   workflow and pip pins once the Renovate GitHub app is installed (not done yet).

## Bumping a consumer

- **Workflow tag**: edit `uses: Cloxy777/platform/.github/workflows/<f>@<tag>`.
- **Python**: edit the pin in `requirements.txt`. For the investment Routine
  environment also change the setup-script text (or add a comment line) so the
  cached setup re-runs.
- **JS kit (vendored)**: copy `packages/telegram-kit/src/index.js` over
  `webhook/src/vendor/telegram-kit.js` and update the 4-line header (tag name).
  Run `npm test` in `webhook/`; with a sibling `platform` checkout the sync test
  proves the copy is exact.

## Adding a new consumer repo

1. Add `.github/workflows/ci.yml` calling `test-py.yml` and/or `test-node.yml`.
   Node callers need a committed `package-lock.json` and an `npm test` script.
2. For Telegram: Python -> pin `platform-notify`; Worker -> vendor the kit.
3. Keep tests runnable offline (inject `opener`/`fetchImpl`, never hit the network).

## Telegram bot token rotation

1. BotFather `/revoke` for the affected bot (this silently clears the webhook).
2. Set the new token everywhere that bot's token lives: Worker secret
   (`wrangler secret put`), Actions secret, Routine environment variable.
3. Re-run `setWebhook` for inbound bots with the same secret token.
4. Verify with `getMe`, then one test message. Old token must return 401.
Do not print token values; do not put them in URLs or logs.

## Claude Routine environment (claude.ai)

The investment Routines run in a cloud environment with a **setup script**.
Facts learned the hard way:
- It runs before Claude Code starts, **not** from the repo root. The clone is
  at `/home/user/<repo>`. Use absolute paths.
- Its result is cached until the script text changes; edit the text to force a
  rerun.
- `python` and `pip` can belong to different interpreters (3.11 vs 3.13).
  Working script (installs into both):
  ```bash
  for PY in /usr/local/bin/python /usr/bin/python3; do
    "$PY" -m pip install -r /home/user/investment-framework/scripts/requirements.txt
  done
  ```
- The environment needs github.com reachable (git-pinned Python dependency).
- Verify by running the daily healthcheck Routine manually and reading the run
  log; a clean run needs no interpreter workarounds.

## Verifying the booking Worker after a deploy

Deploy happens on push to `main` touching `webhook/**` (its own workflow).
After a deploy send `/notify list` to the bot: expect exactly one reply. Rollback:
`npx wrangler rollback` from `webhook/` or revert the commit.

## Windows notes (the owner's machine)

PowerShell; use `npx.cmd wrangler ...` and `curl.exe --ssl-no-revoke` for
Telegram. Large multi-file shell heredocs in Git Bash can fail to parse; write
files with an editor tool instead.

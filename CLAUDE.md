# platform

Public repo of shared building blocks for the owner's personal automation repos.
It must contain **no personal data, chat ids, account ids, tokens or secrets**.

Before changing anything, read in this order:
1. `docs/architecture.md` - what exists and how consumers use it
2. `docs/decisions.md` - why it is this way (do not undo without a new decision)
3. `docs/operations.md` - releasing, bumping consumers, rotation, Routine env
4. `docs/design.md` and `docs/roadmap.md` - what is planned, in priority order

Working rules:
- Branch `claude/<topic>`, open a PR, merge only when the owner says yes
  (`gh pr merge <n> --squash --delete-branch`). Never auto-merge.
- Tag only what changed: `v*` (workflows), `telegram-kit-v*`, `py-v*`. Never move
  or delete a pushed tag.
- `claude-global/` is stdlib-only Python; edit rules/hooks there, never in a consumer's generated `platform-*` files. Guard hook changes need a test in `claude-global/tests`.
- Keep `packages/telegram-kit` dependency-free and `py/platform_notify`
  stdlib-only. Error messages must never contain a token.
- Tests must be offline (inject `fetchImpl` / `opener`).
- After a change that affects consumers, update `docs/architecture.md` (section 4)
  and add to `docs/decisions.md` if a choice was made.
- Commits end with `Co-Authored-By: Claude <noreply@anthropic.com>`.
- No tool here may place, modify or cancel broker orders.

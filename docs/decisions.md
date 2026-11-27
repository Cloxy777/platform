# Decisions

Numbered, newest last. Each entry: decision, why, consequence. Add new entries
at the bottom; never rewrite history, supersede instead.

## D1 - One public `platform` mono-repo (2026-11-26)

Instead of four repos (core, claude, mcp, template). A solo maintainer with ~10
repos and ~500 lines of shareable code does not benefit from four release
streams. Path-prefixed tags give independent versions inside one repo:
`v<semver>` (workflows), `telegram-kit-v<semver>`, `py-v<semver>`. The repo is
public with zero data so private repos consume it with no token. `template-domain`
may become a separate GitHub *template* repo later (it must be one to be a
template); everything else stays here.

## D2 - JS kit is vendored, not installed (2026-11-27)

npm cannot install a subdirectory of a git repo, and publishing to npm adds an
account, a token and a release pipeline for ~100 lines. So consumers copy
`packages/telegram-kit/src/index.js` to `src/vendor/telegram-kit.js` with a
header naming the source tag. Drift is guarded by a header test plus a local
byte comparison. Revisit if there are more than ~3 JS consumers or the kit
grows: then publish to the public npm registry from Actions.

## D3 - Python is a git-tag pin (2026-11-27)

`platform-notify @ git+https://github.com/Cloxy777/platform@py-vX#subdirectory=py`
in `requirements.txt`. pip supports subdirectories, so no copy is needed.
Consequence: every runner needs github.com reachable at install time
(Routine environments included) and installs are not cached across tag bumps.

## D4 - `firstSeen` fails open (2026-11-27)

A dropped real command is worse than a duplicate reply. If KV errors or the
update has no `update_id`, the update is processed. Dedup is best-effort, not
exactly-once.

## D5 - Compatibility shims over call-site rewrites (2026-11-27)

`automation-framework/scripts/notify_telegram.py` and the Worker's
`sendMessage`/`answerCallbackQuery`/`editMessage*` helpers keep their old
signatures and delegate to the kit. The production bot has ~1500 lines; touching
every call site adds risk for no gain. New code should call the kit directly.

## D6 - Parity-first migration of production code (2026-11-27)

Before changing the booking Worker, handler-level tests were written against the
old code and had to pass unchanged on the new code (17 tests), then new
behaviour (dedup) got its own tests. Use this pattern for any migration of a
production surface.

## D7 - `investment-framework` is private; merge is a direct squash (2026-11-25/26)

The repo exposed a broker account id and holdings. Auto-merge was removed from
all commands and Routine prompts because it is unavailable on free private
repos; Routines now squash-merge directly. Recorded in that repo's `decisions/`.

## D8 - Branch protection is not relied on (2026-11-24)

Unavailable on free private repos (HTTP 403). Safety comes from process: `claude/*`
branches, PRs, merge only on the owner's yes, CI, fine-grained tokens,
single-use callbacks (when built).

## D9 - Bot topology is per-domain today; grouping is a gateway concern (2026-11-24, refined 2026-11-27)

Bots are separate per domain and stay so until a gateway exists. The owner's
stated goal is flexible grouping (one bot for a batch of projects, or one bot per
project). That is a configuration problem solved by a gateway with a routing
table, not by sharing tokens between repos. See design.md section 2.

## D10 - Global vs project Claude assets are layered (2026-11-27)

Rules that are true everywhere (GitHub workflow, secret handling, "never invent
data", no broker orders) live in `platform` and reach repos through a plugin or
an import, never copy-paste. Domain behaviour (how investment actions are
decided) stays in the domain repo's `CLAUDE.md`/`.claude/`. See design.md
section 3. **Not built yet.**

## D11 - No MCP server for now (2026-11-24)

No custom MCP server exists in any repo and nothing needs one. Add only when a
concrete need appears.

## D12 - Booking dispatch suspension is intentional

The booking Worker's automatic dispatch of new bookings was suspended on
2026-10-23 by the owner (commit 4d6d4ce in `automation-framework`). Do not
re-enable without the owner's explicit request; reminders, auto-cancel and the
digest keep running.

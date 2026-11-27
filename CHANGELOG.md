# Changelog

Three independent tag streams (see docs/decisions.md D1):
`v*` workflows and `claude-global`, `telegram-kit-v*`, `py-v*`.
A PR that changes a released path must add a line under **Unreleased** (CI
checks this; see `scripts/check_changelog.py`). On release, move the lines to a
dated heading named after the tag.

## Unreleased

- Add CHANGELOG and a CI check that released paths come with a changelog line.

## py-v0.2.0 - 2026-11-27 (stream `py-v*`)

- Add `send_document` (multipart) and a CLI
  `python -m platform_notify message|document|get-me` to replace curl snippets.

## v0.2.0 - 2026-11-27 (stream `v*`)

- Add `claude-global/`: rules (github-workflow, secrets, no-broker-orders,
  cite-sources), `platform-guard.py` PreToolUse hook, `settings.fragment.json`,
  `sync.py` (render into a consumer, `--check` for drift).
- Add reusable workflow `check-claude-sync.yml`.

## v0.1.0 - 2026-11-26 (stream `v*`)

- Reusable workflows `test-py.yml`, `test-node.yml`, `deploy-worker.yml`.

## telegram-kit-v0.1.0 - 2026-11-27 (stream `telegram-kit-v*`)

- First release: `verifyWebhook` (constant-time), `firstSeen` dedup, send/edit
  helpers, allowlist, `sign`/`verifySignature`.

## py-v0.1.0 - 2026-11-27 (stream `py-v*`)

- First release: stdlib-only `platform_notify` (`send_message`, `get_me`).

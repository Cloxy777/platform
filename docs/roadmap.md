# Roadmap and status

As of 2026-11-27. Original plan phases are R0-R9; this file is the live version.
Domain-specific and private housekeeping is tracked in the private repos, not
here.

## Done

| Item | What | Where |
|---|---|---|
| R0a | Investment repo made private; auto-merge replaced by direct squash merge | investment-framework |
| R0b | Leaked bot tokens revoked (old-token 401 check still to confirm) | all |
| R0c | `__pycache__` untracked in carry repo; abandoned public repo made private | carry, game-scripts |
| R0e | Cloudflare cron dispatch of workflows already existed (Sept); booking dispatch then deliberately suspended | automation-framework |
| R1 | CI runs tests on PRs in all three active repos | investment, automation, carry |
| R2 | Public `platform` with reusable `test-py`, `test-node`, `deploy-worker` (`v0.1.0`); private-repo pilot works | platform |
| R3 | `telegram-kit` (JS, vendored into the booking Worker) and `platform_notify` (Py) extracted and adopted: Worker has constant-time secret check and update_id dedup; Python senders in 3 repos | platform + consumers |
| - | Daily healthcheck Routine environment fixed (dependencies install into both interpreters) and passing | investment (claude.ai env) |
| - | This documentation | platform/docs |

## Not done (priority order)

### P1 - finish the foundation (small, valuable)

1. **Install the Renovate GitHub app** on `platform` consumers so tag bumps
   (workflows, pip pin) arrive as PRs. Acceptance: a test bump PR appears.
2. DONE (PR in review): `CHANGELOG.md` plus `scripts/check_changelog.py`, run in
   CI on pull requests (fails if a released path changed without a changelog line).
3. DONE 2026-11-27 (automation #116, manual deploy run green). **Use `deploy-worker.yml`** from `automation-framework` in place of its own
   `deploy-webhook.yml` (proves the third reusable workflow). Acceptance: deploy
   runs via the reusable workflow; same result.
4. Repo side DONE: `py-v0.2.0` adds `send_document` + CLI; investment snippets replaced (#1001). Owner steps left: re-paste Routine prompts, refresh the Routine environment, verify one real send. **Replace the remaining curl-based Telegram sends** in Routine prompts and
   slash commands with a repo script using `platform_notify` (still re-pasting
   prompts in claude.ai). Acceptance: no raw `curl ...sendMessage` left.
5. DONE: `py-v0.3.0` adds `platform_notify.health` + `get_chat`; carry (ua-carry-trade #60) and investment (#1002) healthchecks migrated parity-first (existing tests unchanged). Each repo keeps its own probes; shared: result model, rendering, exit code, `silent_when_ok` policy, Telegram probe.

### P2 - the original goal: global vs local Claude assets (design section 3)

6. DONE (docs read 2026-11-27, live tests T1 and T3 passed): plugin schema and
   Routine/cloud support verified in design 3.3. Result: plugins cannot ship
   always-on rules and repo-declared marketplaces do not load in cloud, so
   the generated-files fallback becomes the primary mechanism.
7. DONE in PR (T1, T3 passed; T2, T4 skipped as moot): `claude-global/` with
   rules, guard hook, settings fragment, `sync.py`, 49 tests, and
   `check-claude-sync.yml` (architecture 3.4, decisions D13). Not tagged yet.
8. Pilot DONE 2026-11-27: `v0.2.0` tagged, synced into `ua-carry-trade` (#59),
   Routine confirmed rules in context and hook firing. Rolled out to
   `investment-framework` (#999; Routine 7 run showed no guard blocks) and
   `automation-framework` (#115). The four life-* repos are synced too
   (life-sport #14, life-health #1, life-car #3, life-context #1). Remaining:
   dormant repos only. Slimming each repo's `CLAUDE.md` to domain-only is optional
   and left to the owner.

### P3 - the original goal: flexible bots and integrations (design section 2, 4)

9. DONE (`telegram-kit-v0.2.0`): `docs/contract.md` + `packages/telegram-kit/src/registry.js` validators with tests.
10. DONE: `Cloxy777/template-domain` (private GitHub template repo): Worker skeleton with `/manifest`, `/report`, `/command`, `/action`, vendored `registry.js` (telegram-kit-v0.2.0), contract tests, CI via `test-node` and `check-claude-sync` at v0.2.0, manual `deploy` workflow, `CLAUDE.md` stub. Initial commit went straight to `main` (empty repo); later changes via PR.
11. PARTIAL: `Cloxy777/life-gateway` (private) core built (PR #1 open): multi-bot `/bot/<name>`, registry from `REGISTRY` secret, ACL, command allowlist, signed single-use owner-only confirms, digest cron, 17 offline tests. Service-binding transport only. Pilot domain built: `ua-carry-trade/worker` (PR #63; read-only, dates only, Python parity via golden file). Left: owner config (secrets, KV, bindings, `setWebhook`, deploy both Workers), run the pilot for a week next to the Actions reminder, `https` transport if needed.
12. PARTIAL: `invest-bot` built in `investment-framework/worker` (PR #1004): owner-only via registry ACL, privacy minimal, aggregates only (sync age, stale-score count, next routine dates, open PR/issue counts) from a bundled `status.json` (owner chose a bundle over a runtime GitHub token). Confirm-flow action built (investment #1005, PR open): `/refresh` dispatches `status-refresh.yml` (regenerate status.json + deploy); disabled without Worker secret `DISPATCH_TOKEN` (owner creates a fine-grained token, Actions:write on that repo only). Routines cannot be fired with a GitHub token, so a workflow is the only dispatchable target. Left: owner token and secrets, deploy and gateway config.
13. DONE in code (PRs open until merged): status-only domains for health (life-health #2, privacy minimal), car (life-car #4) and sport (life-sport #15), each with a linted `worker/status.json` (D15) and a pinned read-only `context/` mirror of life-context (D14; `context-sync`, `check-context-sync.yml`, `v0.3.0`; `telegram-kit-v0.3.0`). Owner left: deploy, registry/bindings, and updating each `status.json` when records change (rules added to AGENTS/CLAUDE). `life-context` itself is unchanged (still the canonical store; local sessions only).
14. DONE in code (PR open): `routines/routine_drift.py` drift check (design 4.2) and the registry template `docs/integration-registry.md` (4.1). Owner left: create the private registry from the template; run `snapshot` in investment-framework and commit `routines/`; run `check` after each Routine edit in claude.ai.

### P4 - later / optional

15. NOT STARTED, no concrete need: remote MCP server on a Worker. Revisit if a Routine or session needs a tool that a domain Worker already exposes.
16. NOT STARTED, trigger not met: npm publish of the JS kit (D2). Every JS consumer (carry, invest, template-domain, life-gateway, three status domains) vendors one file with a header test; revisit if re-copying becomes painful or a consumer outside these repos appears.
17. DONE in PRs (trading-framework #49, career-hub #8): `claude-global` v0.2.0 synced and `claude-sync` CI added. Remaining dormant: `game-scripts`.

## Risks to watch

- Every Python consumer now depends on github.com being reachable at install
  time. A failed install breaks the job (including Routines). Pin tags; keep
  `platform_notify` stdlib-only.
- The vendored JS kit can drift from the tagged source; the header test only
  catches a missing header, the byte check needs a sibling checkout.
- Free-plan limits (Actions minutes, Workers cron count, KV writes) unverified;
  check before the gateway adds cron/KV load.
- Advisory rules do not enforce anything; the must-never rules need hooks.

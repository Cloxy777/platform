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
2. **Release hygiene**: add a `CHANGELOG.md` and a release checklist test (CI
   fails if a tag-worthy path changed without a version note).
3. **Use `deploy-worker.yml`** from `automation-framework` in place of its own
   `deploy-webhook.yml` (proves the third reusable workflow). Acceptance: deploy
   runs via the reusable workflow; same result.
4. **Replace the remaining curl-based Telegram sends** in Routine prompts and
   slash commands with a repo script using `platform_notify` (still re-pasting
   prompts in claude.ai). Acceptance: no raw `curl ...sendMessage` left.
5. **Unify the two healthchecks** (design 4.3).

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

9. Write `docs/contract.md` (domain contract) and the registry schema as code
   with validation tests.
10. `template-domain` as a separate GitHub *template* repo (Worker skeleton,
    `/manifest`, CI via the reusable workflows, `CLAUDE.md` stub).
11. `life-gateway` Worker: multi-bot at `/bot/<name>`, per-domain ACL, registry
    from private config, one cron fan-out digest. Pilot domain: the carry
    reminders (keep the Actions reminder running in parallel for a week).
12. `invest-bot` Worker: owner-only, status and read-only reports, confirm flow
    for non-broker actions. Aggregates only, no account ids or positions.
13. Roll domains out: health (status-only schema with a lint test), sport, car;
    resolve `life-context` (sibling-path reads do not work in cloud sessions).
14. Integration registry and Routine-definitions-in-git drift check (design 4.1-4.2).

### P4 - later / optional

15. Remote MCP server on a Worker (only if a concrete need appears).
16. Publish the JS kit to npm if more JS consumers appear (decision D2).
17. Normalise dormant repos (`trading-framework`, `career-hub`).

## Risks to watch

- Every Python consumer now depends on github.com being reachable at install
  time. A failed install breaks the job (including Routines). Pin tags; keep
  `platform_notify` stdlib-only.
- The vendored JS kit can drift from the tagged source; the header test only
  catches a missing header, the byte check needs a sibling checkout.
- Free-plan limits (Actions minutes, Workers cron count, KV writes) unverified;
  check before the gateway adds cron/KV load.
- Advisory rules do not enforce anything; the must-never rules need hooks.

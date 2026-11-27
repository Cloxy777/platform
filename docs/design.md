# Design for what is NOT built yet

Everything here is a design, not running code. Items marked [unverified] rely on
a product behaviour that must be checked against current docs before building.
Status of the build is in [roadmap.md](roadmap.md).

The owner's goals this serves:
1. Manage integrations (Telegram, Cloudflare, GitHub, claude.ai Routines)
   in one common way, available to every project.
2. Have **global** Claude assets (rules, skills, agents, prompts) and **local**
   ones, with a clear split: e.g. "how we work with GitHub" is global, "how we
   decide an investment action" belongs to the investment repo only.
3. Group projects freely: one Telegram bot for a batch of projects, or one bot
   per project, by configuration.

## 1. Layering model (applies to everything)

| Layer | Lives in | Visible to | Examples |
|---|---|---|---|
| Global | `platform` repo (public, no data) | every repo, local and cloud | GitHub workflow rules, secret handling, "never invent data / cite source", "no broker orders", worktree/dep-install hooks, CI workflows, Telegram kits |
| Group | a private "group" repo or a folder in one (optional) | repos in that group | life-* record conventions, shared restrictions file |
| Project | the domain repo (`CLAUDE.md`, `.claude/`) | that repo only | investment scoring rules, booking schedules, carry-trade grace calculations |

Rule: a rule is as global as it is true. Never copy a global rule into a repo
by hand; reference or generate it so one edit updates everyone.

## 2. Telegram topology: bots, groups, domains

### 2.1 Concepts

- **Bot**: one token (secret), one webhook URL. Created in BotFather.
- **Domain**: one repo's backend capability (commands, a daily report, actions).
- **Group**: a named set of domains served by one bot.
- **ACL**: which chat ids may talk to which domain. Per domain, not per bot.

Wanted modes, all expressible as configuration:
- one bot per project: a bot whose group contains a single domain;
- one bot for a batch: a bot whose group lists several domains;
- a domain reachable from two bots: allowed (listed in two groups).

### 2.2 Gateway

One **gateway Worker** (public code in `platform`, private config) receives
webhooks for any number of bots at `/bot/<name>`, each with its own token and
webhook secret. For each update it runs the standard checks (section 2.4), then
routes to a domain.

Routing options, in order of preference:
1. Explicit namespace when a bot serves >1 domain: `/inv status`, `/carry due`.
   When it serves one domain, the namespace is implicit.
2. A per-chat default domain (`/use carry`) for chats that talk to one domain.
3. Digest aggregation: the gateway's cron calls each domain's `/report` and
   sends one combined message per bot (a domain failure shows as a warning
   line, never blocks the digest).

### 2.3 Configuration (private, never in `platform`)

The registry contains chat ids and secret references, so it lives in a private
repo or Worker secrets/KV, not here. Schema sketch (values are placeholders):

```jsonc
{
  "bots": {
    "<bot-name>": {
      "token_secret": "BOT_<NAME>_TOKEN",
      "webhook_secret": "BOT_<NAME>_WEBHOOK_SECRET",
      "domains": ["<domain-a>", "<domain-b>"]
    }
  },
  "domains": {
    "<domain-a>": {
      "transport": "service-binding | https",
      "target": "<binding-or-url>",
      "privacy": "normal | minimal",
      "acl": { "chats": ["<chat-id>"], "owners": ["<chat-id>"] }
    }
  }
}
```

Changing the topology = editing this file (and `setWebhook` for a new bot). No
code change. Existing per-domain bots can be adopted one at a time.

### 2.4 Checks on every inbound update (order matters)

1. POST only; constant-time secret header check (`verifyWebhook`). [built]
2. `update_id` dedup (`firstSeen`). [built]
3. Resolve `chat.id` and `from.id` (callbacks too) against the domain ACL;
   unknown -> silent 200. [allowlist built; per-domain ACL not]
4. Per-domain command allowlist; unknown commands ignored. [not built]
5. Callback data signed (HMAC), single-use, short TTL, bound to chat and
   action id. [`sign`/`verifySignature` built; flow not]
6. Never log message text for `privacy: "minimal"` domains; redact tokens/ids in logs. [not built]

### 2.5 Domain contract

Each domain exposes (JSON over a Worker service binding, no public URL):

```
GET  /manifest -> { name, version, commands:[{cmd, help}], privacy, schedule:[{id, cron}] }
POST /report   -> { digest:{ title, lines[], status:"ok|warn|fail", ts } }
POST /command  -> in {cmd,args,chat,from}  out {text, buttons?, proposal?:{id,summary,expires}}
POST /action   -> in {action_id,chat,from} out {text}
```
Rules: domain returns plain data (gateway escapes), every call carries
`request_id`, `privacy:"minimal"` domains return only status and counters, the
gateway enforces ACL before forwarding.

### 2.6 Confirm-before-execute (any side effect)

Command -> domain returns a `proposal` and stores it with a content hash ->
gateway renders `[Confirm][Cancel]` with signed single-use callback data ->
callback is checked (2.4), the pending action is consumed (delete on read),
the domain re-validates live state and executes idempotently with the proposal
id as key, writing an audit row -> gateway edits the message and answers the
callback. **Scope limit: no broker order placement, ever.** Allowed actions:
trigger a workflow/Routine, acknowledge, snooze.

### 2.7 Privacy rule for sensitive domains

A `privacy:"minimal"` domain (health) exposes only `ok / review due / stale`
plus counters. No values, names or document titles in Telegram, KV, D1 or logs.
Telegram chats are not end-to-end encrypted; treat them as public-ish.

### 2.8 Limits to verify [unverified]

Cloudflare free-plan cron triggers per account (believed ~5), KV writes per day
(~1000), D1 limits. A single gateway cron that fans out keeps the cron count
low. The existing booking Worker already uses one `*/5` cron.

## 3. Global and local Claude assets

### 3.1 What Claude Code can load (verify current docs) [unverified details]

- User-level files on the owner's machine (`~/.claude/CLAUDE.md`, skills,
  agents): personal, **not visible to cloud sessions or Routines**.
- Project files (`CLAUDE.md`, `.claude/commands|skills|agents|hooks|settings.json`):
  travel with the repo, so they work in cloud sessions.
- Plugins from a marketplace repo (versioned bundles of commands, skills,
  agents, hooks), enabled per repo via `.claude/settings.json`.
- Sibling-folder reads (`../other-repo/...`) work only on a local checkout, never
  in cloud sessions. Do not design anything that depends on them.

### 3.2 Recommended structure

`platform/claude-plugin/` (public, no data) holds the **global** layer:
- `rules/` (markdown): `github-workflow.md` (branches `claude/*`, PRs, merge only
  on the owner's yes, direct squash merge, commit/PR trailers, no auto-merge),
  `secrets.md`, `cite-sources-never-invent.md`, `no-broker-orders.md`,
  `glossary-output.md` (if wanted globally), `record-keeping.md`.
- `hooks/`: worktree check and dependency install (currently only in the
  investment repo), plus guard hooks that make some rules **enforced** rather
  than advisory (e.g. block `gh pr merge` without confirmation, block printing
  of env secrets).
- `skills/` and `agents/`: reusable ones only (healthcheck pattern, review
  agent). Domain skills stay in their repos.

Each repo then has:
- `.claude/settings.json` enabling the plugin at a pinned version;
- a short `CLAUDE.md` that holds **only** domain rules and says global rules come
  from the plugin.

Enforcement reality: rules in markdown are advisory. Anything that must never
happen (placing broker orders, leaking secrets, merging without consent) needs
a hook or a permission rule in the plugin's settings, plus a test.

### 3.3 Plugin and Routine support: verified 2026-11-27

Source: current Claude Code docs under https://code.claude.com/docs/en/
(`plugins/manifest-reference`, `plugins/components`, `plugins/marketplace-reference`,
`plugins/install`, `plugins/loading`, `cloud-environments`, `settings`,
`permissions`, `hooks`, `routines`). Read by a docs-check agent, not yet proven
by a live test. Items marked [test] need an empirical check before we rely on them.

**Schema (documented)**
- `.claude-plugin/plugin.json`: only `name` required. Components by default
  location: `skills/<n>/SKILL.md`, `commands/`, `agents/`, `hooks/hooks.json`,
  `.mcp.json`, `bin/`, output styles, workflows.
- `.claude-plugin/marketplace.json`: `name`, `owner.name`, `plugins[]`; each entry
  needs `name` and `source`. Sources: relative path, `github`, `url`, `git-subdir`,
  `npm`, `archive`, `command`. Pin with `ref` (tag/branch) and `sha` (40 chars).
- Repo enables a plugin in committed `.claude/settings.json`:
  `extraKnownMarketplaces: {<mkt>: {source: {source: "github", repo: "<owner>/<repo>"}}}`
  and `enabledPlugins: {"<plugin>@<mkt>": true}`.
- A marketplace in a repo subfolder needs a `path` in the marketplace source
  (unverified for relative plugin sources) [test].

**Consequences for our design**
1. **A plugin cannot ship always-on rules.** There is no rules component, and a
   `CLAUDE.md` at the plugin root is not loaded (validate warns). Rules in a
   plugin only load as skills (on demand, by description match) or via a hook
   that injects context. The "plugin with a `rules/` dir" in 3.2 does not work as
   drawn. Advisory rules must reach each repo as repo files.
2. **Cloud sessions do not add repo-declared marketplaces** in Anthropic-hosted
   environments (needs the trust dialog, which cloud does not show). Plugins
   enabled only in repo settings are therefore not expected to load there. The
   documented route is plugins synced from the owner's claude.ai account.
3. **Routines: undocumented, but see T1 (committed rules and hooks work).** The docs say a run clones the selected repos and
   starts in auto mode; they do not say whether plugins, skills, hooks,
   `.claude/settings.json` or `CLAUDE.md` load. Cloud-session rules suggest
   `CLAUDE.md`, `.claude/agents`, committed `.claude/settings.json` (project
   hooks, deny/ask rules) are present, plugins are not [test].
4. **Hooks and deny rules**: `PreToolUse` can deny (JSON `permissionDecision:
   "deny"` or exit 2) and a deny stays a deny even if another hook allows.
   Hook events fire in cloud sessions. Project `deny` and `ask` permission rules
   apply without trust. Plugins have no documented way to ship permission rules.
   Timeouts fail open unless `onFailure: "block"` (v2.1.295+).
   Hook execution inside a Routine is not documented [test].

**Decision (proposed, see decisions.md when accepted)**
Do not depend on plugin loading for anything that must hold in cloud or
Routines. Use the fallback below as the primary mechanism:

- `platform` holds the single source: `rules/*.md`, `hooks/*` (scripts), and
  `settings.fragment.json` (deny/ask rules and hook wiring).
- A release workflow in `platform` renders them into each consumer as committed
  files: `.claude/rules/platform-<name>.md` (header "GENERATED from
  platform@<tag>, do not edit"), `.claude/hooks/platform-*`, and a merged block in
  `.claude/settings.json`; it opens a PR per consumer. The consumer `CLAUDE.md`
  imports the rules (`@.claude/rules/platform-*.md`) [test import syntax] and
  keeps only domain rules.
- Committed files travel with the clone, so they work locally, in cloud sessions
  and (per test) in Routines. Hooks and deny rules there are the enforcement for
  the must-never list (no broker orders, no secret printing, no merge without yes).
- A real plugin stays optional, for local interactive use only (skills such as
  the review agent), installed per machine. It is never a dependency.

**Tests to run before building (P2 step 7)**
- T1: **PASSED 2026-11-27.** A Routine on a throwaway private repo saw the
  committed `CLAUDE.md` rule in context, and a committed `.claude/settings.json`
  `PreToolUse` hook (python script) blocked a matching Bash call while a
  non-matching call ran. Repo-provided skills/plugins: none listed. So committed
  rules and hooks work in Routines. Notes: a Routine run needs an environment
  without a repo-specific setup script; the claude.ai UI attaches ALL account
  connectors to a new task by default (IBKR included), so clear them via API
  (`clear_mcp_connections`). Original test text: in a throwaway private repo, commit a `PreToolUse` deny hook and a
  `CLAUDE.md` rule; run a Routine on it; confirm the rule is in context and the
  hook blocks. (Creates a test Routine: needs the owner's yes.)
- T2: same repo in a cloud session with a repo-declared marketplace: confirm
  the plugin does not load.
- T3: `@` import of a generated rules file from `CLAUDE.md` in cloud.
- T4: marketplace in a subfolder with relative plugin source.

### 3.4 System prompts

Long operating briefs (like the investment operating brief) are project assets.
Shared fragments (output conventions, citation discipline) move to the plugin
rules and are referenced, not pasted. Routine prompts are not in git today;
see 4.2.

## 4. Integrations managed in one way

### 4.1 Registry (private)

One private document/repo lists every integration instance: Telegram bots,
Cloudflare Workers/KV/crons, GitHub fine-grained tokens, claude.ai connectors and
Routines. Columns: name, owner repo, where each secret lives (Worker secret,
Actions secret, Routine env), rotation steps (see operations.md), healthcheck
that covers it. Secret **values** are never recorded.

### 4.2 Routine definitions in git

Routine prompts live in claude.ai, outside git, so they drift from the docs.
Proposal: store each Routine's prompt, schedule, environment id and connector
list as a file in its repo, and add a read-only check (via the Routines API) that
compares live definitions with the files and reports drift. Updates still go
through the API on the owner's yes.

### 4.3 One healthcheck contract

Two healthchecks exist with opposite semantics (one silent when OK, one sends
"OK" daily). Unify: one `platform_notify`-based probe library, one output
format, one policy knob (`silent_when_ok`), reused by every repo's check.

## 5. Security items still open (from the original audit)

- Connector scope: Routine environments expose broker order-creating tools
  (verified 2026-11-27). Restrict the connector to read-only tools; this is a
  claude.ai setting.
- The booking Worker's GitHub token has Contents:read and Actions:write; reduce
  to Actions:write once history is served from KV/D1.
- Bot token duplicated in Worker secret and Actions secret (two rotation points);
  route outbound sends through the Worker's `POST /send` so the token lives once.
- Chat allowlist is in `wrangler.toml [vars]` (committed). Move to a secret or
  KV when the gateway lands.

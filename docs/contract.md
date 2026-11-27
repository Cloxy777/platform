# Domain contract and gateway registry

Normative spec for P3. Rationale and options live in `design.md` section 2; this
file is what a domain or the gateway must implement. Validators:
`packages/telegram-kit/src/registry.js` (import `@cloxy777/telegram-kit/registry`),
tests in `packages/telegram-kit/test/registry.test.js`. This repo holds only the
schema and code: **registry values (chat ids, secret names in use) stay private**.

## 1. Registry (private config)

```jsonc
{
  "bots": {
    "<bot-name>": {
      "token_secret": "BOT_<NAME>_TOKEN",          // name of a Worker secret, never a value
      "webhook_secret": "BOT_<NAME>_WEBHOOK_SECRET",
      "domains": ["<domain>", "..."]                 // one entry = one bot per project
    }
  },
  "domains": {
    "<domain>": {
      "transport": "service-binding | https",
      "target": "<binding name | https URL>",
      "privacy": "normal | minimal",                 // default normal
      "acl": { "chats": ["<chat-id>"], "owners": ["<chat-id>"] }   // owners subset of chats
    }
  }
}
```

`validateRegistry(reg)` returns a list of errors (empty = valid). It enforces:

- names match `^[a-z][a-z0-9-]{0,31}$`; secret refs are `UPPER_SNAKE` names (a pasted
  token fails), unique across all bots;
- every `bots.*.domains` entry exists; every domain is served by at least one bot
  (a domain may be in several bots);
- `acl.chats` non-empty; `owners` must be listed in `chats`;
- `https` transport needs an `https://` target.

Run it in the private config repo's CI and in the gateway at startup (fail closed).
Topology change = edit the file, redeploy, `setWebhook` for a new bot.

## 2. Domain endpoints

JSON over a Worker service binding (no public URL) or authenticated https. Every call
carries a `request_id`. Domains return plain data; the gateway escapes it.

| Call | Request | Response | Validator |
|---|---|---|---|
| `GET /manifest` | - | `{name, version, privacy, commands:[{cmd, help}], schedule:[{id, cron}]}` | `validateManifest` |
| `POST /report` | `{request_id}` | `{digest:{title, lines[], status:"ok\|warn\|fail", ts}}` | `validateReport(r, {privacy})` |
| `POST /command` | `{request_id, cmd, args, chat, from}` | `{text, buttons?, proposal?:{id, summary, expires}}` | `validateCommandResult` |
| `POST /action` | `{request_id, action_id, chat, from}` | `{text}` | - |

Rules:

- `manifest.name` must equal the registry domain name; commands match
  `^[a-z][a-z0-9_]{0,31}$` and are the only ones the gateway forwards (allowlist).
- Cron expressions are 5-field; the gateway runs one cron and fans out, domains do not
  own crons for digests.
- A `/report` failure shows as a warning line in the digest and never blocks it.
- `privacy: "minimal"`: report lines must be `<label>: ok|review due|stale|<count>`
  (lowercase label, no values, names or titles). Nothing from such a domain is logged
  or stored in KV/D1.
- Side effects (design 2.6): `/command` returns a `proposal` (id, summary, ISO
  `expires`); execution happens only through `/action` after a signed single-use
  confirm callback, idempotent on the proposal id, with an audit row.
- **No broker order placement, modification or cancellation by any domain.** Allowed
  actions: trigger a workflow or Routine, acknowledge, snooze.

## 3. Gateway checks (summary, order matters)

Webhook secret -> `update_id` dedup -> ACL by `chat.id` and `from.id` (callbacks too;
unknown = silent 200) -> command allowlist -> signed callback data -> no text logging
for `minimal` domains. Built today in the kit: secret check, dedup, allowlist, HMAC
sign/verify. Not yet built: per-domain ACL, command allowlist, confirm flow, log
redaction (P3 steps 11 and 12).

## 4. Versioning

Changing a field or a rule here is a kit change: add an Unreleased line, tag
`telegram-kit-v*`, and note it in `architecture.md`. Additive fields are minor; a
removed or stricter field is a major bump and needs a decision in `decisions.md`.

# platform

Shared, domain-neutral building blocks for personal automation repos. Contains no personal data and no secrets.

## Reusable workflows

Call from any repo (public or private):

| Workflow | Purpose |
|---|---|
| `test-py.yml` | Run pytest (inputs: `python-version`, `test-path`, `requirements-file`, `working-directory`) |
| `test-node.yml` | `npm ci` + `npm test` |
| `deploy-worker.yml` | `wrangler deploy` (secret: `CLOUDFLARE_API_TOKEN`) |

```yaml
jobs:
  test:
    uses: Cloxy777/platform/.github/workflows/test-py.yml@v0.1.0
    with:
      test-path: tests
```

Pin to a tag. Renovate (see `renovate.json` in consumers) bumps the tag.

## Packages

| Path | What |
|---|---|
| `packages/telegram-kit` | JS, zero deps. `verifyWebhook` (constant time), `parseAllowlist`/`isAllowed`, `parseCommand`, `firstSeen` (update_id dedup in KV), `sign`/`verifySignature` (HMAC callback tokens), `createClient` (`send`, `answerCallback`, `editText`, `editMarkup`) |
| `py/platform_notify` | Python stdlib only. `send_message`, `get_me`. Errors never contain the token |

Consume by tag, e.g. `github:Cloxy777/platform#telegram-kit-v0.1.0` (JS) or
`pip install "git+https://github.com/Cloxy777/platform@py-v0.1.0#subdirectory=py"`.

## Planned

`packages/worker-kit`, `claude-plugin/`.

## Rules

- No personal data, ids, tokens or chat ids in this repo. Ever.
- No tool here may place, modify or cancel broker orders.

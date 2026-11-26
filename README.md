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

## Planned

`packages/telegram-kit`, `packages/worker-kit`, `py/platform_notify`, `claude-plugin/`. See `docs/`.

## Rules

- No personal data, ids, tokens or chat ids in this repo. Ever.
- No tool here may place, modify or cancel broker orders.

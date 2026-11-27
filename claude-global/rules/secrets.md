# Secrets (global)

- Never print, echo, log, commit or paste a secret value: tokens, API keys,
  passwords, webhook secrets, chat ids tied to a person, account numbers.
- To check a secret exists, test that it is set (`[ -n "$VAR" ]`) or call the
  service and report only the status code. Do not dump the environment or read
  `.env` files.
- Error messages, test output, commit messages and PR text must not contain a
  secret. Tests must run offline with fake values.
- If you see a secret in a file, log or screenshot, tell the owner to rotate it.
  Do not reuse it.
- Do not create tokens, accounts or keys yourself; ask the owner.

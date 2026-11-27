# GitHub workflow (global)

- Work on a `claude/<topic>` branch. Never commit to `main` directly.
- Every change goes through a pull request. Report the PR link and CI status.
- Merge only after the owner says yes in chat for that specific PR. One yes
  covers one PR, not later ones. Use `gh pr merge <n> --squash --delete-branch`.
- Never use `--auto` or `--admin` merge, never force-push, never `--no-verify`.
- Never delete a repo, branch or tag, change repo visibility, or create an
  account or token without an explicit ask in chat.
- End commit messages with the `Co-Authored-By` line and PR bodies with the
  Claude Code line, exactly as configured for the session.
- Update the docs in the same PR whenever a change affects other repos.

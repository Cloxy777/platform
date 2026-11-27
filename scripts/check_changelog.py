"""Fail when a PR changes a released path without touching CHANGELOG.md.

    python scripts/check_changelog.py <base-ref>

Compares `git diff --name-only <base-ref>...HEAD`. Tests, docs and this script
do not need a changelog line. Stdlib only.
"""
import subprocess
import sys

# (stream, path prefixes that ship in a release)
STREAMS = [
    ("v*", (".github/workflows/test-py.yml", ".github/workflows/test-node.yml",
            ".github/workflows/deploy-worker.yml", ".github/workflows/check-claude-sync.yml",
            "claude-global/rules/", "claude-global/hooks/", "claude-global/settings.fragment.json",
            "claude-global/sync.py")),
    ("telegram-kit-v*", ("packages/telegram-kit/src/",)),
    ("py-v*", ("py/platform_notify/", "py/pyproject.toml")),
]
CHANGELOG = "CHANGELOG.md"


def released_streams(changed):
    """Return the sorted tag streams whose released paths appear in `changed`."""
    hit = set()
    for stream, prefixes in STREAMS:
        if any(f.startswith(p) for f in changed for p in prefixes):
            hit.add(stream)
    return sorted(hit)


def check(changed):
    """Return an error string, or None when the change set is fine."""
    streams = released_streams(changed)
    if streams and CHANGELOG not in changed:
        return ("released paths changed (%s) but %s was not updated: add a line under Unreleased"
                % (", ".join(streams), CHANGELOG))
    return None


def main(argv):
    if len(argv) != 2:
        print(__doc__)
        return 2
    out = subprocess.run(["git", "diff", "--name-only", argv[1] + "...HEAD"],
                         capture_output=True, text=True, check=True).stdout
    err = check([line.strip() for line in out.splitlines() if line.strip()])
    if err:
        print("ERROR: " + err, file=sys.stderr)
        return 1
    print("changelog ok")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

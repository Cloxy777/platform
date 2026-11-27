#!/usr/bin/env python3
"""Mirror selected life-context files into a consumer repo as read-only context/.

Cloud sessions (Routines) check out one repo only, so sibling-folder reads such as
../life-context/restrictions.md do not work there. This copies the files a repo needs
into `context/`, pins the source commit and records content hashes in
`context/MANIFEST.json`. Canonical edits still happen in life-context; re-run this
after changing it.

    python context-sync/sync.py --source ../life-context --files restrictions.md conventions.md .
    python context-sync/sync.py --check .                      # CI: mirror untouched by hand
    python context-sync/sync.py --check --source ../life-context .   # local: also up to date

Exit codes: 0 ok, 1 drift or error. Stdlib only. No file content is printed.
"""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

DIR = "context"
MANIFEST = "MANIFEST.json"
BANNER = ("<!-- MIRROR of life-context/{name} @ {sha}. Read-only: edit it in life-context "
          "and re-run platform context-sync/sync.py. -->\n\n")


def sha256(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def source_commit(source, allow_dirty=False):
    def git(*a):
        return subprocess.run(["git", "-C", str(source), *a], capture_output=True, text=True)
    head = git("rev-parse", "HEAD")
    if head.returncode != 0:
        raise SystemExit("ERROR: --source is not a git checkout")
    if not allow_dirty and git("status", "--porcelain").stdout.strip():
        raise SystemExit("ERROR: source has uncommitted changes (commit first, or --allow-dirty)")
    return head.stdout.strip()


def render(name, content, sha):
    return BANNER.format(name=name, sha=sha[:12]) + content


def sync(source, target, files, allow_dirty=False):
    sha = source_commit(source, allow_dirty)
    out = Path(target) / DIR
    out.mkdir(parents=True, exist_ok=True)
    hashes = {}
    for name in files:
        src = Path(source) / name
        if not src.is_file():
            raise SystemExit(f"ERROR: {name} not found in source")
        text = render(name, src.read_text(encoding="utf-8"), sha)
        (out / name).write_text(text, encoding="utf-8", newline="\n")
        hashes[name] = sha256(text)
    (out / MANIFEST).write_text(json.dumps({"source_commit": sha, "files": hashes}, indent=1, sort_keys=True) + "\n",
                                encoding="utf-8", newline="\n")
    return sha


def check(target, source=None):
    """Return a list of problems (empty = ok). Never includes file content."""
    mpath = Path(target) / DIR / MANIFEST
    if not mpath.is_file():
        return [f"{DIR}/{MANIFEST} missing: run context-sync/sync.py"]
    m = json.loads(mpath.read_text(encoding="utf-8"))
    problems = []
    for name, want in sorted(m["files"].items()):
        p = Path(target) / DIR / name
        if not p.is_file():
            problems.append(f"{DIR}/{name} missing")
        elif sha256(p.read_text(encoding="utf-8")) != want:
            problems.append(f"{DIR}/{name} was edited by hand (does not match MANIFEST.json)")
    extra = {p.name for p in (Path(target) / DIR).glob("*.md")} - set(m["files"])
    problems += [f"{DIR}/{n} is not in MANIFEST.json" for n in sorted(extra)]
    if source is not None:
        head = source_commit(source, allow_dirty=True)
        if head != m["source_commit"]:
            problems.append("mirror is behind life-context: re-run context-sync/sync.py")
        else:
            for name in m["files"]:
                if render(name, (Path(source) / name).read_text(encoding="utf-8"), head) != (Path(target) / DIR / name).read_text(encoding="utf-8"):
                    problems.append(f"{DIR}/{name} differs from the source at the pinned commit")
    return problems


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("target")
    ap.add_argument("--source")
    ap.add_argument("--files", nargs="+")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--allow-dirty", action="store_true")
    a = ap.parse_args(argv)
    if a.check:
        problems = check(a.target, a.source)
        for p in problems:
            print(f"DRIFT: {p}")
        return 1 if problems else 0
    if not (a.source and a.files):
        ap.error("--source and --files are required to sync")
    sha = sync(a.source, a.target, a.files, a.allow_dirty)
    print(f"mirrored {len(a.files)} file(s) from life-context@{sha[:12]} into {a.target}/{DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

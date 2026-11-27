#!/usr/bin/env python3
"""Keep Routine definitions in git and report drift against the live account.

Routines live in claude.ai. A session lists them with the RemoteTrigger tool
(action `list`); save that JSON to a file and feed it here. This script never
touches the network, and prompts are never printed (only a sha256 prefix).

    python routines/routine_drift.py snapshot live.json routines/ --id trig_... --id trig_...
    python routines/routine_drift.py check live.json routines/ --ignore trig_...   # exit 1 on drift

Layout of the definitions directory (kept in the repo that owns the Routines):
    routines.json         {"routines": [{id, name, cron, enabled, environment_id, repos, connectors, prompt_file}]}
    prompts/<slug>.md     the prompt text

Updating a live Routine stays a manual, owner-approved API call; this only reports.
Stdlib only.
"""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

MANIFEST = "routines.json"
FIELDS = ("name", "cron", "enabled", "environment_id", "repos", "connectors")


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def slug(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:48] or "routine"


def normalize(trigger):
    """Live API object -> (comparable dict, prompt)."""
    ccr = trigger.get("job_config", {}).get("ccr", {})
    ctx = ccr.get("session_context", {})
    repos = sorted(
        s["git_repository"]["url"].rstrip("/").removeprefix("https://github.com/")
        for s in ctx.get("sources", []) if "git_repository" in s)
    meta = {
        "id": trigger["id"],
        "name": trigger.get("name") or "",
        "cron": trigger.get("cron_expression") or "",
        "enabled": bool(trigger.get("enabled")),
        "environment_id": ccr.get("environment_id") or "",
        "repos": repos,
        "connectors": sorted(m.get("name", "") for m in trigger.get("mcp_connections") or []),
    }
    return meta, trigger.get("derived_state", {}).get("prompt", "")


def load_live(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    items = data["data"] if isinstance(data, dict) else data
    return {t["id"]: normalize(t) for t in items}


def snapshot(live_path, outdir, ids):
    live = load_live(live_path)
    out = Path(outdir)
    (out / "prompts").mkdir(parents=True, exist_ok=True)
    rows = []
    for i in ids:
        if i not in live:
            raise SystemExit(f"ERROR: {i} not in live list")
        meta, prompt = live[i]
        fname = f"prompts/{slug(meta['name'])}.md"
        (out / fname).write_text(prompt, encoding="utf-8", newline="\n")
        rows.append({**meta, "prompt_file": fname})
    (out / MANIFEST).write_text(json.dumps({"routines": rows}, indent=2, ensure_ascii=False) + "\n",
                                encoding="utf-8", newline="\n")
    return len(rows)


def check(live_path, outdir, ignore=()):
    """Return drift lines (empty = in sync). Never includes prompt text."""
    live = load_live(live_path)
    out = Path(outdir)
    mpath = out / MANIFEST
    if not mpath.is_file():
        return [f"{MANIFEST} missing: run snapshot"]
    rows = json.loads(mpath.read_text(encoding="utf-8"))["routines"]
    problems, tracked = [], set()
    for row in rows:
        rid = row["id"]
        tracked.add(rid)
        label = f"{rid[:14]} ({slug(row['name'])})"
        if rid not in live:
            problems.append(f"{label}: defined in git but missing live")
            continue
        meta, prompt = live[rid]
        for f in FIELDS:
            if meta[f] != row.get(f):
                problems.append(f"{label}: {f} differs (git vs live)")
        p = out / row["prompt_file"]
        if not p.is_file():
            problems.append(f"{label}: prompt file missing")
        else:
            git_hash = sha(p.read_text(encoding="utf-8"))
            if git_hash != sha(prompt):
                problems.append(f"{label}: prompt differs (git {git_hash[:8]} vs live {sha(prompt)[:8]})")
    for rid, (meta, _) in sorted(live.items()):
        if rid not in tracked and rid not in ignore:
            problems.append(f"{rid[:14]} ({slug(meta['name'])}): live but not in git")
    return problems


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("snapshot")
    s.add_argument("live")
    s.add_argument("outdir")
    s.add_argument("--id", action="append", required=True)
    c = sub.add_parser("check")
    c.add_argument("live")
    c.add_argument("outdir")
    c.add_argument("--ignore", action="append", default=[], help="live id to skip (another repo's Routine)")
    a = ap.parse_args(argv)
    if a.cmd == "snapshot":
        print(f"wrote {snapshot(a.live, a.outdir, a.id)} routine definition(s) to {a.outdir}")
        return 0
    problems = check(a.live, a.outdir, set(a.ignore))
    for p in problems:
        print(f"DRIFT: {p}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())

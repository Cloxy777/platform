import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import sync  # noqa: E402

SRC = Path(__file__).resolve().parents[1]
RULES = sorted(p.stem for p in (SRC / "rules").glob("*.md"))


def do(target, tag="v9.9.9", check=False):
    return sync.run(SRC, target, tag, check=check)


def test_fresh_repo_gets_everything(tmp_path):
    do(tmp_path)
    for r in RULES:
        text = (tmp_path / (".claude/rules/platform-%s.md" % r)).read_text(encoding="utf-8")
        assert text.startswith("<!-- GENERATED from platform@v9.9.9, do not edit")
    hook = (tmp_path / ".claude/hooks/platform-guard.py").read_text(encoding="utf-8")
    assert hook.startswith("# GENERATED")
    claude = (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")
    for r in RULES:
        assert "@.claude/rules/platform-%s.md" % r in claude
    settings = json.loads((tmp_path / ".claude/settings.json").read_text(encoding="utf-8"))
    cmd = settings["hooks"]["PreToolUse"][0]["hooks"][0]["command"]
    assert ".claude/hooks/platform-guard.py" in cmd


def test_idempotent_and_check_clean(tmp_path):
    do(tmp_path)
    assert do(tmp_path) == []
    assert do(tmp_path, check=True) == []


def test_check_reports_drift_and_changes_nothing(tmp_path):
    do(tmp_path)
    rule = tmp_path / ".claude/rules/platform-secrets.md"
    rule.write_text("edited by hand\n", encoding="utf-8")
    assert do(tmp_path, check=True) == ["write .claude/rules/platform-secrets.md"]
    assert rule.read_text(encoding="utf-8") == "edited by hand\n"
    assert sync.main([str(tmp_path), "--tag", "v9.9.9", "--check"]) == 1
    do(tmp_path)
    assert sync.main([str(tmp_path), "--tag", "v9.9.9", "--check"]) == 0


def test_tag_change_is_drift(tmp_path):
    do(tmp_path, tag="v1")
    assert do(tmp_path, tag="v2", check=True) != []


def test_consumer_content_preserved(tmp_path):
    (tmp_path / ".claude").mkdir()
    (tmp_path / "CLAUDE.md").write_text("# Mine\n\nDomain rule.\n", encoding="utf-8")
    own = {"matcher": "Bash", "hooks": [{"type": "command", "command": "python3 .claude/hooks/own.py"}]}
    start = {"permissions": {"deny": ["x"]}, "hooks": {"PreToolUse": [own], "Stop": [own]}}
    (tmp_path / ".claude/settings.json").write_text(json.dumps(start), encoding="utf-8")
    do(tmp_path)
    do(tmp_path)
    claude = (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")
    assert claude.startswith("# Mine\n\nDomain rule.\n")
    assert claude.count(sync.BEGIN) == 1
    s = json.loads((tmp_path / ".claude/settings.json").read_text(encoding="utf-8"))
    assert s["permissions"] == {"deny": ["x"]}
    pre = s["hooks"]["PreToolUse"]
    assert own in pre and sum(sync._is_managed(e) for e in pre) == 1
    assert s["hooks"]["Stop"] == [own]


def test_stale_platform_files_removed_but_not_others(tmp_path):
    do(tmp_path)
    (tmp_path / ".claude/rules/platform-old.md").write_text("x", encoding="utf-8")
    (tmp_path / ".claude/rules/mine.md").write_text("keep", encoding="utf-8")
    assert do(tmp_path) == ["remove .claude/rules/platform-old.md"]
    assert (tmp_path / ".claude/rules/mine.md").exists()


def test_crlf_in_consumer_is_not_drift(tmp_path):
    do(tmp_path)
    f = tmp_path / ".claude/rules/platform-secrets.md"
    f.write_bytes(f.read_bytes().replace(b"\n", b"\r\n"))
    assert do(tmp_path, check=True) == []

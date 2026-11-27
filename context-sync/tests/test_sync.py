import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import sync as cs  # noqa: E402


def git(repo, *a):
    subprocess.run(["git", "-C", str(repo), *a], check=True, capture_output=True)


@pytest.fixture
def src(tmp_path):
    d = tmp_path / "life-context"
    d.mkdir()
    git(d, "init", "-q", "-b", "main")
    git(d, "config", "user.email", "t@example.invalid")
    git(d, "config", "user.name", "t")
    (d / "restrictions.md").write_text("# Active Restrictions\n| a | b |\n", encoding="utf-8")
    (d / "conventions.md").write_text("# Conventions\n", encoding="utf-8")
    git(d, "add", "-A")
    git(d, "commit", "-qm", "init")
    return d


@pytest.fixture
def tgt(tmp_path):
    d = tmp_path / "consumer"
    d.mkdir()
    return d


def test_sync_then_check_clean(src, tgt):
    assert cs.main([str(tgt), "--source", str(src), "--files", "restrictions.md", "conventions.md"]) == 0
    text = (tgt / "context" / "restrictions.md").read_text(encoding="utf-8")
    assert text.startswith("<!-- MIRROR of life-context/restrictions.md @ ")
    assert "# Active Restrictions" in text
    assert cs.check(tgt) == []
    assert cs.check(tgt, src) == []


def test_hand_edit_is_drift(src, tgt):
    cs.sync(src, tgt, ["restrictions.md"])
    p = tgt / "context" / "restrictions.md"
    p.write_text(p.read_text(encoding="utf-8") + "extra\n", encoding="utf-8")
    problems = cs.check(tgt)
    assert any("edited by hand" in x for x in problems)
    assert "extra" not in "\n".join(problems)  # content is never echoed


def test_missing_manifest_and_unlisted_file(src, tgt):
    assert any("MANIFEST.json missing" in x for x in cs.check(tgt))
    cs.sync(src, tgt, ["restrictions.md"])
    (tgt / "context" / "stray.md").write_text("x", encoding="utf-8")
    assert any("not in MANIFEST" in x for x in cs.check(tgt))


def test_source_moves_on_is_reported_locally_only(src, tgt):
    cs.sync(src, tgt, ["restrictions.md"])
    (src / "restrictions.md").write_text("# changed\n", encoding="utf-8")
    git(src, "commit", "-qam", "change")
    assert cs.check(tgt) == []  # CI view: no source access, mirror untouched
    assert any("behind life-context" in x for x in cs.check(tgt, src))


def test_dirty_source_refused_unless_allowed(src, tgt):
    (src / "restrictions.md").write_text("# dirty\n", encoding="utf-8")
    with pytest.raises(SystemExit):
        cs.sync(src, tgt, ["restrictions.md"])
    cs.sync(src, tgt, ["restrictions.md"], allow_dirty=True)


def test_missing_source_file_and_non_git_source(src, tgt, tmp_path):
    with pytest.raises(SystemExit):
        cs.sync(src, tgt, ["nope.md"])
    plain = tmp_path / "plain"
    plain.mkdir()
    with pytest.raises(SystemExit):
        cs.sync(plain, tgt, ["x.md"])


def test_cli_check_exit_codes(src, tgt, capsys):
    cs.sync(src, tgt, ["restrictions.md"])
    assert cs.main([str(tgt), "--check"]) == 0
    (tgt / "context" / "restrictions.md").write_text("tampered", encoding="utf-8")
    assert cs.main([str(tgt), "--check"]) == 1
    assert "DRIFT" in capsys.readouterr().out

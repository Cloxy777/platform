import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import check_changelog as cc  # noqa: E402


def test_docs_and_tests_need_no_changelog():
    changed = ["docs/design.md", "claude-global/tests/test_guard.py", "py/tests/test_telegram.py",
               "packages/telegram-kit/test/kit.test.js", "scripts/check_changelog.py", "README.md"]
    assert cc.released_streams(changed) == []
    assert cc.check(changed) is None


def test_each_stream_detected():
    assert cc.released_streams([".github/workflows/test-py.yml"]) == ["v*"]
    assert cc.released_streams(["claude-global/rules/secrets.md"]) == ["v*"]
    assert cc.released_streams(["packages/telegram-kit/src/index.js"]) == ["telegram-kit-v*"]
    assert cc.released_streams(["py/platform_notify/telegram.py"]) == ["py-v*"]
    both = cc.released_streams(["claude-global/sync.py", "py/platform_notify/__init__.py"])
    assert both == ["py-v*", "v*"]


def test_ci_workflow_itself_is_not_a_release():
    assert cc.check([".github/workflows/ci.yml"]) is None


def test_released_change_without_changelog_fails():
    err = cc.check(["py/platform_notify/telegram.py"])
    assert err and "py-v*" in err and "CHANGELOG.md" in err


def test_released_change_with_changelog_passes():
    assert cc.check(["py/platform_notify/telegram.py", "CHANGELOG.md"]) is None

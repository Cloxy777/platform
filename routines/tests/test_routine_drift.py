import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import routine_drift as rd  # noqa: E402

SECRET = "PROMPT-SECRET-TEXT"


def trig(i, name="Routine 1 - Daily", cron="30 21 * * *", prompt=SECRET, enabled=True, conns=("Notion", "Google-Drive")):
    return {"id": i, "name": name, "cron_expression": cron, "enabled": enabled,
            "mcp_connections": [{"name": c} for c in conns],
            "derived_state": {"prompt": prompt},
            "job_config": {"ccr": {"environment_id": "env_x", "session_context": {
                "sources": [{"git_repository": {"url": "https://github.com/Cloxy777/investment-framework"}}]}}}}


@pytest.fixture
def live(tmp_path):
    def write(*ts):
        p = tmp_path / "live.json"
        p.write_text(json.dumps({"data": list(ts), "has_more": False}), encoding="utf-8")
        return p
    return write


def test_snapshot_then_check_clean(live, tmp_path):
    lp = live(trig("trig_a"), trig("trig_b", name="Other"))
    out = tmp_path / "routines"
    assert rd.main(["snapshot", str(lp), str(out), "--id", "trig_a"]) == 0
    row = json.loads((out / "routines.json").read_text(encoding="utf-8"))["routines"][0]
    assert row["connectors"] == ["Google-Drive", "Notion"] and row["repos"] == ["Cloxy777/investment-framework"]
    assert rd.check(lp, out, {"trig_b"}) == []


def test_drift_fields_prompt_untracked_and_no_prompt_echo(live, tmp_path):
    out = tmp_path / "routines"
    rd.snapshot(live(trig("trig_a")), out, ["trig_a"])
    changed = live(trig("trig_a", cron="0 1 * * *", enabled=False, prompt=SECRET + " edited", conns=("Notion",)),
                   trig("trig_new", name="New"))
    text = "\n".join(rd.check(changed, out))
    for needle in ("cron differs", "enabled differs", "connectors differs", "prompt differs", "live but not in git"):
        assert needle in text
    assert SECRET not in text


def test_missing_live_missing_prompt_and_manifest(live, tmp_path):
    out = tmp_path / "routines"
    assert any("missing: run snapshot" in p for p in rd.check(live(), out))
    lp = live(trig("trig_a"))
    rd.snapshot(lp, out, ["trig_a"])
    (out / "prompts" / "routine-1-daily.md").unlink()
    assert any("prompt file missing" in p for p in rd.check(lp, out))
    assert any("missing live" in p for p in rd.check(live(), out))
    with pytest.raises(SystemExit):
        rd.snapshot(lp, out, ["trig_zzz"])


def test_cli_exit_code(live, tmp_path, capsys):
    out = tmp_path / "routines"
    lp = live(trig("trig_a"))
    rd.main(["snapshot", str(lp), str(out), "--id", "trig_a"])
    assert rd.main(["check", str(lp), str(out)]) == 0
    assert rd.main(["check", str(live(trig("trig_a", cron="1 1 * * *"))), str(out)]) == 1
    assert "DRIFT" in capsys.readouterr().out

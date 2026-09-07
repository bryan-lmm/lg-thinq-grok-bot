import json
from pathlib import Path

from thinq_specialty.cli import main

FIXTURE = Path(__file__).parent / "fixtures" / "sample_tower_washer.json"


def test_help_exits_zero(capsys):
    try:
        main(["--help"])
    except SystemExit as exc:
        assert exc.code == 0
    out = capsys.readouterr().out
    assert "login" in out
    assert "devices" in out
    assert "courses" in out
    assert "start" in out
    assert "dry-run" in out.lower()


def test_start_help_mentions_execute(capsys):
    try:
        main(["start", "--help"])
    except SystemExit as exc:
        assert exc.code == 0
    out = capsys.readouterr().out
    assert "--execute" in out
    assert "dry-run" in out.lower()


def test_courses_offline_json(capsys):
    assert main(["courses", "--model-json", str(FIXTURE), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    ids = {item["id"] for item in payload["courses"]}
    assert "SPECIALTY_CYCLE_1" in ids
    assert "COURSE_A" in ids
    assert any(item["specialty"] for item in payload["courses"])
    field_names = {item["name"] for item in payload["start_option_fields"]}
    assert "steam" in field_names


def test_start_is_dry_run_without_execute(capsys):
    code = main(
        [
            "start",
            "--model-json",
            str(FIXTURE),
            "--course",
            "SPECIALTY_CYCLE_1",
            "--option",
            "reserveTimeHour=2",
        ]
    )
    assert code == 0
    out = capsys.readouterr().out
    assert "DRY-RUN" in out
    assert "was not sent" in out
    assert "--execute" in out
    payload = json.loads(out[out.index("{") : out.rindex("}") + 1])
    body = payload["dataSetList"]["washerDryer"]
    assert body["smartCourseSampleTowerWasher"] == "SPECIALTY_CYCLE_1"
    assert body["reserveTimeHour"] == 2

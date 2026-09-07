import pytest

from thinq_specialty.catalog import CourseCatalog
from thinq_specialty.exceptions import PayloadError
from thinq_specialty.start import build_remote_start


def test_specialty_payload_uses_smartcourse_key(sample_model):
    catalog = CourseCatalog.from_model(sample_model)
    plan = build_remote_start(catalog, "SPECIALTY_CYCLE_1")
    body = plan.body
    payload = plan.as_control_payload()

    assert payload["command"] == "Set"
    assert payload["ctrlKey"] == "WMStart"
    assert payload["dataSetList"]["washerDryer"] == body
    assert body["courseType"] == "SmartCourse"
    assert body["smartCourseSampleTowerWasher"] == "SPECIALTY_CYCLE_1"
    assert body["courseSampleTowerWasher"] == "COURSE_A"
    assert body["initialBit"] == "INITIAL_BIT_ON"
    assert body["steam"] == "STEAM_ON"
    assert body["temp"] == "TEMP_COLD"
    assert body["remoteStart"] == "REMOTE_START_ON"
    assert plan.dry_run is True


def test_base_payload_clears_smartcourse(sample_model):
    catalog = CourseCatalog.from_model(sample_model)
    plan = build_remote_start(catalog, "COURSE_B", options={"preWash": "PREWASH_ON"})
    body = plan.body

    assert body["courseType"] == "Course"
    assert body["courseSampleTowerWasher"] == "COURSE_B"
    assert body["smartCourseSampleTowerWasher"] == "NOT_SELECTED"
    assert body["preWash"] == "PREWASH_ON"
    assert body["temp"] == "TEMP_COLD"


def test_rejects_unknown_option_field(sample_model):
    catalog = CourseCatalog.from_model(sample_model)
    with pytest.raises(PayloadError, match="not present in the device model"):
        build_remote_start(catalog, "COURSE_A", options={"notARealField": "X"})


def test_rejects_value_outside_model_enum(sample_model):
    catalog = CourseCatalog.from_model(sample_model)
    with pytest.raises(PayloadError, match="not in the model-declared values"):
        build_remote_start(catalog, "COURSE_A", options={"steam": "STEAM_MAYBE"})

from thinq_specialty.catalog import CourseCatalog, CourseType


def test_catalog_includes_base_and_specialty(sample_model):
    catalog = CourseCatalog.from_model(sample_model)

    assert catalog.model_type == "SAMPLE_TOWER_WASHER"
    assert catalog.course_key == "courseSampleTowerWasher"
    assert catalog.smart_course_key == "smartCourseSampleTowerWasher"

    base_ids = {item.course_id for item in catalog.base_courses()}
    specialty_ids = {item.course_id for item in catalog.specialty_courses()}
    assert base_ids == {"COURSE_A", "COURSE_B"}
    assert specialty_ids == {"SPECIALTY_CYCLE_1", "SPECIALTY_CYCLE_2"}

    specialty = catalog.find("SPECIALTY_CYCLE_1")
    assert specialty.course_type is CourseType.SMARTCOURSE
    assert specialty.is_specialty
    assert specialty.base_course_id == "COURSE_A"
    assert specialty.defaults["steam"] == "STEAM_ON"


def test_start_option_fields_come_from_model(sample_model):
    catalog = CourseCatalog.from_model(sample_model)
    names = {item.name for item in catalog.start_option_fields}
    assert "steam" in names
    assert "reserveTimeHour" in names
    assert "temp" in names
    assert "courseType" not in names
    assert "smartCourse" not in names

    steam = catalog.option_field("steam")
    assert steam is not None
    assert "STEAM_ON" in steam.allowed_values
    assert "STEAM_OFF" in steam.allowed_values

    reserve = catalog.option_field("reserveTimeHour")
    assert reserve is not None
    assert reserve.allowed_values == ()

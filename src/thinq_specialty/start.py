"""Build ThinQ2 remote-start payloads that can select a specialty cycle.

The payload shape matches community WMStart / control-sync traffic:

    {
      "command": "Set",
      "ctrlKey": "WMStart",
      "dataSetList": {
        "washerDryer": {
          "courseType": "SmartCourse" | "Course",
          "<course key>": "<id>" | "NOT_SELECTED",
          "<smart course key>": "<id>" | "NOT_SELECTED",
          "initialBit": "INITIAL_BIT_ON",
          ... model-declared start-option fields ...
        }
      }
    }

Specialty (download/SmartCourse) ids go on the smart-course key. Base Course
ids go on the course key. Option fields are taken from the device model
(control template + cycle function defaults) and can be overridden by the
caller.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .catalog import Course, CourseCatalog, CourseType
from .const import (
    CMD_SET,
    CTRL_WM_START,
    CYCLE_TEMPLATE_KEYS,
    INITIAL_BIT_ON,
    NOT_SELECTED,
    REMOTE_START_ON,
    WM_ROOT,
)
from .exceptions import PayloadError


@dataclass
class RemoteStartPlan:
    """A remote-start request: HTTP envelope plus the washerDryer body."""

    course: Course
    body: dict[str, Any]
    dry_run: bool = True
    notes: list[str] = field(default_factory=list)

    def as_control_payload(self) -> dict[str, Any]:
        return {
            "command": CMD_SET,
            "ctrlKey": CTRL_WM_START,
            "dataSetList": {WM_ROOT: dict(self.body)},
        }


def build_remote_start(
    catalog: CourseCatalog,
    course_id: str,
    *,
    options: dict[str, Any] | None = None,
    include_template_defaults: bool = True,
    strict_options: bool = True,
) -> RemoteStartPlan:
    """Build a WMStart payload that can select a specialty cycle id.

    Parameters
    ----------
    catalog:
        Parsed model catalog (base + specialty).
    course_id:
        Cycle id or label from the catalog.
    options:
        Extra start-option fields from the device model (name -> value).
    include_template_defaults:
        Copy non-empty defaults from ControlWifi.WMStart.
    strict_options:
        Reject option names that the model does not declare.
    """
    course = catalog.find(course_id)
    notes: list[str] = []
    body: dict[str, Any] = {}

    if include_template_defaults:
        for key, value in catalog.control_template.items():
            if key in CYCLE_TEMPLATE_KEYS:
                continue
            if value in ("", None):
                continue
            body[str(key)] = value

    for key, value in course.defaults.items():
        body[key] = value

    course_key = catalog.course_key or "course"
    smart_key = catalog.smart_course_key or "smartCourse"

    if course.course_type is CourseType.SMARTCOURSE:
        body["courseType"] = CourseType.SMARTCOURSE.value
        body[smart_key] = course.course_id
        body[course_key] = course.base_course_id or NOT_SELECTED
        notes.append(
            "Selected a specialty (download/SmartCourse) cycle. "
            "The official ThinQ Connect / PAT API generally cannot do this."
        )
    else:
        body["courseType"] = CourseType.COURSE.value
        body[course_key] = course.course_id
        if catalog.smart_course_key:
            body[smart_key] = NOT_SELECTED

    body.setdefault("initialBit", INITIAL_BIT_ON)
    if "remoteStart" in catalog.control_template or "remoteStart" in body:
        body.setdefault("remoteStart", REMOTE_START_ON)

    declared = {item.name for item in catalog.start_option_fields}
    for name, value in (options or {}).items():
        if strict_options and name not in declared and name not in body:
            known = ", ".join(sorted(declared)) or "(none declared)"
            raise PayloadError(
                f"Start-option field {name!r} is not present in the device model. "
                f"Declared fields: {known}"
            )
        field_info = catalog.option_field(name)
        if (
            field_info
            and field_info.allowed_values
            and str(value) not in field_info.allowed_values
        ):
            raise PayloadError(
                f"Value {value!r} is not in the model-declared values for {name!r}: "
                f"{', '.join(field_info.allowed_values)}"
            )
        body[name] = value

    return RemoteStartPlan(course=course, body=body, notes=notes)

"""Dump base + specialty (download/SmartCourse) cycles from device model info.

Community clients often expose only CourseType.COURSE in a UI course list.
This catalog also loads SmartCourse (and downloadedCourseType), which is where
specialty / download cycles live on many ThinQ2 laundry models.

Parsing follows the public model-info layout documented by
ollo69/ha-smartthinq-sensors (Config keys, MonitoringValue references, and
Course / SmartCourse sections).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .const import (
    COURSE_CONFIG_KEYS,
    COURSE_SECTION_CANDIDATES,
    CYCLE_TEMPLATE_KEYS,
    SMARTCOURSE_CONFIG_KEYS,
    SMARTCOURSE_SECTION_CANDIDATES,
    WM_ROOT,
)
from .exceptions import ModelInfoError


class CourseType(str, Enum):
    """Course families present on ThinQ laundry model JSON."""

    COURSE = "Course"
    SMARTCOURSE = "SmartCourse"
    OPCOURSE = "OpCourse"


@dataclass(frozen=True)
class Course:
    """One selectable cycle from the device model catalog."""

    course_id: str
    course_type: CourseType
    label: str
    defaults: dict[str, str]
    base_course_id: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def is_specialty(self) -> bool:
        return self.course_type is CourseType.SMARTCOURSE


@dataclass(frozen=True)
class StartOptionField:
    """A start-option field declared by the device model."""

    name: str
    allowed_values: tuple[str, ...] = ()
    default: str | None = None
    source: str = "model"


@dataclass
class CourseCatalog:
    """Base cycles, specialty cycles, and model-declared start-option fields."""

    model_type: str
    course_key: str | None
    smart_course_key: str | None
    courses: list[Course]
    start_option_fields: list[StartOptionField]
    control_template: dict[str, Any]
    raw_model: dict[str, Any]

    def find(self, course_id: str) -> Course:
        needle = course_id.strip()
        matches = [item for item in self.courses if item.course_id == needle]
        if not matches:
            by_label = [item for item in self.courses if item.label.lower() == needle.lower()]
            matches = by_label
        if not matches:
            known = ", ".join(item.course_id for item in self.courses) or "(empty catalog)"
            raise ModelInfoError(f"Unknown cycle {course_id!r}. Known ids: {known}")
        if len(matches) > 1:
            # Prefer an exact id match, then specialty when labels collide.
            exact = [item for item in matches if item.course_id == needle]
            if exact:
                return exact[0]
            specialty = [item for item in matches if item.is_specialty]
            return specialty[0] if specialty else matches[0]
        return matches[0]

    def specialty_courses(self) -> list[Course]:
        return [item for item in self.courses if item.is_specialty]

    def base_courses(self) -> list[Course]:
        return [item for item in self.courses if item.course_type is CourseType.COURSE]

    def option_field(self, name: str) -> StartOptionField | None:
        for field_info in self.start_option_fields:
            if field_info.name == name:
                return field_info
        return None

    @classmethod
    def from_model(cls, model: dict[str, Any]) -> CourseCatalog:
        if not isinstance(model, dict) or not model:
            raise ModelInfoError("Model info is empty")

        config = model.get("Config") if isinstance(model.get("Config"), dict) else {}
        info = model.get("Info") if isinstance(model.get("Info"), dict) else {}
        model_type = str(info.get("modelType") or config.get("modelType") or "unknown")

        course_key = _resolve_catalog_key(
            model, config, COURSE_CONFIG_KEYS, COURSE_SECTION_CANDIDATES
        )
        smart_key = _resolve_catalog_key(
            model, config, SMARTCOURSE_CONFIG_KEYS, SMARTCOURSE_SECTION_CANDIDATES
        )

        courses: list[Course] = []
        courses.extend(_load_section(model, course_key, CourseType.COURSE))
        courses.extend(_load_section(model, smart_key, CourseType.SMARTCOURSE))

        if not courses:
            raise ModelInfoError(
                "Model info has no Course or SmartCourse catalog. "
                "This client targets ThinQ2 laundry model JSON."
            )

        template = _control_template(model)
        option_fields = _collect_option_fields(model, courses, template)
        return cls(
            model_type=model_type,
            course_key=course_key,
            smart_course_key=smart_key,
            courses=courses,
            start_option_fields=option_fields,
            control_template=template,
            raw_model=model,
        )


def _monitoring_value(model: dict[str, Any], name: str) -> dict[str, Any] | None:
    monitoring = model.get("MonitoringValue")
    if isinstance(monitoring, dict) and isinstance(monitoring.get(name), dict):
        return monitoring[name]
    values = model.get("Value")
    if isinstance(values, dict) and isinstance(values.get(name), dict):
        return values[name]
    return None


def _value_exists(model: dict[str, Any], name: str) -> bool:
    if name in model:
        return True
    return _monitoring_value(model, name) is not None


def _resolve_catalog_key(
    model: dict[str, Any],
    config: dict[str, Any],
    config_keys: tuple[str, ...],
    section_names: tuple[str, ...],
) -> str | None:
    for key in config_keys:
        pointed = config.get(key)
        if pointed and _value_exists(model, str(pointed)):
            return str(pointed)
    for name in section_names:
        if _value_exists(model, name) or name in model:
            return name
    return None


def _reference_table(model: dict[str, Any], catalog_key: str | None) -> dict[str, Any]:
    if not catalog_key:
        return {}
    meta = _monitoring_value(model, catalog_key) or {}
    ref = meta.get("ref")
    if isinstance(ref, str) and isinstance(model.get(ref), dict):
        return model[ref]
    option = meta.get("option")
    if isinstance(option, list) and option and isinstance(model.get(option[0]), dict):
        return model[option[0]]
    if isinstance(model.get(catalog_key), dict) and not meta:
        table = model[catalog_key]
        # A MonitoringValue entry is metadata, not the cycle table.
        if "dataType" not in table and "type" not in table:
            return table
    for fallback in (catalog_key, *_guess_section(catalog_key)):
        if isinstance(model.get(fallback), dict):
            table = model[fallback]
            if table and "dataType" not in table:
                return table
    return {}


def _guess_section(catalog_key: str) -> tuple[str, ...]:
    lowered = catalog_key.lower()
    if "smart" in lowered or "download" in lowered:
        return SMARTCOURSE_SECTION_CANDIDATES
    return COURSE_SECTION_CANDIDATES


def _course_label(course_id: str, entry: dict[str, Any]) -> str:
    for key in ("_comment", "label", "name"):
        value = entry.get(key)
        if isinstance(value, str) and value and not value.startswith("@"):
            return value
    return course_id


def _function_defaults(entry: dict[str, Any]) -> dict[str, str]:
    functions = entry.get("function") or []
    defaults: dict[str, str] = {}
    if not isinstance(functions, list):
        return defaults
    for item in functions:
        if not isinstance(item, dict):
            continue
        name = item.get("value")
        default = item.get("default")
        if name is None or default is None:
            continue
        defaults[str(name)] = str(default)
    return defaults


def _base_course_id(entry: dict[str, Any]) -> str | None:
    for key in ("Course", "APCourse", "course"):
        value = entry.get(key)
        if value not in (None, "", 0, "0"):
            return str(value)
    return None


def _load_section(
    model: dict[str, Any],
    catalog_key: str | None,
    course_type: CourseType,
) -> list[Course]:
    table = _reference_table(model, catalog_key)
    courses: list[Course] = []
    for course_id, entry in table.items():
        if not isinstance(entry, dict):
            continue
        if str(course_id).upper() in {"NOT_SELECTED", "NONE"}:
            continue
        declared = entry.get("courseType")
        resolved_type = course_type
        if isinstance(declared, str):
            lowered = declared.replace(" ", "").lower()
            if lowered == "smartcourse":
                resolved_type = CourseType.SMARTCOURSE
            elif lowered == "course":
                resolved_type = CourseType.COURSE
        courses.append(
            Course(
                course_id=str(course_id),
                course_type=resolved_type,
                label=_course_label(str(course_id), entry),
                defaults=_function_defaults(entry),
                base_course_id=_base_course_id(entry),
                raw=entry,
            )
        )
    return courses


def _control_template(model: dict[str, Any]) -> dict[str, Any]:
    control = model.get("ControlWifi")
    if not isinstance(control, dict):
        return {}
    start = control.get("WMStart") or control.get("action", {}).get("WMStart")
    if not isinstance(start, dict):
        return {}
    data = start.get("data")
    if isinstance(data, dict) and isinstance(data.get(WM_ROOT), dict):
        return dict(data[WM_ROOT])
    if isinstance(data, dict):
        return dict(data)
    return {}


def _enum_values(model: dict[str, Any], name: str) -> tuple[str, ...]:
    meta = _monitoring_value(model, name)
    if not meta:
        return ()
    data_type = str(meta.get("dataType") or meta.get("type") or meta.get("data_type") or "").lower()
    if data_type in {"range", "number", "string"}:
        return ()
    mapping = meta.get("valueMapping") or meta.get("option") or meta.get("value_mapping")
    if isinstance(mapping, dict):
        return tuple(str(key) for key in mapping if str(key).upper() != "NOT_SELECTED")
    return ()


def _collect_option_fields(
    model: dict[str, Any],
    courses: list[Course],
    template: dict[str, Any],
) -> list[StartOptionField]:
    names: list[str] = []

    def add(name: str) -> None:
        if name and name not in CYCLE_TEMPLATE_KEYS and name not in names:
            names.append(name)

    for key in template:
        add(str(key))
    for course in courses:
        for key in course.defaults:
            add(key)

    monitoring = model.get("MonitoringValue")
    if isinstance(monitoring, dict):
        for key, meta in monitoring.items():
            if not isinstance(meta, dict):
                continue
            data_type = str(meta.get("dataType") or "").lower()
            if data_type in {"enum", "boolean", "range"} and key not in CYCLE_TEMPLATE_KEYS:
                # Only promote fields that already appear on start templates or cycles.
                if key in names:
                    add(key)

    fields: list[StartOptionField] = []
    for name in names:
        default = template.get(name)
        if default in ("", None):
            default = None
        fields.append(
            StartOptionField(
                name=name,
                allowed_values=_enum_values(model, name),
                default=None if default is None else str(default),
                source="model",
            )
        )
    return fields

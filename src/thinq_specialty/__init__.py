"""Unofficial ThinQ2 client for specialty laundry cycles and start-option fields.

This package talks to LG's community-documented ThinQ2 (app) API. It is not
the official ThinQ Connect / PAT API, and it is not affiliated with LG.

See NOTICE for prior art: ollo69/ha-smartthinq-sensors, sampsyo/wideq, and
tinkerborg/thinq2-python.
"""

from .catalog import Course, CourseCatalog, CourseType, StartOptionField
from .client import ThinQClient
from .devices import Device, DeviceType
from .exceptions import AuthError, ThinQError, TokenError
from .start import RemoteStartPlan, build_remote_start

__all__ = [
    "AuthError",
    "Course",
    "CourseCatalog",
    "CourseType",
    "Device",
    "DeviceType",
    "RemoteStartPlan",
    "StartOptionField",
    "ThinQClient",
    "ThinQError",
    "TokenError",
    "build_remote_start",
]

__version__ = "0.1.0"

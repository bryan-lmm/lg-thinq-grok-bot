"""Public ThinQ2 protocol constants documented by community clients.

These values are the well-known app-client identifiers used by unofficial
ThinQ libraries (wideq, ha-smartthinq-sensors). They are not user secrets
and are not account credentials.
"""

from __future__ import annotations

DEFAULT_COUNTRY = "US"
DEFAULT_LANGUAGE = "en-US"
DEFAULT_TIMEOUT = 20.0

# ThinQ2 route / headers (community-documented app API).
V2_GATEWAY_URL = "https://route.lgthinq.com:46030/v1/service/application/gateway-uri"
V2_API_KEY = "VGhpblEyLjAgU0VSVklDRQ=="
V2_SVC_PHASE = "OP"
V2_APP_LEVEL = "PRD"
V2_APP_OS = "ANDROID"
V2_APP_TYPE = "NUTS"
V2_APP_VER = "5.0.1200"
SVC_CODE = "SVC202"
SECURITY_KEY = "nuts_securitykey"

# EMP OAuth (same public client used by wideq and later ThinQ2 clients).
CLIENT_ID = "LGAO221A02"
OAUTH_CLIENT_KEY = "LGAO722A02"
OAUTH_SECRET_KEY = "c053c2a6ddeb7ad97cb0eed0dcb31cf8"
OAUTH_AUTH_PATH = "/oauth/1.0/oauth2/token"
OAUTH_LOGIN_HOST = "us.m.lgaccount.com"
OAUTH_LOGIN_PATH = "login/signIn"
OAUTH_REDIRECT_PATH = "login/iabClose"
OAUTH_REDIRECT_URI = f"https://kr.m.lgaccount.com/{OAUTH_REDIRECT_PATH}"
EMP_REDIRECT_URL = "lgaccount.lgsmartthinq:/"
DATE_FORMAT = "%a, %d %b %Y %H:%M:%S +0000"
APPLICATION_KEY = "6V1V8H2BN5P9ZQGOI5DAQ92YZBDO3EK9"
USER_INFO_PATH = "/users/profile"

# Laundry snapshot / control root used by ThinQ2 washer and dryer models.
WM_ROOT = "washerDryer"
CTRL_WM_START = "WMStart"
CMD_SET = "Set"
NOT_SELECTED = "NOT_SELECTED"
INITIAL_BIT_ON = "INITIAL_BIT_ON"
REMOTE_START_ON = "REMOTE_START_ON"

# Model-info config keys that point at course catalogs (ThinQ2).
COURSE_CONFIG_KEYS = ("courseType",)
SMARTCOURSE_CONFIG_KEYS = ("smartCourseType", "downloadedCourseType")
COURSE_SECTION_CANDIDATES = ("Course", "APCourse")
SMARTCOURSE_SECTION_CANDIDATES = ("SmartCourse",)

# Template keys that identify a cycle, not a start-option field.
CYCLE_TEMPLATE_KEYS = frozenset(
    {
        "course",
        "Course",
        "ApCourse",
        "APCourse",
        "smartCourse",
        "SmartCourse",
        "courseType",
        "opCourse",
        "OpCourse",
        "initialBit",
    }
)

# Device type codes used by ThinQ laundry (community DeviceType map).
WASHER = 201
DRYER = 202
TOWER_WASHER = 221
TOWER_DRYER = 222
TOWER_WASHER_DRYER = 223
LAUNDRY_DEVICE_TYPES = frozenset(
    {WASHER, DRYER, TOWER_WASHER, TOWER_DRYER, TOWER_WASHER_DRYER}
)

SUCCESS_CODE = "0000"

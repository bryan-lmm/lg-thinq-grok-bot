"""ThinQ2 device list helpers for laundry appliances."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import Any

from .const import LAUNDRY_DEVICE_TYPES, TOWER_DRYER, TOWER_WASHER, TOWER_WASHER_DRYER


class DeviceType(IntEnum):
    """ThinQ deviceType codes used by laundry products."""

    WASHER = 201
    DRYER = 202
    TOWER_WASHER = 221
    TOWER_DRYER = 222
    TOWER_WASHER_DRYER = 223
    UNKNOWN = 0

    @classmethod
    def from_code(cls, code: Any) -> DeviceType:
        try:
            return cls(int(code))
        except (TypeError, ValueError):
            return cls.UNKNOWN


@dataclass(frozen=True)
class Device:
    """A ThinQ2 device as returned by dashboard / homes APIs."""

    device_id: str
    name: str
    model_name: str
    device_type: DeviceType
    platform_type: str
    online: bool
    model_json_uri: str | None
    raw: dict[str, Any]

    @property
    def is_laundry(self) -> bool:
        return (
            int(self.device_type) in LAUNDRY_DEVICE_TYPES
            or self.device_type is DeviceType.UNKNOWN
        )

    @property
    def is_thinq2(self) -> bool:
        return (self.platform_type or "").lower() in {"thinq2", ""}

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> Device:
        device_id = str(data.get("deviceId") or "")
        model = str(data.get("modelName") or data.get("modelNm") or "")
        return cls(
            device_id=device_id,
            name=str(data.get("alias") or device_id),
            model_name=model,
            device_type=DeviceType.from_code(data.get("deviceType")),
            platform_type=str(data.get("platformType") or "thinq2"),
            online=bool(data.get("online", False)),
            model_json_uri=data.get("modelJsonUri") or data.get("modelJsonUrl"),
            raw=data,
        )


def snapshot_root(device: Device) -> dict[str, Any]:
    """Return the washerDryer (or similar) snapshot object when present."""
    snapshot = device.raw.get("snapshot") or {}
    if not isinstance(snapshot, dict):
        return {}
    if isinstance(snapshot.get("washerDryer"), dict):
        return snapshot["washerDryer"]
    return snapshot


def describe_device_type(device_type: DeviceType) -> str:
    labels = {
        DeviceType.WASHER: "washer",
        DeviceType.DRYER: "dryer",
        DeviceType.TOWER_WASHER: "tower washer",
        DeviceType.TOWER_DRYER: "tower dryer",
        DeviceType.TOWER_WASHER_DRYER: "tower washer/dryer",
        DeviceType.UNKNOWN: "unknown",
    }
    return labels.get(device_type, "unknown")


# Keep the numeric codes importable for fixtures (221 / 222).
SAMPLE_TOWER_WASHER_TYPE = TOWER_WASHER
SAMPLE_TOWER_DRYER_TYPE = TOWER_DRYER
SAMPLE_COMBO_TYPE = TOWER_WASHER_DRYER

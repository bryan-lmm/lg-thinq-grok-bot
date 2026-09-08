"""ThinQ2 HTTP client: devices, model JSON, and optional remote start."""

from __future__ import annotations

import hashlib
from typing import Any
from urllib.parse import urljoin

import httpx

from .auth import (
    Credentials,
    Gateway,
    discover_gateway,
    fetch_user_number,
    refresh_access_token,
    resolve_oauth_base,
    thinq2_headers,
)
from .catalog import CourseCatalog
from .const import DEFAULT_TIMEOUT, SUCCESS_CODE
from .devices import Device
from .exceptions import APIError, AuthError, DeviceNotFoundError, ModelInfoError, TokenError
from .start import RemoteStartPlan, build_remote_start


def _client_id_for(credentials: Credentials) -> str:
    """Stable per-account client id. Do not rotate daily — LG rate-limits that."""
    if credentials.client_id:
        return credentials.client_id
    seed = credentials.user_number or credentials.refresh_token[:32]
    return hashlib.sha256(f"thinq-specialty:{seed}".encode()).hexdigest()


class ThinQClient:
    """Synchronous ThinQ2 client. Auth comes from the environment or Credentials."""

    def __init__(
        self,
        credentials: Credentials,
        *,
        http: httpx.Client | None = None,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        self.credentials = credentials
        self._owned_http = http is None
        self.http = http or httpx.Client(timeout=timeout, follow_redirects=True)
        self.gateway: Gateway | None = None
        self._oauth_base: str | None = None

    @classmethod
    def from_env(cls, **kwargs: Any) -> ThinQClient:
        return cls(Credentials.from_env(), **kwargs)

    def close(self) -> None:
        if self._owned_http:
            self.http.close()

    def __enter__(self) -> ThinQClient:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def connect(self) -> None:
        """Discover the regional gateway and refresh the access token if needed."""
        self.gateway = discover_gateway(
            self.http,
            country=self.credentials.country,
            language=self.credentials.language,
        )
        self._oauth_base = resolve_oauth_base(self.gateway)
        if not self.credentials.access_token:
            self.refresh()
        if not self.credentials.user_number and self.credentials.access_token:
            try:
                self.credentials.user_number = fetch_user_number(
                    self.http, self._oauth_base, self.credentials.access_token
                )
            except (AuthError, httpx.HTTPError):
                pass

    def refresh(self) -> None:
        if not self._oauth_base:
            if not self.gateway:
                self.connect()
                return
            self._oauth_base = resolve_oauth_base(self.gateway)
        try:
            tokens = refresh_access_token(
                self.http, self._oauth_base, self.credentials.refresh_token
            )
        except TokenError:
            raise
        except httpx.HTTPError as exc:
            raise TokenError(f"Failed to refresh access token: {exc}") from exc
        self.credentials.access_token = tokens["access_token"]

    def _headers(self, *, security_key: bool = False) -> dict[str, str]:
        if not self.credentials.access_token:
            self.connect()
        return thinq2_headers(
            self.credentials.country,
            self.credentials.language,
            client_id=_client_id_for(self.credentials),
            access_token=self.credentials.access_token,
            user_number=self.credentials.user_number,
            security_key=security_key,
        )

    def _thinq2(self, path: str) -> str:
        if not self.gateway:
            self.connect()
        assert self.gateway is not None
        return urljoin(self.gateway.thinq2_uri, path)

    def _unwrap(self, payload: dict[str, Any]) -> Any:
        code = payload.get("resultCode")
        if code not in (None, SUCCESS_CODE):
            if str(code) in {"0102", "0110"}:
                self.refresh()
            raise APIError(str(payload.get("result") or "ThinQ2 error"), code=str(code))
        return payload.get("result", payload)

    def get2(self, path: str) -> Any:
        response = self.http.get(self._thinq2(path), headers=self._headers())
        response.raise_for_status()
        return self._unwrap(response.json())

    def post2(self, path: str, data: dict[str, Any]) -> Any:
        response = self.http.post(
            self._thinq2(path),
            headers=self._headers(security_key=True),
            json=data,
        )
        response.raise_for_status()
        return self._unwrap(response.json())

    def list_devices(self, *, laundry_only: bool = True) -> list[Device]:
        """List devices on the account (dashboard, then homes fallback)."""
        raw_items = self._list_raw_devices()
        devices = [Device.from_api(item) for item in raw_items if isinstance(item, dict)]
        devices = [item for item in devices if item.device_id]
        if laundry_only:
            laundry = [item for item in devices if item.is_laundry and item.device_type.value != 0]
            if laundry:
                return laundry
        return devices

    def _list_raw_devices(self) -> list[dict[str, Any]]:
        try:
            dashboard = self.get2("service/application/dashboard")
            if isinstance(dashboard, dict):
                items = dashboard.get("item") or dashboard.get("devices") or []
                if isinstance(items, list) and items:
                    return items
        except APIError:
            pass

        homes = self.get2("service/homes")
        items: list[dict[str, Any]] = []
        home_list = []
        if isinstance(homes, dict):
            home_list = homes.get("item") or []
        if isinstance(home_list, dict):
            home_list = [home_list]
        for home in home_list:
            if not isinstance(home, dict):
                continue
            home_id = home.get("homeId")
            if not home_id:
                continue
            detail = self.get2(f"service/homes/{home_id}")
            if isinstance(detail, dict):
                devices = detail.get("devices") or []
                if isinstance(devices, list):
                    items.extend(item for item in devices if isinstance(item, dict))
        return items

    def get_device(self, device_id: str) -> Device:
        for device in self.list_devices(laundry_only=False):
            if device.device_id == device_id:
                return device
        raise DeviceNotFoundError(f"No device with id {device_id!r}")

    def fetch_model_info(self, device: Device) -> dict[str, Any]:
        """Download the device model JSON (usually a public object-store URL)."""
        uri = device.model_json_uri
        if not uri:
            detail = self.get2(f"service/devices/{device.device_id}")
            if isinstance(detail, dict):
                uri = detail.get("modelJsonUri") or detail.get("modelJsonUrl")
        if not uri:
            raise ModelInfoError(
                f"Device {device.device_id} has no modelJsonUri; cannot dump the course catalog."
            )
        response = self.http.get(uri)
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise ModelInfoError("Model JSON was not an object")
        return payload

    def course_catalog(self, device: Device, model: dict[str, Any] | None = None) -> CourseCatalog:
        return CourseCatalog.from_model(model or self.fetch_model_info(device))

    def plan_start(
        self,
        device: Device,
        course_id: str,
        *,
        options: dict[str, Any] | None = None,
        model: dict[str, Any] | None = None,
    ) -> RemoteStartPlan:
        catalog = self.course_catalog(device, model=model)
        return build_remote_start(catalog, course_id, options=options)

    def execute_start(self, device_id: str, plan: RemoteStartPlan) -> Any:
        """POST control-sync. The appliance must already allow remote start."""
        return self.post2(
            f"service/devices/{device_id}/control-sync",
            plan.as_control_payload(),
        )

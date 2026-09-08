"""Env-based ThinQ2 authentication. No secrets are stored in this repository.

Login is LG account OAuth. After the browser redirect, this module exchanges
an authorization code or parses tokens from the callback URL. Day-to-day use
is a refresh token loaded from the environment.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from urllib.parse import parse_qs, urlencode, urljoin, urlparse, urlunparse

import httpx

from .const import (
    APPLICATION_KEY,
    CLIENT_ID,
    DATE_FORMAT,
    DEFAULT_COUNTRY,
    DEFAULT_LANGUAGE,
    EMP_REDIRECT_URL,
    OAUTH_AUTH_PATH,
    OAUTH_LOGIN_HOST,
    OAUTH_LOGIN_PATH,
    OAUTH_REDIRECT_PATH,
    OAUTH_SECRET_KEY,
    SECURITY_KEY,
    SVC_CODE,
    USER_INFO_PATH,
    V2_API_KEY,
    V2_APP_LEVEL,
    V2_APP_OS,
    V2_APP_TYPE,
    V2_APP_VER,
    V2_GATEWAY_URL,
    V2_SVC_PHASE,
)
from .exceptions import AuthError, TokenError


def new_message_id() -> str:
    return str(uuid.uuid4())


def thinq2_headers(
    country: str,
    language: str,
    *,
    client_id: str | None = None,
    access_token: str | None = None,
    user_number: str | None = None,
    extra: dict[str, str] | None = None,
    security_key: bool = False,
) -> dict[str, str]:
    """Headers used by the unofficial ThinQ2 app API."""
    headers = {
        "Accept": "application/json",
        "Content-type": "application/json;charset=UTF-8",
        "x-api-key": V2_API_KEY,
        "x-client-id": client_id or hashlib.sha256(new_message_id().encode()).hexdigest(),
        "x-country-code": country,
        "x-language-code": language,
        "x-message-id": new_message_id(),
        "x-service-code": SVC_CODE,
        "x-service-phase": V2_SVC_PHASE,
        "x-thinq-app-level": V2_APP_LEVEL,
        "x-thinq-app-os": V2_APP_OS,
        "x-thinq-app-type": V2_APP_TYPE,
        "x-thinq-app-ver": V2_APP_VER,
    }
    if security_key:
        headers["x-thinq-security-key"] = SECURITY_KEY
    if access_token:
        headers["x-emp-token"] = access_token
    if user_number:
        headers["x-user-no"] = user_number
    if extra:
        headers.update(extra)
    return headers


def oauth2_signature(message: str, secret: str) -> str:
    """Base64 SHA-1 HMAC used by EMP OAuth (community-documented)."""
    digest = hmac.new(secret.encode("utf-8"), message.encode("utf-8"), hashlib.sha1).digest()
    return base64.b64encode(digest).decode("utf-8")


def _utc_oauth_date() -> str:
    return datetime.now(timezone.utc).strftime(DATE_FORMAT)


@dataclass(frozen=True)
class Gateway:
    """Regional ThinQ2 hosts from gateway-uri discovery."""

    emp_uri: str
    emp_terms_uri: str
    emp_spx_uri: str
    thinq1_uri: str
    thinq2_uri: str
    oauth_uri: str | None
    country: str
    language: str

    def login_url(self, state: str | None = None) -> str:
        """Browser URL that starts LG account OAuth for ThinQ."""
        login_base = urlparse(self.emp_spx_uri)
        redirect = urlunparse(
            (
                login_base.scheme,
                login_base.netloc,
                urljoin(login_base.path, OAUTH_REDIRECT_PATH),
                "",
                "",
                "",
            )
        )
        query = urlencode(
            {
                "country": self.country,
                "language": self.language,
                "client_id": CLIENT_ID,
                "svc_list": SVC_CODE,
                "svc_integrated": "Y",
                "show_thirdparty_login": "LGE,MYLG,google,amazon,facebook,apple",
                "division": "ha",
                "callback_url": redirect,
                "oauth2State": state or uuid.uuid4().hex,
                "show_select_country": "N",
            }
        )
        netloc = OAUTH_LOGIN_HOST
        if login_base.port:
            netloc = f"{netloc}:{login_base.port}"
        return urlunparse(
            (
                login_base.scheme,
                netloc,
                urljoin(login_base.path, OAUTH_LOGIN_PATH),
                "",
                query,
                "",
            )
        )


@dataclass
class Credentials:
    """Tokens used by the ThinQ2 client. Never log these."""

    refresh_token: str
    access_token: str | None = None
    user_number: str | None = None
    client_id: str | None = None
    country: str = DEFAULT_COUNTRY
    language: str = DEFAULT_LANGUAGE

    @classmethod
    def from_env(cls) -> Credentials:
        """Load credentials from process environment. Raises if refresh token missing."""
        refresh = os.environ.get("THINQ_REFRESH_TOKEN", "").strip()
        if not refresh:
            raise AuthError(
                "THINQ_REFRESH_TOKEN is not set. Run `thinq-specialty login` and "
                "export the refresh token (do not commit it)."
            )
        return cls(
            refresh_token=refresh,
            access_token=os.environ.get("THINQ_ACCESS_TOKEN") or None,
            user_number=os.environ.get("THINQ_USER_NUMBER") or None,
            client_id=os.environ.get("THINQ_CLIENT_ID") or None,
            country=os.environ.get("THINQ_COUNTRY", DEFAULT_COUNTRY).strip() or DEFAULT_COUNTRY,
            language=os.environ.get("THINQ_LANGUAGE", DEFAULT_LANGUAGE).strip()
            or DEFAULT_LANGUAGE,
        )

    def export_lines(self) -> str:
        """Shell exports for the user to copy. Does not write files."""
        lines = [
            f"export THINQ_COUNTRY={self.country}",
            f"export THINQ_LANGUAGE={self.language}",
            f"export THINQ_REFRESH_TOKEN={self.refresh_token}",
        ]
        if self.access_token:
            lines.append(f"export THINQ_ACCESS_TOKEN={self.access_token}")
        if self.user_number:
            lines.append(f"export THINQ_USER_NUMBER={self.user_number}")
        if self.client_id:
            lines.append(f"export THINQ_CLIENT_ID={self.client_id}")
        return "\n".join(lines) + "\n"


def _ensure_slash(url: str) -> str:
    return url if url.endswith("/") else url + "/"


def _unwrap_v2(payload: dict[str, Any]) -> dict[str, Any]:
    if payload.get("resultCode") not in (None, "0000"):
        raise AuthError(
            str(payload.get("result") or "ThinQ2 gateway error"),
            code=str(payload.get("resultCode")),
        )
    result = payload.get("result")
    if isinstance(result, dict):
        return result
    return payload


def discover_gateway(
    client: httpx.Client,
    *,
    country: str = DEFAULT_COUNTRY,
    language: str = DEFAULT_LANGUAGE,
) -> Gateway:
    """Resolve ThinQ2 hosts for a country / language pair."""
    response = client.get(V2_GATEWAY_URL, headers=thinq2_headers(country, language))
    response.raise_for_status()
    data = _unwrap_v2(response.json())
    uris = data.get("uris") if isinstance(data.get("uris"), dict) else {}
    oauth = None
    if isinstance(uris, dict):
        oauth = uris.get("empOauthBaseUri")
    oauth = oauth or data.get("empOauthBaseUri") or data.get("oauthUri")
    try:
        return Gateway(
            emp_uri=_ensure_slash(data["empUri"]),
            emp_terms_uri=_ensure_slash(data.get("empTermsUri") or data["empUri"]),
            emp_spx_uri=_ensure_slash(data["empSpxUri"]),
            thinq1_uri=_ensure_slash(data["thinq1Uri"]),
            thinq2_uri=_ensure_slash(data["thinq2Uri"]),
            oauth_uri=_ensure_slash(oauth) if oauth else None,
            country=country,
            language=language,
        )
    except KeyError as exc:
        raise AuthError(f"Gateway discovery returned an unexpected payload: missing {exc}") from exc


def parse_oauth_callback(url: str) -> dict[str, str]:
    """Parse the browser redirect URL after LG account login."""
    parsed = urlparse(url.strip())
    params = {key: values[0] for key, values in parse_qs(parsed.query).items()}
    if parsed.fragment:
        params.update({key: values[0] for key, values in parse_qs(parsed.fragment).items()})
    return params


def _oauth_request(
    client: httpx.Client,
    oauth_base: str,
    form: dict[str, str],
) -> dict[str, Any]:
    timestamp = _utc_oauth_date()
    req_url = f"{OAUTH_AUTH_PATH}?{urlencode(form)}"
    signature = oauth2_signature(f"{req_url}\n{timestamp}", OAUTH_SECRET_KEY)
    headers = {
        "x-lge-appkey": CLIENT_ID,
        "x-lge-oauth-signature": signature,
        "x-lge-oauth-date": timestamp,
        "Accept": "application/json",
    }
    response = client.post(urljoin(oauth_base, OAUTH_AUTH_PATH), headers=headers, data=form)
    if response.status_code != 200:
        raise TokenError(f"OAuth token endpoint returned HTTP {response.status_code}")
    payload = response.json()
    if "access_token" not in payload:
        raise TokenError(str(payload.get("error_description") or payload or "token rejected"))
    return payload


def exchange_auth_code(
    client: httpx.Client,
    oauth_base: str,
    code: str,
) -> dict[str, Any]:
    """Swap an authorization code for access + refresh tokens."""
    return _oauth_request(
        client,
        oauth_base,
        {
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": EMP_REDIRECT_URL,
        },
    )


def refresh_access_token(
    client: httpx.Client,
    oauth_base: str,
    refresh_token: str,
) -> dict[str, Any]:
    """Get a new access token from a refresh token."""
    return _oauth_request(
        client,
        oauth_base,
        {"grant_type": "refresh_token", "refresh_token": refresh_token},
    )


def fetch_user_number(client: httpx.Client, oauth_base: str, access_token: str) -> str:
    """Resolve the EMP user number required by ThinQ2 headers."""
    timestamp = _utc_oauth_date()
    signature = oauth2_signature(f"{USER_INFO_PATH}\n{timestamp}", OAUTH_SECRET_KEY)
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {access_token}",
        "X-Lge-Svccode": SVC_CODE,
        "X-Application-Key": APPLICATION_KEY,
        "lgemp-x-app-key": CLIENT_ID,
        "X-Device-Type": "M01",
        "X-Device-Platform": "ADR",
        "x-lge-oauth-date": timestamp,
        "x-lge-oauth-signature": signature,
    }
    response = client.get(urljoin(oauth_base, USER_INFO_PATH), headers=headers)
    response.raise_for_status()
    payload = response.json()
    account = payload.get("account") or {}
    user_no = account.get("userNo")
    if not user_no:
        raise AuthError("EMP profile response did not include a user number")
    return str(user_no)


def resolve_oauth_base(gateway: Gateway) -> str:
    if gateway.oauth_uri:
        return gateway.oauth_uri
    # Fallback used by community clients when gateway-uri omits empOauthBaseUri.
    return "https://us.lgeapi.com/"


def credentials_from_callback(
    client: httpx.Client,
    gateway: Gateway,
    callback_url: str,
) -> Credentials:
    """Finish login from the URL the browser lands on after LG account OAuth."""
    params = parse_oauth_callback(callback_url)
    oauth_base = params.get("oauth2_backend_url") or resolve_oauth_base(gateway)
    if not oauth_base.endswith("/"):
        oauth_base += "/"

    refresh_token = params.get("refresh_token")
    access_token = params.get("access_token")
    if params.get("code") and not refresh_token:
        tokens = exchange_auth_code(client, oauth_base, params["code"])
        refresh_token = tokens["refresh_token"]
        access_token = tokens.get("access_token")
    if not refresh_token:
        raise AuthError(
            "Callback URL did not contain a refresh_token or authorization code. "
            "Copy the full redirected URL from the browser address bar."
        )

    if not access_token:
        tokens = refresh_access_token(client, oauth_base, refresh_token)
        access_token = tokens["access_token"]

    user_number = params.get("user_number")
    if not user_number and access_token:
        try:
            user_number = fetch_user_number(client, oauth_base, access_token)
        except (AuthError, httpx.HTTPError):
            user_number = None

    seed = user_number or refresh_token[:32]
    client_id = hashlib.sha256(f"thinq-specialty:{seed}".encode()).hexdigest()
    return Credentials(
        refresh_token=refresh_token,
        access_token=access_token,
        user_number=user_number,
        client_id=client_id,
        country=gateway.country,
        language=gateway.language,
    )

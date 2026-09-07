import pytest

from thinq_specialty.auth import Credentials, parse_oauth_callback
from thinq_specialty.exceptions import AuthError


def test_parse_oauth_callback_query_and_fragment():
    params = parse_oauth_callback(
        "https://kr.m.lgaccount.com/login/iabClose?code=abc123&user_number=U1#access_token=tok"
    )
    assert params["code"] == "abc123"
    assert params["user_number"] == "U1"
    assert params["access_token"] == "tok"


def test_credentials_from_env_requires_refresh(monkeypatch):
    monkeypatch.delenv("THINQ_REFRESH_TOKEN", raising=False)
    with pytest.raises(AuthError, match="THINQ_REFRESH_TOKEN"):
        Credentials.from_env()


def test_credentials_from_env(monkeypatch):
    monkeypatch.setenv("THINQ_REFRESH_TOKEN", "refresh-example")
    monkeypatch.setenv("THINQ_COUNTRY", "US")
    creds = Credentials.from_env()
    assert creds.refresh_token == "refresh-example"
    assert "THINQ_REFRESH_TOKEN=refresh-example" in creds.export_lines()

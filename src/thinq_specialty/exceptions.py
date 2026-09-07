"""Errors raised by the unofficial ThinQ2 client."""


class ThinQError(Exception):
    """Base error for ThinQ2 client failures."""

    def __init__(self, message: str, code: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.code = code

    def __str__(self) -> str:
        if self.code:
            return f"[{self.code}] {self.message}"
        return self.message


class AuthError(ThinQError):
    """Login or session setup failed."""


class TokenError(AuthError):
    """Refresh token was rejected or expired."""


class APIError(ThinQError):
    """The ThinQ2 service returned a non-success result code."""


class DeviceNotFoundError(ThinQError):
    """No matching laundry device is available on the account."""


class ModelInfoError(ThinQError):
    """Device model JSON is missing, invalid, or lacks a course catalog."""


class PayloadError(ThinQError):
    """A remote-start payload could not be built from the requested inputs."""

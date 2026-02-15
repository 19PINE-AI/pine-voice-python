"""Exception hierarchy for the Pine Voice SDK."""

from __future__ import annotations

from typing import Dict, NoReturn, Optional


class PineVoiceError(Exception):
    """Base exception for all Pine Voice SDK errors.

    Attributes:
        code: Machine-readable error code from the API (e.g. "TOKEN_EXPIRED").
        status: HTTP status code.
        message: Human-readable error description.
    """

    def __init__(self, code: str, message: str, status: int = 0) -> None:
        super().__init__(message)
        self.code = code
        self.status = status
        self.message = message


class AuthError(PineVoiceError):
    """Authentication errors (401, token expired, missing credentials)."""


class RateLimitError(PineVoiceError):
    """Rate limit errors (429)."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(code, message, 429)


class CallError(PineVoiceError):
    """Call-specific errors (invalid phone, DND blocked, policy violation, etc.)."""


_CALL_ERROR_CODES = frozenset({
    "INVALID_PHONE",
    "DND_BLOCKED",
    "POLICY_VIOLATION",
    "INSUFFICIENT_DETAIL",
    "SUBSCRIPTION_REQUIRED",
    "INSUFFICIENT_CREDITS",
    "ACCESS_DENIED",
    "NOT_FOUND",
})


def raise_api_error(http_status: int, body: Optional[Dict[str, object]]) -> NoReturn:
    """Parse an API error response and raise the appropriate typed exception.

    This function always raises.
    """
    error = (body or {}).get("error", {})
    code: str = error.get("code", "UNKNOWN")
    message: str = error.get("message", f"HTTP {http_status}")

    if http_status == 401 or code in ("TOKEN_EXPIRED", "AUTH_REQUIRED"):
        raise AuthError(code, message, http_status)
    if http_status == 429 or code == "RATE_LIMITED":
        raise RateLimitError(code, message)
    if code in _CALL_ERROR_CODES:
        raise CallError(code, message, http_status)

    raise PineVoiceError(code, message, http_status)

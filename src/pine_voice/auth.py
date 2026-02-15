"""Authentication helpers for Pine Voice (sync and async)."""

from __future__ import annotations

import httpx

from .exceptions import AuthError
from .types import Credentials

DEFAULT_AUTH_URL = "https://www.19pine.ai"


class Auth:
    """Synchronous authentication helpers. Access via ``PineVoice.auth``."""

    def __init__(self, auth_url: str = DEFAULT_AUTH_URL) -> None:
        self._auth_url = auth_url.rstrip("/")

    def request_code(self, email: str) -> str:
        """Request a verification code sent to *email*.

        Returns:
            The ``request_token`` needed for :meth:`verify_code`.
        """
        resp = httpx.post(
            f"{self._auth_url}/api/v2/auth/email/request",
            json={"email": email},
        )
        if resp.status_code >= 400:
            body = resp.json() if resp.content else {}
            code = body.get("error", {}).get("code", "AUTH_REQUEST_FAILED")
            msg = body.get("error", {}).get("message", f"HTTP {resp.status_code}")
            raise AuthError(code, msg, resp.status_code)

        data = resp.json()
        token = (data.get("data") or {}).get("request_token")
        if not token:
            raise AuthError("NO_TOKEN", "Server did not return a request token", 500)
        return token

    def verify_code(self, email: str, request_token: str, code: str) -> Credentials:
        """Verify the email code and return access credentials.

        Returns:
            :class:`~pine_voice.types.Credentials` with ``access_token`` and ``user_id``.
        """
        resp = httpx.post(
            f"{self._auth_url}/api/v2/auth/email/verify",
            json={"email": email, "request_token": request_token, "code": code},
        )
        if resp.status_code >= 400:
            body = resp.json() if resp.content else {}
            err_code = body.get("error", {}).get("code", "AUTH_VERIFY_FAILED")
            msg = body.get("error", {}).get("message", f"HTTP {resp.status_code}")
            raise AuthError(err_code, msg, resp.status_code)

        data = resp.json()
        access_token = (data.get("data") or {}).get("access_token")
        user_id = (data.get("data") or {}).get("id")
        if not access_token or not user_id:
            raise AuthError("NO_CREDENTIALS", "Server did not return valid credentials", 500)

        return Credentials(access_token=access_token, user_id=user_id)


class AsyncAuth:
    """Asynchronous authentication helpers. Access via ``AsyncPineVoice.auth``."""

    def __init__(self, auth_url: str = DEFAULT_AUTH_URL) -> None:
        self._auth_url = auth_url.rstrip("/")

    async def request_code(self, email: str) -> str:
        """Request a verification code sent to *email*.

        Returns:
            The ``request_token`` needed for :meth:`verify_code`.
        """
        async with httpx.AsyncClient() as http:
            resp = await http.post(
                f"{self._auth_url}/api/v2/auth/email/request",
                json={"email": email},
            )
        if resp.status_code >= 400:
            body = resp.json() if resp.content else {}
            code = body.get("error", {}).get("code", "AUTH_REQUEST_FAILED")
            msg = body.get("error", {}).get("message", f"HTTP {resp.status_code}")
            raise AuthError(code, msg, resp.status_code)

        data = resp.json()
        token = (data.get("data") or {}).get("request_token")
        if not token:
            raise AuthError("NO_TOKEN", "Server did not return a request token", 500)
        return token

    async def verify_code(self, email: str, request_token: str, code: str) -> Credentials:
        """Verify the email code and return access credentials.

        Returns:
            :class:`~pine_voice.types.Credentials` with ``access_token`` and ``user_id``.
        """
        async with httpx.AsyncClient() as http:
            resp = await http.post(
                f"{self._auth_url}/api/v2/auth/email/verify",
                json={"email": email, "request_token": request_token, "code": code},
            )
        if resp.status_code >= 400:
            body = resp.json() if resp.content else {}
            err_code = body.get("error", {}).get("code", "AUTH_VERIFY_FAILED")
            msg = body.get("error", {}).get("message", f"HTTP {resp.status_code}")
            raise AuthError(err_code, msg, resp.status_code)

        data = resp.json()
        access_token = (data.get("data") or {}).get("access_token")
        user_id = (data.get("data") or {}).get("id")
        if not access_token or not user_id:
            raise AuthError("NO_CREDENTIALS", "Server did not return valid credentials", 500)

        return Credentials(access_token=access_token, user_id=user_id)

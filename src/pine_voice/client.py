"""Synchronous Pine Voice client."""

from __future__ import annotations

from typing import Optional

import httpx

from ._base_client import _BasePineVoice
from .auth import Auth
from .calls import CallsAPI


class PineVoice(_BasePineVoice):
    """Synchronous Pine Voice SDK client.

    Example::

        from pine_voice import PineVoice

        client = PineVoice(access_token="...", user_id="...")
        result = client.calls.create_and_wait(
            to="+14155551234",
            name="Dr. Smith Office",
            context="Local dentist office",
            objective="Schedule a cleaning for Tuesday",
        )
        print(result.transcript)
    """

    auth = Auth()
    """Static authentication helpers (no credentials needed)."""

    def __init__(
        self,
        access_token: Optional[str] = None,
        user_id: Optional[str] = None,
        gateway_url: Optional[str] = None,
    ) -> None:
        super().__init__(access_token, user_id, gateway_url)
        self._http = httpx.Client(timeout=httpx.Timeout(30.0, read=300.0))
        self.calls = CallsAPI(self._http, self._gateway_url, self._headers())

    def close(self) -> None:
        """Close the underlying HTTP client."""
        self._http.close()

    def __enter__(self) -> PineVoice:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

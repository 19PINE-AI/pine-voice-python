"""Asynchronous Pine Voice client."""

from __future__ import annotations

from typing import Optional

import httpx

from ._base_client import _BasePineVoice
from .auth import AsyncAuth
from .calls import AsyncCallsAPI


class AsyncPineVoice(_BasePineVoice):
    """Asynchronous Pine Voice SDK client.

    Example::

        from pine_voice import AsyncPineVoice

        client = AsyncPineVoice(access_token="...", user_id="...")
        result = await client.calls.create_and_wait(
            to="+14155551234",
            name="Dr. Smith Office",
            context="Local dentist office",
            objective="Schedule a cleaning for Tuesday",
        )
        print(result.summary)
    """

    auth = AsyncAuth()
    """Static async authentication helpers (no credentials needed)."""

    def __init__(
        self,
        access_token: Optional[str] = None,
        user_id: Optional[str] = None,
        gateway_url: Optional[str] = None,
    ) -> None:
        super().__init__(access_token, user_id, gateway_url)
        self._http = httpx.AsyncClient(timeout=httpx.Timeout(30.0, read=300.0))
        self.calls = AsyncCallsAPI(self._http, self._gateway_url, self._headers())

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._http.aclose()

    async def __aenter__(self) -> AsyncPineVoice:
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.close()

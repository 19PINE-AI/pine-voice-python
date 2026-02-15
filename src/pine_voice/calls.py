"""Sync and async voice call APIs."""

from __future__ import annotations

import asyncio
import time
from typing import Optional, Union
from urllib.parse import quote

import httpx

from ._base_client import (
    TERMINAL_STATUSES,
    build_call_body,
    check_response,
    parse_call_initiated,
    parse_call_response,
)
from .types import CallInitiated, CallResult, CallStatus

DEFAULT_POLL_INTERVAL = 10  # seconds


class CallsAPI:
    """Synchronous voice call operations. Access via ``client.calls``."""

    def __init__(self, http: httpx.Client, gateway_url: str, headers: dict) -> None:
        self._http = http
        self._gateway_url = gateway_url
        self._headers = headers

    def create(
        self,
        *,
        to: str,
        name: str,
        context: str,
        objective: str,
        instructions: Optional[str] = None,
        caller: Optional[str] = None,
        voice: Optional[str] = None,
        max_duration_minutes: Optional[int] = None,
    ) -> CallInitiated:
        """Initiate a phone call. Returns immediately with a call ID.

        Use :meth:`get` or :meth:`create_and_wait` to track progress.
        """
        body = build_call_body(
            to=to,
            name=name,
            context=context,
            objective=objective,
            instructions=instructions,
            caller=caller,
            voice=voice,
            max_duration_minutes=max_duration_minutes,
        )
        resp = self._http.post(
            f"{self._gateway_url}/api/v2/voice/call",
            json=body,
            headers=self._headers,
        )
        data = resp.json() if resp.content else None
        check_response(resp.status_code, data)
        return parse_call_initiated(data)  # type: ignore[arg-type]

    def get(self, call_id: str) -> Union[CallStatus, CallResult]:
        """Get the current status of a call.

        Returns full transcript and summary when the call is complete.
        """
        resp = self._http.get(
            f"{self._gateway_url}/api/v2/voice/call/{quote(call_id, safe='')}",
            headers=self._headers,
        )
        data = resp.json() if resp.content else None
        check_response(resp.status_code, data)
        return parse_call_response(data)  # type: ignore[arg-type]

    def create_and_wait(
        self,
        *,
        to: str,
        name: str,
        context: str,
        objective: str,
        instructions: Optional[str] = None,
        caller: Optional[str] = None,
        voice: Optional[str] = None,
        max_duration_minutes: Optional[int] = None,
        poll_interval: int = DEFAULT_POLL_INTERVAL,
    ) -> CallResult:
        """Initiate a call and block until it reaches a terminal state.

        Args:
            poll_interval: Seconds between status checks (default 10).

        Returns:
            The completed :class:`~pine_voice.types.CallResult`.
        """
        initiated = self.create(
            to=to,
            name=name,
            context=context,
            objective=objective,
            instructions=instructions,
            caller=caller,
            voice=voice,
            max_duration_minutes=max_duration_minutes,
        )
        while True:
            time.sleep(poll_interval)
            result = self.get(initiated.call_id)
            if result.status in TERMINAL_STATUSES:
                return result  # type: ignore[return-value]


class AsyncCallsAPI:
    """Asynchronous voice call operations. Access via ``client.calls``."""

    def __init__(self, http: httpx.AsyncClient, gateway_url: str, headers: dict) -> None:
        self._http = http
        self._gateway_url = gateway_url
        self._headers = headers

    async def create(
        self,
        *,
        to: str,
        name: str,
        context: str,
        objective: str,
        instructions: Optional[str] = None,
        caller: Optional[str] = None,
        voice: Optional[str] = None,
        max_duration_minutes: Optional[int] = None,
    ) -> CallInitiated:
        """Initiate a phone call. Returns immediately with a call ID.

        Use :meth:`get` or :meth:`create_and_wait` to track progress.
        """
        body = build_call_body(
            to=to,
            name=name,
            context=context,
            objective=objective,
            instructions=instructions,
            caller=caller,
            voice=voice,
            max_duration_minutes=max_duration_minutes,
        )
        resp = await self._http.post(
            f"{self._gateway_url}/api/v2/voice/call",
            json=body,
            headers=self._headers,
        )
        data = resp.json() if resp.content else None
        check_response(resp.status_code, data)
        return parse_call_initiated(data)  # type: ignore[arg-type]

    async def get(self, call_id: str) -> Union[CallStatus, CallResult]:
        """Get the current status of a call.

        Returns full transcript and summary when the call is complete.
        """
        resp = await self._http.get(
            f"{self._gateway_url}/api/v2/voice/call/{quote(call_id, safe='')}",
            headers=self._headers,
        )
        data = resp.json() if resp.content else None
        check_response(resp.status_code, data)
        return parse_call_response(data)  # type: ignore[arg-type]

    async def create_and_wait(
        self,
        *,
        to: str,
        name: str,
        context: str,
        objective: str,
        instructions: Optional[str] = None,
        caller: Optional[str] = None,
        voice: Optional[str] = None,
        max_duration_minutes: Optional[int] = None,
        poll_interval: int = DEFAULT_POLL_INTERVAL,
    ) -> CallResult:
        """Initiate a call and await until it reaches a terminal state.

        Args:
            poll_interval: Seconds between status checks (default 10).

        Returns:
            The completed :class:`~pine_voice.types.CallResult`.
        """
        initiated = await self.create(
            to=to,
            name=name,
            context=context,
            objective=objective,
            instructions=instructions,
            caller=caller,
            voice=voice,
            max_duration_minutes=max_duration_minutes,
        )
        while True:
            await asyncio.sleep(poll_interval)
            result = await self.get(initiated.call_id)
            if result.status in TERMINAL_STATUSES:
                return result  # type: ignore[return-value]

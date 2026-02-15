"""Sync and async voice call APIs."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, Dict, Optional, Union
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
_MAX_SSE_RECONNECTS = 1
_SSE_TIMEOUT = httpx.Timeout(30.0, read=7500.0)  # long read timeout for SSE

_log = logging.getLogger("pine_voice")


# --- Shared SSE parsing ---

def _parse_sse_event(lines: list[str]) -> Dict[str, str]:
    """Parse accumulated SSE lines into an event dict with id/event/data fields."""
    event: Dict[str, str] = {}
    data_parts: list[str] = []
    for line in lines:
        if line.startswith("id:"):
            event["id"] = line[3:].strip()
        elif line.startswith("event:"):
            event["event"] = line[6:].strip()
        elif line.startswith("data:"):
            data_parts.append(line[5:].strip())
        # Lines starting with ':' are comments (heartbeats) — ignore
    if data_parts:
        event["data"] = "\n".join(data_parts)
    return event


def _result_from_sse_data(raw: str) -> CallResult:
    """Deserialize an SSE data payload into a CallResult via parse_call_response."""
    data: Dict[str, Any] = json.loads(raw)
    result = parse_call_response(data)
    if not isinstance(result, CallResult):
        raise ValueError("SSE result event did not contain a terminal status")
    return result


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
        enable_summary: bool = False,
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
            enable_summary=enable_summary,
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

        Returns full transcript when the call is complete
        (and summary if ``enable_summary`` was set).
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
        enable_summary: bool = False,
        poll_interval: int = DEFAULT_POLL_INTERVAL,
        use_sse: bool = True,
    ) -> CallResult:
        """Initiate a call and block until it reaches a terminal state.

        Automatically uses SSE for real-time delivery, falling back to
        polling if SSE is unavailable or the connection drops.

        Args:
            enable_summary: Request an LLM-generated summary after the call (default False).
            poll_interval: Seconds between status checks for polling fallback (default 10).
            use_sse: Try SSE streaming first (default True). Set False to force polling.

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
            enable_summary=enable_summary,
        )
        if use_sse:
            try:
                return self._stream_until_complete(initiated.call_id)
            except Exception:
                _log.debug("SSE failed for call %s, falling back to polling", initiated.call_id)
        return self._poll_until_complete(initiated.call_id, poll_interval)

    def _poll_until_complete(self, call_id: str, poll_interval: int) -> CallResult:
        """Poll GET endpoint until a terminal status is reached."""
        while True:
            time.sleep(poll_interval)
            result = self.get(call_id)
            if result.status in TERMINAL_STATUSES:
                return result  # type: ignore[return-value]

    def _stream_until_complete(self, call_id: str) -> CallResult:
        """Open an SSE stream and wait for the result event.

        Reconnects up to ``_MAX_SSE_RECONNECTS`` times on connection drop.
        """
        last_event_id: Optional[str] = None
        for attempt in range(_MAX_SSE_RECONNECTS + 1):
            try:
                result, last_event_id = self._sse_connect(call_id, last_event_id)
                if result is not None:
                    return result
            except (httpx.TransportError, httpx.StreamError) as exc:
                if attempt >= _MAX_SSE_RECONNECTS:
                    raise
                _log.debug("SSE connection lost (attempt %d), reconnecting: %s", attempt, exc)
        raise RuntimeError("SSE stream ended without result")

    def _sse_connect(
        self, call_id: str, last_event_id: Optional[str]
    ) -> tuple[Optional[CallResult], Optional[str]]:
        """Single SSE connection attempt.

        Returns (CallResult, last_event_id) or (None, last_event_id) if stream ended cleanly.
        """
        url = f"{self._gateway_url}/api/v2/voice/call/{quote(call_id, safe='')}/stream"
        headers = {**self._headers, "Accept": "text/event-stream"}
        if last_event_id:
            headers["Last-Event-Id"] = last_event_id

        with self._http.stream("GET", url, headers=headers, timeout=_SSE_TIMEOUT) as resp:
            if resp.status_code >= 400:
                data = None
                try:
                    body = b"".join(resp.iter_bytes())
                    data = json.loads(body)
                except Exception:
                    pass
                check_response(resp.status_code, data)

            buf: list[str] = []
            for raw_line in resp.iter_lines():
                line = raw_line.rstrip("\r\n") if isinstance(raw_line, str) else raw_line.decode().rstrip("\r\n")
                if line:
                    buf.append(line)
                else:
                    # Blank line = end of event
                    if buf:
                        event = _parse_sse_event(buf)
                        buf.clear()
                        if event.get("id"):
                            last_event_id = event["id"]
                        if event.get("event") == "result" and "data" in event:
                            return _result_from_sse_data(event["data"]), last_event_id
        return None, last_event_id


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
        enable_summary: bool = False,
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
            enable_summary=enable_summary,
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

        Returns full transcript when the call is complete
        (and summary if ``enable_summary`` was set).
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
        enable_summary: bool = False,
        poll_interval: int = DEFAULT_POLL_INTERVAL,
        use_sse: bool = True,
    ) -> CallResult:
        """Initiate a call and await until it reaches a terminal state.

        Automatically uses SSE for real-time delivery, falling back to
        polling if SSE is unavailable or the connection drops.

        Args:
            enable_summary: Request an LLM-generated summary after the call (default False).
            poll_interval: Seconds between status checks for polling fallback (default 10).
            use_sse: Try SSE streaming first (default True). Set False to force polling.

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
            enable_summary=enable_summary,
        )
        if use_sse:
            try:
                return await self._stream_until_complete(initiated.call_id)
            except Exception:
                _log.debug("SSE failed for call %s, falling back to polling", initiated.call_id)
        return await self._poll_until_complete(initiated.call_id, poll_interval)

    async def _poll_until_complete(self, call_id: str, poll_interval: int) -> CallResult:
        """Poll GET endpoint until a terminal status is reached."""
        while True:
            await asyncio.sleep(poll_interval)
            result = await self.get(call_id)
            if result.status in TERMINAL_STATUSES:
                return result  # type: ignore[return-value]

    async def _stream_until_complete(self, call_id: str) -> CallResult:
        """Open an SSE stream and wait for the result event.

        Reconnects up to ``_MAX_SSE_RECONNECTS`` times on connection drop.
        """
        last_event_id: Optional[str] = None
        for attempt in range(_MAX_SSE_RECONNECTS + 1):
            try:
                result, last_event_id = await self._sse_connect(call_id, last_event_id)
                if result is not None:
                    return result
            except (httpx.TransportError, httpx.StreamError) as exc:
                if attempt >= _MAX_SSE_RECONNECTS:
                    raise
                _log.debug("SSE connection lost (attempt %d), reconnecting: %s", attempt, exc)
        raise RuntimeError("SSE stream ended without result")

    async def _sse_connect(
        self, call_id: str, last_event_id: Optional[str]
    ) -> tuple[Optional[CallResult], Optional[str]]:
        """Single async SSE connection attempt.

        Returns (CallResult, last_event_id) or (None, last_event_id) if stream ended cleanly.
        """
        url = f"{self._gateway_url}/api/v2/voice/call/{quote(call_id, safe='')}/stream"
        headers = {**self._headers, "Accept": "text/event-stream"}
        if last_event_id:
            headers["Last-Event-Id"] = last_event_id

        async with self._http.stream("GET", url, headers=headers, timeout=_SSE_TIMEOUT) as resp:
            if resp.status_code >= 400:
                data = None
                try:
                    body = b"".join([chunk async for chunk in resp.aiter_bytes()])
                    data = json.loads(body)
                except Exception:
                    pass
                check_response(resp.status_code, data)

            buf: list[str] = []
            async for raw_line in resp.aiter_lines():
                line = raw_line.rstrip("\r\n") if isinstance(raw_line, str) else raw_line.decode().rstrip("\r\n")
                if line:
                    buf.append(line)
                else:
                    # Blank line = end of event
                    if buf:
                        event = _parse_sse_event(buf)
                        buf.clear()
                        if event.get("id"):
                            last_event_id = event["id"]
                        if event.get("event") == "result" and "data" in event:
                            return _result_from_sse_data(event["data"]), last_event_id
        return None, last_event_id

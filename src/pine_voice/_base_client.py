"""Shared base logic for sync and async Pine Voice clients."""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from .exceptions import AuthError, PineVoiceError, raise_api_error
from .types import CallInitiated, CallResult, CallStatus, TranscriptEntry

DEFAULT_GATEWAY_URL = "https://agent3-api-gateway-staging.19pine.ai"
TERMINAL_STATUSES = frozenset({"completed", "failed", "cancelled"})


def _env_fallback(explicit: Optional[str], env_var: str) -> Optional[str]:
    """Resolve: explicit value > environment variable > None."""
    if explicit:
        return explicit
    return os.environ.get(env_var) or None


class _BasePineVoice:
    """Shared configuration and helpers for PineVoice / AsyncPineVoice."""

    def __init__(
        self,
        access_token: Optional[str] = None,
        user_id: Optional[str] = None,
        gateway_url: Optional[str] = None,
    ) -> None:
        resolved_token = _env_fallback(access_token, "PINE_ACCESS_TOKEN")
        resolved_user = _env_fallback(user_id, "PINE_USER_ID")

        if not resolved_token or not resolved_user:
            raise AuthError(
                "MISSING_CREDENTIALS",
                "Pine Voice requires access_token and user_id. "
                "Pass them in the constructor or set PINE_ACCESS_TOKEN and PINE_USER_ID environment variables.",
            )

        self._access_token: str = resolved_token
        self._user_id: str = resolved_user
        self._gateway_url = (
            _env_fallback(gateway_url, "PINE_GATEWAY_URL") or DEFAULT_GATEWAY_URL
        ).rstrip("/")

    def _headers(self) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._access_token}",
            "X-Pine-User-Id": self._user_id,
        }


# ---- Shared param/response mapping ----

def build_call_body(
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
) -> Dict[str, Any]:
    """Map SDK parameters to wire-format JSON body."""
    body: Dict[str, Any] = {
        "dialed_number": to,
        "callee_name": name,
        "callee_context": context,
        "call_objective": objective,
        "detailed_instructions": instructions or "",
        "max_duration_minutes": max_duration_minutes if max_duration_minutes is not None else 120,
    }
    if caller is not None:
        body["caller"] = caller
    if voice is not None:
        body["voice"] = voice
    if enable_summary:
        body["enable_summary"] = True
    return body


def parse_call_initiated(data: Optional[Dict[str, Any]]) -> CallInitiated:
    if not data or "call_id" not in data:
        raise PineVoiceError("EMPTY_RESPONSE", "Server returned an empty or invalid response", 200)
    return CallInitiated(call_id=data["call_id"], status="in_progress")


def parse_call_response(data: Optional[Dict[str, Any]]) -> CallStatus | CallResult:
    """Parse API response into CallStatus or CallResult."""
    if not data:
        raise PineVoiceError("EMPTY_RESPONSE", "Server returned an empty or invalid response", 200)
    status = data.get("status", "")

    if status in TERMINAL_STATUSES:
        transcript_raw: List[Dict[str, str]] = data.get("transcript") or []
        transcript = [
            TranscriptEntry(speaker=t.get("speaker", ""), text=t.get("text", ""))
            for t in transcript_raw
        ]
        return CallResult(
            call_id=data.get("call_id", ""),
            status=status,
            duration_seconds=data.get("duration_seconds", 0),
            summary=data.get("summary", ""),
            transcript=transcript,
            triage_category=data.get("triage_category", ""),
            credits_charged=data.get("credits_charged", 0),
        )

    return CallStatus(
        call_id=data.get("call_id", ""),
        status=status,
        duration_seconds=data.get("duration_seconds"),
    )


def check_response(status_code: int, data: Optional[Dict[str, Any]]) -> None:
    """Raise if the HTTP response indicates an error."""
    if status_code >= 400:
        raise_api_error(status_code, data)

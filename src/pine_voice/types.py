"""Data types for the Pine Voice SDK."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Credentials:
    """Access credentials returned after email verification."""

    access_token: str
    user_id: str


@dataclass
class CallInitiated:
    """Returned when a call is successfully initiated."""

    call_id: str
    status: str  # "in_progress"


@dataclass
class TranscriptEntry:
    """A single turn in the call transcript."""

    speaker: str  # "agent" | "user"
    text: str


@dataclass
class TranscriptTurn:
    """A single speaker turn in a transcript."""

    speaker: str
    text: str


@dataclass
class CallStatus:
    """Returned when polling a call that may still be in progress."""

    call_id: str
    status: str  # "initiated" | "in_progress" | "completed" | "failed" | "cancelled"
    duration_seconds: Optional[int] = None
    phase: Optional[str] = None
    partial_transcript: Optional[List[TranscriptTurn]] = None


@dataclass
class CallProgress:
    """Call progress snapshot (non-terminal state).

    Note: Real-time intermediate updates (partial transcripts, phase changes
    like "connected") are NOT currently available. The server does not provide
    real-time call progress events. The SSE stream delivers only the final
    result after call completion. During polling fallback, progress callbacks
    will fire with basic status information but no partial transcript data.
    """

    call_id: str
    status: str
    phase: Optional[str] = None
    duration_seconds: Optional[int] = None
    partial_transcript: Optional[List[TranscriptTurn]] = None


@dataclass
class CallResult:
    """Returned when a call reaches a terminal state."""

    call_id: str
    status: str
    duration_seconds: int = 0
    summary: str = ""
    transcript: List[TranscriptEntry] = field(default_factory=list)
    credits_charged: int = 0

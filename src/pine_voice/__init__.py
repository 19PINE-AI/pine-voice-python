"""Pine Voice SDK — official Python client for Pine AI voice calls."""

__version__ = "0.1.5"

from .async_client import AsyncPineVoice
from .client import PineVoice
from .exceptions import AuthError, CallError, PineVoiceError, RateLimitError
from .types import (
    CallInitiated,
    CallProgress,
    CallResult,
    CallStatus,
    Credentials,
    TranscriptEntry,
)

__all__ = [
    "__version__",
    "PineVoice",
    "AsyncPineVoice",
    "PineVoiceError",
    "AuthError",
    "RateLimitError",
    "CallError",
    "Credentials",
    "CallInitiated",
    "CallStatus",
    "CallProgress",
    "CallResult",
    "TranscriptEntry",
]

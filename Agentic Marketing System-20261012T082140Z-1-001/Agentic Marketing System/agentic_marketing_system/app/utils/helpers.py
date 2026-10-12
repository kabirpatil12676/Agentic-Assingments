"""
Shared helper functions.

Small, pure utilities that don't belong to any single agent or service.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone


def generate_id(prefix: str = "") -> str:
    """Return a short unique ID, optionally prefixed (e.g. ``cmp_a1b2c3``)."""
    short = uuid.uuid4().hex[:8]
    return f"{prefix}_{short}" if prefix else short


def utcnow_iso() -> str:
    """Return current UTC time as an ISO-8601 string."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """Division that returns *default* instead of raising on zero-denominator."""
    if denominator == 0:
        return default
    return numerator / denominator


def clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    """Clamp a value to [lo, hi]."""
    return max(lo, min(hi, value))

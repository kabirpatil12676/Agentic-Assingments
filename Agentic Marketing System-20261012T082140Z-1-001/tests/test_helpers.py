"""
Tests for utility helpers.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.utils.helpers import generate_id, safe_divide, clamp, utcnow_iso


def test_generate_id_with_prefix() -> None:
    result = generate_id("cmp")
    assert result.startswith("cmp_")
    assert len(result) == 12  # "cmp_" + 8 hex chars


def test_generate_id_no_prefix() -> None:
    result = generate_id()
    assert "_" not in result
    assert len(result) == 8


def test_safe_divide_normal() -> None:
    assert safe_divide(10, 2) == 5.0


def test_safe_divide_zero() -> None:
    assert safe_divide(10, 0) == 0.0
    assert safe_divide(10, 0, default=-1.0) == -1.0


def test_clamp() -> None:
    assert clamp(0.5) == 0.5
    assert clamp(-0.1) == 0.0
    assert clamp(1.5) == 1.0
    assert clamp(50, lo=0, hi=100) == 50


def test_utcnow_iso() -> None:
    result = utcnow_iso()
    assert result.endswith("Z")
    assert "T" in result

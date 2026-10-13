"""
Tests for configuration loading.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import load_config, LLMConfig, Config


def test_default_config() -> None:
    """load_config() should return sane defaults when no env vars are set."""
    cfg = load_config()
    assert isinstance(cfg, Config)
    assert cfg.llm.provider in ("ollama", "openai")
    assert cfg.max_optimization_loops >= 1


def test_env_override(monkeypatch) -> None:
    """Environment variables should override defaults."""
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("LLM_MODEL", "gpt-4o")
    monkeypatch.setenv("DEMO_MODE", "false")
    monkeypatch.setenv("MAX_OPT_LOOPS", "5")

    cfg = load_config()
    assert cfg.llm.provider == "openai"
    assert cfg.llm.model == "gpt-4o"
    assert cfg.demo_mode is False
    assert cfg.max_optimization_loops == 5

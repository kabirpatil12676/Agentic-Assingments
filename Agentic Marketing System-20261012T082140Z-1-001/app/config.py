"""
Application configuration.

Loads settings from environment variables / .env file.
Provides a single Config dataclass used throughout the system.
"""

from __future__ import annotations

import os
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent  # agentic_marketing_system/
DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
GENERATED_DATA_DIR = DATA_DIR / "generated"
DB_PATH = GENERATED_DATA_DIR / "marketing.db"

# ---------------------------------------------------------------------------
# Configuration dataclass
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class LLMConfig:
    """LLM provider settings."""
    provider: Literal["ollama", "openai"] = "ollama"
    model: str = "qwen3:8b"
    base_url: str = "http://localhost:11434"
    api_key: str = ""           # only needed for openai-compatible
    temperature: float = 0.7
    max_tokens: int = 2048
    timeout: int = 120


@dataclass(frozen=True)
class Config:
    """Top-level application configuration."""
    # --- Mode ---
    demo_mode: bool = True      # deterministic mock mode – no external services
    log_level: str = "INFO"

    # --- LLM ---
    llm: LLMConfig = field(default_factory=LLMConfig)

    # --- Database ---
    db_path: Path = DB_PATH

    # --- Workflow ---
    max_optimization_loops: int = 3
    optimization_threshold: float = 0.05  # min lift to accept


def load_config() -> Config:
    """Build a Config from environment variables (with sane defaults)."""

    provider = os.getenv("LLM_PROVIDER", "ollama")
    model = os.getenv("LLM_MODEL", "qwen3:8b")
    base_url = os.getenv("LLM_BASE_URL", "http://localhost:11434")
    api_key = os.getenv("LLM_API_KEY", "")
    demo_mode = os.getenv("DEMO_MODE", "true").lower() in ("true", "1", "yes")
    log_level = os.getenv("LOG_LEVEL", "INFO")

    llm_cfg = LLMConfig(
        provider=provider,      # type: ignore[arg-type]
        model=model,
        base_url=base_url,
        api_key=api_key,
        temperature=float(os.getenv("LLM_TEMPERATURE", "0.7")),
        max_tokens=int(os.getenv("LLM_MAX_TOKENS", "2048")),
        timeout=int(os.getenv("LLM_TIMEOUT", "120")),
    )

    cfg = Config(
        demo_mode=demo_mode,
        log_level=log_level,
        llm=llm_cfg,
        db_path=Path(os.getenv("DB_PATH", str(DB_PATH))),
        max_optimization_loops=int(os.getenv("MAX_OPT_LOOPS", "3")),
        optimization_threshold=float(os.getenv("OPT_THRESHOLD", "0.05")),
    )

    logger.info("Config loaded  demo_mode=%s  provider=%s  model=%s",
                cfg.demo_mode, cfg.llm.provider, cfg.llm.model)
    return cfg

"""
Agentic AI Personalized Marketing Campaign Optimization System
==============================================================

Entry point.  Bootstraps configuration, logging, and the LangGraph
workflow, then runs the pipeline for a given user goal.

Usage:
    python main.py                   # runs in DEMO mode
    python main.py --goal "..."      # override goal text
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

# Ensure project root is on sys.path so ``app.*`` imports work.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.config import load_config  # noqa: E402
from app.utils.logging_config import setup_logging  # noqa: E402

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Agentic Marketing Campaign Optimization System",
    )
    parser.add_argument(
        "--goal",
        type=str,
        default="Launch an email campaign for our new wireless headphones targeting young professionals",
        help="Marketing goal in natural language",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        default=False,
        help="Force DEMO mode (overrides DEMO_MODE env var)",
    )
    return parser.parse_args()


async def run(goal_text: str, demo: bool) -> None:
    """Load config, build the workflow graph, and execute."""
    import os

    if demo:
        os.environ["DEMO_MODE"] = "true"

    config = load_config()
    setup_logging(config.log_level)

    logger.info("=" * 60)
    logger.info("Agentic Marketing System - starting")
    logger.info("Goal: %s", goal_text)
    logger.info("Demo mode: %s", config.demo_mode)
    logger.info("=" * 60)

    from app.models.schemas import WorkflowState, UserGoal, CampaignChannel
    from app.workflow.graph import build_workflow_graph

    workflow = build_workflow_graph(config)
    goal = UserGoal(
        goal_text=goal_text,
        budget=1000.0,
        target_audience="general",
        channels=[CampaignChannel.EMAIL],
    )
    initial_state = WorkflowState(goal=goal).model_dump()

    logger.info("Invoking workflow graph...")
    result = await workflow.ainvoke(initial_state)
    state = WorkflowState(**result)

    # ── Summary ────────────────────────────────────────────────────────────────
    logger.info("=" * 60)
    logger.info("Workflow complete.  Optimization iterations: %d", state.optimization_iteration)
    if state.product_info:
        logger.info("Product selected: %s (%s)", state.product_info.name, state.product_info.category)
    if state.segments:
        logger.info("Target segment: %s  (size=%d)", state.segments[-1].name, state.segments[-1].size)
    if state.campaigns:
        logger.info("Campaigns generated: %d", len(state.campaigns))
    if state.metrics:
        m = state.metrics[-1]
        logger.info(
            "Final metrics  open=%.2f%%  click=%.2f%%  conv=%.2f%%  roi=%.1f%%",
            m.open_rate * 100, m.click_rate * 100, m.conversion_rate * 100, m.roi * 100,
        )
    if state.baseline:
        b = state.baseline
        logger.info(
            "Baseline revenue=$%.2f  campaign_revenue=$%.2f  lift=%.2f%%  achieved=%s",
            b.historical_revenue,
            b.campaign_revenue or 0.0,
            (b.actual_lift_pct or 0.0) * 100,
            b.target_achieved,
        )
    if state.optimization:
        logger.info("Optimization decision: %s — %s", state.optimization.decision.value, state.optimization.reason)
    if state.errors:
        logger.warning("Errors encountered during run: %s", state.errors)
    logger.info("=" * 60)


def main() -> None:
    args = parse_args()
    asyncio.run(run(goal_text=args.goal, demo=args.demo))


if __name__ == "__main__":
    main()

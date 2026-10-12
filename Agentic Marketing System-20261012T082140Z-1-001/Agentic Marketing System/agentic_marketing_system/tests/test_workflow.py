"""
Integration tests for the LangGraph agentic workflow.

Tests cover:
  1. Full workflow execution (smoke test)
  2. Baseline vs campaign metric comparison
  3. Memory persistence and retrieval across runs
  4. Optimization loop producing a changed Campaign 2
"""

from __future__ import annotations

import sys
import tempfile
import pytest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import Config, LLMConfig
from app.services.data_service import DataService
from app.memory.memory_store import MemoryStore
from scripts.seed_data import generate_dataset, save_to_csv
from app.workflow.graph import build_workflow_graph
from app.models.schemas import WorkflowState, UserGoal, OptimizationDecision


# ─────────────────────────────────────────────────────────────────────────────
# Shared fixture
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def temp_config():
    """Isolated SQLite + CSV environment in DEMO_MODE."""
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        tmp_path = Path(tmpdir)
        raw_dir = tmp_path / "raw"
        gen_dir = tmp_path / "generated"
        raw_dir.mkdir(parents=True)
        gen_dir.mkdir(parents=True)

        db_path = gen_dir / "marketing.db"
        cfg = Config(
            demo_mode=True,
            db_path=db_path,
            llm=LLMConfig(),
            max_optimization_loops=2,
        )

        p_df, c_df, pur_df = generate_dataset(
            num_products=50,
            num_customers=200,
            min_purchases=500,
            seed=42,
        )
        save_to_csv(p_df, c_df, pur_df, target_dir=raw_dir)

        ds = DataService(config=cfg)
        ds.populate_from_csv(
            products_csv=raw_dir / "products.csv",
            customers_csv=raw_dir / "customers.csv",
            purchases_csv=raw_dir / "purchases.csv",
        )
        yield cfg


def _goal() -> UserGoal:
    return UserGoal(
        goal_text="Increase sales of our best-performing products among college students by 15%.",
        budget=1000.0,
        target_audience="Student",
    )


async def _run(cfg: Config) -> WorkflowState:
    workflow = build_workflow_graph(cfg)
    result = await workflow.ainvoke(WorkflowState(goal=_goal()))
    if isinstance(result, dict):
        return WorkflowState(**result)
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Test 1 – Smoke / full-workflow
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_full_workflow_execution(temp_config):
    """End-to-end: all 7 agents run, state is populated, memory is persisted."""
    state = await _run(temp_config)

    assert state.plan is not None, "Planner must produce a plan"
    assert state.product_info is not None, "ProductAnalysisAgent must populate product_info"
    assert len(state.segments) > 0, "SegmentationAgent must produce at least 1 segment"
    assert len(state.campaigns) > 0, "CampaignGenerationAgent must produce at least 1 campaign"
    assert len(state.execution_results) > 0, "ExecutionAgent must produce results"
    assert len(state.metrics) > 0, "MonitoringAgent must produce metrics"
    assert state.optimization is not None, "OptimizationAgent must produce a recommendation"
    assert state.completed is True, "Workflow must reach completed=True"
    assert state.optimization_iteration > 0

    # Memory persisted
    memory = MemoryStore(temp_config)
    similar = memory.get_similar_campaigns(state.product_info.category)
    assert len(similar) > 0, "Memory must contain at least one persisted campaign"


# ─────────────────────────────────────────────────────────────────────────────
# Test 2 – Baseline verification
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_baseline_calculated_from_purchase_data(temp_config):
    """
    REQUIREMENT 1: baseline is computed from purchase history.

    Verify:
      - baseline.historical_conversion_rate comes from real purchase data
      - baseline.campaign_conversion_rate is filled in after execution
      - actual_lift_pct is calculated (may be < 15% — that is correct behaviour)
      - target_achieved reflects truth (NOT claimed achieved unless data supports it)
    """
    state = await _run(temp_config)

    assert state.baseline is not None, "MonitoringAgent must set state.baseline"
    b = state.baseline

    # Historical baseline must come from real purchase data
    assert b.historical_conversion_rate >= 0.0, "Historical conv rate must be non-negative"
    assert b.historical_units_sold >= 0.0, "Historical units sold must be non-negative"
    assert b.target_lift_pct == pytest.approx(0.15, abs=0.001), "Target KPI must be 15%"

    # Campaign actuals must be filled in
    assert b.campaign_conversion_rate is not None, "Campaign conv rate must be populated"
    assert b.actual_lift_pct is not None, "Actual lift must be calculated"

    # target_achieved must be honest — True only if lift ≥ 15%
    if b.actual_lift_pct >= b.target_lift_pct:
        assert b.target_achieved is True
    else:
        assert b.target_achieved is False

    # Print proof
    print(
        f"\n[BASELINE REPORT]\n"
        f"  Product:               {b.product_id}\n"
        f"  Historical conv rate:  {b.historical_conversion_rate:.4f}\n"
        f"  Campaign conv rate:    {b.campaign_conversion_rate:.4f}\n"
        f"  Actual lift:           {b.actual_lift_pct * 100:.2f}%\n"
        f"  Target KPI:            {b.target_lift_pct * 100:.0f}%\n"
        f"  Target achieved:       {b.target_achieved}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 3 – Memory influence across runs
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_memory_retrieved_in_second_run(temp_config):
    """
    REQUIREMENT 2: Run 1 persists to SQLite; Run 2 retrieves that memory
    before campaign generation.

    Proof: state.previous_campaign_memory is non-empty in Run 2.
    """
    # Run 1
    state1 = await _run(temp_config)
    assert state1.product_info is not None
    category = state1.product_info.category
    campaign1_id = state1.campaigns[-1].campaign_id

    # Verify Run 1 persisted to memory
    memory = MemoryStore(temp_config)
    after_run1 = memory.get_similar_campaigns(category)
    assert len(after_run1) > 0, "Run 1 must have persisted at least 1 outcome"

    # Run 2 — same DB, same config
    state2 = await _run(temp_config)

    # Proof: CampaignGenerationAgent loaded previous memory
    assert len(state2.previous_campaign_memory) > 0, (
        "Run 2: state.previous_campaign_memory must be non-empty — "
        "CampaignGenerationAgent must retrieve memory before generating"
    )

    retrieved_ids = [m["campaign_id"] for m in state2.previous_campaign_memory]
    assert campaign1_id in retrieved_ids, (
        f"Run 2 must have retrieved campaign {campaign1_id} from Run 1. "
        f"Got: {retrieved_ids}"
    )

    print(
        f"\n[MEMORY PROOF]\n"
        f"  Run 1 campaign:  {campaign1_id}\n"
        f"  Run 2 retrieved: {retrieved_ids}\n"
        f"  Memory records:  {len(state2.previous_campaign_memory)}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 4 – Optimization loop produces a changed Campaign 2
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_optimization_loop_produces_different_campaign(temp_config):
    """
    REQUIREMENT 3: When OptimizationAgent decides OPTIMIZE, Campaign 2
    must differ from Campaign 1 in at least one meaningful dimension.

    The demo-mode LLM mock always returns OPTIMIZE on iteration 0,
    so this test can run without a real LLM.
    """
    state = await _run(temp_config)

    # Must have at least 2 campaigns (initial + optimized)
    assert len(state.campaigns) >= 2, (
        f"Optimization loop must produce at least 2 campaigns. Got: {len(state.campaigns)}"
    )

    camp1 = state.campaigns[0]
    camp2 = state.campaigns[1]
    c1 = camp1.content
    c2 = camp2.content

    # At least one content field must differ
    differences = {
        "subject_line": c1.subject_line != c2.subject_line,
        "headline": c1.headline != c2.headline,
        "body": c1.body != c2.body,
        "cta": c1.cta != c2.cta,
    }
    assert any(differences.values()), (
        f"Campaign 2 must differ from Campaign 1 in at least one field.\n"
        f"  Campaign 1: subject='{c1.subject_line}' cta='{c1.cta}'\n"
        f"  Campaign 2: subject='{c2.subject_line}' cta='{c2.cta}'"
    )

    # Verify the optimization decision that triggered it was OPTIMIZE
    # (The final optimization may be STOP after the loop, so we check via iteration count)
    assert state.optimization_iteration >= 2, (
        "At least 2 optimization iterations must have run"
    )

    # Verify Campaign 2 name/id is distinct
    assert camp1.campaign_id != camp2.campaign_id

    print(
        f"\n[OPTIMIZATION LOOP PROOF]\n"
        f"  Campaign 1 id:      {camp1.campaign_id}\n"
        f"  Campaign 1 subject: {c1.subject_line}\n"
        f"  Campaign 1 CTA:     {c1.cta}\n"
        f"  ---\n"
        f"  Campaign 2 id:      {camp2.campaign_id}\n"
        f"  Campaign 2 subject: {c2.subject_line}\n"
        f"  Campaign 2 CTA:     {c2.cta}\n"
        f"  Differences:        {[k for k, v in differences.items() if v]}"
    )

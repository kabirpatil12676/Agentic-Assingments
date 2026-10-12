"""
Smoke tests for Pydantic models.

Validates that all schemas can be instantiated, serialised,
and round-tripped without errors.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure project root is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.models.schemas import (
    Campaign,
    CampaignChannel,
    CampaignContent,
    CampaignMetrics,
    CampaignStatus,
    CustomerSegment,
    ExecutionPlan,
    ExecutionResult,
    OptimizationDecision,
    OptimizationRecommendation,
    PlanStep,
    ProductInfo,
    UserGoal,
    WorkflowState,
)


def test_user_goal_defaults() -> None:
    goal = UserGoal(goal_text="Test goal")
    assert goal.goal_text == "Test goal"
    assert goal.budget == 0.0
    assert goal.channels == []


def test_product_info_roundtrip() -> None:
    p = ProductInfo(
        product_id="p1",
        name="Widget",
        category="Electronics",
        price=29.99,
        description="A fine widget",
        features=["bluetooth", "waterproof"],
    )
    data = p.model_dump()
    p2 = ProductInfo(**data)
    assert p == p2


def test_campaign_defaults() -> None:
    c = Campaign(
        campaign_id="c1",
        name="Summer Sale",
        product_id="p1",
        segment_id="s1",
        channel=CampaignChannel.EMAIL,
        content=CampaignContent(headline="Buy now"),
    )
    assert c.status == CampaignStatus.DRAFT
    assert c.budget == 0.0


def test_workflow_state_mutable() -> None:
    state = WorkflowState()
    state.current_step = "planner"
    state.logs.append("started")
    assert state.current_step == "planner"
    assert len(state.logs) == 1


def test_optimization_recommendation() -> None:
    rec = OptimizationRecommendation(
        campaign_id="c1",
        decision=OptimizationDecision.OPTIMIZE,
        reason="CTR below threshold",
        predicted_lift=0.12,
        iteration=1,
    )
    assert rec.decision == OptimizationDecision.OPTIMIZE
    assert rec.predicted_lift == 0.12


def test_customer_segment() -> None:
    seg = CustomerSegment(
        segment_id="s1",
        name="Young Professionals",
        description="Ages 25-35, urban, high income",
        size=5000,
        avg_age=30.0,
        preferred_channels=[CampaignChannel.EMAIL, CampaignChannel.PUSH],
        engagement_score=0.75,
    )
    assert seg.size == 5000
    assert CampaignChannel.PUSH in seg.preferred_channels


def test_execution_result() -> None:
    er = ExecutionResult(
        campaign_id="c1",
        delivered=1000,
        opened=350,
        clicked=120,
        converted=25,
        cost=500.0,
    )
    assert er.delivered == 1000


def test_campaign_metrics() -> None:
    m = CampaignMetrics(
        campaign_id="c1",
        open_rate=0.35,
        click_rate=0.12,
        conversion_rate=0.025,
        roi=1.5,
    )
    assert m.roi == 1.5


def test_execution_plan() -> None:
    plan = ExecutionPlan(
        goal=UserGoal(goal_text="Test"),
        steps=[
            PlanStep(step_name="analyse", agent="product_analyst", description="Analyse product"),
            PlanStep(step_name="segment", agent="segmentation", description="Segment customers", depends_on=["analyse"]),
        ],
    )
    assert len(plan.steps) == 2
    assert plan.steps[1].depends_on == ["analyse"]

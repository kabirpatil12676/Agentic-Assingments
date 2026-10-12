"""
Pydantic models for all agent inputs, outputs, and shared state.

Every agent communicates through typed schemas defined here.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


# ── Enums ─────────────────────────────────────────────────────────────────────

class CampaignChannel(str, Enum):
    EMAIL = "email"
    SMS = "sms"
    SOCIAL = "social"
    PUSH = "push"


class CampaignStatus(str, Enum):
    DRAFT = "draft"
    PLANNED = "planned"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    OPTIMIZING = "optimizing"


class OptimizationDecision(str, Enum):
    CONTINUE = "continue"
    OPTIMIZE = "optimize"
    STOP = "stop"


# ── Product ───────────────────────────────────────────────────────────────────

class ProductInfo(BaseModel):
    product_id: str
    name: str
    category: str
    price: float
    description: str
    features: list[str] = Field(default_factory=list)
    target_demographics: list[str] = Field(default_factory=list)
    sentiment_score: Optional[float] = None
    competitive_position: Optional[str] = None


# ── Customer / Segmentation ──────────────────────────────────────────────────

class CustomerSegment(BaseModel):
    segment_id: str
    name: str
    description: str
    size: int
    avg_age: Optional[float] = None
    avg_income: Optional[float] = None
    preferred_channels: list[CampaignChannel] = Field(default_factory=list)
    engagement_score: float = 0.0
    conversion_rate: float = 0.0


# ── Campaign ─────────────────────────────────────────────────────────────────

class CampaignContent(BaseModel):
    subject_line: str = ""
    headline: str = ""
    body: str = ""
    cta: str = ""          # call-to-action
    channel: CampaignChannel = CampaignChannel.EMAIL


class Campaign(BaseModel):
    campaign_id: str
    name: str
    product_id: str
    segment_id: str
    channel: CampaignChannel
    content: CampaignContent
    status: CampaignStatus = CampaignStatus.DRAFT
    budget: float = 0.0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    scheduled_at: Optional[datetime] = None


# ── Execution ────────────────────────────────────────────────────────────────

class ExecutionResult(BaseModel):
    campaign_id: str
    delivered: int = 0
    opened: int = 0
    clicked: int = 0
    converted: int = 0
    bounced: int = 0
    cost: float = 0.0
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ── Monitoring / Metrics ─────────────────────────────────────────────────────

class CampaignMetrics(BaseModel):
    campaign_id: str
    revenue: float = 0.0
    open_rate: float = 0.0
    click_rate: float = 0.0
    conversion_rate: float = 0.0
    cost_per_conversion: float = 0.0
    roi: float = 0.0
    engagement_score: float = 0.0
    anomalies: list[str] = Field(default_factory=list)


class BaselineMetrics(BaseModel):
    """Historical baseline computed from purchase data before campaign launch."""
    product_id: str
    category: str
    # From purchase history: average weekly units sold in target segment
    historical_units_sold: float = 0.0
    historical_revenue: float = 0.0
    historical_conversion_rate: float = 0.0
    # Target KPI (e.g. 15% lift)
    target_lift_pct: float = 0.15
    # Post-campaign actuals (filled in by MonitoringAgent after execution)
    campaign_conversion_rate: Optional[float] = None
    campaign_revenue: Optional[float] = None
    # Derived KPI
    actual_lift_pct: Optional[float] = Field(None, description="Sales / Revenue lift percentage vs historical baseline")
    target_achieved: Optional[bool] = None


# ── Optimization ─────────────────────────────────────────────────────────────

class OptimizationRecommendation(BaseModel):
    campaign_id: str
    decision: OptimizationDecision
    reason: str = ""
    suggested_changes: dict[str, Any] = Field(default_factory=dict)
    predicted_lift: float = 0.0
    iteration: int = 0


# ── Planner ──────────────────────────────────────────────────────────────────

class UserGoal(BaseModel):
    goal_text: str
    product_id: Optional[str] = None
    budget: float = 0.0
    target_audience: Optional[str] = None
    channels: list[CampaignChannel] = Field(default_factory=list)
    constraints: dict[str, Any] = Field(default_factory=dict)


class PlanStep(BaseModel):
    step_name: str
    agent: str
    description: str
    depends_on: list[str] = Field(default_factory=list)


class ExecutionPlan(BaseModel):
    goal: UserGoal
    steps: list[PlanStep] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ── Shared workflow state (used by LangGraph) ────────────────────────────────

class WorkflowState(BaseModel):
    """Mutable state passed through the LangGraph workflow."""
    # input
    goal: Optional[UserGoal] = None
    plan: Optional[ExecutionPlan] = None

    # intermediate
    product_info: Optional[ProductInfo] = None
    segments: list[CustomerSegment] = Field(default_factory=list)
    campaigns: list[Campaign] = Field(default_factory=list)
    execution_results: list[ExecutionResult] = Field(default_factory=list)
    metrics: list[CampaignMetrics] = Field(default_factory=list)
    optimization: Optional[OptimizationRecommendation] = None

    # baseline (computed from purchase history before execution)
    baseline: Optional["BaselineMetrics"] = None

    # memory retrieved from previous runs (injected into CampaignGenerationAgent)
    previous_campaign_memory: list[dict[str, Any]] = Field(default_factory=list)

    # control
    current_step: str = ""
    optimization_iteration: int = 0
    errors: list[str] = Field(default_factory=list)
    logs: list[str] = Field(default_factory=list)
    completed: bool = False


# ── Data Layer Schemas ────────────────────────────────────────────────────────

class ProductRecord(BaseModel):
    product_id: str
    product_name: str
    category: str
    price: float
    cost: float
    units_sold: int = 0
    revenue: float = 0.0
    average_rating: float = 0.0
    review_count: int = 0
    conversion_rate: float = 0.0
    inventory: int = 0


class CustomerRecord(BaseModel):
    customer_id: str
    name: str
    email: str
    age: int
    occupation: str
    city: str
    customer_type: str
    total_spend: float = 0.0
    total_orders: int = 0
    last_purchase_date: Optional[str] = None


class PurchaseRecord(BaseModel):
    purchase_id: str
    customer_id: str
    product_id: str
    purchase_date: str
    quantity: int
    unit_price: float
    total_amount: float


class CampaignEventRecord(BaseModel):
    event_id: str
    campaign_id: str
    customer_id: str
    variant: str = "control"
    channel: str = "email"
    sent: int = 1
    opened: int = 0
    clicked: int = 0
    converted: int = 0
    revenue: float = 0.0
    timestamp: str

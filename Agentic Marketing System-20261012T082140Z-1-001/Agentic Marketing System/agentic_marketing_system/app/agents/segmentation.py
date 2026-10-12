"""
Customer Segmentation Agent – clusters customers into segments.

All clustering, scoring, and aggregation is done with Pandas/NumPy.
The LLM is used only to generate human-readable segment descriptions.

Implementation pending.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING
from app.services.analytics_service import CustomerAnalytics
from app.services.data_service import DataService
from app.services.llm_provider import LLMProvider
from app.models.schemas import CustomerSegment, CampaignChannel

if TYPE_CHECKING:
    from app.config import Config
    from app.models.schemas import WorkflowState

logger = logging.getLogger(__name__)


class SegmentationAgent:
    """Segments customers using deterministic analytics."""

    def __init__(self, config: "Config") -> None:
        self.config = config
        self.data_service = DataService(config)
        self.llm = LLMProvider(config.llm, demo_mode=config.demo_mode)
        logger.info("SegmentationAgent initialised")

    async def run(self, state: "WorkflowState") -> "WorkflowState":
        """Execute segmentation."""
        logger.info("SegmentationAgent running...")
        
        target = state.goal.target_audience.lower() if state.goal and state.goal.target_audience else "all"
        
        # Deterministic Analytics: Fetch all customers and filter
        df = self.data_service.load_customers()
        if df.empty:
            state.errors.append("SegmentationAgent: No customer data available.")
            return state
            
        # Basic deterministic filtering (if target mentions student, filter by occupation, etc.)
        if "student" in target:
            segment_df = df[df["occupation"].str.lower() == "student"]
        elif "professional" in target:
            segment_df = df[df["occupation"].str.lower().isin(["software engineer", "marketing manager", "data scientist", "teacher", "accountant"])]
        else:
            segment_df = df # default to all if no clear match
            
        if segment_df.empty:
            segment_df = df # fallback
            
        # Ensure we drop duplicate customers to enforce: size <= unique customers
        segment_df = segment_df.drop_duplicates(subset=["customer_id"])
            
        size = len(segment_df)
        avg_age = segment_df["age"].mean()
        avg_spend = segment_df["total_spend"].mean()
        
        segment = CustomerSegment(
            segment_id=f"seg_{target.replace(' ', '_')}_{size}",
            name=f"Target: {target.title()}",
            description="",
            size=size,
            avg_age=float(avg_age),
            engagement_score=min(1.0, float(avg_spend) / 1000.0), # Mock score based on spend
            preferred_channels=[CampaignChannel.EMAIL] # Defaulting to email
        )
        
        # Use LLM to write a nice description
        system_prompt = "You are a marketing analyst. Write a 2-sentence description of this customer segment."
        prompt = f"Segment: {segment.name}, Size: {size}, Avg Age: {avg_age:.1f}, Target query: {target}"
        
        try:
            desc = await self.llm.generate(prompt, system_prompt=system_prompt)
            segment.description = desc
        except Exception as e:
            logger.error(f"LLM failed to generate segment description: {e}")
            segment.description = f"A segment of {size} customers targeting {target}."
            
        state.segments.append(segment)
        state.logs.append(f"SegmentationAgent created segment '{segment.name}' with {size} users.")
        
        return state

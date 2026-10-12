"""
Execution Agent – simulates or executes campaign delivery.

In DEMO mode, generates realistic synthetic delivery metrics.
In production mode, would integrate with external delivery APIs.

Implementation pending.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING
import pandas as pd
from app.services.simulator import CampaignSimulator
from app.services.data_service import DataService
from app.models.schemas import ExecutionResult

if TYPE_CHECKING:
    from app.config import Config
    from app.models.schemas import WorkflowState

logger = logging.getLogger(__name__)


class ExecutionAgent:
    """Simulates / executes campaign delivery and records results."""

    def __init__(self, config: "Config") -> None:
        self.config = config
        self.data_service = DataService(config)
        self.simulator = CampaignSimulator()
        logger.info("ExecutionAgent initialised")

    async def run(self, state: "WorkflowState") -> "WorkflowState":
        """Execute campaign delivery."""
        logger.info("ExecutionAgent running...")
        
        if not state.campaigns:
            state.errors.append("ExecutionAgent: No campaign to execute.")
            return state
            
        campaign = state.campaigns[-1]
        
        # Load customers
        all_customers = self.data_service.load_customers()
        if all_customers.empty:
            state.errors.append("ExecutionAgent: No customer data to simulate on.")
            return state
            
        # Simplified target sampling based on segment size
        segment_size = 100 # fallback
        if state.segments:
            segment_size = state.segments[-1].size
            
        # For demo purposes, sample 'segment_size' customers deterministically
        target_customers = all_customers.head(segment_size)
        
        product_dict = {"price": 49.99, "average_rating": 4.5, "conversion_rate": 0.05}
        if state.product_info:
            product_dict = state.product_info.model_dump()

        # ── Persist the campaign record first (FK requirement) ──────────────
        from datetime import datetime, timezone
        content = campaign.content
        self.data_service.save_campaign({
            "campaign_id": campaign.campaign_id,
            "name": campaign.name,
            "product_id": campaign.product_id,
            "segment_id": campaign.segment_id,
            "channel": campaign.channel.value,
            "status": "active",
            "budget": campaign.budget,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "subject_line": content.subject_line if content else None,
            "headline": content.headline if content else None,
            "body": content.body if content else None,
            "cta": content.cta if content else None,
        })

        events = self.simulator.simulate(
            campaign_id=campaign.campaign_id,
            target_customers=target_customers,
            product=product_dict,
            variant="variant_A" if state.optimization_iteration > 0 else "control",
            channel=campaign.channel.value
        )

        # Save events
        self.data_service.save_campaign_events(events)
        
        # Create execution result summary
        sent = sum(1 for e in events if e.get("sent"))
        opened = sum(1 for e in events if e.get("opened"))
        clicked = sum(1 for e in events if e.get("clicked"))
        converted = sum(1 for e in events if e.get("converted"))
        
        result = ExecutionResult(
            campaign_id=campaign.campaign_id,
            delivered=sent,
            opened=opened,
            clicked=clicked,
            converted=converted,
            cost=campaign.budget
        )
        state.execution_results.append(result)
        state.logs.append(f"ExecutionAgent executed {campaign.campaign_id}: {sent} sent, {converted} converted.")
        
        return state

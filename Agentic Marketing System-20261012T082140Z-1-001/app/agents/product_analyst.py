"""
Product Analysis Agent – analyses product catalogue data.

Uses Pandas for numerical analysis (pricing, feature comparison),
and the LLM only for generating natural-language competitive positioning.

Implementation pending.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING
from app.services.analytics_service import ProductAnalytics
from app.services.data_service import DataService
from app.services.llm_provider import LLMProvider
from app.models.schemas import ProductInfo

if TYPE_CHECKING:
    from app.config import Config
    from app.models.schemas import WorkflowState

logger = logging.getLogger(__name__)


class ProductAnalysisAgent:
    """Analyses product data and derives competitive positioning."""

    def __init__(self, config: "Config") -> None:
        self.config = config
        self.data_service = DataService(config)
        self.llm = LLMProvider(config.llm, demo_mode=config.demo_mode)
        logger.info("ProductAnalysisAgent initialised")

    async def run(self, state: "WorkflowState") -> "WorkflowState":
        """Execute product analysis."""
        logger.info("ProductAnalysisAgent running...")
        
        target_product_id = state.goal.product_id if state.goal else None
        
        # If no specific product is requested, find the top performing one
        if not target_product_id:
            logger.info("No target product specified, finding top performer.")
            products_df = self.data_service.load_products()
            metrics_df = ProductAnalytics.get_top_products(products_df)
            if not metrics_df.empty:
                # Get the product with highest score
                top_product_row = metrics_df.iloc[0]
                target_product_id = top_product_row["product_id"]
            else:
                state.errors.append("ProductAnalysisAgent: No product metrics available.")
                return state
                
        # Fetch full product record
        product_record = self.data_service.get_product(target_product_id)
        if not product_record:
            state.errors.append(f"ProductAnalysisAgent: Product {target_product_id} not found.")
            return state

        # Build initial ProductInfo
        product_info = ProductInfo(
            product_id=product_record["product_id"],
            name=product_record["product_name"],
            category=product_record["category"],
            price=product_record["price"],
            description=f"A top-selling product in {product_record['category']}.",
            sentiment_score=product_record["average_rating"] / 5.0, # Approximate sentiment
        )
        
        # Use LLM to generate competitive positioning
        system_prompt = "You are a product marketing expert. Write a 1-sentence competitive positioning statement."
        prompt = f"Product: {product_info.name} ({product_info.category}). Rating: {product_record['average_rating']}/5.0"
        
        try:
            positioning = await self.llm.generate(prompt, system_prompt=system_prompt)
            product_info.competitive_position = positioning
        except Exception as e:
            logger.error(f"LLM failed to generate positioning: {e}")
            product_info.competitive_position = "A solid choice in its category."
            
        state.product_info = product_info
        state.logs.append(f"ProductAnalysisAgent analyzed {product_info.name}.")
        return state

"""
Campaign Generation Agent – creates personalised campaign content.

Uses the LLM for creative copy generation (subject lines, headlines, body).
Channel selection and budget allocation are deterministic.

On optimization iterations:
  - Retrieves previous campaign memory from SQLite
  - Injects optimization feedback into the LLM prompt
  - Produces content that demonstrably differs from prior iterations
"""

from __future__ import annotations

import logging
import uuid
from typing import TYPE_CHECKING
from app.services.llm_provider import LLMProvider
from app.memory.memory_store import MemoryStore
from app.models.schemas import Campaign, CampaignContent, CampaignChannel, OptimizationDecision

if TYPE_CHECKING:
    from app.config import Config
    from app.models.schemas import WorkflowState

logger = logging.getLogger(__name__)


class CampaignGenerationAgent:
    """Generates campaign content using LLM for copy, deterministic logic for targeting."""

    def __init__(self, config: "Config") -> None:
        self.config = config
        self.llm = LLMProvider(config.llm, demo_mode=config.demo_mode)
        self.memory = MemoryStore(config)
        logger.info("CampaignGenerationAgent initialised")

    async def run(self, state: "WorkflowState") -> "WorkflowState":
        """Generate campaigns."""
        logger.info("CampaignGenerationAgent running (iteration=%d)...", state.optimization_iteration)

        if not state.product_info:
            state.errors.append("CampaignGenerationAgent: Missing product_info.")
            return state
        if not state.segments:
            state.errors.append("CampaignGenerationAgent: Missing customer segment.")
            return state

        segment = state.segments[-1]

        # ── Step 1: Retrieve long-term memory ──────────────────────────────────
        memory_context = ""
        similar = self.memory.get_similar_campaigns(
            product_category=state.product_info.category, limit=3
        )
        # Store retrieved memory in state so tests can verify it was used
        state.previous_campaign_memory = similar

        if similar:
            memory_lines = []
            for m in similar:
                outcome = m.get("outcome", {})
                metrics = outcome.get("metrics", {})
                suggestion = outcome.get("suggested_changes", {})
                memory_lines.append(
                    f"  - Campaign {m['campaign_id']}: "
                    f"conv_rate={metrics.get('conversion_rate', 'N/A')}, "
                    f"roi={metrics.get('roi', 'N/A')}, "
                    f"suggestion={suggestion}"
                )
            memory_context = (
                "\n\nHISTORICAL CAMPAIGN MEMORY (use to avoid past mistakes):\n"
                + "\n".join(memory_lines)
            )
            logger.info(
                "CampaignGenerationAgent: loaded %d memory records for category=%s",
                len(similar),
                state.product_info.category,
            )
        else:
            logger.info("CampaignGenerationAgent: no prior memory found for category=%s", state.product_info.category)

        # ── Step 2: Build prompt ───────────────────────────────────────────────
        is_optimization_run = (
            state.optimization is not None
            and state.optimization.decision == OptimizationDecision.OPTIMIZE
        )

        system_prompt = (
            "You are an expert copywriter. Generate marketing campaign content. "
            "Output valid JSON matching the CampaignContent schema "
            "(subject_line, headline, body, cta, channel)."
        )

        prompt = (
            f"Product: {state.product_info.name}\n"
            f"Category: {state.product_info.category}\n"
            f"Positioning: {state.product_info.competitive_position}\n"
            f"Audience: {segment.description}\n"
            f"Iteration: {state.optimization_iteration}"
            f"{memory_context}"
        )

        # Inject optimization feedback so Campaign 2 differs from Campaign 1
        if is_optimization_run and state.optimization:
            opt = state.optimization
            changes_str = ", ".join(
                f"{k}='{v}'" for k, v in (opt.suggested_changes or {}).items()
            ) or "improve the CTA and urgency"
            prompt += (
                f"\n\nOPTIMIZATION FEEDBACK (MUST apply these changes):\n"
                f"  Reason: {opt.reason}\n"
                f"  Required changes: {changes_str}\n"
                "Create a DIFFERENT subject line, CTA, and body reflecting these changes."
            )
            logger.info("CampaignGenerationAgent: injecting optimization feedback: %s", opt.reason)

        # ── Step 3: Generate content ───────────────────────────────────────────
        try:
            content_dict = await self.llm.generate_structured(prompt, system_prompt=system_prompt)

            # Fallback — use iteration-aware defaults so iterations differ even in demo mode
            if not content_dict or "subject_line" not in content_dict:
                if is_optimization_run:
                    content_dict = {
                        "subject_line": f"[OPTIMIZED] Last Chance: Save 20% on {state.product_info.name}!",
                        "headline": f"Don't Miss Out – Our Best Deal on {state.product_info.name}",
                        "body": (
                            "We noticed you showed interest before. Based on feedback, "
                            "we've improved our offer. Act now — limited time only."
                        ),
                        "cta": "Buy Now and Save!",   # Changed CTA per optimization
                        "channel": CampaignChannel.EMAIL,
                    }
                else:
                    content_dict = {
                        "subject_line": f"Exclusive Offer on {state.product_info.name}",
                        "headline": f"Discover the best {state.product_info.category}",
                        "body": "We think you will love this product based on your preferences.",
                        "cta": "Shop Now",
                        "channel": CampaignChannel.EMAIL,
                    }

            # Normalise channel string → enum
            if isinstance(content_dict.get("channel"), str):
                try:
                    content_dict["channel"] = CampaignChannel(content_dict["channel"].lower())
                except ValueError:
                    content_dict["channel"] = CampaignChannel.EMAIL

            content = CampaignContent(**content_dict)

            campaign = Campaign(
                campaign_id=f"camp_{uuid.uuid4().hex[:8]}",
                name=(
                    f"Campaign for {state.product_info.name} "
                    f"- {'Optimized' if is_optimization_run else 'Initial'} "
                    f"Iter {state.optimization_iteration}"
                ),
                product_id=state.product_info.product_id,
                segment_id=segment.segment_id,
                channel=content.channel,
                content=content,
                budget=state.goal.budget if state.goal else 0.0,
            )
            state.campaigns.append(campaign)
            state.logs.append(
                f"CampaignGenerationAgent generated {campaign.campaign_id} "
                f"({'optimized' if is_optimization_run else 'initial'})."
            )

        except Exception as e:
            logger.error("CampaignGenerationAgent error: %s", e)
            state.errors.append(f"CampaignGenerationAgent error: {e}")

        return state

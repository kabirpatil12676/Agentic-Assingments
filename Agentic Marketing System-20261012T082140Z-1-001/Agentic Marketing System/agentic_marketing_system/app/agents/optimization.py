"""
Optimization Agent – decides whether to optimise, continue, or stop.

Uses deterministic scoring (Pandas) for metric comparison and
the LLM only to generate a human-readable rationale for the decision.

Implementation pending.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING
from app.services.llm_provider import LLMProvider
from app.memory.memory_store import MemoryStore
from app.models.schemas import OptimizationRecommendation, OptimizationDecision

if TYPE_CHECKING:
    from app.config import Config
    from app.models.schemas import WorkflowState

logger = logging.getLogger(__name__)


class OptimizationAgent:
    """Evaluates campaign performance and recommends optimisation actions."""

    def __init__(self, config: "Config") -> None:
        self.config = config
        self.llm = LLMProvider(config.llm, demo_mode=config.demo_mode)
        self.memory = MemoryStore(config)
        logger.info("OptimizationAgent initialised")

    async def run(self, state: "WorkflowState") -> "WorkflowState":
        """Evaluate and optimise."""
        logger.info("OptimizationAgent running...")
        
        if not state.metrics:
            state.errors.append("OptimizationAgent: No metrics to optimize on.")
            return state
            
        metrics = state.metrics[-1]
        
        # Check if we've hit max loops
        if state.optimization_iteration >= self.config.max_optimization_loops:
            decision = OptimizationDecision.STOP
            reason = "Max optimization loops reached."
            rec = OptimizationRecommendation(
                campaign_id=metrics.campaign_id,
                decision=decision,
                reason=reason,
                iteration=state.optimization_iteration
            )
        else:
            system_prompt = (
                "You are an optimization specialist. Decide whether to 'optimize' (try again with changes) "
                "or 'stop' (metrics are good enough or campaign failed). "
                "Output JSON matching OptimizationRecommendation schema."
            )
            prompt = f"Iteration: {state.optimization_iteration}, Metrics: {metrics.model_dump()}"
            
            try:
                rec_dict = await self.llm.generate_structured(prompt, system_prompt=system_prompt)
                
                # fallback if LLM fails
                if not rec_dict or "decision" not in rec_dict:
                    rec_dict = {
                        "campaign_id": metrics.campaign_id,
                        "decision": "stop",
                        "reason": "Default fallback decision.",
                        "iteration": state.optimization_iteration
                    }
                
                # Normalize decision to enum
                if isinstance(rec_dict.get("decision"), str):
                    try:
                        rec_dict["decision"] = OptimizationDecision(rec_dict["decision"].lower())
                    except ValueError:
                        rec_dict["decision"] = OptimizationDecision.STOP
                        
                rec = OptimizationRecommendation(**rec_dict)
            except Exception as e:
                logger.error(f"OptimizationAgent error: {e}")
                rec = OptimizationRecommendation(
                    campaign_id=metrics.campaign_id,
                    decision=OptimizationDecision.STOP,
                    reason=f"Error in LLM: {e}",
                    iteration=state.optimization_iteration
                )
        
        state.optimization = rec
        state.optimization_iteration += 1

        # ── Persist outcome on EVERY iteration (memory available for next run) ──
        self.memory.store_campaign_outcome(
            campaign_id=metrics.campaign_id,
            outcome={
                "product_category": state.product_info.category if state.product_info else "unknown",
                "metrics": metrics.model_dump(),
                "decision": rec.decision.value,
                "suggested_changes": rec.suggested_changes,
                "reason": rec.reason,
                "final_iteration": state.optimization_iteration,
                "target_segment": state.segments[-1].name if state.segments else "unknown",
            }
        )

        if rec.decision in (OptimizationDecision.STOP, OptimizationDecision.CONTINUE):
            state.completed = True

        state.logs.append(f"OptimizationAgent decision: {rec.decision.value}. Reason: {rec.reason}")
        return state


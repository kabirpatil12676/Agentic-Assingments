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
        
        target_achieved = state.baseline.target_achieved if state.baseline else None

        # Check if we've hit max loops
        if state.optimization_iteration >= self.config.max_optimization_loops:
            decision = OptimizationDecision.STOP
            if target_achieved is True:
                reason = f"Iteration limit reached ({state.optimization_iteration}/{self.config.max_optimization_loops}). Target performance achieved."
            elif target_achieved is False:
                reason = (
                    f"Iteration limit reached ({state.optimization_iteration}/{self.config.max_optimization_loops}). "
                    "Target sales lift was not achieved. Recommend further optimization in next campaign cycle."
                )
            else:
                reason = (
                    f"Iteration limit reached ({state.optimization_iteration}/{self.config.max_optimization_loops}). "
                    "Sales lift could not be evaluated due to missing historical campaign baseline. Recommend establishing campaign benchmark."
                )
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
                    if target_achieved is True:
                        fallback_reason = "Target performance achieved."
                    elif target_achieved is False:
                        fallback_reason = "Iteration limit reached. Target sales lift was not achieved; further optimization recommended."
                    else:
                        fallback_reason = "Iteration limit reached. Comparable historical campaign baseline is unavailable."
                    rec_dict = {
                        "campaign_id": metrics.campaign_id,
                        "decision": "stop",
                        "reason": fallback_reason,
                        "iteration": state.optimization_iteration
                    }
                
                # Normalize decision to enum
                if isinstance(rec_dict.get("decision"), str):
                    try:
                        rec_dict["decision"] = OptimizationDecision(rec_dict["decision"].lower())
                    except ValueError:
                        rec_dict["decision"] = OptimizationDecision.STOP
                
                # Prevent misreporting poor performance as accepted
                if rec_dict.get("decision") == OptimizationDecision.STOP:
                    orig_reason = rec_dict.get("reason", "")
                    if target_achieved is None:
                        rec_dict["reason"] = (
                            f"Iteration limit reached ({state.optimization_iteration + 1}/{self.config.max_optimization_loops}). "
                            "Comparable historical campaign baseline is unavailable; recommend establishing campaign benchmark."
                        )
                    elif not target_achieved and ("accepting" in orig_reason.lower() or not orig_reason):
                        rec_dict["reason"] = (
                            f"Iteration limit reached ({state.optimization_iteration + 1}/{self.config.max_optimization_loops}). "
                            "Target sales lift was not achieved. Recommend further optimization in next campaign cycle."
                        )

                rec = OptimizationRecommendation(**rec_dict)
            except Exception as e:
                logger.error(f"OptimizationAgent error: {e}")
                rec = OptimizationRecommendation(
                    campaign_id=metrics.campaign_id,
                    decision=OptimizationDecision.STOP,
                    reason=f"Error in LLM: {e}. Target sales lift was not achieved.",
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


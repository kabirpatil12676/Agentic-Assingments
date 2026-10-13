"""
Planner Agent – decomposes a user goal into an ordered execution plan.

Uses the LLM to reason about which agents should run and in what order,
then outputs a typed ExecutionPlan.

Implementation pending.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING
from app.services.llm_provider import LLMProvider
from app.models.schemas import ExecutionPlan, PlanStep, UserGoal

if TYPE_CHECKING:
    from app.config import Config
    from app.models.schemas import WorkflowState

logger = logging.getLogger(__name__)


class PlannerAgent:
    """Decomposes a user goal into a step-by-step execution plan."""

    def __init__(self, config: "Config") -> None:
        self.config = config
        self.llm = LLMProvider(config.llm, demo_mode=config.demo_mode)
        logger.info("PlannerAgent initialised (demo_mode=%s)", config.demo_mode)

    async def run(self, state: "WorkflowState") -> "WorkflowState":
        """Execute planning logic."""
        logger.info("PlannerAgent running...")
        if not state.goal:
            state.errors.append("PlannerAgent failed: No goal provided in state.")
            return state

        system_prompt = (
            "You are a marketing planner. Decompose the user's goal into a structured execution plan. "
            "Output valid JSON matching the ExecutionPlan schema."
        )
        prompt = f"Goal: {state.goal.goal_text}\nBudget: {state.goal.budget}"
        
        try:
            plan_dict = await self.llm.generate_structured(prompt, system_prompt=system_prompt)
            # Default to a generic plan if LLM output is empty or invalid
            if not plan_dict or "steps" not in plan_dict:
                plan_dict = self._get_fallback_plan(state.goal)
                
            # If the LLM didn't return a proper goal dict, use the original state goal
            if "goal" not in plan_dict or not isinstance(plan_dict["goal"], dict):
                plan_dict["goal"] = state.goal.model_dump()
                
            state.plan = ExecutionPlan(**plan_dict)
            state.logs.append(f"PlannerAgent created plan with {len(state.plan.steps)} steps.")
        except Exception as e:
            logger.error(f"PlannerAgent error: {e}")
            state.errors.append(f"PlannerAgent error: {e}")
            
        return state

    def _get_fallback_plan(self, goal: UserGoal) -> dict:
        return {
            "goal": goal.model_dump(),
            "steps": [
                {"step_name": "Identify Product", "agent": "product_analysis", "description": "Find top product", "depends_on": []},
                {"step_name": "Segment", "agent": "customer_segmentation", "description": "Find target audience", "depends_on": ["Identify Product"]},
                {"step_name": "Generate", "agent": "campaign_generation", "description": "Create campaign", "depends_on": ["Segment"]},
                {"step_name": "Execute", "agent": "execution", "description": "Send campaign", "depends_on": ["Generate"]},
                {"step_name": "Monitor", "agent": "monitoring", "description": "Check results", "depends_on": ["Execute"]},
                {"step_name": "Optimize", "agent": "optimization", "description": "Decide next steps", "depends_on": ["Monitor"]}
            ]
        }

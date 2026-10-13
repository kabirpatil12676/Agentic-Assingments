"""
LangGraph workflow graph definition.

Defines the directed graph of agent nodes and conditional edges,
including the optimisation feedback loop.

Implementation pending.
"""

import logging
from typing import Any
from langgraph.graph import StateGraph, START, END

from app.config import Config
from app.models.schemas import WorkflowState, OptimizationDecision
from app.agents.planner import PlannerAgent
from app.agents.product_analyst import ProductAnalysisAgent
from app.agents.segmentation import SegmentationAgent
from app.agents.campaign_gen import CampaignGenerationAgent
from app.agents.execution import ExecutionAgent
from app.agents.monitoring import MonitoringAgent
from app.agents.optimization import OptimizationAgent

logger = logging.getLogger(__name__)


def build_workflow_graph(config: Config):
    """
    Construct and return the LangGraph StateGraph.

    Node layout:
        planner → product_analysis → segmentation → campaign_generation
        → execution → monitoring → optimization
        → (conditional) → campaign_generation  OR  END

    Returns:
        CompiledGraph ready for invocation.
    """
    logger.info("Building workflow graph...")

    # Initialize agents
    planner = PlannerAgent(config)
    product_analyst = ProductAnalysisAgent(config)
    segmentation = SegmentationAgent(config)
    campaign_gen = CampaignGenerationAgent(config)
    execution = ExecutionAgent(config)
    monitoring = MonitoringAgent(config)
    optimization = OptimizationAgent(config)

    # Define StateGraph
    workflow = StateGraph(WorkflowState)

    # Add nodes
    workflow.add_node("planner", planner.run)
    workflow.add_node("product_analysis", product_analyst.run)
    workflow.add_node("segmentation", segmentation.run)
    workflow.add_node("campaign_generation", campaign_gen.run)
    workflow.add_node("execution", execution.run)
    workflow.add_node("monitoring", monitoring.run)
    workflow.add_node("optimization", optimization.run)

    # Add edges
    workflow.add_edge(START, "planner")
    workflow.add_edge("planner", "product_analysis")
    workflow.add_edge("product_analysis", "segmentation")
    workflow.add_edge("segmentation", "campaign_generation")
    workflow.add_edge("campaign_generation", "execution")
    workflow.add_edge("execution", "monitoring")
    workflow.add_edge("monitoring", "optimization")

    # Define conditional logic
    def should_optimize(state: WorkflowState) -> str:
        if state.optimization and state.optimization.decision == OptimizationDecision.OPTIMIZE:
            return "campaign_generation"
        return END

    workflow.add_conditional_edges(
        "optimization",
        should_optimize,
        {
            "campaign_generation": "campaign_generation",
            END: END
        }
    )

    return workflow.compile()

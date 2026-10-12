"""
Assignment 3 - Agentic AI
Name: Kabir Patil
Roll No: B-26
Title: Agentic AI Personalized Marketing Campaign Optimization System
"""

import sys
import os
import asyncio
import warnings
warnings.filterwarnings("ignore")

from pathlib import Path

# Add marketing system project directory to path
PROJECT_DIR = Path(__file__).resolve().parent / "Agentic Marketing System-20261012T082140Z-1-001" / "Agentic Marketing System" / "agentic_marketing_system"
sys.path.insert(0, str(PROJECT_DIR))

from app.config import load_config
from app.utils.logging_config import setup_logging
from app.models.schemas import WorkflowState, UserGoal, CampaignChannel
from app.workflow.graph import build_workflow_graph

async def run_marketing_system(goal_text: str = None):
    os.environ["DEMO_MODE"] = "true"
    if not goal_text:
        goal_text = "Launch an email campaign for our new wireless headphones targeting young professionals"

    print("\n============================================================")
    print("   Assignment 3: Agentic Marketing Campaign System")
    print("============================================================")
    print(f"Goal: {goal_text}\n")
    print("Executing Autonomous LangGraph Multi-Agent Workflow...\n")

    config = load_config()
    setup_logging("WARNING")

    workflow = build_workflow_graph(config)
    goal = UserGoal(
        goal_text=goal_text,
        budget=1000.0,
        target_audience="general",
        channels=[CampaignChannel.EMAIL],
    )
    initial_state = WorkflowState(goal=goal).model_dump()

    result = await workflow.ainvoke(initial_state)
    state = WorkflowState(**result)

    print("\n" + "=" * 60)
    print("   WORKFLOW EXECUTION RESULTS")
    print("=" * 60)
    print(f"Goal: {goal_text}")
    print(f"Optimization Iterations: {state.optimization_iteration}")
    
    if state.product_info:
        print(f"Product Selected: {state.product_info.name} ({state.product_info.category})")
    
    if state.segments:
        seg = state.segments[-1]
        print(f"Target Segment: {seg.name} (Size: {seg.size})")

    if state.campaigns:
        print(f"Campaigns Generated: {len(state.campaigns)}")
        latest_c = state.campaigns[-1]
        print(f"\n--- Latest Generated Campaign ---")
        if latest_c.content:
            print(f"Subject Line : {latest_c.content.subject_line}")
            print(f"Headline     : {latest_c.content.headline}")
            print(f"Body Preview : {latest_c.content.body[:200]}...")
            print(f"Call To Action: {latest_c.content.cta}")

    if state.metrics:
        m = state.metrics[-1]
        print(f"\n--- Performance Metrics ---")
        print(f"Open Rate       : {m.open_rate * 100:.2f}%")
        print(f"Click Rate      : {m.click_rate * 100:.2f}%")
        print(f"Conversion Rate : {m.conversion_rate * 100:.2f}%")
        print(f"ROI             : {m.roi * 100:.1f}%")

    if state.baseline:
        b = state.baseline
        print(f"\n--- Baseline vs Campaign Comparison ---")
        print(f"Historical Revenue : ${b.historical_revenue:.2f}")
        print(f"Campaign Revenue   : ${b.campaign_revenue or 0.0:.2f}")
        print(f"Sales Lift         : {(b.actual_lift_pct or 0.0) * 100:.2f}%")
        print(f"Target Achieved    : {b.target_achieved}")

    if state.optimization:
        opt = state.optimization[-1] if isinstance(state.optimization, list) else state.optimization
        action_val = getattr(opt, 'action', 'stop')
        reason_val = getattr(opt, 'reason', '')
        print(f"\nOptimization Decision: {str(action_val).upper()} - {reason_val}")
    print("=" * 60)

def main():
    print("Agentic Marketing System (Assignment 3)")
    default_goal = "Launch an email campaign for our new wireless headphones targeting young professionals"
    try:
        user_goal = input(f"Enter marketing goal (default: '{default_goal}'): ").strip()
    except (EOFError, KeyboardInterrupt):
        user_goal = ""
    if not user_goal:
        user_goal = default_goal
    
    asyncio.run(run_marketing_system(user_goal))

if __name__ == "__main__":
    try:
        main()
    except (EOFError, KeyboardInterrupt):
        print("\nExiting Assignment 3...")

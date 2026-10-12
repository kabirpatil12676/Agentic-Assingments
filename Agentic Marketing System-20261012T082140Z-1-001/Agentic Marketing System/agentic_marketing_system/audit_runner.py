import sys
import asyncio
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.config import Config, LLMConfig
from app.models.schemas import WorkflowState, UserGoal, CampaignChannel
from app.workflow.graph import build_workflow_graph
from app.memory.memory_store import MemoryStore

async def audit_run():
    config = Config(
        demo_mode=True,
        log_level="INFO",
        llm=LLMConfig(),
        max_optimization_loops=2,
    )

    print("=== STARTING AUDIT RUN ===")
    workflow = build_workflow_graph(config)
    
    # Run 1
    print("\n--- RUN 1 ---")
    goal = UserGoal(
        goal_text="Increase sales of our best-performing products among college students by 15%.",
        budget=1000.0,
        target_audience="Student",
        channels=[CampaignChannel.EMAIL]
    )
    initial_state = WorkflowState(goal=goal)
    result = await workflow.ainvoke(initial_state.model_dump())
    state1 = WorkflowState(**result)
    
    print("\nRun 1 - Planner Output:")
    print(state1.plan.model_dump_json(indent=2))
    
    print("\nRun 1 - Product Selection:")
    print(state1.product_info.model_dump_json(indent=2))
    
    print("\nRun 1 - Customer Segment:")
    print(state1.segments[-1].model_dump_json(indent=2))
    
    print("\nRun 1 - Campaign 1 (Before Execution):")
    print(state1.campaigns[0].content.model_dump_json(indent=2))
    
    print("\nRun 1 - Execution Metrics:")
    print(state1.execution_results[0].model_dump_json(indent=2))
    
    print("\nRun 1 - Baseline and Monitoring:")
    print(state1.baseline.model_dump_json(indent=2))
    print(state1.metrics[0].model_dump_json(indent=2))
    
    print("\nRun 1 - Optimization Decision:")
    print(state1.optimization.model_dump_json(indent=2))
    
    if len(state1.campaigns) > 1:
        print("\nRun 1 - Campaign 2 (After Optimization):")
        print(state1.campaigns[1].content.model_dump_json(indent=2))
        
    print(f"\nRun 1 - Total Iterations: {state1.optimization_iteration}")
    
    # Run 2
    print("\n--- RUN 2 ---")
    initial_state2 = WorkflowState(goal=goal)
    result2 = await workflow.ainvoke(initial_state2.model_dump())
    state2 = WorkflowState(**result2)
    
    print("\nRun 2 - Previous Memory Retrieved:")
    print(json.dumps(state2.previous_campaign_memory, indent=2))
    
    print("\n=== AUDIT COMPLETE ===")

if __name__ == "__main__":
    asyncio.run(audit_run())

import pytest
import asyncio
from typing import Any
from app.models.schemas import WorkflowState, CampaignMetrics, BaselineMetrics, OptimizationDecision, OptimizationRecommendation
from app.agents.monitoring import MonitoringAgent
from app.agents.optimization import OptimizationAgent
from app.config import Config, LLMConfig
from app.services.llm_provider import LLMProvider

class MockDataService:
    def get_campaign_events(self, campaign_id: str):
        import pandas as pd
        if campaign_id == "zero_rev":
            return pd.DataFrame([{"sent": 100, "opened": 10, "clicked": 1, "converted": 0, "revenue": 0.0}])
        elif campaign_id == "high_rev":
            return pd.DataFrame([{"sent": 100, "opened": 10, "clicked": 1, "converted": 1, "revenue": 5000.0}])
        return pd.DataFrame()

@pytest.mark.asyncio
async def test_baseline_revenue_zero():
    # 1. baseline revenue = 0, campaign revenue > 0
    config = Config(demo_mode=True, llm=LLMConfig())
    agent = MonitoringAgent(config)
    agent.data_service = MockDataService()
    
    state = WorkflowState()
    # Mock execution result
    from app.models.schemas import ExecutionResult, ProductInfo
    state.execution_results.append(ExecutionResult(campaign_id="high_rev", cost=100.0))
    state.product_info = ProductInfo(product_id="prod", name="P", category="C", price=10.0, description="D")
    
    # Force baseline revenue to 0
    state.baseline = BaselineMetrics(product_id="prod", category="C", historical_revenue=0.0, target_lift_pct=0.15)
    
    state = await agent.run(state)
    
    # Lift should be 1.0 (100%) because rev > 0 and baseline == 0
    assert state.baseline.actual_lift_pct == 1.0
    assert state.baseline.target_achieved is True

@pytest.mark.asyncio
async def test_campaign_revenue_zero():
    # 2. campaign revenue = 0
    config = Config(demo_mode=True, llm=LLMConfig())
    agent = MonitoringAgent(config)
    agent.data_service = MockDataService()
    
    state = WorkflowState()
    from app.models.schemas import ExecutionResult, ProductInfo
    state.execution_results.append(ExecutionResult(campaign_id="zero_rev", cost=100.0))
    state.product_info = ProductInfo(product_id="prod", name="P", category="C", price=10.0, description="D")
    
    # Force baseline revenue > 0
    state.baseline = BaselineMetrics(product_id="prod", category="C", historical_revenue=1000.0, target_lift_pct=0.15)
    
    state = await agent.run(state)
    
    # Lift should be -1.0 (-100%) because rev == 0 and baseline == 1000.0
    assert state.baseline.actual_lift_pct == -1.0
    assert state.baseline.target_achieved is False

@pytest.mark.asyncio
async def test_campaign_revenue_greater_and_lower():
    # 3. campaign revenue > baseline
    config = Config(demo_mode=True, llm=LLMConfig())
    agent = MonitoringAgent(config)
    agent.data_service = MockDataService()
    
    state = WorkflowState()
    from app.models.schemas import ExecutionResult, ProductInfo
    state.execution_results.append(ExecutionResult(campaign_id="high_rev", cost=100.0))
    state.product_info = ProductInfo(product_id="prod", name="P", category="C", price=10.0, description="D")
    
    # baseline = 1000, rev = 5000 -> lift = 4.0
    state.baseline = BaselineMetrics(product_id="prod", category="C", historical_revenue=1000.0, target_lift_pct=0.15)
    state = await agent.run(state)
    assert state.baseline.actual_lift_pct == 4.0
    assert state.baseline.target_achieved is True

    # 4. campaign revenue < baseline
    state.execution_results[-1] = ExecutionResult(campaign_id="high_rev", cost=100.0) # rev is 5000
    state.baseline = BaselineMetrics(product_id="prod", category="C", historical_revenue=10000.0, target_lift_pct=0.15)
    state = await agent.run(state)
    assert state.baseline.actual_lift_pct == -0.5
    assert state.baseline.target_achieved is False

@pytest.mark.asyncio
async def test_campaign_cost_zero():
    # 5. campaign cost = 0
    config = Config(demo_mode=True, llm=LLMConfig())
    agent = MonitoringAgent(config)
    agent.data_service = MockDataService()
    
    state = WorkflowState()
    from app.models.schemas import ExecutionResult, ProductInfo
    state.execution_results.append(ExecutionResult(campaign_id="high_rev", cost=0.0))
    state.product_info = ProductInfo(product_id="prod", name="P", category="C", price=10.0, description="D")
    
    state = await agent.run(state)
    
    # rev = 5000, cost = 0 -> roi = rev = 5000.0
    assert state.metrics[-1].roi == 5000.0

@pytest.mark.asyncio
async def test_malformed_empty_demo_llm():
    # 6. malformed/empty DEMO LLM output
    llm = LLMProvider(LLMConfig(), demo_mode=True)
    
    # Test fallback on empty string
    res = await llm.generate_structured("test unknown", "system prompt")
    assert isinstance(res, dict)
    assert len(res) == 0

@pytest.mark.asyncio
async def test_optimization_max_iteration_limit():
    # 7. optimization max-iteration limit
    config = Config(demo_mode=True, llm=LLMConfig(), max_optimization_loops=1)
    agent = OptimizationAgent(config)
    
    state = WorkflowState(optimization_iteration=1)
    
    # We don't need real memory store, just run agent to see if it forces STOP
    from app.models.schemas import Campaign, CampaignContent, CampaignChannel
    state.campaigns.append(Campaign(campaign_id="c1", name="N", product_id="P", segment_id="S", channel=CampaignChannel.EMAIL, content=CampaignContent()))
    state.metrics.append(CampaignMetrics(campaign_id="c1"))
    
    state = await agent.run(state)
    
    # Because config.max_optimization_loops == 1 and state.optimization_iteration == 1,
    # the decision MUST be STOP, even if LLM said OPTIMIZE.
    assert state.optimization.decision == OptimizationDecision.STOP

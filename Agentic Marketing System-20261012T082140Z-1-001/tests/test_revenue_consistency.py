import pytest
from app.models.schemas import WorkflowState, CampaignMetrics, BaselineMetrics, ExecutionResult, ProductInfo
from app.agents.monitoring import MonitoringAgent
from app.config import Config, LLMConfig
import pandas as pd

class MockDataServiceForRevenueCheck:
    def get_campaign_events(self, campaign_id: str):
        # We explicitly set a revenue that is not easily confused with cost
        return pd.DataFrame([{
            "sent": 100, 
            "opened": 50, 
            "clicked": 10, 
            "converted": 5, 
            "revenue": 3500.50
        }])
        
    def load_purchases(self):
        return pd.DataFrame()
        
    def load_customers(self):
        return pd.DataFrame()

@pytest.mark.asyncio
async def test_revenue_consistency_between_metrics_and_roi():
    config = Config(demo_mode=True, llm=LLMConfig())
    agent = MonitoringAgent(config)
    agent.data_service = MockDataServiceForRevenueCheck()
    
    state = WorkflowState()
    state.execution_results.append(ExecutionResult(campaign_id="rev_test", cost=500.0))
    state.product_info = ProductInfo(product_id="prod", name="P", category="C", price=10.0, description="D")
    
    state = await agent.run(state)
    
    metrics = state.metrics[-1]
    
    # 1. Assert the CampaignMetrics explicitly stores the revenue
    assert hasattr(metrics, "revenue"), "CampaignMetrics must have a revenue field"
    assert metrics.revenue == 3500.50
    
    # 2. Assert the baseline campaign_revenue matches exactly
    assert state.baseline.campaign_revenue == 3500.50
    
    # 3. Assert ROI was calculated using the exact same revenue
    expected_roi = (3500.50 - 500.0) / 500.0
    assert metrics.roi == expected_roi
    
    # This guarantees no second independent revenue calculation was used.

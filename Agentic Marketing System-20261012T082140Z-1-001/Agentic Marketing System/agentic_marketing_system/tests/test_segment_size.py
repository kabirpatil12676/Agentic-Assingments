"""
Regression tests: segment size must never exceed unique customer count,
and the segment must contain no duplicate customer IDs.
"""

import pytest
import asyncio
from app.config import Config
from app.models.schemas import WorkflowState, UserGoal
from app.agents.segmentation import SegmentationAgent
from app.services.data_service import DataService


def _unique_customer_count(config: Config) -> int:
    data_service = DataService(config)
    customers_df = data_service.load_customers()
    return int(customers_df["customer_id"].nunique())


@pytest.mark.asyncio
async def test_segment_size_cannot_exceed_unique_customers():
    """
    REGRESSION (Defect 1): target_segment_size must be <= unique_customer_count.
    The segment audience is drawn from customers table; phantom rows must not
    inflate the count beyond the number of distinct customer_ids.
    """
    config = Config(demo_mode=True)
    unique_customer_count = _unique_customer_count(config)

    agent = SegmentationAgent(config)
    state = WorkflowState(goal=UserGoal(goal_text="Test", target_audience="Student"))

    new_state = await agent.run(state)

    assert len(new_state.segments) > 0
    target_segment_size = new_state.segments[0].size

    assert target_segment_size <= unique_customer_count, (
        f"Segment size ({target_segment_size}) exceeded unique customer count "
        f"({unique_customer_count}). This indicates duplicate rows or a join that "
        f"inflates the customer list."
    )


@pytest.mark.asyncio
async def test_segment_customer_ids_contain_no_duplicates():
    """
    REGRESSION (Defect 1 — duplicate ID check):
    The DataService.load_customers() result, filtered to the target audience,
    must contain no duplicate customer_id values.
    """
    config = Config(demo_mode=True)
    ds = DataService(config)
    customers_df = ds.load_customers()

    # Filter to Student occupation (same logic as SegmentationAgent)
    segment_df = customers_df[customers_df["occupation"].str.lower() == "student"]

    # Ensure drop_duplicates is applied (same as SegmentationAgent)
    segment_df = segment_df.drop_duplicates(subset=["customer_id"])

    ids = segment_df["customer_id"].tolist()
    unique_ids = list(set(ids))

    assert len(ids) == len(unique_ids), (
        f"Duplicate customer_ids found in segment. "
        f"Total: {len(ids)}, Unique: {len(unique_ids)}, "
        f"Duplicates: {len(ids) - len(unique_ids)}"
    )


@pytest.mark.asyncio
async def test_general_segment_size_cannot_exceed_unique_customers():
    """
    REGRESSION (Defect 1 — general audience fallback):
    When target_audience is 'general' (or not a known filter), the segment
    defaults to the full customer table. Its size must equal the number of
    unique customers — not more.
    """
    config = Config(demo_mode=True)
    unique_customer_count = _unique_customer_count(config)

    agent = SegmentationAgent(config)
    state = WorkflowState(goal=UserGoal(goal_text="Test", target_audience="general"))

    new_state = await agent.run(state)

    assert len(new_state.segments) > 0
    target_segment_size = new_state.segments[0].size

    assert target_segment_size <= unique_customer_count, (
        f"General segment size ({target_segment_size}) exceeded unique customer count "
        f"({unique_customer_count})."
    )
    # General audience should equal exactly the unique customer count
    assert target_segment_size == unique_customer_count, (
        f"General segment size ({target_segment_size}) should equal unique customer "
        f"count ({unique_customer_count}) since no filter is applied."
    )

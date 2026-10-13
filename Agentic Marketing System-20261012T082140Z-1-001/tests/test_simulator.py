"""
Tests for deterministic campaign event simulator.
"""

from __future__ import annotations

import sys
from pathlib import Path
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.simulator import CampaignSimulator
from app.services.analytics_service import CampaignAnalytics
from scripts.seed_data import generate_dataset


@pytest.fixture(scope="module")
def sim_data():
    return generate_dataset(
        num_products=100,
        num_customers=1000,
        min_purchases=5000,
        seed=42,
    )


def test_simulator_generates_valid_events(sim_data):
    products_df, customers_df, purchases_df = sim_data
    simulator = CampaignSimulator(default_seed=42)

    product = products_df.iloc[0].to_dict()
    cohort = customers_df.head(50)

    events = simulator.simulate(
        campaign_id="cmp_test_sim",
        target_customers=cohort,
        product=product,
        purchases_df=purchases_df,
        products_df=products_df,
        variant="variant_A",
        channel="email",
    )

    assert len(events) == len(cohort)

    # Check required fields
    required_fields = {
        "event_id", "campaign_id", "customer_id", "variant",
        "channel", "sent", "opened", "clicked", "converted",
        "revenue", "timestamp",
    }
    for ev in events:
        assert required_fields.issubset(set(ev.keys()))


def test_simulator_funnel_consistency(sim_data):
    products_df, customers_df, purchases_df = sim_data
    simulator = CampaignSimulator(default_seed=42)

    product = products_df.iloc[0].to_dict()
    cohort = customers_df.head(200)

    events = simulator.simulate(
        campaign_id="cmp_funnel_test",
        target_customers=cohort,
        product=product,
        purchases_df=purchases_df,
        products_df=products_df,
    )

    for ev in events:
        # Cannot click without opening
        if ev["clicked"] == 1:
            assert ev["opened"] == 1, "Customer clicked without opening"
        # Cannot convert without clicking
        if ev["converted"] == 1:
            assert ev["clicked"] == 1, "Customer converted without clicking"
            assert ev["revenue"] > 0.0, "Conversion must generate positive revenue"
        else:
            assert ev["revenue"] == 0.0, "Non-converted event should have 0 revenue"


def test_simulator_deterministic_reproducibility(sim_data):
    products_df, customers_df, purchases_df = sim_data
    simulator1 = CampaignSimulator(default_seed=99)
    simulator2 = CampaignSimulator(default_seed=99)

    product = products_df.iloc[5].to_dict()
    cohort = customers_df.head(100)

    run1 = simulator1.simulate(
        campaign_id="cmp_repro",
        target_customers=cohort,
        product=product,
        purchases_df=purchases_df,
        products_df=products_df,
        seed=123,
    )
    run2 = simulator2.simulate(
        campaign_id="cmp_repro",
        target_customers=cohort,
        product=product,
        purchases_df=purchases_df,
        products_df=products_df,
        seed=123,
    )

    # Output should be 100% identical when seed matches (ignoring timestamp)
    for e1, e2 in zip(run1, run2):
        assert e1["customer_id"] == e2["customer_id"]
        assert e1["opened"] == e2["opened"]
        assert e1["clicked"] == e2["clicked"]
        assert e1["converted"] == e2["converted"]
        assert e1["revenue"] == e2["revenue"]


def test_simulator_ab_test_splitting(sim_data):
    products_df, customers_df, purchases_df = sim_data
    simulator = CampaignSimulator(default_seed=42)

    product = products_df.iloc[2].to_dict()
    cohort = customers_df.head(100)

    events = simulator.simulate_ab_test(
        campaign_id="cmp_ab_split",
        target_customers=cohort,
        product=product,
        purchases_df=purchases_df,
        products_df=products_df,
        treatment_variant="variant_A",
        split_ratio=0.5,
        seed=42,
    )

    assert len(events) == len(cohort)

    variants = [ev["variant"] for ev in events]
    assert "control" in variants
    assert "variant_A" in variants

    events_df = pd.DataFrame(events)
    ab_res = CampaignAnalytics.calculate_ab_variant_metrics(events_df, control_variant="control")
    assert "variants" in ab_res
    assert "control" in ab_res["variants"]
    assert "variant_A" in ab_res["variants"]

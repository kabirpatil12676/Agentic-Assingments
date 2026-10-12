"""
Tests for deterministic analytics services (Product, Customer, and Campaign).
"""

from __future__ import annotations

import sys
from pathlib import Path
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.analytics_service import (
    CampaignAnalytics,
    CustomerAnalytics,
    ProductAnalytics,
)
from scripts.seed_data import generate_dataset


@pytest.fixture(scope="module")
def analytics_data():
    return generate_dataset(
        num_products=100,
        num_customers=1000,
        min_purchases=5000,
        seed=42,
    )


# ─────────────────────────────────────────────────────────────────────────────
# 1. Product Analytics Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_product_analytics_calculations(analytics_data):
    products_df, _, purchases_df = analytics_data

    analyzed = ProductAnalytics.analyze_products(products_df, purchases_df)

    # Check required columns
    required = {
        "total_units_sold",
        "revenue",
        "average_rating",
        "conversion_rate",
        "revenue_contribution",
        "product_performance_score",
    }
    assert required.issubset(set(analyzed.columns))

    # Revenue contribution percentage should sum to approximately 100%
    total_share = analyzed["revenue_contribution"].sum()
    assert 99.0 <= total_share <= 101.0

    # Scores must be bounded [0, 100]
    assert (analyzed["product_performance_score"] >= 0.0).all()
    assert (analyzed["product_performance_score"] <= 100.0).all()


def test_product_top_products_and_category_summary(analytics_data):
    products_df, _, _ = analytics_data

    top5 = ProductAnalytics.get_top_products(products_df, top_n=5)
    assert len(top5) == 5
    # Order should be descending
    scores = top5["product_performance_score"].tolist()
    assert scores == sorted(scores, reverse=True)

    cat_summary = ProductAnalytics.get_category_summary(products_df)
    assert not cat_summary.empty
    assert "category" in cat_summary.columns
    assert "total_revenue" in cat_summary.columns
    assert "product_count" in cat_summary.columns


# ─────────────────────────────────────────────────────────────────────────────
# 2. Customer Analytics Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_customer_segmentation(analytics_data):
    _, customers_df, purchases_df = analytics_data

    segmented = CustomerAnalytics.segment_customers(customers_df, purchases_df)
    assert "segment" in segmented.columns

    unique_segments = set(segmented["segment"])
    expected_segments = {
        "High-Value Champions",
        "Loyal Regulars",
        "Budget Explorers",
        "Promising Newcomers",
        "At-Risk / Inactive",
        "General Occasional",
    }
    # At least some of these segments should be populated
    assert len(unique_segments.intersection(expected_segments)) >= 3
    assert len(segmented) == len(customers_df)


def test_customer_audience_filtering_and_summary(analytics_data):
    products_df, customers_df, purchases_df = analytics_data

    # Filter by occupation: Students
    students_df = CustomerAnalytics.filter_target_audience(
        customers_df,
        purchases_df,
        products_df,
        occupations=["Student"],
    )
    assert not students_df.empty
    assert (students_df["occupation"] == "Student").all()

    # Calculate audience summary
    summary = CustomerAnalytics.calculate_audience_summary(
        students_df,
        purchases_df,
        products_df,
    )
    assert summary["total_customers"] == len(students_df)
    assert 18.0 <= summary["average_age"] <= 26.0
    assert summary["average_spend"] > 0
    assert summary["order_frequency"] > 0
    assert len(summary["target_customer_ids"]) == len(students_df)
    assert isinstance(summary["preferred_product_categories"], list)


def test_customer_filter_age_and_spend(analytics_data):
    products_df, customers_df, purchases_df = analytics_data

    filtered = CustomerAnalytics.filter_target_audience(
        customers_df,
        purchases_df,
        products_df,
        min_age=25,
        max_age=35,
        min_spend=100.0,
    )
    assert (filtered["age"] >= 25).all()
    assert (filtered["age"] <= 35).all()
    assert (filtered["total_spend"] >= 100.0).all()


# ─────────────────────────────────────────────────────────────────────────────
# 3. Campaign Analytics Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_campaign_metrics_calculation():
    # Synthetic test events
    events_data = {
        "sent": [1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
        "opened": [1, 1, 1, 1, 0, 0, 1, 0, 1, 1],      # 7 opened
        "clicked": [1, 1, 0, 1, 0, 0, 0, 0, 0, 1],     # 4 clicked
        "converted": [1, 0, 0, 1, 0, 0, 0, 0, 0, 0],   # 2 converted
        "revenue": [100.0, 0.0, 0.0, 50.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],  # 150.0
    }
    events_df = pd.DataFrame(events_data)

    metrics = CampaignAnalytics.calculate_campaign_metrics(events_df)

    assert metrics["sent"] == 10
    assert metrics["opened"] == 7
    assert metrics["clicked"] == 4
    assert metrics["converted"] == 2
    assert metrics["open_rate"] == 0.70
    assert metrics["click_rate"] == 0.40
    assert metrics["conversion_rate"] == 0.20
    assert metrics["revenue"] == 150.0
    assert metrics["average_order_value"] == 75.0


def test_ab_variant_metrics_and_lift():
    # Control vs Treatment
    events_data = {
        "variant": ["control"] * 5 + ["variant_A"] * 5,
        "sent": [1] * 10,
        "opened": [1, 0, 1, 0, 0] + [1, 1, 1, 1, 0],       # ctrl: 2/5=0.40, varA: 4/5=0.80
        "clicked": [1, 0, 0, 0, 0] + [1, 1, 0, 0, 0],      # ctrl: 1/5=0.20, varA: 2/5=0.40
        "converted": [1, 0, 0, 0, 0] + [1, 1, 0, 0, 0],    # ctrl: 1/5=0.20, varA: 2/5=0.40
        "revenue": [50.0, 0.0, 0.0, 0.0, 0.0] + [50.0, 70.0, 0.0, 0.0, 0.0], # ctrl: 50, varA: 120
    }
    events_df = pd.DataFrame(events_data)

    res = CampaignAnalytics.calculate_ab_variant_metrics(events_df, control_variant="control")

    assert "control" in res["variants"]
    assert "variant_A" in res["variants"]

    ctrl = res["variants"]["control"]
    var_a = res["variants"]["variant_A"]

    assert ctrl["open_rate"] == 0.40
    assert var_a["open_rate"] == 0.80
    assert var_a["revenue"] == 120.0

    # Lifts
    lifts = res["lifts"]["variant_A"]
    # (0.80 - 0.40) / 0.40 = 1.0 (100% lift)
    assert lifts["open_rate_lift"] == 1.0
    # (120 - 50) / 50 = 1.4 (140% lift)
    assert lifts["revenue_lift"] == 1.4

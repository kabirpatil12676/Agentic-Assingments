"""
Deterministic analytics service.

Provides pure Python / Pandas / SQL calculations for:
- Product analysis (units sold, revenue, average rating, conversion rate, revenue contribution %, performance score)
- Customer analysis (segmentation, target audience filtering, average age, average spend, order frequency, preferred categories, target IDs)
- Campaign analytics (sent, opened, clicked, converted, open rate, click rate, conversion rate, revenue, AOV, A/B variant metrics & lift)

NO LLM calls are used for metrics or arithmetic.
"""

from __future__ import annotations

import logging
from typing import Any, Optional, Sequence
import pandas as pd

from app.utils.helpers import safe_divide, clamp

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Product Analytics
# ─────────────────────────────────────────────────────────────────────────────

class ProductAnalytics:
    """Deterministic product analysis service."""

    @staticmethod
    def analyze_products(
        products_df: pd.DataFrame,
        purchases_df: Optional[pd.DataFrame] = None,
    ) -> pd.DataFrame:
        """
        Compute performance metrics for every product in the catalogue.

        Returns a DataFrame containing:
        - product_id, product_name, category, price, cost
        - total_units_sold: sum of units sold
        - revenue: total revenue generated
        - average_rating: customer rating
        - conversion_rate: base conversion rate
        - revenue_contribution: percentage share of total catalogue revenue (0-100%)
        - product_performance_score: composite score (0-100)
        """
        df = products_df.copy()

        # If purchases_df is provided, verify or re-compute sales aggregates
        if purchases_df is not None and not purchases_df.empty:
            agg = (
                purchases_df.groupby("product_id")
                .agg(
                    calc_units=("quantity", "sum"),
                    calc_revenue=("total_amount", "sum"),
                )
                .reset_index()
            )
            df = df.drop(columns=["units_sold", "revenue"], errors="ignore").merge(
                agg, on="product_id", how="left"
            )
            df["total_units_sold"] = df["calc_units"].fillna(0).astype(int)
            df["revenue"] = df["calc_revenue"].fillna(0.0).round(2)
        else:
            df["total_units_sold"] = df["units_sold"].astype(int)
            df["revenue"] = df["revenue"].astype(float)

        total_store_revenue = float(df["revenue"].sum())

        # Revenue contribution (%)
        if total_store_revenue > 0:
            df["revenue_contribution"] = (
                (df["revenue"] / total_store_revenue) * 100.0
            ).round(2)
        else:
            df["revenue_contribution"] = 0.0

        # Product performance score (deterministic composite formula, scale 0 - 100)
        # 1. Rating score (weight 25%): rating / 5.0 * 25
        rating_score = (df["average_rating"] / 5.0).clip(0.0, 1.0) * 25.0

        # 2. Conversion score (weight 25%): normalized relative to max
        max_conv = float(df["conversion_rate"].max())
        if max_conv > 0:
            conv_score = (df["conversion_rate"] / max_conv).clip(0.0, 1.0) * 25.0
        else:
            conv_score = 0.0

        # 3. Revenue contribution score (weight 30%): capped multiplier
        rev_score = (df["revenue_contribution"] * 3.0).clip(0.0, 30.0)

        # 4. Sales volume score (weight 20%): relative to top seller
        max_units = float(df["total_units_sold"].max())
        if max_units > 0:
            vol_score = (df["total_units_sold"] / max_units).clip(0.0, 1.0) * 20.0
        else:
            vol_score = 0.0

        df["product_performance_score"] = (
            rating_score + conv_score + rev_score + vol_score
        ).round(2).clip(0.0, 100.0)

        return df

    @staticmethod
    def get_top_products(
        products_df: pd.DataFrame,
        by: str = "product_performance_score",
        top_n: int = 10,
    ) -> pd.DataFrame:
        """Return top N products by given metric."""
        analyzed = ProductAnalytics.analyze_products(products_df)
        return analyzed.sort_values(by=by, ascending=False).head(top_n)

    @staticmethod
    def get_category_summary(products_df: pd.DataFrame) -> pd.DataFrame:
        """Aggregate product metrics by category."""
        analyzed = ProductAnalytics.analyze_products(products_df)
        summary = (
            analyzed.groupby("category")
            .agg(
                product_count=("product_id", "count"),
                total_units_sold=("total_units_sold", "sum"),
                total_revenue=("revenue", "sum"),
                average_price=("price", "mean"),
                average_rating=("average_rating", "mean"),
                avg_performance_score=("product_performance_score", "mean"),
            )
            .reset_index()
        )
        summary["total_revenue"] = summary["total_revenue"].round(2)
        summary["average_price"] = summary["average_price"].round(2)
        summary["average_rating"] = summary["average_rating"].round(2)
        summary["avg_performance_score"] = summary["avg_performance_score"].round(2)
        return summary


# ─────────────────────────────────────────────────────────────────────────────
# Customer Analytics
# ─────────────────────────────────────────────────────────────────────────────

class CustomerAnalytics:
    """Deterministic customer analysis and segmentation service."""

    @staticmethod
    def segment_customers(
        customers_df: pd.DataFrame,
        purchases_df: Optional[pd.DataFrame] = None,
    ) -> pd.DataFrame:
        """
        Segment customers into behavioural tiers based on deterministic rules:
        - 'High-Value Champions'
        - 'Loyal Regulars'
        - 'Budget Explorers'
        - 'Promising Newcomers'
        - 'At-Risk / Inactive'
        - 'General Occasional'
        """
        df = customers_df.copy()

        # Quantile thresholds for segmentation
        spend_p75 = df["total_spend"].quantile(0.75)
        spend_p50 = df["total_spend"].quantile(0.50)
        orders_p75 = df["total_orders"].quantile(0.75)
        orders_p50 = df["total_orders"].quantile(0.50)

        # Average order value
        df["avg_order_value"] = (
            df["total_spend"] / df["total_orders"].replace(0, 1)
        ).round(2)
        aov_p30 = df["avg_order_value"].quantile(0.30)

        segments: list[str] = []
        for _, row in df.iterrows():
            spend = row["total_spend"]
            orders = row["total_orders"]
            c_type = row["customer_type"]
            aov = row["avg_order_value"]

            if c_type == "Inactive" or orders == 0:
                segments.append("At-Risk / Inactive")
            elif spend >= spend_p75 and orders >= orders_p75:
                segments.append("High-Value Champions")
            elif spend >= spend_p50 and orders >= orders_p50:
                segments.append("Loyal Regulars")
            elif c_type == "New" or orders <= 1:
                segments.append("Promising Newcomers")
            elif aov <= aov_p30 and orders > 1:
                segments.append("Budget Explorers")
            else:
                segments.append("General Occasional")

        df["segment"] = segments
        return df

    @staticmethod
    def filter_target_audience(
        customers_df: pd.DataFrame,
        purchases_df: Optional[pd.DataFrame] = None,
        products_df: Optional[pd.DataFrame] = None,
        *,
        occupations: Optional[Sequence[str]] = None,
        min_age: Optional[int] = None,
        max_age: Optional[int] = None,
        min_spend: Optional[float] = None,
        max_spend: Optional[float] = None,
        customer_types: Optional[Sequence[str]] = None,
        cities: Optional[Sequence[str]] = None,
        segments: Optional[Sequence[str]] = None,
        preferred_categories: Optional[Sequence[str]] = None,
    ) -> pd.DataFrame:
        """
        Filter customer base based on multiple criteria deterministically.
        """
        df = customers_df.copy()

        if "segment" not in df.columns:
            df = CustomerAnalytics.segment_customers(df)

        if occupations:
            df = df[df["occupation"].isin(occupations)]

        if min_age is not None:
            df = df[df["age"] >= min_age]

        if max_age is not None:
            df = df[df["age"] <= max_age]

        if min_spend is not None:
            df = df[df["total_spend"] >= min_spend]

        if max_spend is not None:
            df = df[df["total_spend"] <= max_spend]

        if customer_types:
            df = df[df["customer_type"].isin(customer_types)]

        if cities:
            df = df[df["city"].isin(cities)]

        if segments:
            df = df[df["segment"].isin(segments)]

        # Category affinity filter (customers who have purchased in specified categories)
        if preferred_categories and purchases_df is not None and products_df is not None:
            eligible_products = set(
                products_df[products_df["category"].isin(preferred_categories)]["product_id"]
            )
            matching_purchases = purchases_df[purchases_df["product_id"].isin(eligible_products)]
            matching_cust_ids = set(matching_purchases["customer_id"])
            df = df[df["customer_id"].isin(matching_cust_ids)]

        return df

    @staticmethod
    def calculate_audience_summary(
        audience_df: pd.DataFrame,
        purchases_df: Optional[pd.DataFrame] = None,
        products_df: Optional[pd.DataFrame] = None,
    ) -> dict[str, Any]:
        """
        Compute key statistical summary of target audience:
        - average age
        - average spend
        - order frequency (average total orders)
        - preferred product categories
        - target customer IDs
        """
        if audience_df.empty:
            return {
                "total_customers": 0,
                "average_age": 0.0,
                "average_spend": 0.0,
                "order_frequency": 0.0,
                "preferred_product_categories": [],
                "target_customer_ids": [],
            }

        avg_age = round(float(audience_df["age"].mean()), 1)
        avg_spend = round(float(audience_df["total_spend"].mean()), 2)
        order_freq = round(float(audience_df["total_orders"].mean()), 2)
        target_ids = audience_df["customer_id"].tolist()

        # Preferred product categories for this audience
        preferred_cats: list[str] = []
        if purchases_df is not None and products_df is not None and target_ids:
            aud_purchases = purchases_df[purchases_df["customer_id"].isin(target_ids)]
            if not aud_purchases.empty:
                merged = aud_purchases.merge(
                    products_df[["product_id", "category"]], on="product_id", how="left"
                )
                cat_counts = (
                    merged.groupby("category")["quantity"]
                    .sum()
                    .sort_values(ascending=False)
                )
                preferred_cats = cat_counts.index.tolist()

        return {
            "total_customers": len(audience_df),
            "average_age": avg_age,
            "average_spend": avg_spend,
            "order_frequency": order_freq,
            "preferred_product_categories": preferred_cats,
            "target_customer_ids": target_ids,
        }


# ─────────────────────────────────────────────────────────────────────────────
# Campaign Analytics
# ─────────────────────────────────────────────────────────────────────────────

class CampaignAnalytics:
    """Deterministic campaign performance analytics service."""

    @staticmethod
    def calculate_campaign_metrics(events_df: pd.DataFrame) -> dict[str, Any]:
        """
        Calculate standard performance KPIs from campaign interaction events:
        - sent, opened, clicked, converted
        - open rate, click rate, click-to-open rate, conversion rate
        - total revenue, average order value (AOV)
        """
        if events_df.empty:
            return {
                "sent": 0,
                "opened": 0,
                "clicked": 0,
                "converted": 0,
                "open_rate": 0.0,
                "click_rate": 0.0,
                "click_to_open_rate": 0.0,
                "conversion_rate": 0.0,
                "revenue": 0.0,
                "average_order_value": 0.0,
            }

        sent = int(events_df["sent"].sum())
        opened = int(events_df["opened"].sum())
        clicked = int(events_df["clicked"].sum())
        converted = int(events_df["converted"].sum())
        total_rev = round(float(events_df["revenue"].sum()), 2)

        open_rate = round(safe_divide(opened, sent), 4)
        click_rate = round(safe_divide(clicked, sent), 4)
        click_to_open_rate = round(safe_divide(clicked, opened), 4)
        conv_rate = round(safe_divide(converted, sent), 4)
        aov = round(safe_divide(total_rev, converted), 2)

        return {
            "sent": sent,
            "opened": opened,
            "clicked": clicked,
            "converted": converted,
            "open_rate": open_rate,
            "click_rate": click_rate,
            "click_to_open_rate": click_to_open_rate,
            "conversion_rate": conv_rate,
            "revenue": total_rev,
            "average_order_value": aov,
        }

    @staticmethod
    def calculate_ab_variant_metrics(
        events_df: pd.DataFrame,
        control_variant: str = "control",
    ) -> dict[str, Any]:
        """
        Compute A/B test variant metrics and comparative lifts against control:
        Returns per-variant KPI dictionaries plus lift relative to control.
        """
        if events_df.empty or "variant" not in events_df.columns:
            return {}

        variants = events_df["variant"].unique()
        variant_metrics: dict[str, Any] = {}

        for var in sorted(variants):
            v_df = events_df[events_df["variant"] == var]
            variant_metrics[var] = CampaignAnalytics.calculate_campaign_metrics(v_df)

        # Compute lifts if control variant exists
        lifts: dict[str, dict[str, float]] = {}
        if control_variant in variant_metrics:
            ctrl = variant_metrics[control_variant]
            for var, met in variant_metrics.items():
                if var == control_variant:
                    continue

                open_lift = round(safe_divide(met["open_rate"] - ctrl["open_rate"], ctrl["open_rate"]), 4)
                click_lift = round(safe_divide(met["click_rate"] - ctrl["click_rate"], ctrl["click_rate"]), 4)
                conv_lift = round(safe_divide(met["conversion_rate"] - ctrl["conversion_rate"], ctrl["conversion_rate"]), 4)
                rev_lift = round(safe_divide(met["revenue"] - ctrl["revenue"], ctrl["revenue"]), 4)

                lifts[var] = {
                    "open_rate_lift": open_lift,
                    "click_rate_lift": click_lift,
                    "conversion_rate_lift": conv_lift,
                    "revenue_lift": rev_lift,
                }

        return {
            "variants": variant_metrics,
            "lifts": lifts,
        }

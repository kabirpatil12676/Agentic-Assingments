"""
Deterministic campaign event simulator.

Generates simulated campaign interaction events:
- sent
- opened
- clicked
- converted
- revenue

Simulation dynamics depend realistically on:
- Customer profile (customer_type, occupation, age, spending level)
- Customer purchase history (past category affinity, order count)
- Selected product (category match, price sensitivity, ratings, conversion rate)
- Campaign variant (treatment boost e.g. discount, urgency, social proof)
- Distribution channel (email, sms, push, social)

Always reproducible given the same random seed.
"""

from __future__ import annotations

import logging
import random
from datetime import datetime, timezone
from typing import Any, Optional, Sequence
import pandas as pd

from app.utils.helpers import clamp, generate_id

logger = logging.getLogger(__name__)


class CampaignSimulator:
    """Simulates realistic campaign delivery and response events."""

    def __init__(self, default_seed: int = 42) -> None:
        self.default_seed = default_seed

    def simulate(
        self,
        campaign_id: str,
        target_customers: pd.DataFrame,
        product: dict[str, Any],
        purchases_df: Optional[pd.DataFrame] = None,
        products_df: Optional[pd.DataFrame] = None,
        variant: str = "control",
        channel: str = "email",
        discount_pct: float = 0.0,
        seed: Optional[int] = None,
    ) -> list[dict[str, Any]]:
        """
        Simulate delivery and funnel events for a target customer cohort.

        Returns:
            List of event records (sent, opened, clicked, converted, revenue).
        """
        sim_seed = seed if seed is not None else self.default_seed
        rng = random.Random(sim_seed)

        if target_customers.empty:
            logger.warning("Simulate called with empty target customer dataframe.")
            return []

        # Precompute customer-category affinities if historical purchases available
        customer_category_affinity: set[str] = set()
        if purchases_df is not None and products_df is not None:
            prod_cat_map = dict(zip(products_df["product_id"], products_df["category"]))
            target_p_cat = product.get("category", "")

            # Filter purchases for target product's category
            cat_purchases = purchases_df[
                purchases_df["product_id"].map(prod_cat_map) == target_p_cat
            ]
            customer_category_affinity = set(cat_purchases["customer_id"].unique())

        # Base channel probabilities
        channel_base = {
            "email": {"open": 0.24, "click": 0.22, "conv": 0.16},
            "sms": {"open": 0.46, "click": 0.18, "conv": 0.13},
            "push": {"open": 0.36, "click": 0.19, "conv": 0.12},
            "social": {"open": 0.18, "click": 0.15, "conv": 0.09},
        }.get(channel.lower(), {"open": 0.24, "click": 0.22, "conv": 0.16})

        # Variant modifiers
        variant_mod = {
            "control": {"open": 0.0, "click": 0.0, "conv": 0.0},
            "variant_A": {"open": 0.05, "click": 0.06, "conv": 0.05},  # e.g. promotional discount
            "variant_B": {"open": 0.03, "click": 0.08, "conv": 0.03},  # e.g. social proof / urgency
            "treatment": {"open": 0.04, "click": 0.07, "conv": 0.04},
        }.get(variant, {"open": 0.0, "click": 0.0, "conv": 0.0})

        # Product attributes
        prod_price = float(product.get("price", 49.99))
        prod_rating = float(product.get("average_rating", 4.0))
        prod_base_conv = float(product.get("conversion_rate", 0.04))

        # Rating modifier
        rating_mod = 0.03 if prod_rating >= 4.4 else (-0.03 if prod_rating < 3.5 else 0.0)

        events: list[dict[str, Any]] = []
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

        for _, cust in target_customers.iterrows():
            c_id = cust["customer_id"]
            c_type = cust.get("customer_type", "Regular")
            occupation = cust.get("occupation", "")
            total_orders = int(cust.get("total_orders", 1))
            total_spend = float(cust.get("total_spend", 50.0))
            avg_order_value = total_spend / total_orders if total_orders > 0 else 50.0

            # 1. Customer profile modifier
            if c_type == "VIP":
                cust_open_mod = 0.14
                cust_click_mod = 0.09
                cust_conv_mod = 0.07
            elif c_type == "Regular":
                cust_open_mod = 0.06
                cust_click_mod = 0.04
                cust_conv_mod = 0.03
            elif c_type == "New":
                cust_open_mod = 0.03
                cust_click_mod = 0.02
                cust_conv_mod = 0.01
            elif c_type == "Inactive":
                cust_open_mod = -0.12
                cust_click_mod = -0.08
                cust_conv_mod = -0.06
            else:  # Occasional
                cust_open_mod = 0.0
                cust_click_mod = 0.0
                cust_conv_mod = 0.0

            # Occupation / Student pattern
            student_mod = 0.0
            if occupation == "Student":
                if prod_price < 60.0:
                    student_mod = 0.06  # students love budget products
                elif prod_price > 120.0:
                    student_mod = -0.08  # price sensitivity

            # Category affinity modifier from past purchase history
            affinity_mod = 0.12 if c_id in customer_category_affinity else 0.0

            # Price sensitivity relative to customer average order value
            if prod_price > avg_order_value * 2.5:
                price_mod = -0.07
            elif prod_price <= avg_order_value:
                price_mod = 0.04
            else:
                price_mod = 0.0

            # ── 1. Sent ──
            sent = 1

            # ── 2. Open probability ──
            p_open = clamp(
                channel_base["open"] + variant_mod["open"] + cust_open_mod + (rating_mod * 0.5),
                0.02,
                0.95,
            )
            opened = 1 if rng.random() < p_open else 0

            # ── 3. Click probability (conditioned on opened) ──
            if opened:
                p_click = clamp(
                    channel_base["click"]
                    + variant_mod["click"]
                    + cust_click_mod
                    + affinity_mod
                    + student_mod,
                    0.02,
                    0.90,
                )
                clicked = 1 if rng.random() < p_click else 0
            else:
                clicked = 0

            # ── 4. Conversion probability (conditioned on clicked) ──
            if clicked:
                p_conv = clamp(
                    channel_base["conv"]
                    + variant_mod["conv"]
                    + cust_conv_mod
                    + price_mod
                    + rating_mod
                    + (prod_base_conv * 0.5),
                    0.01,
                    0.85,
                )
                converted = 1 if rng.random() < p_conv else 0
            else:
                converted = 0

            # ── 5. Attributed Revenue ──
            if converted:
                # VIP customers occasionally buy multiple units
                quantity = 2 if (c_type == "VIP" and rng.random() < 0.30) else 1
                effective_price = round(prod_price * (1.0 - max(0.0, min(0.5, discount_pct))), 2)
                revenue = round(quantity * effective_price, 2)
            else:
                revenue = 0.0

            events.append({
                "event_id": generate_id("evt"),
                "campaign_id": campaign_id,
                "customer_id": c_id,
                "variant": variant,
                "channel": channel,
                "sent": sent,
                "opened": opened,
                "clicked": clicked,
                "converted": converted,
                "revenue": revenue,
                "timestamp": now_str,
            })

        return events

    def simulate_ab_test(
        self,
        campaign_id: str,
        target_customers: pd.DataFrame,
        product: dict[str, Any],
        purchases_df: Optional[pd.DataFrame] = None,
        products_df: Optional[pd.DataFrame] = None,
        channel: str = "email",
        split_ratio: float = 0.5,
        treatment_variant: str = "variant_A",
        discount_pct: float = 0.10,
        seed: Optional[int] = None,
    ) -> list[dict[str, Any]]:
        """
        Run a deterministic A/B test simulation by splitting audience into control and treatment.
        """
        sim_seed = seed if seed is not None else self.default_seed
        rng = random.Random(sim_seed)

        # Shuffle deterministically and split
        shuffled = target_customers.sample(frac=1.0, random_state=sim_seed).reset_index(drop=True)
        split_point = int(len(shuffled) * split_ratio)

        control_group = shuffled.iloc[:split_point]
        treatment_group = shuffled.iloc[split_point:]

        control_events = self.simulate(
            campaign_id=campaign_id,
            target_customers=control_group,
            product=product,
            purchases_df=purchases_df,
            products_df=products_df,
            variant="control",
            channel=channel,
            discount_pct=0.0,
            seed=sim_seed + 1,
        )

        treatment_events = self.simulate(
            campaign_id=campaign_id,
            target_customers=treatment_group,
            product=product,
            purchases_df=purchases_df,
            products_df=products_df,
            variant=treatment_variant,
            channel=channel,
            discount_pct=discount_pct,
            seed=sim_seed + 2,
        )

        return control_events + treatment_events

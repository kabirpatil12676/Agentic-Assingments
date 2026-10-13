"""
Monitoring Agent – computes campaign performance metrics.

All metric calculations (open rates, CTR, ROI, anomaly detection)
are done deterministically with Pandas. No LLM is used for arithmetic.

Baseline:
  On the first pass (optimization_iteration == 1, i.e. after first execution),
  the agent computes a historical baseline from purchase data for the same product
  and target segment before the campaign ran. This gives a real comparison
  against the 15% lift target.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING
from app.services.analytics_service import CampaignAnalytics
from app.services.data_service import DataService
from app.services.llm_provider import LLMProvider
from app.models.schemas import CampaignMetrics, BaselineMetrics

if TYPE_CHECKING:
    from app.config import Config
    from app.models.schemas import WorkflowState

logger = logging.getLogger(__name__)


class MonitoringAgent:
    """Computes campaign metrics, historical baseline, and anomaly summary."""

    def __init__(self, config: "Config") -> None:
        self.config = config
        self.data_service = DataService(config)
        self.llm = LLMProvider(config.llm, demo_mode=config.demo_mode)
        logger.info("MonitoringAgent initialised")

    async def run(self, state: "WorkflowState") -> "WorkflowState":
        """Compute monitoring metrics and update baseline comparison."""
        logger.info("MonitoringAgent running...")

        if not state.execution_results:
            state.errors.append("MonitoringAgent: No execution results available.")
            return state

        latest_exec = state.execution_results[-1]

        # ── 1. Read events from DB ─────────────────────────────────────────────
        events_df = self.data_service.get_campaign_events(latest_exec.campaign_id)
        if events_df.empty:
            state.errors.append(f"MonitoringAgent: No events found for {latest_exec.campaign_id}.")
            return state

        metrics_dict = CampaignAnalytics.calculate_campaign_metrics(events_df)

        # ── 2. Campaign metrics ────────────────────────────────────────────────
        # ROI Formula: (revenue - campaign_cost) / campaign_cost
        rev = metrics_dict.get("revenue", 0.0)
        cost = latest_exec.cost if latest_exec.cost is not None else 1.0
        roi = (rev - cost) / cost if cost > 0 else (rev if rev > 0 else 0.0)

        metrics = CampaignMetrics(
            campaign_id=latest_exec.campaign_id,
            revenue=rev,
            open_rate=metrics_dict.get("open_rate", 0.0),
            click_rate=metrics_dict.get("click_rate", 0.0),
            conversion_rate=metrics_dict.get("conversion_rate", 0.0),
            cost_per_conversion=cost / (metrics_dict.get("converted") or 1),
            roi=roi,
            engagement_score=metrics_dict.get("click_rate", 0.0) * 100,
        )

        # ── 3. Compute / update baseline ───────────────────────────────────────
        #  First pass: build baseline from purchase history.
        #  Subsequent passes: update actuals and compute lift.
        if state.product_info:
            baseline = state.baseline

            if baseline is None:
                # Build baseline from purchase history
                baseline = self._compute_baseline(state)

            # Always fill in campaign actuals (overwrites on loop iterations)
            baseline.campaign_conversion_rate = metrics.conversion_rate
            baseline.campaign_revenue = rev

            # Check for comparable historical campaign revenue in DB (same product, excluding current campaign)
            hist_camp_rev = None
            try:
                with self.data_service.get_connection() as conn:
                    cur = conn.cursor()
                    cur.execute("""
                        SELECT SUM(ce.revenue)
                        FROM campaigns c
                        JOIN campaign_events ce ON c.campaign_id = ce.campaign_id
                        WHERE c.product_id = ? AND c.campaign_id != ?
                        GROUP BY c.campaign_id
                    """, (state.product_info.product_id, latest_exec.campaign_id))
                    rows = [r[0] for r in cur.fetchall() if r[0] is not None]
                    if rows:
                        hist_camp_rev = sum(rows) / len(rows)
            except Exception:
                hist_camp_rev = None

            if hist_camp_rev is not None and hist_camp_rev > 0:
                actual_lift = (rev - hist_camp_rev) / hist_camp_rev
                baseline.actual_lift_pct = round(actual_lift, 4)
                if baseline.target_lift_pct > 0:
                    baseline.target_achieved = actual_lift >= baseline.target_lift_pct
                else:
                    baseline.target_achieved = actual_lift > 0.0
            else:
                # Do NOT calculate sales lift using lifetime purchase aggregates
                # If comparable campaign data is unavailable, lift cannot be reliably calculated
                baseline.actual_lift_pct = None
                baseline.target_achieved = None

            state.baseline = baseline

            lift_str = f"{baseline.actual_lift_pct*100:.1f}%" if baseline.actual_lift_pct is not None else "N/A"
            logger.info(
                "MonitoringAgent BASELINE: hist_camp_rev=%s  campaign_rev=%.2f  "
                "sales_lift=%s  target=%.2f  achieved=%s",
                hist_camp_rev,
                rev,
                lift_str,
                baseline.target_lift_pct,
                baseline.target_achieved,
            )
            state.logs.append(
                f"BASELINE | hist_camp_rev={hist_camp_rev} "
                f"camp_rev=${rev:.2f} "
                f"sales_lift={lift_str} "
                f"target={baseline.target_lift_pct*100:.0f}% "
                f"achieved={baseline.target_achieved}"
            )

        # ── 4. LLM anomaly summary (text only, no arithmetic) ─────────────────
        system_prompt = (
            "You are a data analyst. In one sentence, summarise whether these "
            "campaign metrics indicate normal or anomalous performance."
        )
        prompt = (
            f"Open Rate: {metrics.open_rate:.2%}, Click Rate: {metrics.click_rate:.2%}, "
            f"Conv Rate: {metrics.conversion_rate:.2%}, ROI: {roi:.2f}"
        )
        try:
            anomalies = await self.llm.generate(prompt, system_prompt=system_prompt)
            metrics.anomalies = [anomalies]
        except Exception as e:
            logger.error("MonitoringAgent LLM error: %s", e)

        state.metrics.append(metrics)
        state.logs.append(
            f"MonitoringAgent recorded metrics for {metrics.campaign_id}. ROI: {roi:.2f}"
        )
        return state

    def _compute_baseline(self, state: "WorkflowState") -> "BaselineMetrics":
        """
        Compute historical baseline from purchase data.

        Uses all purchases for this product to derive:
          - historical conversion rate (purchases / customers in segment)
          - historical revenue per customer
          - historical units sold
        """
        product_id = state.product_info.product_id
        category = state.product_info.category

        # Parse target_lift from goal text (look for "X%"), default to 0.0 (positive sales lift)
        target_lift = 0.0
        if state.goal and state.goal.goal_text:
            import re
            match = re.search(r"(\d+(?:\.\d+)?)%", state.goal.goal_text)
            if match:
                target_lift = float(match.group(1)) / 100.0

        try:
            purchases_df = self.data_service.load_purchases()
            customers_df = self.data_service.load_customers()

            # Filter purchases for this product
            prod_purchases = purchases_df[purchases_df["product_id"] == product_id]

            # Segment filter: count customers in target segment
            segment_size = state.segments[-1].size if state.segments else len(customers_df)

            total_customers_in_segment = max(segment_size, 1)
            unique_buyers = prod_purchases["customer_id"].nunique()
            hist_units = float(prod_purchases["quantity"].sum())
            hist_revenue = float(prod_purchases["total_amount"].sum())

            # Conversion rate = buyers who actually purchased / total segment customers
            hist_conversion_rate = min(unique_buyers / total_customers_in_segment, 1.0)

            logger.info(
                "Baseline computed: product=%s  segment_size=%d  buyers=%d  "
                "hist_conv=%.4f  hist_units=%.0f  hist_rev=%.2f",
                product_id, total_customers_in_segment, unique_buyers,
                hist_conversion_rate, hist_units, hist_revenue,
            )

            return BaselineMetrics(
                product_id=product_id,
                category=category,
                historical_units_sold=hist_units,
                historical_revenue=hist_revenue,
                historical_conversion_rate=hist_conversion_rate,
                target_lift_pct=target_lift,
            )

        except Exception as e:
            logger.error("MonitoringAgent: baseline computation failed: %s", e)
            return BaselineMetrics(
                product_id=product_id,
                category=category,
                target_lift_pct=target_lift,
            )

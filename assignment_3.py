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
PROJECT_DIR = Path(__file__).resolve().parent / "Agentic Marketing System-20261012T082140Z-1-001"
sys.path.insert(0, str(PROJECT_DIR))

from app.config import load_config
from app.utils.logging_config import setup_logging
from app.models.schemas import WorkflowState, UserGoal, CampaignChannel
from app.workflow.graph import build_workflow_graph
from app.services.data_service import DataService


def _ensure_db(config) -> None:
    """Initialize and populate the marketing DB if the products table is missing."""
    import sqlite3
    db = DataService(config)
    # Check if products table already has data
    try:
        with db.get_connection() as conn:
            count = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
            if count > 0:
                return   # DB already populated
    except Exception:
        pass   # Table missing → populate below

    print("Initializing marketing database from CSV files...")
    db.init_db()
    db.populate_from_csv()
    print("Database ready.\n")

async def run_marketing_system(goal_text: str = None):
    os.environ["DEMO_MODE"] = "true"
    default_goal = "Launch an email campaign for our new wireless headphones targeting young professionals"
    if goal_text:
        goal_text = goal_text.lstrip('\ufeff').strip()
    if not goal_text:
        goal_text = default_goal

    print("\n============================================================")
    print("   Assignment 3: Agentic Marketing Campaign System")
    print("============================================================")
    print(f"Goal: {goal_text}\n")
    print("Executing Autonomous LangGraph Multi-Agent Workflow...\n")

    os.environ.setdefault("MAX_OPT_LOOPS", "2")
    config = load_config()
    setup_logging("WARNING")
    _ensure_db(config)

    goal_lower = goal_text.lower()
    if "young professional" in goal_lower or "professional" in goal_lower:
        audience = "young professionals"
    elif "student" in goal_lower:
        audience = "students"
    elif "senior" in goal_lower or "retiree" in goal_lower:
        audience = "seniors"
    elif "freelancer" in goal_lower:
        audience = "freelancers"
    elif "nurse" in goal_lower or "healthcare" in goal_lower:
        audience = "nurses"
    else:
        audience = "general"

    # Connect product selection to user's goal
    target_product_id = None
    try:
        db = DataService(config)
        products_df = db.load_products()
        if not products_df.empty:
            for _, row in products_df.iterrows():
                p_name = str(row["product_name"]).lower()
                if "headphone" in goal_lower and "headphone" in p_name:
                    target_product_id = row["product_id"]
                    break
                elif "mouse" in goal_lower and "mouse" in p_name:
                    target_product_id = row["product_id"]
                    break
                elif "charging" in goal_lower and "charging" in p_name:
                    target_product_id = row["product_id"]
                    break
    except Exception:
        pass

    workflow = build_workflow_graph(config)
    goal = UserGoal(
        goal_text=goal_text,
        product_id=target_product_id,
        budget=1000.0,
        target_audience=audience,
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
        print(f"Target Segment: {seg.name} (Size: {seg.size} customers)")

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
        print(f"ROI             : {m.roi * 100:.1f}%  (Net Return on $1,000 Campaign Budget)")

    # ── Revenue Comparison & Sales Lift Evaluation ──
    import re
    lift_match = re.search(r"(\d+(?:\.\d+)?)%", goal_text)
    if lift_match:
        target_lift_pct = float(lift_match.group(1)) / 100.0
        target_label = f"{lift_match.group(1)}% sales lift"
    else:
        target_lift_pct = 0.0
        target_label = "Positive sales lift (> 0.0%)"

    # Check if comparable historical campaign revenue exists in DB (same product, excluding current run)
    comparable_hist_camp_rev = None
    if state.product_info:
        prod_id = state.product_info.product_id
        current_ids = [c.campaign_id for c in state.campaigns]
        try:
            db = DataService(config)
            with db.get_connection() as conn:
                placeholders = ",".join("?" for _ in current_ids)
                cur = conn.cursor()
                cur.execute(f"""
                    SELECT SUM(ce.revenue)
                    FROM campaigns c
                    JOIN campaign_events ce ON c.campaign_id = ce.campaign_id
                    WHERE c.product_id = ? AND c.campaign_id NOT IN ({placeholders})
                    GROUP BY c.campaign_id
                """, [prod_id] + current_ids)
                rows = [r[0] for r in cur.fetchall() if r[0] is not None]
                if rows:
                    comparable_hist_camp_rev = sum(rows) / len(rows)
        except Exception:
            comparable_hist_camp_rev = None

    camp_rev = state.metrics[-1].revenue if state.metrics else (state.baseline.campaign_revenue if state.baseline else 0.0)

    print(f"\n--- Baseline vs Campaign Comparison ---")
    if comparable_hist_camp_rev is not None and comparable_hist_camp_rev > 0:
        actual_lift = (camp_rev - comparable_hist_camp_rev) / comparable_hist_camp_rev
        target_achieved = actual_lift >= target_lift_pct if target_lift_pct > 0 else actual_lift > 0.0
        print(f"Historical Campaign Revenue : ${comparable_hist_camp_rev:.2f}  (Average of prior comparable campaigns)")
        print(f"Campaign Revenue            : ${camp_rev:.2f}  (Actual revenue generated from this campaign)")
        print(f"Sales Lift Target           : {target_label}")
        print(f"Sales Lift                  : {actual_lift * 100:.2f}%")
        print(f"Target Achieved             : {target_achieved}")
    else:
        actual_lift = None
        target_achieved = None
        lifetime_purchases = state.baseline.historical_revenue if state.baseline else 0.0
        print(f"Historical Campaign Revenue : Unavailable (No comparable historical campaign data for this audience & period)")
        print(f"Campaign Revenue            : ${camp_rev:.2f}  (Revenue from this campaign)")
        print(f"Sales Lift Target           : {target_label}")
        print(f"Sales Lift                  : Not reliably calculable (lifetime catalog purchases of ${lifetime_purchases:.2f} are not comparable)")
        print(f"Target Achieved             : Pending baseline (cannot be determined without comparable historical campaign data)")

    if state.optimization:
        opt = state.optimization[-1] if isinstance(state.optimization, list) else state.optimization
        decision_val = getattr(opt, 'decision', getattr(opt, 'action', 'stop'))
        # Extract the string value from enum if needed
        if hasattr(decision_val, 'value'):
            decision_val = decision_val.value
        reason_val = getattr(opt, 'reason', '')
        print(f"\nOptimization Decision: {str(decision_val).upper()}")
        print(f"Reason             : {reason_val}")
        if target_achieved is True:
            print("Status             : Campaign achieved target performance successfully.")
        elif target_achieved is False:
            print("Status             : Target sales lift was NOT met. Iteration limit reached; further optimization recommended.")
        else:
            print("Status             : Iteration limit reached (2/2). Target status pending comparable historical baseline.")
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

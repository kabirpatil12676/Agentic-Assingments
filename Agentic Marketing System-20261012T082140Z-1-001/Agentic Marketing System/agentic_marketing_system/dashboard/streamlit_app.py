"""
Streamlit dashboard entry point.

Provides a rich UI for:
  - Submitting marketing goals
  - Viewing the workflow execution in real time
  - Inspecting agent outputs
  - Interactive Plotly charts for campaign metrics
  - Long-term memory exploration

Launch:
    streamlit run dashboard/streamlit_app.py
"""

from __future__ import annotations

import sys
import asyncio
from pathlib import Path
from typing import Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Ensure project root is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import Config, load_config
from app.models.schemas import WorkflowState, UserGoal, CampaignChannel
from app.workflow.graph import build_workflow_graph
from app.memory.memory_store import MemoryStore


def display_product_intelligence(state: WorkflowState) -> None:
    st.header("🛒 Product Intelligence")
    if not state.product_info:
        st.warning("No product selected.")
        return

    p = state.product_info
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Product ID", p.product_id)
    col2.metric("Name", p.name)
    col3.metric("Category", p.category)
    col4.metric("Price", f"${p.price:.2f}")

    st.write(f"**Description:** {p.description}")
    st.write(f"**Competitive Position:** {p.competitive_position}")


def display_customer_intelligence(state: WorkflowState) -> None:
    st.header("👥 Customer Intelligence")
    if not state.segments:
        st.warning("No customer segments defined.")
        return

    segment = state.segments[-1]
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Segment Name", segment.name)
    col2.metric("Audience Size", f"{segment.size:,}")
    col3.metric("Avg Age", f"{segment.avg_age:.1f}" if segment.avg_age else "N/A")
    col4.metric("Avg Income", f"${segment.avg_income:,.2f}" if segment.avg_income else "N/A")

    st.write(f"**Description:** {segment.description}")
    
    if segment.preferred_channels:
        st.write(f"**Preferred Channels:** {', '.join(c.value for c in segment.preferred_channels)}")


def display_campaign_generation(state: WorkflowState) -> None:
    st.header("📝 Campaign Generation")
    if not state.campaigns:
        st.warning("No campaigns generated.")
        return

    for i, camp in enumerate(state.campaigns):
        with st.expander(f"Campaign Iteration {i} - {camp.campaign_id}", expanded=(i == len(state.campaigns) - 1)):
            c = camp.content
            st.subheader(f"Variant: {camp.name}")
            st.write(f"**Subject:** {c.subject_line}")
            st.write(f"**Headline:** {c.headline}")
            st.write(f"**Body:** {c.body}")
            st.write(f"**CTA:** {c.cta}")
            st.write(f"**Channel:** {c.channel.value}")


def display_campaign_performance(state: WorkflowState) -> None:
    st.header("📈 Campaign Performance")
    
    if state.baseline:
        st.subheader("🎯 PRIMARY OBJECTIVE")
        b = state.baseline
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Baseline Revenue", f"${b.historical_revenue:,.2f}")
        c2.metric("Campaign Revenue", f"${b.campaign_revenue:,.2f}" if b.campaign_revenue is not None else "N/A")
        
        lift_str = f"{b.actual_lift_pct * 100:.2f}%" if b.actual_lift_pct is not None else "N/A"
        c3.metric("Sales Lift", lift_str, delta=lift_str if b.actual_lift_pct else None)
        
        c4.metric("Target Achieved?", "✅ YES" if b.target_achieved else "❌ NO")

    if state.metrics:
        st.subheader("📊 SECONDARY KPIs")
        m = state.metrics[-1]
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Open Rate", f"{m.open_rate:.2%}")
        c2.metric("Click Rate", f"{m.click_rate:.2%}")
        c3.metric("Conversion Rate", f"{m.conversion_rate:.2%}")
        c4.metric("ROI", f"{m.roi * 100:.2f}%")

        if m.anomalies:
            st.info(f"**Monitoring Summary:** {m.anomalies[0]}")


def display_optimization(state: WorkflowState) -> None:
    st.header("⚙️ Optimization Engine")
    if not state.optimization:
        st.info("No optimization loops executed.")
        return

    opt = state.optimization
    st.subheader(f"Decision: {opt.decision.value.upper()}")
    st.write(f"**Reason:** {opt.reason}")
    if opt.suggested_changes:
        st.write("**Recommended Changes:**")
        st.json(opt.suggested_changes)
    st.write(f"**Iteration Limit Reached:** {state.optimization_iteration >= 2}")


def display_memory_history(config: Config) -> None:
    st.header("🧠 Long-Term Memory")
    memory = MemoryStore(config)
    
    with memory._get_connection() as conn:
        df = pd.read_sql_query("SELECT * FROM campaign_memory ORDER BY timestamp DESC LIMIT 10", conn)
        
    if df.empty:
        st.info("No past campaigns in memory.")
        return

    # Extract JSON metrics for display
    import json
    parsed_data = []
    for _, row in df.iterrows():
        try:
            outcome = json.loads(row["outcome_json"])
            metrics = outcome.get("metrics", {})
            parsed_data.append({
                "Campaign ID": row["campaign_id"],
                "Category": row["product_category"],
                "Decision": outcome.get("decision", "unknown"),
                "Conv Rate": f"{metrics.get('conversion_rate', 0):.2%}",
                "ROI": f"{metrics.get('roi', 0):.2f}",
                "Timestamp": row["timestamp"]
            })
        except Exception:
            pass

    if parsed_data:
        st.dataframe(pd.DataFrame(parsed_data), use_container_width=True)

def _get_connection(self, memory: MemoryStore):
    return memory._get_connection()


async def run_workflow(workflow, initial_state, status_container, log_expander):
    final_state_dict = None
    async for event in workflow.astream(initial_state):
        for node_name, state_update in event.items():
            with status_container:
                st.success(f"✅ **{node_name.replace('_', ' ').title()}** completed.")
            
            if "logs" in state_update and state_update["logs"]:
                with log_expander:
                    st.write(state_update["logs"][-1])
            
            final_state_dict = state_update
    return final_state_dict

def main() -> None:
    st.set_page_config(
        page_title="Agentic Marketing System",
        page_icon="🎯",
        layout="wide",
    )

    st.title("🎯 Agentic AI Marketing Campaign Optimization")

    st.sidebar.header("Configuration")
    demo_mode = st.sidebar.checkbox("Run in DEMO MODE", value=True)
    
    config = load_config()
    import dataclasses
    config = dataclasses.replace(config, demo_mode=demo_mode)

    st.sidebar.markdown("---")
    st.sidebar.write("**Architecture:**")
    st.sidebar.write("• Planner\n• Product Analysis\n• Customer Segmentation\n• Campaign Generation\n• Execution\n• Monitoring\n• Optimization\n• Memory")

    # A. CAMPAIGN SETUP
    with st.form("campaign_setup"):
        st.subheader("Campaign Setup")
        goal_text = st.text_area(
            "Business Goal",
            value="Increase sales of our best-performing products among college students by 15%.",
            height=80
        )
        col1, col2 = st.columns(2)
        target_audience = col1.text_input("Target Audience", value="Student")
        budget = col2.number_input("Budget ($)", value=1000.0, step=100.0)
        
        submitted = st.form_submit_button("Run Campaign", type="primary")

    # B. AGENT WORKFLOW TRACE
    if submitted:
        st.markdown("---")
        st.header("⚡ Agent Workflow Trace")
        
        # Build Workflow
        workflow = build_workflow_graph(config)
        goal = UserGoal(
            goal_text=goal_text,
            budget=budget,
            target_audience=target_audience,
            channels=[CampaignChannel.EMAIL]
        )
        initial_state = WorkflowState(goal=goal).model_dump()
        
        status_container = st.container()
        log_expander = st.expander("Detailed Execution Logs", expanded=True)
        
        with st.spinner("Initializing Agents..."):
            final_state_dict = asyncio.run(run_workflow(workflow, initial_state, status_container, log_expander))

        if final_state_dict:
            state = WorkflowState(**final_state_dict)
            st.markdown("---")
            
            # Rendering components
            display_product_intelligence(state)
            st.markdown("---")
            display_customer_intelligence(state)
            st.markdown("---")
            display_campaign_generation(state)
            st.markdown("---")
            display_campaign_performance(state)
            st.markdown("---")
            display_optimization(state)
            
    st.markdown("---")
    display_memory_history(config)


if __name__ == "__main__":
    main()

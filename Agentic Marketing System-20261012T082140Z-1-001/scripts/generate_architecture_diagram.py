"""
Generate the architecture diagram for the Agentic Marketing System.

Produces: docs/architecture.png

Run:
    python scripts/generate_architecture_diagram.py
"""

from __future__ import annotations
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch

# ── Output path ────────────────────────────────────────────────────────────────
OUT_PATH = Path(__file__).resolve().parent.parent / "docs" / "architecture.png"

# ── Color palette (professional, accessible) ──────────────────────────────────
C_GOAL     = "#1A237E"
C_AGENT    = "#1565C0"
C_OPTIM    = "#0D47A1"
C_DECISION = "#00695C"
C_MEMORY   = "#4A148C"
C_STATE    = "#BF360C"
C_SQLITE   = "#37474F"
C_BG       = "#F8F9FA"
C_WHITE    = "#FFFFFF"
C_TEXT     = "#FFFFFF"
C_DARK     = "#212121"


def box(ax, cx, cy, w, h, label, sublabel=None,
        fc=C_AGENT, tc=C_TEXT, fontsize=8.5, radius=0.015):
    rect = FancyBboxPatch(
        (cx - w / 2, cy - h / 2), w, h,
        boxstyle=f"round,pad=0.008,rounding_size={radius}",
        facecolor=fc, edgecolor=C_WHITE, linewidth=0.8, zorder=3,
    )
    ax.add_patch(rect)
    if sublabel:
        ax.text(cx, cy + 0.013, label, ha="center", va="center",
                fontsize=fontsize, fontweight="bold", color=tc, zorder=4)
        ax.text(cx, cy - 0.016, sublabel, ha="center", va="center",
                fontsize=6.5, color=tc, zorder=4, style="italic")
    else:
        ax.text(cx, cy, label, ha="center", va="center",
                fontsize=fontsize, fontweight="bold", color=tc, zorder=4)


def arrow(ax, x1, y1, x2, y2, color="#455A64", lw=1.2,
          connectionstyle="arc3,rad=0.0", linestyle="solid"):
    ax.annotate(
        "", xy=(x2, y2), xytext=(x1, y1),
        arrowprops=dict(
            arrowstyle="->", color=color, lw=lw,
            linestyle=linestyle,
            connectionstyle=connectionstyle,
        ),
        zorder=2,
    )


def main():
    fig, ax = plt.subplots(figsize=(8.27, 11.69))
    fig.patch.set_facecolor(C_BG)
    ax.set_facecolor(C_BG)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    # ── Title ──────────────────────────────────────────────────────────────────
    ax.text(
        0.5, 0.975,
        "Figure 1. Agentic AI Personalized Marketing Campaign Optimization System Architecture",
        ha="center", va="top", fontsize=9, fontweight="bold", color=C_DARK,
    )

    # ── Main pipeline ─────────────────────────────────────────────────────────
    cx = 0.40
    BW = 0.30
    BH = 0.038

    nodes = [
        (0.90, "USER GOAL",                  '"Increase sales among students by 15%"', C_GOAL),
        (0.84, "PLANNER AGENT",              "Goal decomposition → ExecutionPlan",      C_AGENT),
        (0.78, "PRODUCT ANALYSIS AGENT",     "Pandas ranking → ProductInfo",            C_AGENT),
        (0.72, "CUSTOMER SEGMENTATION AGENT","Demographic filter → CustomerSegment",    C_AGENT),
        (0.66, "CAMPAIGN GENERATION AGENT",  "LLM copywriting → CampaignContent",       C_AGENT),
        (0.60, "EXECUTION AGENT",            "Simulator → ExecutionResult (SQLite)",    C_AGENT),
        (0.54, "MONITORING AGENT",           "Pandas KPIs → CampaignMetrics + Baseline",C_AGENT),
        (0.47, "OPTIMIZATION AGENT",         "LLM decision → OptimizationRecommendation",C_OPTIM),
    ]

    for y, label, sub, color in nodes:
        box(ax, cx, y, BW, BH, label, sub, fc=color)

    # Straight arrows between sequential nodes
    for i in range(len(nodes) - 1):
        y1 = nodes[i][0] - BH / 2
        y2 = nodes[i + 1][0] + BH / 2
        arrow(ax, cx, y1, cx, y2)

    # ── Decision diamond (text only) ──────────────────────────────────────────
    dec_y = nodes[-1][0] - BH / 2 - 0.025
    ax.text(cx, dec_y, "◆  DECISION  ◆", ha="center", va="center",
            fontsize=8, color=C_DARK, fontweight="bold", zorder=4)
    arrow(ax, cx, nodes[-1][0] - BH / 2, cx, dec_y + 0.008)

    # ── OPTIMIZE branch ───────────────────────────────────────────────────────
    opt_x = 0.15
    opt_y = dec_y - 0.08
    box(ax, opt_x, opt_y, 0.20, BH, "OPTIMIZE", "re-run Campaign Gen", fc=C_DECISION)
    arrow(ax, cx - BW / 2, dec_y, opt_x + 0.10, dec_y, color="#00695C")
    arrow(ax, opt_x, dec_y - 0.005, opt_x, opt_y + BH / 2, color="#00695C")

    # Feedback loop (curved left rail back to Campaign Gen)
    cg_y = nodes[4][0]
    ax.annotate(
        "", xy=(cx - BW / 2, cg_y),
        xytext=(opt_x, opt_y - BH / 2),
        arrowprops=dict(
            arrowstyle="->", color="#00695C", lw=1.3,
            connectionstyle="arc3,rad=-0.35",
        ),
        zorder=2,
    )
    ax.text(opt_x - 0.03, (opt_y + cg_y) / 2 + 0.01,
            "inject\noptimization\nfeedback",
            ha="right", va="center", fontsize=6, color="#00695C", style="italic")

    # ── STOP branch ───────────────────────────────────────────────────────────
    stop_x = 0.75
    stop_y = dec_y - 0.08
    box(ax, stop_x, stop_y, 0.18, BH, "STOP", "workflow ends", fc="#C62828")
    arrow(ax, cx + BW / 2, dec_y, stop_x - 0.09, dec_y, color="#C62828")
    arrow(ax, stop_x, dec_y - 0.005, stop_x, stop_y + BH / 2, color="#C62828")

    # ── WorkflowState shared state rail ───────────────────────────────────────
    ws_x = 0.84
    ws_top = nodes[0][0] + BH / 2
    ws_bot = nodes[-1][0] - BH / 2
    ax.plot([ws_x, ws_x], [ws_bot, ws_top], color=C_STATE, lw=2.5, zorder=2,
            solid_capstyle="round")
    for y, *_ in nodes:
        ax.plot([ws_x - 0.008, ws_x], [y, y], color=C_STATE, lw=1, zorder=3)
    ax.text(ws_x + 0.01, (ws_top + ws_bot) / 2,
            "WorkflowState\n(Pydantic)\nshared across\nall agents",
            ha="left", va="center", fontsize=6.5, color=C_STATE)

    # ── Long-Term Memory block ─────────────────────────────────────────────────
    mem_y_top = 0.255
    mem_y_db  = 0.205
    box(ax, opt_x, mem_y_top, 0.24, BH,
        "LONG-TERM MEMORY", "MemoryStore (SQLite: campaign_memory)", fc=C_MEMORY)
    box(ax, opt_x, mem_y_db, 0.24, 0.032,
        "SQLite  marketing.db", fc=C_SQLITE)

    # Optimization agent → memory (persist)
    arrow(ax,
          cx - BW / 2, nodes[-1][0] - 0.01,
          opt_x + 0.12, mem_y_top + BH / 2,
          color=C_MEMORY, lw=1.1, linestyle="dashed",
          connectionstyle="arc3,rad=0.25")
    ax.text((cx - BW / 2 + opt_x + 0.12) / 2 + 0.01, nodes[-1][0] - 0.055,
            "persists\noutcome", ha="center", va="center",
            fontsize=6, color=C_MEMORY, style="italic")

    # Memory → Campaign Gen agent (retrieve)
    arrow(ax,
          opt_x + 0.12, mem_y_top + BH / 2,
          cx - BW / 2, nodes[4][0],
          color="#7B1FA2", lw=1.1, linestyle="dashed",
          connectionstyle="arc3,rad=-0.2")
    ax.text(opt_x + 0.13, (mem_y_top + nodes[4][0]) / 2 - 0.01,
            "retrieves\nprior memory", ha="left", va="center",
            fontsize=6, color="#7B1FA2", style="italic")

    # ── Legend ─────────────────────────────────────────────────────────────────
    legend = [
        (C_AGENT,    "Specialized Agent"),
        (C_OPTIM,    "Optimization Agent"),
        (C_DECISION, "OPTIMIZE decision"),
        ("#C62828",  "STOP decision"),
        (C_MEMORY,   "Long-Term Memory"),
        (C_STATE,    "WorkflowState"),
        (C_SQLITE,   "SQLite Database"),
        (C_GOAL,     "User Goal"),
    ]
    lx, ly = 0.02, 0.175
    cols = 4
    for i, (color, label) in enumerate(legend):
        row, col = i // cols, i % cols
        x = lx + col * 0.245
        y = ly - row * 0.028
        r = FancyBboxPatch((x, y - 0.009), 0.018, 0.018,
                           boxstyle="round,pad=0.002",
                           facecolor=color, edgecolor="none", zorder=4)
        ax.add_patch(r)
        ax.text(x + 0.024, y, label, va="center", fontsize=6.5, color=C_DARK)

    # ── Footer ─────────────────────────────────────────────────────────────────
    ax.text(0.5, 0.005,
            "Agentic AI Personalized Marketing Campaign Optimization System  |  Python · LangGraph · Pandas · SQLite · Streamlit",
            ha="center", va="bottom", fontsize=6, color="#90A4AE")

    fig.savefig(str(OUT_PATH), dpi=200, bbox_inches="tight",
                facecolor=C_BG, edgecolor="none")
    plt.close(fig)
    print(f"[OK] Architecture diagram saved → {OUT_PATH}")


if __name__ == "__main__":
    main()

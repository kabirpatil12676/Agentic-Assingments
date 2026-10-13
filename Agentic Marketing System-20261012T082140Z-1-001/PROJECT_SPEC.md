# PROJECT_SPEC.md — Agentic AI Personalized Marketing Campaign Optimization System

## 1. Project Identity

| Field | Value |
|---|---|
| **Title** | Agentic AI Personalized Marketing Campaign Optimization System |
| **Type** | Academic prototype (college project) |
| **Domain** | Agentic AI, Marketing Automation |
| **Primary Language** | Python 3.11+ |

## 2. Problem Statement

Design and implement a multi-agent AI system that can autonomously:
1. Accept a high-level marketing goal from a user
2. Decompose it into actionable sub-tasks
3. Analyse product data and customer segments
4. Generate personalised marketing campaigns
5. Simulate campaign execution
6. Monitor performance with real-time metrics
7. Optimise underperforming campaigns through a feedback loop
8. Learn from past outcomes via long-term memory

## 3. Agentic AI Concepts Demonstrated

| # | Concept | Where |
|---|---|---|
| 1 | Task decomposition | Planner Agent |
| 2 | Multiple specialised agents | 7 distinct agents |
| 3 | Tool / data usage | Pandas, SQLite, LLM |
| 4 | Shared state | `WorkflowState` (Pydantic) |
| 5 | Conditional workflow | Optimisation → Campaign Gen loop |
| 6 | Campaign execution | Execution Agent |
| 7 | Monitoring | Monitoring Agent |
| 8 | Optimization | Optimization Agent |
| 9 | Long-term memory | SQLite `MemoryStore` |
| 10 | Working UI | Streamlit + Plotly dashboard |

## 4. Technology Stack

| Component | Technology | Rationale |
|---|---|---|
| Orchestration | LangGraph | Native support for stateful, cyclic agent graphs |
| Schemas | Pydantic v2 | Type-safe inter-agent contracts |
| Analytics | Pandas | No-LLM deterministic number crunching |
| Database | SQLite | Zero-config, file-based, stdlib |
| LLM (local) | Ollama + qwen3:8b | Free, local, no API key |
| LLM (cloud) | OpenAI-compatible | Optional upgrade path |
| Dashboard | Streamlit | Rapid prototyping, Python-native |
| Charts | Plotly | Interactive, publication-quality |
| Testing | Pytest | Industry standard |

## 5. Engineering Constraints

- **No LLM for deterministic tasks**: arithmetic, filtering, aggregation, scoring → Python/Pandas/SQL
- **Typed contracts**: all agent I/O through Pydantic models
- **No hardcoded fakes**: demo mode uses deterministic *generators*, not static strings
- **No secrets in code**: `.env.example` template, `.env` gitignored
- **Offline capable**: `DEMO_MODE=true` requires zero network access
- **Modular & testable**: each agent, service, and utility is independently testable
- **Type hints throughout**: enforced by convention
- **Logging & error handling**: structured logging via stdlib `logging`

## 6. Agent Specifications

### 6.1 Planner Agent
- **Input**: `UserGoal`
- **Output**: `ExecutionPlan` (ordered list of `PlanStep`)
- **LLM usage**: Goal interpretation and step sequencing
- **Deterministic**: Validation of plan structure

### 6.2 Product Analysis Agent
- **Input**: `WorkflowState` with product_id
- **Output**: `ProductInfo` with analysis
- **LLM usage**: Competitive positioning narrative
- **Deterministic**: Price analysis, feature extraction (Pandas)

### 6.3 Customer Segmentation Agent
- **Input**: `WorkflowState` with product_info
- **Output**: `list[CustomerSegment]`
- **LLM usage**: Segment name/description generation
- **Deterministic**: Clustering, scoring, aggregation (Pandas/NumPy)

### 6.4 Campaign Generation Agent
- **Input**: `WorkflowState` with segments + product_info
- **Output**: `list[Campaign]` with content
- **LLM usage**: Subject lines, headlines, body copy, CTA
- **Deterministic**: Channel selection, budget allocation

### 6.5 Execution Agent
- **Input**: `WorkflowState` with campaigns
- **Output**: `list[ExecutionResult]`
- **LLM usage**: None
- **Deterministic**: Simulated delivery with statistical model (DEMO mode)

### 6.6 Monitoring Agent
- **Input**: `WorkflowState` with execution_results
- **Output**: `list[CampaignMetrics]`
- **LLM usage**: None
- **Deterministic**: KPI calculation, anomaly detection (Pandas)

### 6.7 Optimization Agent
- **Input**: `WorkflowState` with metrics
- **Output**: `OptimizationRecommendation`
- **LLM usage**: Decision rationale generation
- **Deterministic**: Metric comparison, threshold checks

## 7. Workflow Graph

```
START → Planner → Product Analysis → Segmentation → Campaign Generation
     → Execution → Monitoring → Optimization → {OPTIMIZE? → Campaign Generation}
     → END
```

The conditional edge from Optimization back to Campaign Generation creates the
feedback loop. A maximum iteration count (`MAX_OPT_LOOPS`) prevents infinite loops.

## 8. Data Architecture

### Input Data (data/raw/)
- `products.csv` — product catalogue
- `customers.csv` — customer records

### Persistent Store (SQLite)
- `campaigns` — campaign definitions and content
- `execution_results` — delivery metrics
- `memory` — long-term agent memory (key-value with namespace)
- `campaign_outcomes` — historical performance for learning

### Generated Output (data/generated/)
- Runtime reports, exported charts

## 9. Verification Plan

| Test Category | Tool | Scope |
|---|---|---|
| Unit tests | Pytest | Models, helpers, config |
| Integration tests | Pytest | Agent pipelines, workflow graph |
| Syntax check | `py_compile` | All `.py` files |
| Import check | `python -c "import app..."` | Package structure |
| Dashboard smoke | Manual | Streamlit launches without error |

## 10. Future Enhancements (Out of Scope)

- Real email/SMS delivery integration
- A/B testing framework
- Multi-language campaign support
- Real-time streaming metrics
- User authentication

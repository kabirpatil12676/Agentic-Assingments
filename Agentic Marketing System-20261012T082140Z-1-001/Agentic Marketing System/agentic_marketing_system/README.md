# Agentic AI Personalized Marketing Campaign Optimization System

> An academic prototype demonstrating multi-agent orchestration with LangGraph for end-to-end marketing campaign optimization.

## 1. Project Title
Agentic AI Personalized Marketing Campaign Optimization System

## 2. Problem Statement
Modern marketing requires high personalization and rapid optimization to be effective. Traditional systems rely on manual audience segmentation, static copy generation, and slow A/B testing loops. There is a need for an autonomous system that can analyze product and customer data, generate targeted campaigns, monitor their performance, and optimize them iteratively without constant human intervention.

## 3. Objective
To build a production-quality, agentic workflow that automates the entire lifecycle of a marketing campaign—from goal decomposition to performance optimization. The system demonstrates the capabilities of autonomous AI agents working collaboratively to achieve a measurable business objective, such as increasing sales of a specific product category by a target percentage.

## 4. Architecture
The system employs a multi-agent architecture orchestrated by **LangGraph**. It utilizes a shared typed state (`WorkflowState`) that flows through a Directed Acyclic Graph (DAG) of specialized agents. Deterministic analytics (using Pandas) handle data processing, while an LLM handles natural language generation and decision-making logic, ensuring a robust and non-hallucinated workflow.

## 5. Agent Descriptions
1. **Planner Agent:** Decomposes the high-level business goal into an actionable execution plan.
2. **Product Analysis Agent:** Identifies top-performing products using deterministic sales data and uses the LLM to write competitive positioning.
3. **Customer Segmentation Agent:** Filters the customer database to identify the optimal target audience (e.g., college students) based on the goal.
4. **Campaign Generation Agent:** Writes the marketing copy (subject, headline, body, CTA). It incorporates feedback from past iterations and long-term memory.
5. **Execution Agent:** Simulates the dispatch of the campaign to the target audience and records interaction events.
6. **Monitoring Agent:** Calculates deterministic KPIs (Open Rate, Conversion Rate, ROI, Lift) and compares performance against a historical baseline.
7. **Optimization Agent:** Evaluates metrics against thresholds and decides whether to `STOP`, `CONTINUE`, or `OPTIMIZE`. It suggests concrete changes for the next iteration.

## 6. LangGraph Workflow
The orchestration uses a `StateGraph`:
`Planner` → `Product Analysis` → `Customer Segmentation` → `Campaign Generation` → `Execution` → `Monitoring` → `Optimization`
A **conditional edge** from the Optimization node loops back to the Campaign Generation node if the decision is `OPTIMIZE`, allowing iterative improvements.

## 7. Data Layer
Data management is centralized in `DataService`. All operations use parameterized SQLite queries and enforce foreign keys to ensure data integrity. Deterministic calculations are performed using Pandas DataFrames to avoid LLM hallucinations for metrics like ROI and conversion rates.

## 8. Database Schema
- `products`: Catalog, pricing, historical sales data.
- `customers`: Demographics, total spend, customer type.
- `purchases`: Ledger of all historical transactions (Foreign keys to products and customers).
- `campaigns`: Generated campaigns, budgets, copy, targeting parameters.
- `campaign_events`: Dispatch ledger recording simulated interactions (sent, opened, clicked, converted).
- `campaign_memory` & `kv_memory`: Persistent storage for agent learning across runs.

## 9. Memory Architecture
Long-term memory is handled by the `MemoryStore`.
- **Persistence:** The `OptimizationAgent` saves the campaign outcomes, metrics, and decisions to the SQLite database on every iteration.
- **Retrieval:** The `CampaignGenerationAgent` queries this historical memory before drafting new content to avoid past mistakes and leverage what worked previously.

## 10. LLM Provider Architecture
The `LLMProvider` is an abstraction layer that seamlessly switches between:
- **Ollama** (Local execution, default `qwen3:8b`).
- **OpenAI** (Cloud-based API).
- **Demo Mode** (Deterministic, network-free mock responses for consistent grading and offline demos).

## 11. DEMO Mode
By setting `DEMO_MODE=true` in the configuration, the system runs entirely offline. The `CampaignSimulator` generates realistic synthetic delivery metrics, and the `LLMProvider` returns consistent mock responses. This mode is critical for reproducible academic demonstrations.

## 12. Installation
```bash
# 1. Clone & enter
cd agentic_marketing_system

# 2. Create virtual environment
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Copy environment template
# Windows: copy .env.example .env
# macOS/Linux: cp .env.example .env
```

## 13. Running the Application
```bash
# 1. Seed demo data (Creates SQLite database)
python scripts/seed_data.py

# 2. Launch the Streamlit dashboard
streamlit run dashboard/streamlit_app.py
```

## 14. Example Input
> "Increase sales of our best-performing products among college students by 15%."

## 15. Example Output
The dashboard will display:
- **Baseline:** Historical revenue vs Campaign Revenue (e.g. 15% Sales Lift target).
- **Campaign Iteration 1:** CTA "Shop Now", Sales Lift -10%, ROI 100%.
- **Optimization Decision:** OPTIMIZE, Suggestion: "Switch to a more urgent CTA."
- **Campaign Iteration 2:** CTA "Buy Now and Save!", Sales Lift +20%, ROI 250%.
- **Long-term Memory Table:** Records of all previous runs showing how the agent adapted.

## 16. Testing
The project includes a comprehensive Pytest suite covering all 48 test cases, including an asynchronous end-to-end LangGraph integration test.
```bash
pytest tests/ -v
```

## 17. Limitations
- Synthetic data may not fully capture the complexity of real-world buyer behavior.
- The default local LLM (`qwen3:8b`) may occasionally fail to return perfectly structured JSON if the prompt context becomes too long.
- Email dispatch is currently simulated.

## 18. Future Scope
- Integration with live CRM systems (e.g., Salesforce) and marketing platforms (e.g., Mailchimp).
- Multi-channel campaigns spanning Email, SMS, and Social Media simultaneously.
- Advanced Reinforcement Learning (RL) for dynamic budget reallocation during execution.

## 19. Why this qualifies as Agentic AI
This system goes beyond a simple LLM wrapper by exhibiting true agentic behaviors:
- **Planning:** It dynamically decomposes a high-level goal into an executable multi-step plan.
- **Specialized Agents:** Tasks are routed to specialized personas (e.g., Data Analyst vs. Copywriter).
- **Tool Usage:** It utilizes Python APIs (Pandas, SQLite) to retrieve data and compute deterministic math rather than guessing.
- **Shared State:** Agents collaborate by mutating a strict `WorkflowState` schema.
- **Conditional Routing:** Execution paths change dynamically based on runtime metrics.
- **Feedback Loop & Optimization:** The system criticizes its own outputs and autonomously creates a second iteration to improve performance.
- **Long-Term Memory:** Past successes and failures are persisted to a database and retrieved to influence future runs, allowing the system to "learn" over time.

## 20. Known Prototype Limitations

> **Baseline vs. Campaign Revenue Comparability (Prototype Limitation)**
>
> The **Historical Baseline Revenue** (`$97,943.47`) is computed from the *entire synthetic purchase history* for the Electronics category across all customers. The **Campaign Revenue** (`$2,099.86` – `$4,049.73`) is computed from a *single simulated campaign execution* sent to a segment of 1,200 customers over a single run.
>
> These two figures are **not measured over a comparable time window or customer population**. This is an inherent limitation of operating with a synthetic dataset in an academic prototype where there is no live A/B test infrastructure.
>
> **Implication:** The Sales Lift figure (`-95.87%`) should be interpreted as a **prototype comparison metric**, not a production-valid revenue lift measurement. It correctly demonstrates that the system *calculates and reports* baseline vs. campaign revenue and flags whether the KPI target is met — which is the academic objective.
>
> In a production deployment, both baseline and campaign revenue would be measured over the same rolling time window (e.g., 30-day pre-campaign vs. 30-day during-campaign) for the same customer segment, making the comparison statistically valid.

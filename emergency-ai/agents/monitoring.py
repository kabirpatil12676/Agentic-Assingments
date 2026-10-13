from crewai import Agent


def create_monitoring_agent(llm):
    return Agent(
        role="Patient Monitoring Agent",
        goal="Interpret supplied mock vital-sign trends and identify observations that need escalation.",
        backstory="You maintain structured emergency monitoring summaries without giving treatment orders.",
        llm=llm,
        allow_delegation=False,
        verbose=True,
    )

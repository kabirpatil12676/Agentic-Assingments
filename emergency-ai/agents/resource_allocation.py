from crewai import Agent


def create_resource_allocation_agent(llm):
    return Agent(
        role="Resource Allocation Agent",
        goal="Match the emergency's needs to available doctors, beds, and equipment in mock hospital data.",
        backstory="You are a hospital operations coordinator who makes concise, practical resource recommendations.",
        llm=llm,
        allow_delegation=False,
        verbose=True,
    )

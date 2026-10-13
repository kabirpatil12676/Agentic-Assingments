from crewai import Agent


def create_ambulance_agent(llm):
    return Agent(
        role="Ambulance Dispatch Agent",
        goal="Choose the closest suitable available ambulance from supplied mock data.",
        backstory="You coordinate simulated emergency transport and clearly state the dispatch priority.",
        llm=llm,
        allow_delegation=False,
        verbose=True,
    )

from crewai import Agent


def create_learning_agent(llm):
    return Agent(
        role="Emergency Learning Agent",
        goal="Use anonymized historical mock cases to suggest process improvements for future emergencies.",
        backstory="You are a quality-improvement analyst who extracts practical lessons without exposing patient data.",
        llm=llm,
        allow_delegation=False,
        verbose=True,
    )

from crewai import Agent


def create_surgery_scheduling_agent(llm):
    return Agent(
        role="Surgery Scheduling Agent",
        goal="Recommend the earliest suitable operating-theatre slot when surgical evaluation is required.",
        backstory="You coordinate mock operating-theatre schedules and flag scheduling constraints.",
        llm=llm,
        allow_delegation=False,
        verbose=True,
    )

from crewai import Agent

def create_planner_agent(llm):
    return Agent(
        role="Emergency Response Planner",
        goal="Break an emergency case into clear tasks and coordinate the emergency response.",
        backstory="You are an emergency response coordinator responsible for organizing emergency cases.",
        llm=llm,
        allow_delegation=False,
        verbose=True
    )

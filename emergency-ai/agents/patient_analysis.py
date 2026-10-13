from crewai import Agent

def create_patient_analysis_agent(llm):
    return Agent(
        role="Patient Analysis and Triage Specialist",
        goal="Analyze patient information and determine urgency and required resources.",
        backstory="You analyze emergency patient information and provide structured triage assessments.",
        llm=llm,
        allow_delegation=False,
        verbose=True
    )

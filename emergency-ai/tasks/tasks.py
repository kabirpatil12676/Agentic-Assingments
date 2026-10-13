from crewai import Task


def create_tasks(agents):
    """Build the seven linked tasks for one simulated emergency case."""
    planner = Task(
        description=(
            "Analyze the emergency case: {case}. Create exactly five ordered coordination "
            "steps covering triage, transport, hospital preparation, specialist review, and handover. "
            "This is a simulation: do not provide treatment instructions. Maximum 130 words."
        ),
        expected_output="Exactly five ordered emergency coordination steps.", agent=agents["planner"],
    )
    patient_analysis = Task(
        description=(
            "Assess this simulated emergency case: {case}. State acuity (Critical, High, "
            "Moderate, or Low), main risks, transport priority, and resources to prepare. "
            "Do not diagnose or prescribe treatment. Maximum 120 words."
        ),
        expected_output="A concise triage and resource assessment.", agent=agents["patient_analysis"], context=[planner],
    )
    resource_allocation = Task(
        description=(
            "Using this mock hospital data, select appropriate available resources for the case.\n"
            "{hospital_summary}\n\nDoctors:\n{doctor_summary}\n\nGive exactly four bullets: destination area, "
            "bed, specialists, and theatre readiness. Use only supplied facts. Maximum 110 words."
        ),
        expected_output="Exactly four resource-allocation bullets.", agent=agents["resource_allocation"], context=[patient_analysis],
    )
    ambulance = Task(
        description=(
            "Choose one ambulance for this simulated case using only this data:\n{ambulance_summary}\n\n"
            "Begin with 'Selected ambulance:'. State its ID, ETA, capability, and one reason. "
            "Never select a busy ambulance. Maximum 80 words."
        ),
        expected_output="One eligible ambulance selection with a concise justification.", agent=agents["ambulance"], context=[patient_analysis],
    )
    surgery = Task(
        description=(
            "From the triage and resource reports, decide whether urgent surgical evaluation should be "
            "prepared. If yes, reserve the earliest supplied available theatre slot; if no, say no mock "
            "slot is reserved. Include the theatre and time only when supplied. This is a planning "
            "simulation, not a booking. Maximum 80 words."
        ),
        expected_output="A simulated surgery-readiness decision and, if applicable, the earliest slot.", agent=agents["surgery"], context=[patient_analysis, resource_allocation],
    )
    monitoring = Task(
        description=(
            "Interpret these supplied mock observations:\n{vital_trend}\n\nGive exactly three bullets: "
            "trend, escalation concern, and handover observation. Do not prescribe care or calculate "
            "values not provided. Maximum 90 words."
        ),
        expected_output="Exactly three monitoring bullets.", agent=agents["monitoring"], context=[ambulance],
    )
    learning = Task(
        description=(
            "Use the anonymized historical mock lessons below and the crew outputs to provide exactly "
            "three process improvements for future simulations. Focus on dispatch, hospital readiness, "
            "and escalation timing; do not identify patients or prescribe care.\n\n{historical_lessons}\n\n"
            "Maximum 100 words."
        ),
        expected_output="Exactly three quality-improvement actions.", agent=agents["learning"], context=[resource_allocation, ambulance, surgery, monitoring],
    )
    return [planner, patient_analysis, resource_allocation, ambulance, surgery, monitoring, learning]

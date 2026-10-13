# Emergency Response CrewAI Simulation

An educational multi-agent simulation for emergency-response coordination. It uses mock ambulance, hospital, doctor, monitoring, and historical-case data. It must not be used to dispatch real ambulances, allocate real beds, book theatres, or make clinical decisions.

## Agents

1. Planner Agent — breaks the emergency into coordination tasks.
2. Patient Analysis Agent — produces a non-prescriptive triage summary.
3. Resource Allocation Agent — matches mock doctors, beds, and theatre readiness.
4. Ambulance Agent — selects an eligible mock ambulance.
5. Surgery Scheduling Agent — recommends a mock theatre-readiness slot.
6. Monitoring Agent — summarizes supplied mock vital-sign trends.
7. Learning Agent — suggests process improvements from anonymized mock lessons.

## Run

1. Create a `.env` file in this folder with your Gemini key:

   ```env
   GEMINI_API_KEY=your_key_here
   # Optional:
   LLM_MODEL=gemini/gemini-3.5-flash-lite
   ```

2. Activate the virtual environment and install dependencies if needed:

   ```powershell
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

3. Run the simulation:

   ```powershell
   python main.py
   ```

The console displays the Learning Agent's final output. The complete seven-agent report is saved to `output/emergency_response_report.txt`.

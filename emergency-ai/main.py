import os
import sys
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
VENV_PYTHON = BASE_DIR / ".venv" / "Scripts" / "python.exe"
if VENV_PYTHON.exists() and sys.executable.lower() != str(VENV_PYTHON).lower():
    try:
        import crewai
    except ImportError:
        res = subprocess.run([str(VENV_PYTHON), str(Path(__file__).resolve())] + sys.argv[1:])
        sys.exit(res.returncode)

from dotenv import load_dotenv
from crewai import Crew, LLM, Process

from agents.ambulance import create_ambulance_agent
from agents.learning import create_learning_agent
from agents.monitoring import create_monitoring_agent
from agents.patient_analysis import create_patient_analysis_agent
from agents.planner import create_planner_agent
from agents.resource_allocation import create_resource_allocation_agent
from agents.surgery_scheduling import create_surgery_scheduling_agent
from tasks.tasks import create_tasks
from tools.ambulance_data import ambulance_summary
from tools.doctor_data import doctor_summary
from tools.hospital_data import hospital_summary
from tools.monitoring_data import HISTORICAL_LESSONS, VITAL_TREND

OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)
load_dotenv(BASE_DIR / ".env")

CASE = (
    "A 32-year-old patient was involved in a road accident. "
    "The patient has severe bleeding from the leg and severe pain. "
    "The patient is located 8 km from the hospital."
)


def output_text(task):
    return task.output.raw if task.output else "No output available."


def main():
    print("\n" + "=" * 60)
    print("   Assignment 4: Emergency Response AI")
    print("   Multi-Agent System | Ollama qwen3.5:9b")
    print("=" * 60)
    print(f"\nCase: {CASE}\n")
    print("Starting 7-agent CrewAI workflow...\n")

    # Use local Ollama qwen3.5:9b (stored on D drive)
    ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    llm = LLM(
        model="ollama/qwen3.5:9b",
        base_url=ollama_base_url,
        temperature=0.2,
        max_tokens=512,
        timeout=180,
        reasoning_effort="none",
    )

    agents = {
        "planner": create_planner_agent(llm),
        "patient_analysis": create_patient_analysis_agent(llm),
        "resource_allocation": create_resource_allocation_agent(llm),
        "ambulance": create_ambulance_agent(llm),
        "surgery": create_surgery_scheduling_agent(llm),
        "monitoring": create_monitoring_agent(llm),
        "learning": create_learning_agent(llm),
    }
    tasks = create_tasks(agents)
    crew = Crew(
        agents=list(agents.values()),
        tasks=tasks,
        process=Process.sequential,
        verbose=True,
    )

    try:
        result = crew.kickoff(inputs={
            "case": CASE,
            "ambulance_summary": ambulance_summary(),
            "doctor_summary": doctor_summary(),
            "hospital_summary": hospital_summary(),
            "vital_trend": VITAL_TREND,
            "historical_lessons": HISTORICAL_LESSONS,
        })
    except Exception as error:
        print("\nCrew execution stopped before completion.")
        print(f"Reason: {error}")
        raise

    # Save full report to output file
    labels = [
        "PLANNER", "PATIENT ANALYSIS", "RESOURCE ALLOCATION",
        "AMBULANCE", "SURGERY SCHEDULING", "MONITORING", "LEARNING"
    ]
    sections = [
        "EMERGENCY RESPONSE SIMULATION REPORT",
        "=" * 36,
        "IMPORTANT: Educational simulation only. Not for real emergency use.",
        f"\nCASE\n{CASE}",
    ]
    for label, task in zip(labels, tasks):
        sections.append(f"\n{label} AGENT\n{output_text(task)}")
    report_path = OUTPUT_DIR / "emergency_response_report.txt"
    report_path.write_text("\n".join(sections), encoding="utf-8")

    print("\n--- FINAL LEARNING AGENT OUTPUT ---\n")
    print(result.raw)
    print(f"\nReport saved: output/emergency_response_report.txt")
    if result.token_usage:
        print(f"Total tokens used: {result.token_usage.total_tokens}")


if __name__ == "__main__":
    main()

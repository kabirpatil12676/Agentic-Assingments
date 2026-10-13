"""
Assignment 4 - Agentic AI
Name: Kabir Patil
Roll No: B-26
Title: Emergency Response AI - Multi-Agent System using CrewAI + Ollama

Agents:
  1. Planner Agent          - Breaks the emergency into tasks
  2. Patient Analysis Agent - Checks injury severity
  3. Resource Allocation    - Finds available doctors and beds
  4. Ambulance Agent        - Selects nearest ambulance
  5. Surgery Scheduling     - Books OT
  6. Monitoring Agent       - Tracks patient condition
  7. Learning Agent         - Learns from previous emergencies
"""
import sys
import os
import subprocess
from pathlib import Path

# Add the emergency-ai project folder to path so its modules are importable
EMERGENCY_DIR = Path(__file__).resolve().parent / "emergency-ai"
VENV_PYTHON = EMERGENCY_DIR / ".venv" / "Scripts" / "python.exe"

# If crewai is not installed in the active Python environment, run with the project venv
if VENV_PYTHON.exists() and sys.executable.lower() != str(VENV_PYTHON).lower():
    try:
        import crewai
    except ImportError:
        res = subprocess.run([str(VENV_PYTHON), str(Path(__file__).resolve())] + sys.argv[1:])
        sys.exit(res.returncode)

sys.path.insert(0, str(EMERGENCY_DIR))

from main import main

if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\nExiting Assignment 4...")


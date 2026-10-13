"""
Agentic AI Assignment 2
Name: Kabir Patil
Roll No: B-26
Department: Information Technology
Institute: Walchand Institute of Technology, Solapur

Aim:
  Create 5 AI agents. Each agent contains:
    {"Agent_ID": "", "Priority": "", "Current_Task": "", "Status": ""}
  Store all agents inside a list.

Requirements:
  1. Sort by Priority
  2. Display Active Agents
  3. Count Completed Tasks
  4. Find Highest Priority Agent

Model: qwen3.5:9b (local Ollama, D:\\Ollama\\Models)
"""

import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
import os
import re
import time
import subprocess
import requests
from dotenv import load_dotenv

# -- Load environment ----------------------------------------------------------
load_dotenv()
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")


# -- Ensure Ollama is running (same approach as assignments 5-9) ---------------
def _ensure_ollama_running():
    try:
        r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=1.5)
        if r.status_code == 200:
            return True
    except Exception:
        pass

    ollama_exe = "D:\\Ollama\\ollama.exe" if os.path.exists("D:\\Ollama\\ollama.exe") else "ollama"
    env = os.environ.copy()
    if os.path.exists("D:\\Ollama\\Models"):
        env["OLLAMA_MODELS"] = "D:\\Ollama\\Models"

    try:
        subprocess.Popen(
            [ollama_exe, "serve"],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
        )
        for _ in range(8):
            time.sleep(0.5)
            try:
                r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=1.0)
                if r.status_code == 200:
                    return True
            except Exception:
                pass
    except Exception:
        pass
    return False


def _get_ollama_model():
    """Pick the best available local model, preferring qwen3.5:9b."""
    env_model = os.getenv("OLLAMA_MODEL")
    if env_model:
        return env_model
    try:
        r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=1.5)
        if r.status_code == 200:
            names = [m["name"] for m in r.json().get("models", [])]
            for pref in ["qwen3.5:9b", "qwen2.5:0.5b", "llama3.2:1b", "llama3.2:3b", "qwen2.5:1.5b"]:
                for n in names:
                    if n == pref or n.startswith(pref):
                        return n
            if names:
                return names[0]
    except Exception:
        pass
    return "qwen3.5:9b"


_ensure_ollama_running()
OLLAMA_MODEL = _get_ollama_model()
print(f"Ollama model : {OLLAMA_MODEL}")


# -- Ollama inference with offline fallback ------------------------------------
def ask_ollama(prompt: str, max_tokens: int = 80) -> str:
    """
    Send a prompt to local Ollama.
    Falls back to a short rule-based description if Ollama is unavailable.
    """
    try:
        payload = {
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "think": False,
            "options": {
                "num_predict": max_tokens,
                "temperature": 0.3
            }
        }
        res = requests.post(f"{OLLAMA_URL}/api/generate", json=payload, timeout=30)
        if res.status_code == 200:
            raw = res.json().get("response", "").strip()
            # Strip chain-of-thought tags produced by some Qwen variants
            clean = re.sub(r'<think>.*?</think>', '', raw, flags=re.DOTALL).strip()
            if clean:
                return clean
    except Exception:
        pass
    # Offline fallback
    task_match = re.search(r'task:\s*"([^"]+)"', prompt, re.IGNORECASE)
    task = task_match.group(1) if task_match else "this task"
    return f"Handles '{task}' operations autonomously within the multi-agent pipeline."


# -- Agent data (exactly as given by madam) ------------------------------------
agents = [
    {
        "Agent_ID": "A003",
        "Priority": 3,
        "Current_Task": "Generate Reports",
        "Status": "Completed"
    },
    {
        "Agent_ID": "A001",
        "Priority": 1,
        "Current_Task": "Monitor Network",
        "Status": "Active"
    },
    {
        "Agent_ID": "A005",
        "Priority": 5,
        "Current_Task": "Email Notifications",
        "Status": "Completed"
    },
    {
        "Agent_ID": "A002",
        "Priority": 2,
        "Current_Task": "Data Analysis",
        "Status": "Active"
    },
    {
        "Agent_ID": "A004",
        "Priority": 4,
        "Current_Task": "Database Backup",
        "Status": "Inactive"
    }
]


# -- AI-powered task descriptions via Ollama -----------------------------------
print("\nGenerating AI task descriptions using Ollama...\n")
for agent in agents:
    task = agent["Current_Task"]
    prompt = (
        f'You are an AI assistant. Describe what an AI agent performing the task: "{task}" '
        f'does in exactly one sentence. Be specific and technical. Do not add greetings or extra text.'
    )
    agent["AI_Description"] = ask_ollama(prompt, max_tokens=80)


# ─────────────────────────────────────────────────────────────────────────────
#  Requirement 1: Sort by Priority
# ─────────────────────────────────────────────────────────────────────────────
sorted_agents = sorted(agents, key=lambda agent: agent["Priority"])

print("=" * 60)
print("         ASSIGNMENT 2 -- AGENTIC AI")
print("=" * 60)

print("\n=== Agents Sorted by Priority ===")
for agent in sorted_agents:
    print(f"\n  Agent_ID     : {agent['Agent_ID']}")
    print(f"  Priority     : {agent['Priority']}")
    print(f"  Current_Task : {agent['Current_Task']}")
    print(f"  Status       : {agent['Status']}")
    print(f"  AI_Insight   : {agent['AI_Description']}")


# ─────────────────────────────────────────────────────────────────────────────
#  Requirement 2: Display Active Agents
# ─────────────────────────────────────────────────────────────────────────────
print("\n=== Active Agents ===")
active_found = False
for agent in sorted_agents:
    if agent["Status"] == "Active":
        active_found = True
        print(f"\n  Agent_ID     : {agent['Agent_ID']}")
        print(f"  Priority     : {agent['Priority']}")
        print(f"  Current_Task : {agent['Current_Task']}")
        print(f"  Status       : {agent['Status']}")
        print(f"  AI_Insight   : {agent['AI_Description']}")
if not active_found:
    print("  No active agents found.")


# ─────────────────────────────────────────────────────────────────────────────
#  Requirement 3: Count Completed Tasks
# ─────────────────────────────────────────────────────────────────────────────
completed_tasks = sum(
    1 for agent in agents if agent["Status"] == "Completed"
)
print(f"\nCompleted Tasks: {completed_tasks}")


# ─────────────────────────────────────────────────────────────────────────────
#  Requirement 4: Find Highest Priority Agent
# ─────────────────────────────────────────────────────────────────────────────
highest_priority_agent = min(agents, key=lambda agent: agent["Priority"])
print("\n=== Highest Priority Agent ===")
print(f"  Agent_ID     : {highest_priority_agent['Agent_ID']}")
print(f"  Priority     : {highest_priority_agent['Priority']}")
print(f"  Current_Task : {highest_priority_agent['Current_Task']}")
print(f"  Status       : {highest_priority_agent['Status']}")
print(f"  AI_Insight   : {highest_priority_agent['AI_Description']}")
print()


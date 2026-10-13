"""
Agentic AI Assignment 1
Name: Kabir Patil
Roll No: B-26
Department: Information Technology
Institute: Walchand Institute of Technology, Solapur

Aim:
  Develop a Python program that simulates an AI agent performing tasks.
  Store each state transition using a dictionary inside a list.

Requirements:
  - Agent ID
  - Current State
  - Previous State
  - Timestamp
  - Action Performed

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
from datetime import datetime
from dotenv import load_dotenv

# -- Load environment ----------------------------------------------------------
load_dotenv()
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")


# -- Ensure Ollama is running (same approach as assignments 1-9) ---------------
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
# Offline fallback actions (mirrors madam's original hardcoded strings)
_FALLBACK_ACTIONS = {
    "Idle":             "Agent Started",
    "Collecting Data":  "Collecting Input Data",
    "Processing":       "Processing Data",
    "Decision Made":    "Decision Generated",
    "Completed":        "Task Completed",
}

def ask_ollama(state: str, max_tokens: int = 60) -> str:
    """
    Ask Ollama to generate a one-phrase action description for the given agent state.
    Falls back to madam's original hardcoded action if Ollama is unavailable.
    """
    prompt = (
        f'An AI agent just entered the state: "{state}". '
        f'Write a short technical action phrase (5-10 words) that describes '
        f'what the agent is doing in this state. Return only the phrase, no punctuation at the end.'
    )
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
            # Keep only first line to avoid verbose output
            first_line = clean.splitlines()[0].strip().rstrip('.')
            if first_line:
                return first_line
    except Exception:
        pass
    return _FALLBACK_ACTIONS.get(state, "Performing assigned task")


# -- Agent state definitions (same as madam's code) ----------------------------
agent_id = "AI001"
states = [
    "Idle",
    "Collecting Data",
    "Processing",
    "Decision Made",
    "Completed"
]

# -- Generate AI-powered action descriptions via Ollama ------------------------
print("\nGenerating AI action descriptions using Ollama...\n")

agent_history = []
previous_state = "None"

for state in states:
    action = ask_ollama(state)
    transition = {
        "Agent ID":        agent_id,
        "Current State":   state,
        "Previous State":  previous_state,
        "Timestamp":       datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Action Performed": action
    }
    agent_history.append(transition)
    previous_state = state


# -- Output Section 1: Quick state summary (matches madam's sample output) -----
print("Agent State History\n")
for i, record in enumerate(agent_history, start=1):
    print(f"Step {i}")
    print(f"State : {record['Current State']}\n")

# -- Output Section 2: Complete history ----------------------------------------
print("=" * 50)
print("Complete Agent History\n")
for i, record in enumerate(agent_history, start=1):
    print(f"Step {i}")
    print(f"Agent ID         : {record['Agent ID']}")
    print(f"Current State    : {record['Current State']}")
    print(f"Previous State   : {record['Previous State']}")
    print(f"Timestamp        : {record['Timestamp']}")
    print(f"Action Performed : {record['Action Performed']}")
    print("-" * 50)

# -- Output Section 3: Reverse order (matches madam's requirement) -------------
print("\nAgent History in Reverse Order\n")
for i, record in enumerate(reversed(agent_history), start=1):
    print(f"Step {i}")
    print(f"Agent ID         : {record['Agent ID']}")
    print(f"Current State    : {record['Current State']}")
    print(f"Previous State   : {record['Previous State']}")
    print(f"Timestamp        : {record['Timestamp']}")
    print(f"Action Performed : {record['Action Performed']}")
    print("-" * 50)


"""
Agentic AI - Master Assignment Runner
Student Name: Kabir Patil
Roll No: B-26
Department: Information Technology

Run any assignment from 1 to 9 easily from this single entry point.
"""

import os
import sys
import subprocess

ASSIGNMENTS = {
    "1": ("Assignment 1: Agent State History & Lifecycle", "assignment_1.py"),
    "2": ("Assignment 2: Priority Queue & Multi-Agent State", "assignment_2.py"),
    "3": ("Assignment 3: Agentic Marketing Campaign System (LangGraph)", "assignment_3.py"),
    "5": ("Assignment 5: LLM Foundations (Tasks 1 - 4)", "assignment_5.py"),
    "6": ("Assignment 6: Agentic Reasoning & Planning (Tasks 5 - 10)", "assignment_6.py"),
    "7": ("Assignment 7: RAG, Embeddings & Multi-Agent (Tasks 11 - 15)", "assignment_7.py"),
    "8": ("Assignment 8: Supervision & ReAct Agents (Tasks 16 - 19)", "assignment_8.py"),
    "9": ("Assignment 9: Supervisor Routing, Weather & ViT (Tasks 20 - 23)", "assignment_9.py"),
}

def run_script(script_name):
    script_path = os.path.join(os.path.dirname(__file__), script_name)
    if not os.path.exists(script_path):
        print(f"Error: Script {script_name} not found.")
        return
    print(f"\n>>> Running {script_name}...\n")
    try:
        subprocess.run([sys.executable, script_path], check=True)
    except KeyboardInterrupt:
        print(f"\nExecution of {script_name} interrupted.")
    except Exception as e:
        print(f"Error executing {script_name}: {e}")

def main():
    while True:
        print("\n" + "=" * 65)
        print("         AGENTIC AI - PRACTICAL ASSIGNMENT SUITE")
        print("         Student: Kabir Patil  |  Roll No: B-26")
        print("=" * 65)
        for key, (title, script) in sorted(ASSIGNMENTS.items(), key=lambda x: int(x[0])):
            print(f"  [{key}] {title}")
        print("  [0] Run All Assignments sequentially")
        print("  [q] Exit")
        print("=" * 65)

        try:
            choice = input("\nSelect Assignment to run (1, 2, 3, 5, 6, 7, 8, 9, 0, q): ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting runner...")
            break

        if choice in ASSIGNMENTS:
            run_script(ASSIGNMENTS[choice][1])
        elif choice == "0":
            for key in sorted(ASSIGNMENTS.keys(), key=lambda x: int(x)):
                print("\n" + "#" * 60)
                print(f"# Launching {ASSIGNMENTS[key][0]}")
                print("#" * 60)
                run_script(ASSIGNMENTS[key][1])
        elif choice in ["q", "exit", "quit"]:
            print("\nExiting Master Assignment Runner. Best of luck with your submission!")
            break
        else:
            print(f"Invalid option '{choice}'. Please select from the menu.")

if __name__ == "__main__":
    main()

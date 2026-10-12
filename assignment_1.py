from datetime import datetime

agent_id = "AI001"
states = [
    ("Idle", "Agent Started"),
    ("Collecting Data", "Collecting Input Data"),
    ("Processing", "Processing Data"),
    ("Decision Made", "Decision Generated"),
    ("Completed", "Task Completed")
]
agent_history = []
previous_state = "None"

for state, action in states:
    transition = {
        "Agent ID": agent_id,
        "Current State": state,
        "Previous State": previous_state,
        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Action Performed": action
    }
    agent_history.append(transition)
    previous_state = state

print("Agent State History\n")

for i, record in enumerate(agent_history, start=1):
    print(f"Step {i}")
    print(f"State : {record['Current State']}\n")

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

print("\nAgent History in Reverse Order\n")
for i, record in enumerate(reversed(agent_history), start=1):
    print(f"Step {i}")
    print(f"Agent ID         : {record['Agent ID']}")
    print(f"Current State    : {record['Current State']}")
    print(f"Previous State   : {record['Previous State']}")
    print(f"Timestamp        : {record['Timestamp']}")
    print(f"Action Performed : {record['Action Performed']}")
    print("-" * 50)

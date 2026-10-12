# Assignment No 2
# Subject: Agentic AI
# Roll No: B-26
# Aim: Create 5 AI agents. Each agent contains {"Agent_ID":"","Priority":"","Current_Task":"","Status":""}
# Store all agents inside a list.
# Requirements:
# 1. Sort by Priority
# 2. Display Active Agents
# 3. Count Completed Tasks
# 4. Find Highest Priority Agent

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

sorted_agents = sorted(agents, key=lambda agent: agent["Priority"])
print("=== Agents Sorted by Priority ===")
for agent in sorted_agents:
    print(agent)

print("\n=== Active Agents ===")
for agent in sorted_agents:
    if agent["Status"] == "Active":
        print(agent)

completed_tasks = sum(
    1 for agent in agents if agent["Status"] == "Completed"
)
print("\nCompleted Tasks:", completed_tasks)

highest_priority_agent = min(agents, key=lambda agent: agent["Priority"])
print("\n=== Highest Priority Agent ===")
print(highest_priority_agent)

AMBULANCES = [
    {"id": "AMB-12", "distance_km": 3.2, "eta_minutes": 7, "status": "Available", "capability": "Advanced life support"},
    {"id": "AMB-08", "distance_km": 5.6, "eta_minutes": 12, "status": "Available", "capability": "Basic life support"},
    {"id": "AMB-03", "distance_km": 2.1, "eta_minutes": 5, "status": "Busy", "capability": "Advanced life support"},
]


def ambulance_summary():
    return "\n".join(
        f"{item['id']}: {item['status']}; {item['distance_km']} km; ETA {item['eta_minutes']} min; {item['capability']}"
        for item in AMBULANCES
    )

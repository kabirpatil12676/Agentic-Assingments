DOCTORS = [
    {"name": "Dr. Rao", "specialty": "Trauma Surgery", "status": "Available now"},
    {"name": "Dr. Shah", "specialty": "Orthopedics", "status": "Available in 20 minutes"},
    {"name": "Dr. Iyer", "specialty": "Emergency Medicine", "status": "Available now"},
]


def doctor_summary():
    return "\n".join(f"{d['name']} — {d['specialty']}: {d['status']}" for d in DOCTORS)

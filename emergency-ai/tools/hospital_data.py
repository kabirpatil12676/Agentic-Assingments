HOSPITAL_RESOURCES = {
    "resuscitation_beds": 2,
    "icu_beds": 1,
    "trauma_bay": "Available",
    "operating_theatres": [
        {"room": "OT-2", "next_slot": "14:30", "status": "Available"},
        {"room": "OT-1", "next_slot": "15:15", "status": "Available"},
    ],
}


def hospital_summary():
    theatres = "; ".join(
        f"{ot['room']}: {ot['status']}, next slot {ot['next_slot']}" for ot in HOSPITAL_RESOURCES["operating_theatres"]
    )
    return (
        f"Resuscitation beds: {HOSPITAL_RESOURCES['resuscitation_beds']}; "
        f"ICU beds: {HOSPITAL_RESOURCES['icu_beds']}; "
        f"Trauma bay: {HOSPITAL_RESOURCES['trauma_bay']}; Operating theatres: {theatres}"
    )

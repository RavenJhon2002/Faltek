import math

HOURS_PER_DAY = 8

PRODUCTIVITY = {
    "excavation": 0.5,
    "gravel": 0.6,
    "concrete": 1.0,
    "reinforcing": 0.8,
    "formwork": 0.9,
    "masonry": 1.2,
    "demolition": 0.7,
}


def get_productivity(activity_name: str) -> float:
    name = activity_name.lower()
    for key, value in PRODUCTIVITY.items():
        if key in name:
            return value
    return 1.0  # safe fallback


def compute_activity_duration(activity):
    """
    Compute duration using Philippine manhour method
    """

    if activity.is_group or not activity.quantity:
        return 1

    # 👷 count workers
    manpower = activity.manpower.all()
    total_workers = sum(m.actual or m.required for m in manpower)

    if total_workers == 0:
        return 1

    productivity = get_productivity(activity.name)

    # 🔥 CORE FORMULA
    total_mh = activity.quantity * productivity
    daily_capacity = total_workers * HOURS_PER_DAY

    if daily_capacity == 0:
        return 1

    duration = total_mh / daily_capacity

    return max(1, math.ceil(duration))

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


def compute_activity_duration(activity, worker_count=None):
    """
    Compute activity duration using manhour formula:
    Duration(days) = (Quantity * Productivity Rate) / (No. of workers * 8 hrs/day)
    """

    if activity.is_group or not activity.quantity:
        return 1

    if worker_count is None:
        manpower = activity.manpower.all()
        # Prefer required manpower for planned duration; fallback to actual if required is empty.
        total_workers = sum((m.required or m.actual or 0) for m in manpower)
    else:
        total_workers = worker_count

    if total_workers <= 0:
        return 1

    productivity = get_productivity(activity.name)
    total_manhours = activity.quantity * productivity
    daily_capacity = total_workers * HOURS_PER_DAY

    if daily_capacity <= 0:
        return 1

    duration = total_manhours / daily_capacity
    return max(1, math.ceil(duration))

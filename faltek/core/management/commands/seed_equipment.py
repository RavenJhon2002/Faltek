from django.core.management.base import BaseCommand
from core.models import Activity, Equipment, ActivityEquipment


EQUIPMENT_MAPPING = [
    {
        "engineering": "Excavation Works",
        "keywords": ["excavation", "trench", "backfill", "clearing", "earthworks"],
        "equipment": [
            {"name": "Excavator", "capacity_per_day": 200, "unit": "cu.m"},
            {"name": "Dump Truck", "capacity_per_trip": 10, "unit": "cu.m"},
            {"name": "Plate Compactor", "capacity_per_day": 50, "unit": "cu.m"},
        ],
    },
    {
        "engineering": "Reinforced Concrete Works",
        "keywords": ["footing", "column", "beam", "slab", "stairs", "concrete"],
        "equipment": [
            {"name": "Concrete Mixer", "capacity_per_day": 6, "unit": "cu.m"},
            {"name": "Concrete Vibrator", "capacity_per_hour": 40, "unit": "cu.m"},
        ],
    },
    {
        "engineering": "Formworks",
        "keywords": ["formworks", "forms", "shuttering"],
        "equipment": [
            {"name": "Minor Tools"},
        ],
    },
    {
        "engineering": "Reinforcing Steel Works",
        "keywords": ["reinforcing", "rebar", "rsb"],
        "equipment": [
            {"name": "Bar Cutter"},
            {"name": "Bar Bender"},
            {"name": "Welding Machine"},
        ],
    },
    {
        "engineering": "Masonry Works",
        "keywords": ["chb", "masonry", "hollow block"],
        "equipment": [
            {"name": "Concrete Mixer"},
        ],
    },
]


def compute_required_capacity(activity_qty, equipment_meta):
    if not activity_qty:
        return 1.0

    if equipment_meta.get("capacity_per_day"):
        return max(0.01, activity_qty / float(equipment_meta["capacity_per_day"]))
    if equipment_meta.get("capacity_per_trip"):
        return max(0.01, activity_qty / float(equipment_meta["capacity_per_trip"]))
    if equipment_meta.get("capacity_per_hour"):
        return max(0.01, activity_qty / float(equipment_meta["capacity_per_hour"]))
    return 1.0


class Command(BaseCommand):
    help = "Seed default equipment records for BOQ activities"

    def add_arguments(self, parser):
        parser.add_argument(
            "--project-id",
            type=int,
            dest="project_id",
            help="Seed equipment only for activities under this project id.",
        )

    def handle(self, *args, **kwargs):
        project_id = kwargs.get("project_id")
        activities = Activity.objects.filter(is_group=False, quantity__isnull=False)
        if project_id:
            activities = activities.filter(project_id=project_id)
        created_count = 0
        updated_count = 0

        for activity in activities:
            name_lower = (activity.name or "").lower()
            matched = None
            for mapping in EQUIPMENT_MAPPING:
                if any(keyword in name_lower for keyword in mapping["keywords"]):
                    matched = mapping
                    break

            if not matched:
                continue

            for equipment_meta in matched["equipment"]:
                equipment_obj, _ = Equipment.objects.get_or_create(name=equipment_meta["name"])

                required = round(compute_required_capacity(activity.quantity or 0, equipment_meta), 2)
                unit = equipment_meta.get("unit") or activity.unit or ""
                quantity_int = max(0, int(round(required)))

                row, created = ActivityEquipment.objects.update_or_create(
                    activity=activity,
                    equipment=equipment_obj,
                    defaults={
                        "quantity": quantity_int,
                        "required": required,
                        "unit": unit,
                    },
                )

                if created:
                    created_count += 1
                else:
                    updated_count += 1

        project_text = f" for project {project_id}" if project_id else ""
        self.stdout.write(
            self.style.SUCCESS(
                f"Equipment seeded{project_text}. Created {created_count}, updated {updated_count} records."
            )
        )

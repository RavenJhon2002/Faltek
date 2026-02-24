from django.core.management.base import BaseCommand

from core.models import Activity, ActivityManpower, Role


DEFAULTS = {
    "excavation": (1, 1, 2),
    "gravel": (1, 1, 2),
    "concrete": (1, 2, 3),
    "reinforcing": (1, 2, 1),
    "formwork": (1, 3, 2),
    "scaffold": (1, 2, 2),
    "masonry": (1, 1, 2),
    "metal": (1, 2, 2),
    "truss": (1, 3, 2),
    "roof": (1, 2, 2),
    "floor": (1, 2, 2),
    "wall": (1, 2, 2),
    "ceiling": (1, 2, 2),
    "paint": (1, 2, 1),
    "thermal": (1, 2, 2),
    "moisture": (1, 2, 2),
    "demolition": (1, 2, 3),
}


class Command(BaseCommand):
    help = "Seed default manpower for BOQ activities with quantity only"

    def add_arguments(self, parser):
        parser.add_argument(
            "--project-id",
            type=int,
            dest="project_id",
            help="Seed manpower only for activities under this project id.",
        )

    def handle(self, *args, **kwargs):
        project_id = kwargs.get("project_id")

        roles = ["Foreman", "Skilled Worker", "Labor"]
        role_objs = {}
        for role_name in roles:
            role_obj, _ = Role.objects.get_or_create(name=role_name)
            role_objs[role_name] = role_obj

        activities = Activity.objects.filter(is_group=False, quantity__isnull=False)
        if project_id:
            activities = activities.filter(project_id=project_id)

        created_count = 0
        for activity in activities:
            name_lower = (activity.name or "").lower()

            crew = (1, 1, 1)
            for keyword, values in DEFAULTS.items():
                if keyword in name_lower:
                    crew = values
                    break

            mapping = {
                "Foreman": crew[0],
                "Skilled Worker": crew[1],
                "Labor": crew[2],
            }

            for role_name, qty in mapping.items():
                _, created = ActivityManpower.objects.get_or_create(
                    activity=activity,
                    role=role_objs[role_name],
                    defaults={"required": qty, "actual": 0},
                )
                if created:
                    created_count += 1

        project_text = f" for project {project_id}" if project_id else ""
        self.stdout.write(
            self.style.SUCCESS(
                f"Manpower seeded{project_text}. Created {created_count} records."
            )
        )

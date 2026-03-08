from django.db import migrations, models
import uuid


def fill_project_share_tokens(apps, schema_editor):
    Project = apps.get_model("core", "Project")
    for project in Project.objects.filter(share_token__isnull=True):
        project.share_token = uuid.uuid4()
        project.save(update_fields=["share_token"])


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0012_activity_actual_progress_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="project",
            name="share_token",
            field=models.UUIDField(null=True, editable=False),
        ),
        migrations.RunPython(fill_project_share_tokens, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="project",
            name="share_token",
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
    ]

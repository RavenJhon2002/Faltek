from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0010_activity_actual_progress_and_more"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="activity",
            name="actual_progress",
        ),
        migrations.RemoveField(
            model_name="activity",
            name="progress_updated_at",
        ),
    ]

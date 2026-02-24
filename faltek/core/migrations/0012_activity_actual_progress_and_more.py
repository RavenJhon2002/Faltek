from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0011_remove_activity_actual_progress_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="activity",
            name="actual_progress",
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name="activity",
            name="progress_updated_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]

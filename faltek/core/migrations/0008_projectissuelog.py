from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0007_activitymanpower_actual_updated_at"),
    ]

    operations = [
        migrations.CreateModel(
            name="ProjectIssueLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("report_date", models.DateField()),
                ("short_description", models.TextField()),
                ("image", models.FileField(blank=True, null=True, upload_to="issue_logs/")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("project", models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="issue_logs", to="core.project")),
            ],
            options={
                "ordering": ["-report_date", "-created_at"],
            },
        ),
    ]

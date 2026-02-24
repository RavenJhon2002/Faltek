from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0006_activity_is_group_activity_quantity_activity_unit_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="activitymanpower",
            name="actual_updated_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]

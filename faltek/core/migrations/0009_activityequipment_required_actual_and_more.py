from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0008_projectissuelog"),
    ]

    operations = [
        migrations.AddField(
            model_name="activityequipment",
            name="actual",
            field=models.FloatField(default=0),
        ),
        migrations.AddField(
            model_name="activityequipment",
            name="actual_updated_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="activityequipment",
            name="required",
            field=models.FloatField(default=0),
        ),
        migrations.AddField(
            model_name="activityequipment",
            name="unit",
            field=models.CharField(blank=True, max_length=30),
        ),
    ]

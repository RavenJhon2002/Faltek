from django.db import models
from django.contrib.auth.models import User
import uuid


class Project(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    name = models.CharField(max_length=255)
    project_type = models.CharField(max_length=100, blank=True)
    location = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)

    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    share_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    def __str__(self):
        return self.name


class Task(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="tasks")
    name = models.CharField(max_length=255)
    start_date = models.DateField()
    end_date = models.DateField()
    progress = models.IntegerField(default=0)


class Activity(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Ongoing', 'Ongoing'),
        ('Done', 'Done'),
    ]

    project = models.ForeignKey(
        Project,
        related_name='activities',
        on_delete=models.CASCADE
    )

    name = models.CharField(max_length=255)

    # ⭐ NEW FIELDS (IMPORTANT)
    quantity = models.FloatField(null=True, blank=True)
    unit = models.CharField(max_length=50, blank=True)
    is_group = models.BooleanField(default=False)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='Pending'
    )

    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    actual_progress = models.IntegerField(default=0)
    progress_updated_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.name


class Role(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class Equipment(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class ActivityManpower(models.Model):
    activity = models.ForeignKey(
        Activity,
        related_name="manpower",
        on_delete=models.CASCADE
    )
    role = models.ForeignKey(Role, on_delete=models.CASCADE)
    required = models.IntegerField(default=0)
    actual = models.IntegerField(default=0)
    actual_updated_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.activity.name} - {self.role.name}"


class ActivityEquipment(models.Model):
    activity = models.ForeignKey(
        Activity,
        related_name="equipment",
        on_delete=models.CASCADE
    )
    equipment = models.ForeignKey(Equipment, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=0)
    required = models.FloatField(default=0)
    actual = models.FloatField(default=0)
    unit = models.CharField(max_length=30, blank=True)
    actual_updated_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.activity.name} - {self.equipment.name}"


class ProjectIssueLog(models.Model):
    project = models.ForeignKey(
        Project,
        related_name="issue_logs",
        on_delete=models.CASCADE
    )
    report_date = models.DateField()
    short_description = models.TextField()
    image = models.FileField(upload_to="issue_logs/", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-report_date", "-created_at"]

    def __str__(self):
        return f"{self.project.name} - {self.report_date}"

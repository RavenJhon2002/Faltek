from django.contrib import admin
from .models import (
    Project, Activity, Role, Equipment,
    ActivityManpower, ActivityEquipment, ProjectIssueLog, ProjectBOQUpload
)


admin.site.register(Project)
admin.site.register(Activity)
admin.site.register(Role)
admin.site.register(Equipment)
admin.site.register(ActivityManpower)
admin.site.register(ActivityEquipment)
admin.site.register(ProjectIssueLog)
admin.site.register(ProjectBOQUpload)

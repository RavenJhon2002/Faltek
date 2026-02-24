import pandas as pd
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from .models import Project
from django.shortcuts import render, redirect
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from .forms import ProjectForm
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import user_passes_test
from django.http import JsonResponse
import json
from django.utils.safestring import mark_safe
from .forms import BOQUploadForm, ProjectIssueLogForm
from .models import Project, Activity, ActivityManpower, ActivityEquipment, ProjectIssueLog
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Max, Sum
from datetime import timedelta
from django.utils import timezone
from django.urls import reverse
from core.utils.scheduling import compute_activity_duration
from django.core.management import call_command
from django.utils.dateparse import parse_date


def is_admin(user):
    return user.groups.filter(name='Admin').exists()

def is_user(user):
    return user.groups.filter(name='User').exists()


def clamp_percent(value):
    return max(0, min(100, int(value)))


def get_delay_status(required_workers, actual_workers, end_date=None, latest_update=None):
    if required_workers <= 0:
        return "on_schedule"

    # If update was recorded after planned end date, mark delayed.
    if end_date and latest_update:
        late_days = (latest_update.date() - end_date).days
        if late_days > 0:
            if late_days <= 3:
                return "minor_delay"
            return "significant_delay"

    coverage = actual_workers / required_workers
    if coverage >= 1:
        return "on_schedule"
    if coverage >= 0.7:
        return "minor_delay"
    return "significant_delay"


def compute_planned_progress_for_date(start_date, end_date, as_of_date):
    if not start_date or not end_date:
        return 0

    total_days = max(1, (end_date - start_date).days)
    elapsed_days = (as_of_date - start_date).days
    planned = round((elapsed_days / total_days) * 100)
    return clamp_percent(planned)


def get_progress_delay_status(planned_progress, actual_progress, end_date=None, latest_update=None):
    if end_date and latest_update:
        late_days = (latest_update.date() - end_date).days
        if late_days > 0:
            if late_days <= 3:
                return "minor_delay", "MINOR DELAY"
            return "significant_delay", "SIGNIFICANT DELAY"

    variance = actual_progress - planned_progress
    if variance >= 0:
        return "on_schedule", "ON SCHEDULE"
    if variance >= -10:
        return "minor_delay", "MINOR DELAY"
    return "significant_delay", "SIGNIFICANT DELAY"



@login_required
def project_list(request):
    projects = Project.objects.filter(user=request.user)
    return render(request, 'core/project_list.html', {
        'projects': projects,
    })

def signup(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('/')
    else:
        form = UserCreationForm()

    return render(request, 'core/signup.html', {'form': form})

@login_required
def project_create(request):
    if request.method == 'POST':
        form = ProjectForm(request.POST)
        if form.is_valid():
            project = form.save(commit=False)
            project.user = request.user
            project.save()
            return redirect('project_list')
    else:
        form = ProjectForm()

    return render(request, 'core/project_form.html', {
        'form': form
    })   



@login_required
def project_edit(request, pk):
    project = get_object_or_404(Project, pk=pk, user=request.user)

    if request.method == 'POST':
        form = ProjectForm(request.POST, instance=project)
        if form.is_valid():
            form.save()
            return redirect('project_list')
    else:
        form = ProjectForm(instance=project)

    return render(request, 'core/project_form.html', {
        'form': form,
        'edit_mode': True
    })

@login_required
def project_delete(request, pk):
    project = get_object_or_404(Project, pk=pk, user=request.user)

    if request.method == 'POST':
        project.delete()
        return redirect('project_list')

    return render(request, 'core/project_confirm_delete.html', {
        'project': project
    })


@login_required
def dashboard(request):
    projects = Project.objects.filter(user=request.user)

    gantt_data = []
    for p in projects:
        gantt_data.append({
            "name": p.name,
            "start": p.start_date.isoformat(),
            "end": p.end_date.isoformat(),
        })


    return render(request, "dashboard.html", {
        "gantt_data": gantt_data
    })
    
def project_gantt_data(request):
    projects = Project.objects.filter(user=request.user)
    data = [
        {
            "id": p.id,
            "name": p.name,
            "start": p.start_date,
            "end": p.end_date,
            "type": p.project_type,
        }
        for p in projects
    ]
    return JsonResponse(data, safe=False)

@login_required
def upload_boq(request, project_id):
    project = get_object_or_404(Project, id=project_id, user=request.user)

    if request.method == "POST":
        form = BOQUploadForm(request.POST, request.FILES)

        if form.is_valid():
            file = request.FILES["file"]

            
            sheets = pd.read_excel(file, sheet_name=None, engine="openpyxl")

            Activity.objects.filter(project=project).delete()

            for sheet_name, df in sheets.items():
                print(f"\nREADING SHEET: {sheet_name}")


                df.columns = (
                    df.columns.astype(str)
                    .str.lower()
                    .str.strip()
                    .str.replace(" ", "_")
                )

                print("COLUMNS:", list(df.columns))


                desc_col = None
                possible_desc = [
                    "bill_of_quantities",
                    "work_description_and_scope_of_works",
                    "work_description_and",
                    "description",
                ]

                for col in possible_desc:
                    if col in df.columns:
                        desc_col = col
                        break

                if not desc_col:
                    print(" No usable description column in", sheet_name)
                    continue

                qty_col = None
                possible_qty = ["qty", "quantity", "unnamed:_2"]

                for col in possible_qty:
                    if col in df.columns:
                        qty_col = col
                        break


                unit_col = None
                possible_unit = ["unit", "unnamed:_3"]

                for col in possible_unit:
                    if col in df.columns:
                        unit_col = col
                        break

                for _, row in df.iterrows():
                    description = row.get(desc_col)
                    qty = row.get(qty_col) if qty_col else None
                    unit = row.get(unit_col) if unit_col else ""

                    if pd.isna(description):
                        continue

                    description = str(description).strip()

                    if not description:
                        continue

                    if any(word in description.lower() for word in [
                        "include", "including", "must be", "performed",
                        "installation of", "all necessary"
                    ]):
                        continue

                    if any(word in description.lower() for word in [
                        "direct cost", "labor cost", "materials cost"
                    ]):
                        continue


                    qty_value = None
                    if qty_col:
                        try:
                            qty_value = float(str(qty).replace(",", ""))
                        except:
                            qty_value = None


                    if qty_value is not None and qty_value > 0:

                        Activity.objects.create(
                            project=project,
                            name=description,
                            quantity=qty_value,
                            unit=str(unit) if unit else "",
                            is_group=False,
                            status="Pending",
                            start_date=project.start_date,
                            end_date=project.start_date
                        )

                        print(" ACTIVITY CREATED:", description, qty_value)

                    else:

                        Activity.objects.create(
                            project=project,
                            name=description,
                            is_group=True,
                            status="Pending",
                            start_date=project.start_date,
                            end_date=project.start_date
                        )

                        print(" GROUP CREATED:", description)

            # Always regenerate mappings from the latest BOQ upload.
            call_command("seed_manpower", project_id=project.id)
            call_command("seed_equipment", project_id=project.id)

            return redirect("project_detail", project.id)

    else:
        form = BOQUploadForm()

    return render(request, "core/upload_boq.html", {
        "form": form,
        "project": project
    })

@login_required
def project_gantt(request, project_id):
    project = get_object_or_404(Project, id=project_id, user=request.user)


    tasks = Activity.objects.filter(project=project)

    gantt_data = [
        {
            "name": t.name,
            "start": t.start_date.isoformat(),
            "end": t.end_date.isoformat(),
            "progress": getattr(t, "progress", 0),
        }
        for t in tasks
        if t.start_date and t.end_date
    ]

    return render(
        request,
        "core/project_gantt.html",
        {
            "project": project,
            "gantt_data": mark_safe(json.dumps(gantt_data)),
        }
    )
    


# 🔧 Productivity rates (tune anytime)
PRODUCTIVITY = {
    "excavation": 10,
    "concrete": 5,
    "formwork": 8,
    "reinforcing": 6,
    "masonry": 12,
    "default": 8,
}


@login_required
def project_detail(request, pk):
    project = get_object_or_404(Project, pk=pk, user=request.user)
    activities = project.activities.all().order_by("id")
    issue_log_form = ProjectIssueLogForm()
    open_reports_modal = request.GET.get("modal") == "reports"
    open_equipment_modal = request.GET.get("modal") == "equipment"
    equipment_open_view = request.GET.get("equipment_view") or "settings"
    if equipment_open_view not in {"settings", "reports"}:
        equipment_open_view = "settings"

    if request.method == "POST":
        if request.POST.get("save_issue_log") == "1":
            issue_log_form = ProjectIssueLogForm(request.POST, request.FILES)
            if issue_log_form.is_valid():
                issue_log = issue_log_form.save(commit=False)
                issue_log.project = project
                issue_log.save()
                detail_url = reverse("project_detail", kwargs={"pk": project.pk})
                return redirect(f"{detail_url}?modal=reports")
            open_reports_modal = True
        elif request.POST.get("save_equipment") == "1":
            equipment_entry_date = parse_date(request.POST.get("equipment_entry_date", ""))
            for key, value in request.POST.items():
                if not key.startswith("eq_actual_"):
                    continue

                equipment_id = key.replace("eq_actual_", "").strip()
                if not equipment_id.isdigit():
                    continue

                try:
                    actual_value = float(value)
                except (TypeError, ValueError):
                    actual_value = 0

                actual_value = max(0, actual_value)
                if actual_value > 0:
                    updated_at = timezone.now()
                    if equipment_entry_date:
                        updated_at = updated_at.replace(
                            year=equipment_entry_date.year,
                            month=equipment_entry_date.month,
                            day=equipment_entry_date.day,
                        )
                else:
                    updated_at = None

                ActivityEquipment.objects.filter(
                    id=int(equipment_id),
                    activity__project=project
                ).update(
                    actual=actual_value,
                    actual_updated_at=updated_at
                )

            detail_url = reverse("project_detail", kwargs={"pk": project.pk})
            return redirect(f"{detail_url}?modal=equipment&equipment_view=settings")
        else:
            manpower_entry_date = parse_date(request.POST.get("manpower_entry_date", ""))
            for key, value in request.POST.items():
                if not key.startswith("actual_"):
                    continue

                manpower_id = key.replace("actual_", "").strip()
                if not manpower_id.isdigit():
                    continue

                try:
                    actual_value = int(value)
                except (TypeError, ValueError):
                    actual_value = 0

                actual_value = max(0, actual_value)

                if actual_value > 0:
                    updated_at = timezone.now()
                    if manpower_entry_date:
                        updated_at = updated_at.replace(
                            year=manpower_entry_date.year,
                            month=manpower_entry_date.month,
                            day=manpower_entry_date.day,
                        )
                else:
                    updated_at = None

                ActivityManpower.objects.filter(
                    id=int(manpower_id),
                    activity__project=project
                ).update(
                    actual=actual_value,
                    actual_updated_at=updated_at
                )

            return redirect("project_detail", pk=project.pk)

    gantt_data = []
    total_required_workers = 0
    total_actual_workers = 0
    total_timeline_days = 0
    weighted_actual_days = 0.0
    timeline_start = None
    timeline_end = None
    activity_progress_rows = []

    HOURS_PER_DAY = 8
    PRODUCTIVITY_RATE = 0.5  # you can move this to DB later

    for act in activities:
        # MANPOWER TOTALS
        manpower_totals = act.manpower.aggregate(
            required=Sum("required"),
            actual=Sum("actual"),
            latest_update=Max("actual_updated_at"),
        )

        required_workers = manpower_totals["required"] or 0
        actual_workers = manpower_totals["actual"] or 0
        latest_update = manpower_totals["latest_update"]
        total_required_workers += required_workers
        total_actual_workers += actual_workers

        # COMPUTE DURATION FROM FORMULA
        duration_days = 0
        start_date = act.start_date or project.start_date
        end_date = act.end_date

        if (
            act.quantity
            and required_workers > 0
            and start_date
            and not act.is_group
        ):
            total_mh = act.quantity * PRODUCTIVITY_RATE
            duration_days = total_mh / (required_workers * HOURS_PER_DAY)

            # round up to whole day
            duration_days = max(1, int(duration_days + 0.999))

            end_date = start_date + timedelta(days=duration_days)

        if (
            not act.is_group
            and start_date
            and end_date
        ):
            timeline_start = min(timeline_start, start_date) if timeline_start else start_date
            timeline_end = max(timeline_end, end_date) if timeline_end else end_date

            task_days = max(1, (end_date - start_date).days)
            total_timeline_days += task_days

            if required_workers > 0:
                manpower_ratio = min(1.0, actual_workers / required_workers)
                weighted_actual_days += task_days * manpower_ratio

            planned_task_progress = compute_planned_progress_for_date(
                start_date,
                end_date,
                timezone.localdate(),
            )
            if required_workers > 0:
                actual_task_progress = clamp_percent(round((actual_workers / required_workers) * 100))
            else:
                actual_task_progress = 100
            progress_delay_key, progress_delay_label = get_progress_delay_status(
                planned_task_progress,
                actual_task_progress,
                end_date=end_date,
                latest_update=latest_update,
            )

            delay_date = ""
            if progress_delay_key in {"minor_delay", "significant_delay"} and latest_update:
                delay_date = latest_update.date().isoformat()

            activity_progress_rows.append({
                "id": act.id,
                "name": act.name,
                "planned_progress": planned_task_progress,
                "actual_progress": actual_task_progress,
                "delay_status_key": progress_delay_key,
                "delay_status_label": progress_delay_label,
                "delay_date": delay_date,
                "progress_updated_at": latest_update,
            })

        # BUILD GANTT DATA
        if start_date and end_date:
            delay_status = get_delay_status(
                required_workers,
                actual_workers,
                end_date=end_date,
                latest_update=latest_update,
            )
            delay_date = ""
            if delay_status in {"minor_delay", "significant_delay"}:
                if latest_update:
                    delay_date = latest_update.date().isoformat()
                else:
                    delay_date = timezone.localdate().isoformat()

            gantt_data.append({
                "name": act.name,
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
                "required": required_workers,
                "actual": actual_workers,
                "delay_status": delay_status,
                "delay_date": delay_date,
                "is_group": getattr(act, "is_group", False),
                "duration": duration_days,
                "quantity": act.quantity,
                "unit": act.unit,
            })

    actual_progress = 0
    if total_timeline_days > 0:
        actual_progress = round((weighted_actual_days / total_timeline_days) * 100)
        actual_progress = max(0, min(100, actual_progress))

    expected_progress = 0
    today = timezone.localdate()
    if timeline_start and timeline_end:
        planned_days = max(1, (timeline_end - timeline_start).days)
        elapsed_days = (today - timeline_start).days
        expected_progress = round((elapsed_days / planned_days) * 100)
        expected_progress = max(0, min(100, expected_progress))

    variance = actual_progress - expected_progress
    if variance >= 0:
        progress_status = "ON TIME"
    elif variance >= -10:
        progress_status = "SLIGHTLY DELAYED"
    else:
        progress_status = "DELAYED"

    manpower_activities = (
        activities
        .filter(is_group=False)
        .prefetch_related("manpower__role")
    )

    manpower_rows = ActivityManpower.objects.filter(activity__project=project).select_related("role", "activity")

    manpower_report_map = {}
    for row in manpower_rows:
        role_name = row.role.name
        if role_name not in manpower_report_map:
            manpower_report_map[role_name] = {
                "role": role_name,
                "required": 0,
                "actual": 0,
            }

        manpower_report_map[role_name]["required"] += row.required or 0
        manpower_report_map[role_name]["actual"] += row.actual or 0

    role_priority = {"Foreman": 0, "Skilled Worker": 1, "Labor": 2}
    manpower_report_rows = sorted(
        manpower_report_map.values(),
        key=lambda x: (role_priority.get(x["role"], 99), x["role"])
    )

    for row in manpower_report_rows:
        required = row["required"] or 0
        actual = row["actual"] or 0
        row["completion"] = 0 if required <= 0 else round((actual / required) * 100)
        row["completion"] = max(0, min(100, row["completion"]))

    manpower_completion = 0
    if total_required_workers > 0:
        manpower_completion = round((total_actual_workers / total_required_workers) * 100)
        manpower_completion = max(0, min(100, manpower_completion))

    manpower_report_details = []
    date_values = set()
    for row in manpower_rows:
        actual = row.actual or 0
        if actual <= 0:
            continue

        report_date = row.actual_updated_at.date() if row.actual_updated_at else None
        if report_date:
            date_values.add(report_date.isoformat())

        required = row.required or 0
        completion = 0 if required <= 0 else round((actual / required) * 100)
        completion = max(0, min(100, completion))

        manpower_report_details.append({
            "activity": row.activity.name,
            "role": row.role.name,
            "required": required,
            "actual": actual,
            "completion": completion,
            "updated_at": row.actual_updated_at,
            "report_date": report_date.isoformat() if report_date else "",
        })

    manpower_report_details.sort(
        key=lambda x: (
            x["updated_at"] is not None,
            x["updated_at"].isoformat() if x["updated_at"] else "",
            x["activity"],
            x["role"],
        ),
        reverse=True
    )
    manpower_report_dates = sorted(date_values, reverse=True)
    issue_logs = ProjectIssueLog.objects.filter(project=project)
    equipment_activities = (
        activities
        .filter(is_group=False)
        .prefetch_related("equipment__equipment")
    )

    equipment_rows = ActivityEquipment.objects.filter(
        activity__project=project
    ).select_related("equipment", "activity")

    total_required_equipment = 0.0
    total_actual_equipment = 0.0
    equipment_report_details = []
    equipment_date_values = set()

    for row in equipment_rows:
        required = row.required or float(row.quantity or 0)
        actual = row.actual or 0
        total_required_equipment += required
        total_actual_equipment += actual

        if actual <= 0:
            continue

        report_date = row.actual_updated_at.date() if row.actual_updated_at else None
        if report_date:
            equipment_date_values.add(report_date.isoformat())

        completion = 0 if required <= 0 else round((actual / required) * 100)
        completion = max(0, min(100, completion))

        equipment_report_details.append({
            "activity": row.activity.name,
            "equipment": row.equipment.name,
            "required": round(required, 2),
            "actual": round(actual, 2),
            "unit": row.unit or row.activity.unit or "",
            "completion": completion,
            "updated_at": row.actual_updated_at,
            "report_date": report_date.isoformat() if report_date else "",
        })

    equipment_report_details.sort(
        key=lambda x: (
            x["updated_at"] is not None,
            x["updated_at"].isoformat() if x["updated_at"] else "",
            x["activity"],
            x["equipment"],
        ),
        reverse=True
    )

    equipment_report_dates = sorted(equipment_date_values, reverse=True)
    equipment_completion = 0
    if total_required_equipment > 0:
        equipment_completion = round((total_actual_equipment / total_required_equipment) * 100)
        equipment_completion = max(0, min(100, equipment_completion))

    today_iso = timezone.localdate().isoformat()

    context = {
        "project": project,
        "activities": activities,
        "gantt_data_json": json.dumps(gantt_data),
        "actual_progress": actual_progress,
        "expected_progress": expected_progress,
        "progress_status": progress_status,
        "timeline_start": timeline_start,
        "timeline_end": timeline_end,
        "activity_progress_rows": activity_progress_rows,
        "total_required_workers": total_required_workers,
        "total_actual_workers": total_actual_workers,
        "manpower_activities": manpower_activities,
        "manpower_completion": manpower_completion,
        "manpower_report_rows": manpower_report_rows,
        "manpower_report_details": manpower_report_details,
        "manpower_report_dates": manpower_report_dates,
        "issue_log_form": issue_log_form,
        "issue_logs": issue_logs,
        "open_reports_modal": open_reports_modal,
        "equipment_activities": equipment_activities,
        "equipment_report_details": equipment_report_details,
        "equipment_report_dates": equipment_report_dates,
        "total_required_equipment": round(total_required_equipment, 2),
        "total_actual_equipment": round(total_actual_equipment, 2),
        "equipment_completion": equipment_completion,
        "open_equipment_modal": open_equipment_modal,
        "equipment_open_view": equipment_open_view,
        "today_iso": today_iso,
    }

    return render(request, "core/project_detail.html", context)
    
def schedule_project(project):
    current_date = project.start_date

    activities = project.activities.filter(is_group=False).order_by("id")

    for act in activities:
        duration = compute_activity_duration(act)

        act.start_date = current_date
        act.end_date = current_date + timedelta(days=duration)
        act.save()

        current_date = act.end_date


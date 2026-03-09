import pandas as pd
from zipfile import BadZipFile
import re
import os
import logging
from io import BytesIO
from django.contrib.auth.decorators import login_required
from django.contrib import messages
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
from .models import Project, Activity, ActivityManpower, ActivityEquipment, ProjectIssueLog, ProjectBOQUpload
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Max, Sum
from django.db import DataError, transaction
from datetime import timedelta
from django.utils import timezone
from django.urls import reverse
from core.utils.scheduling import compute_activity_duration
from django.core.management import call_command
from django.core.management.base import CommandError
from django.utils.dateparse import parse_date
from django.core.files.base import ContentFile

logger = logging.getLogger(__name__)

def is_admin(user):
    return user.groups.filter(name='Admin').exists()

def is_user(user):
    return user.groups.filter(name='User').exists()


def get_project_for_user(user, **lookup):
    if is_admin(user):
        return get_object_or_404(Project, **lookup)
    return get_object_or_404(Project, user=user, **lookup)


def clamp_percent(value):
    return max(0, min(100, int(value)))


def get_resource_shortage_level(required, actual):
    if required <= 0:
        return "met"

    coverage = actual / required
    if coverage >= 1:
        return "met"
    if coverage >= 0.7:
        return "slight"
    return "significant"


def compute_planned_progress_for_date(start_date, end_date, as_of_date):
    if not start_date or not end_date:
        return 0

    total_days = max(1, (end_date - start_date).days)
    if as_of_date < start_date:
        return 0
    if as_of_date >= end_date:
        return 100

    # Count passed days including today, aligned with day-based site reporting.
    elapsed_days = (as_of_date - start_date).days + 1
    elapsed_days = max(0, min(total_days, elapsed_days))
    planned = round((elapsed_days / total_days) * 100)
    return clamp_percent(planned)


def get_progress_delay_status(
    planned_progress,
    actual_progress,
    manpower_required=0,
    manpower_actual=0,
    equipment_required=0,
    equipment_actual=0,
):
    # Progress thresholds:
    # - GREEN: actual >= expected
    # - ORANGE: up to 15% behind expected
    # - RED: more than 15% behind expected
    lag = planned_progress - actual_progress
    if lag <= 0:
        progress_level = 0
    elif lag <= 15:
        progress_level = 1
    else:
        progress_level = 2

    manpower_shortage = get_resource_shortage_level(manpower_required, manpower_actual)
    equipment_shortage = get_resource_shortage_level(equipment_required, equipment_actual)

    shortage_rank = {
        "met": 0,
        "slight": 1,
        "significant": 2,
    }
    resource_level = max(
        shortage_rank.get(manpower_shortage, 0),
        shortage_rank.get(equipment_shortage, 0),
    )
    overall_level = max(progress_level, resource_level)

    if overall_level == 0:
        return "on_schedule", "ON TIME"
    if overall_level == 1:
        return "minor_delay", "SLIGHTLY DELAYED"
    return "significant_delay", "DELAYED"


def get_progress_only_status(expected_progress, actual_progress):
    lag = expected_progress - actual_progress
    if lag <= 0:
        return "ON TIME"
    if lag <= 15:
        return "SLIGHTLY DELAYED"
    return "DELAYED"


def get_activity_actual_progress(activity, required_workers=0, actual_workers=0):
    if activity.actual_progress is not None and activity.actual_progress > 0:
        return clamp_percent(activity.actual_progress)

    if required_workers > 0:
        derived = round((actual_workers / required_workers) * 100)
        return clamp_percent(derived)

    status_map = {
        "Done": 100,
        "Ongoing": 50,
        "Pending": 0,
    }
    return status_map.get(activity.status, 0)



@login_required
def project_list(request):
    if is_admin(request.user):
        projects = Project.objects.all()
    else:
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
            if request.POST.get("action") == "upload_boq":
                return redirect("upload_boq", project.id)
            return redirect('project_list')
    else:
        form = ProjectForm()

    return render(request, 'core/project_form.html', {
        'form': form,
        'edit_mode': False,
        'project': None,
    })   



@login_required
def project_edit(request, pk):
    project = get_project_for_user(request.user, pk=pk)

    if request.method == 'POST':
        form = ProjectForm(request.POST, instance=project)
        if form.is_valid():
            form.save()
            if request.POST.get("action") == "upload_boq":
                return redirect("upload_boq", project.id)
            return redirect('project_list')
    else:
        form = ProjectForm(instance=project)

    return render(request, 'core/project_form.html', {
        'form': form,
        'edit_mode': True,
        'project': project,
    })

@login_required
def project_delete(request, pk):
    project = get_project_for_user(request.user, pk=pk)

    if request.method == 'POST':
        project.delete()
        return redirect('project_list')

    return render(request, 'core/project_confirm_delete.html', {
        'project': project
    })


@login_required
def dashboard(request):
    if is_admin(request.user):
        projects = Project.objects.all()
    else:
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
    if is_admin(request.user):
        projects = Project.objects.all()
    else:
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
    project = get_project_for_user(request.user, id=project_id)

    if request.method == "POST":
        form = BOQUploadForm(request.POST, request.FILES)

        if form.is_valid():
            uploaded_file = request.FILES["file"]
            uploaded_filename = uploaded_file.name
            uploaded_bytes = uploaded_file.read()
            file_stream = BytesIO(uploaded_bytes)
            base_start = project.start_date or timezone.localdate()

            def normalize_storage_filename(name, max_length=50):
                basename = os.path.basename(name or "upload.xlsx")
                stem, ext = os.path.splitext(basename)
                ext = (ext or ".xlsx")[:10]
                safe_stem = re.sub(r"[^A-Za-z0-9._-]+", "_", stem).strip("._") or "upload"
                safe_stem = safe_stem[: max(1, max_length - len(ext))]
                return f"{safe_stem}{ext}"

            def trim_text(value, max_length):
                value = (value or "").strip()
                if len(value) <= max_length:
                    return value
                return (value[: max_length - 3].rstrip() + "...") if max_length > 3 else value[:max_length]

            try:
                sheets = pd.read_excel(file_stream, sheet_name=None, engine="openpyxl")
            except Exception as exc:
                logger.exception("Excel read failed for project_id=%s: %s", project.id, exc)
                form.add_error(
                    "file",
                    "Invalid Excel file. Please upload a real .xlsx workbook."
                )
                return render(request, "core/upload_boq.html", {
                    "form": form,
                    "project": project,
                })

            try:
                file_stream.seek(0)
                raw_sheets = pd.read_excel(
                    file_stream,
                    sheet_name=None,
                    engine="openpyxl",
                    header=None,
                )
            except Exception as exc:
                logger.exception("Excel raw read failed for project_id=%s: %s", project.id, exc)
                raw_sheets = {}

            def parse_numeric(value):
                if pd.isna(value):
                    return None
                if isinstance(value, (int, float)):
                    return float(value)
                text = str(value).replace(",", "").strip()
                if not text:
                    return None
                match = re.search(r"-?\d+(\.\d+)?", text)
                if not match:
                    return None
                try:
                    return float(match.group(0))
                except ValueError:
                    return None

            def choose_column(columns, exact_candidates, contains_candidates):
                for col in exact_candidates:
                    if col in columns:
                        return col
                for col in columns:
                    if any(token in col for token in contains_candidates):
                        return col
                return None

            def extract_project_duration_days(workbook_sheets):
                for _, raw_df in workbook_sheets.items():
                    if raw_df is None or raw_df.empty:
                        continue
                    for _, raw_row in raw_df.iterrows():
                        cells = []
                        for cell in raw_row.tolist():
                            if pd.isna(cell):
                                cells.append("")
                            else:
                                cells.append(str(cell).strip())

                        non_empty = [c for c in cells if c]
                        if not non_empty:
                            continue

                        row_text = " ".join(non_empty).lower()
                        if "duration" not in row_text:
                            continue

                        # Accept only the BOQ header duration line, not task-duration columns.
                        has_calendar_days = "calendar day" in row_text or "calendar days" in row_text
                        if not has_calendar_days:
                            continue

                        duration_text = ""
                        for i, cell in enumerate(cells):
                            cell_lower = cell.lower()
                            if "duration" in cell_lower:
                                trailing = [c for c in cells[i:] if c]
                                duration_text = " ".join(trailing).lower()
                                break
                        if not duration_text:
                            duration_text = row_text

                        # Prefer explicit "(150)" style value from BOQ header.
                        match = re.search(r"\((\d+)\)", duration_text)
                        if match:
                            return int(match.group(1))

                        # Fallback: allow number before "calendar day(s)" only on this header line.
                        match = re.search(r"(\d+)\s*calendar\s*days?", duration_text)
                        if match:
                            return int(match.group(1))
                return None

            try:
                with transaction.atomic():
                    Activity.objects.filter(project=project).delete()
                    created_starts = []
                    current_cursor = base_start
                    site_group_created = False
                    site_works_rows_found = 0
                    site_works_parts_found = set()
                    project_duration_days = extract_project_duration_days(raw_sheets)
                    if not project_duration_days or project_duration_days <= 0:
                        form.add_error(
                            "file",
                            "Could not find a valid project duration in Excel. Expected text like 'DURATION ... (150) Calendar Days'."
                        )
                        return render(request, "core/upload_boq.html", {
                            "form": form,
                            "project": project,
                        })

                    try:
                        ProjectBOQUpload.objects.create(
                            project=project,
                            uploaded_by=request.user,
                            file=ContentFile(uploaded_bytes, name=normalize_storage_filename(uploaded_filename)),
                            original_filename=trim_text(uploaded_filename, 255),
                        )
                    except Exception as exc:
                        logger.exception(
                            "BOQ file archive save failed for project_id=%s: %s",
                            project.id,
                            exc,
                        )
                        messages.warning(
                            request,
                            "BOQ processed, but the original Excel file could not be archived in cloud storage."
                        )

                    for sheet_name, df in sheets.items():
                        print(f"\nREADING SHEET: {sheet_name}")

                        if df.empty:
                            continue
                        df.columns = (
                            df.columns.astype(str)
                            .str.lower()
                            .str.strip()
                            .str.replace(r"[^0-9a-z]+", "_", regex=True)
                            .str.strip("_")
                        )

                        print("COLUMNS:", list(df.columns))

                        desc_col = choose_column(
                            df.columns,
                            [
                            "bill_of_quantities",
                            "work_description_and_scope_of_works",
                            "work_description_and",
                            "description",
                            "activity",
                            "item_description",
                            ],
                            ["description", "scope_of_work", "activity", "item"],
                        )

                        if not desc_col:
                            print(" No usable description column in", sheet_name)
                            continue

                        qty_col = choose_column(
                            df.columns,
                            ["qty", "quantity", "unnamed_2"],
                            ["qty", "quantity", "volume"],
                        )
                        unit_col = choose_column(
                            df.columns,
                            ["unit", "uom", "unnamed_3"],
                            ["unit", "uom"],
                        )
                        duration_col = choose_column(
                            df.columns,
                            ["duration", "duration_days", "no_of_days"],
                            ["duration", "days"],
                        )

                        fallback_qty_cols = [
                            col for col in ["unnamed_5", "unnamed_4", "unnamed_6", "unnamed_2"]
                            if col in df.columns and col != qty_col
                        ]
                        fallback_unit_cols = [
                            col for col in ["unnamed_6", "unnamed_7", "unnamed_3", "unnamed_4"]
                            if col in df.columns and col != unit_col
                        ]

                        in_site_works = False

                        for _, row in df.iterrows():
                            description = row.get(desc_col)
                            qty = row.get(qty_col) if qty_col else None
                            unit = row.get(unit_col) if unit_col else ""
                            raw_duration = row.get(duration_col) if duration_col else None

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

                            normalized_header = " ".join(description.lower().split())
                            if normalized_header == "site works":
                                in_site_works = True
                                continue

                            section_end_markers = {
                                "general requirements",
                                "civil/ structural works",
                                "civil/structural works",
                                "civil works / structural works",
                                "civil works/structural works",
                                "scope of works",
                                "architectural works",
                                "sanitary/plumbing works",
                                "electrical works",
                                "utility and ancillary works",
                                "mcb",
                                "mdp",
                            }
                            if in_site_works and normalized_header in section_end_markers:
                                in_site_works = False
                                continue

                            qty_value = parse_numeric(qty)
                            if qty_value is None or qty_value <= 0:
                                for alt_col in fallback_qty_cols:
                                    alt_qty_value = parse_numeric(row.get(alt_col))
                                    if alt_qty_value is not None and alt_qty_value > 0:
                                        qty_value = alt_qty_value
                                        break

                            duration_value = parse_numeric(raw_duration)
                            if duration_value is not None and duration_value > 0:
                                duration_days = max(1, int(round(duration_value)))
                            else:
                                duration_days = None

                            unit_value = str(unit).strip() if not pd.isna(unit) else ""
                            if not unit_value or unit_value.lower() == "p":
                                for alt_col in fallback_unit_cols:
                                    alt_unit_raw = row.get(alt_col)
                                    if pd.isna(alt_unit_raw):
                                        continue
                                    alt_unit_value = str(alt_unit_raw).strip()
                                    if not alt_unit_value:
                                        continue
                                    if alt_unit_value.lower() in {"p", "subtotal", "materials cost", "labor cost", "direct cost"}:
                                        continue
                                    unit_value = alt_unit_value
                                    break

                            upper_text = description.upper() == description and any(c.isalpha() for c in description)
                            is_group_row = (
                                qty_value is None
                                and not unit_value
                                and len(description.split()) <= 8
                                and upper_text
                            )

                            if is_group_row:
                                continue

                            if not in_site_works:
                                continue

                            if qty_value is None or qty_value <= 0:
                                continue

                            site_works_rows_found += 1
                            order_index = get_siteworks_order_index(description)
                            if order_index is not None:
                                site_works_parts_found.add(order_index)

                            start_date = current_cursor
                            if duration_days:
                                end_date = start_date + timedelta(days=duration_days)
                            else:
                                end_date = start_date + timedelta(days=1)
                            if end_date < start_date:
                                end_date = start_date

                            if not site_group_created:
                                Activity.objects.create(
                                    project=project,
                                    name="SITE WORKS",
                                    is_group=True,
                                    status="Pending",
                                    start_date=start_date,
                                    end_date=start_date,
                                )
                                site_group_created = True

                            activity_name = trim_text(description, 255)
                            activity = Activity.objects.create(
                                project=project,
                                name=activity_name,
                                quantity=qty_value,
                                unit=trim_text(unit_value, 50),
                                is_group=False,
                                status="Pending",
                                start_date=start_date,
                                end_date=end_date,
                            )

                            created_starts.append(start_date)
                            current_cursor = end_date

                            print(
                                " ROW CREATED:",
                                "ACTIVITY",
                                activity_name,
                                activity.start_date,
                                activity.end_date,
                            )

                    if site_works_rows_found <= 1 or len(site_works_parts_found) <= 1:
                        Activity.objects.filter(project=project).delete()
                        form.add_error(
                            "file",
                            "Wrong Excel format: could not find enough SITE WORKS parts in the BOQ file."
                        )
                        return render(request, "core/upload_boq.html", {
                            "form": form,
                            "project": project,
                        })

                    if created_starts:
                        project.start_date = min(created_starts)
                    else:
                        project.start_date = project.start_date or base_start

                    project.end_date = project.start_date + timedelta(days=project_duration_days)
                    project.save(update_fields=["start_date", "end_date"])

            except (DataError, CommandError) as exc:
                logger.exception("BOQ upload failed for project_id=%s: %s", project.id, exc)
                form.add_error(
                    None,
                    "Could not process this BOQ file due to invalid or too-long values. Please review the file and try again."
                )
                return render(request, "core/upload_boq.html", {
                    "form": form,
                    "project": project,
                })
            except Exception as exc:
                error_ref = timezone.now().strftime("%Y%m%d%H%M%S%f")
                logger.exception(
                    "Unexpected BOQ upload error ref=%s for project_id=%s: %s",
                    error_ref,
                    project.id,
                    exc,
                )
                form.add_error(
                    None,
                    f"Unexpected error while processing BOQ upload. Ref: {error_ref} ({exc.__class__.__name__})"
                )
                return render(request, "core/upload_boq.html", {
                    "form": form,
                    "project": project,
                })

            try:
                call_command("seed_manpower", project_id=project.id)
                call_command("seed_equipment", project_id=project.id)
            except Exception as exc:
                logger.exception("BOQ upload succeeded but seeding failed for project_id=%s: %s", project.id, exc)
                messages.warning(
                    request,
                    "BOQ uploaded, but manpower/equipment defaults were not auto-generated."
                )

            return redirect("project_detail", project.id)

    else:
        form = BOQUploadForm()

    return render(request, "core/upload_boq.html", {
        "form": form,
        "project": project
    })

@login_required
def project_gantt(request, project_id):
    project = get_project_for_user(request.user, id=project_id)


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


SITEWORKS_GANTT_ORDER = [
    ("layout and staking", ["layout", "staking"]),
    ("removal of tree", ["removal", "tree"]),
    ("site clearing and preparation", ["site", "clearing", "preparation"]),
    ("removal of existing roofing and bended accessories", ["removal", "existing", "roofing", "bended", "accessories"]),
    ("removal of existing roof framing", ["removal", "existing", "roof", "framing"]),
    ("removal of existing chb wall partition", ["removal", "existing", "chb", "wall", "partition"]),
    ("demolition works completion / hauling of debris", ["demolition", "hauling", "debris"]),
    ("excavation", ["excavation"]),
    ("column footing excavation & preparation", ["column", "footing", "excavation", "preparation"]),
    ("wall footing excavation", ["wall", "footing", "excavation"]),
    ("soil treatment", ["soil", "treatment"]),
    ("gravel bedding", ["gravel", "bedding"]),
    ("column footing (concreting)", ["column", "footing", "concreting"]),
    ("wall footing (concreting)", ["wall", "footing", "concreting"]),
    ("backfill and compaction", ["backfill", "compaction"]),
    ("imported earthfill", ["imported", "earthfill"]),
    ("slab-on-fill preparation", ["slab", "fill", "preparation"]),
    ("slab-on-fill concreting", ["slab", "fill", "concreting"]),
]


def normalize_activity_name(value):
    if not value:
        return ""
    normalized = re.sub(r"[^a-z0-9]+", " ", value.lower())
    return " ".join(normalized.split())


def get_siteworks_order_index(activity_name):
    normalized = normalize_activity_name(activity_name)
    for index, (_, tokens) in enumerate(SITEWORKS_GANTT_ORDER):
        if all(token in normalized for token in tokens):
            return index

    # Flexible matching for footing activities when wording is shortened.
    if "column" in normalized and "footing" in normalized:
        if "concret" in normalized:
            return 12  # Act 13: Column Footing (concreting)
        return 8  # Act 9: Column Footing excavation & preparation

    if "wall" in normalized and "footing" in normalized:
        if "concret" in normalized:
            return 13  # Act 14: Wall Footing (concreting)
        return 9  # Act 10: Wall Footing excavation

    # Fallback: include slab-on-fill items even if preparation/concreting keyword is missing.
    if "slab" in normalized and "fill" in normalized:
        if "concret" in normalized:
            return 17  # Act 18: slab-on-fill concreting
        return 16  # Act 17: slab-on-fill preparation (default)

    return None


def get_siteworks_display_name_and_indent(activity_name):
    normalized = normalize_activity_name(activity_name)

    if "column" in normalized and "footing" in normalized and "concret" in normalized:
        return "Column Footing - Concreting", 1
    if "wall" in normalized and "footing" in normalized and "concret" in normalized:
        return "Wall Footing - Concreting", 1
    if "column" in normalized and "footing" in normalized and "excavat" in normalized:
        return "Column Footing - Excavation", 1
    if "wall" in normalized and "footing" in normalized and "excavat" in normalized:
        return "Wall Footing - Excavation", 1

    return activity_name, 0


def build_project_detail_context(
    project,
    issue_log_form,
    open_reports_modal=False,
    open_equipment_modal=False,
    equipment_open_view="settings",
    viewer_mode=False,
    viewer_link="",
):
    activities = project.activities.all().order_by("id")
    all_activities = list(activities)

    gantt_data = []
    total_required_workers = 0
    total_actual_workers = 0
    total_timeline_days = 0
    weighted_actual_days = 0.0
    timeline_start = None
    timeline_end = None
    activity_progress_rows = []

    gantt_activities = []
    siteworks_group = None
    siteworks_tasks = []
    seen_siteworks = set()
    in_site_works = False
    for act in all_activities:
        if act.is_group:
            normalized_header = " ".join((act.name or "").lower().split())
            in_site_works = normalized_header == "site works"
            if in_site_works:
                siteworks_group = act
            continue

        if not in_site_works:
            continue
        if not act.quantity or act.quantity <= 0:
            continue

        order_index = get_siteworks_order_index(act.name)
        if order_index is None:
            continue

        dedupe_key = (order_index, normalize_activity_name(act.name))
        if dedupe_key in seen_siteworks:
            continue
        seen_siteworks.add(dedupe_key)
        siteworks_tasks.append((order_index, act.id, act))

    if siteworks_group:
        gantt_activities.append(siteworks_group)

    siteworks_tasks.sort(key=lambda item: (item[0], item[1]))
    gantt_activities.extend([item[2] for item in siteworks_tasks])

    previous_start_date = None
    for act in gantt_activities:
        if getattr(act, "is_group", False):
            group_anchor = project.start_date or act.start_date or timezone.localdate()
            gantt_data.append({
                "name": act.name,
                "start": group_anchor.isoformat(),
                "end": group_anchor.isoformat(),
                "required": 0,
                "actual": 0,
                "delay_status": "on_schedule",
                "delay_date": "",
                "is_group": True,
                "duration": 0,
                "quantity": act.quantity,
                "unit": act.unit,
            })
            continue

        display_name, indent_level = get_siteworks_display_name_and_indent(act.name)

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

        equipment_totals = act.equipment.aggregate(
            required=Sum("required"),
            quantity=Sum("quantity"),
            actual=Sum("actual"),
            latest_update=Max("actual_updated_at"),
        )
        required_equipment = equipment_totals["required"]
        if required_equipment is None:
            required_equipment = float(equipment_totals["quantity"] or 0)
        actual_equipment = float(equipment_totals["actual"] or 0)
        equipment_latest_update = equipment_totals["latest_update"]
        if equipment_latest_update and (not latest_update or equipment_latest_update > latest_update):
            latest_update = equipment_latest_update

        # Keep Act order and always follow the last visible activity start (+1 day),
        # so missing BOQ rows do not create timeline gaps.
        base_start_date = act.start_date or project.start_date or timezone.localdate()
        if previous_start_date:
            start_date = previous_start_date + timedelta(days=1)
        else:
            start_date = base_start_date

        task_span_days = 1

        if act.quantity and required_workers > 0 and start_date:
            task_span_days = compute_activity_duration(act, worker_count=required_workers)
        elif act.start_date and act.end_date:
            task_span_days = max(1, (act.end_date - act.start_date).days)

        end_date = start_date + timedelta(days=task_span_days)
        duration_days = task_span_days
        previous_start_date = start_date

        row_delay_status = "no_progress"
        row_delay_date = ""
        if start_date and end_date:
            timeline_start = min(timeline_start, start_date) if timeline_start else start_date
            timeline_end = max(timeline_end, end_date) if timeline_end else end_date

            task_days = max(1, (end_date - start_date).days)
            total_timeline_days += task_days

            actual_task_progress = get_activity_actual_progress(
                act,
                required_workers=required_workers,
                actual_workers=actual_workers,
            )
            weighted_actual_days += task_days * (actual_task_progress / 100.0)

            planned_task_progress = compute_planned_progress_for_date(
                start_date,
                end_date,
                timezone.localdate(),
            )
            progress_delay_key, progress_delay_label = get_progress_delay_status(
                planned_task_progress,
                actual_task_progress,
                manpower_required=required_workers,
                manpower_actual=actual_workers,
                equipment_required=required_equipment,
                equipment_actual=actual_equipment,
            )

            has_progress_update = bool(latest_update or act.progress_updated_at)
            if has_progress_update:
                row_delay_status = progress_delay_key
            else:
                row_delay_status = "no_progress"
                progress_delay_key = "no_progress"
                progress_delay_label = ""

            delay_date = ""
            if progress_delay_key in {"minor_delay", "significant_delay"} and latest_update:
                delay_date = latest_update.date().isoformat()
            row_delay_date = delay_date

            activity_progress_rows.append({
                "id": act.id,
                "name": display_name,
                "planned_progress": planned_task_progress,
                "actual_progress": actual_task_progress,
                "delay_status_key": progress_delay_key,
                "delay_status_label": progress_delay_label,
                "delay_date": delay_date,
                "progress_updated_at": latest_update,
                "required_manpower": required_workers,
                "actual_manpower": actual_workers,
                "required_equipment": round(required_equipment, 2),
                "actual_equipment": round(actual_equipment, 2),
            })

        # BUILD GANTT DATA
        if start_date and end_date:
            gantt_data.append({
                "name": display_name,
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
                "required": required_workers,
                "actual": actual_workers,
                "delay_status": row_delay_status,
                "delay_date": row_delay_date,
                "is_group": getattr(act, "is_group", False),
                "indent_level": indent_level,
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
    # Home-card expected progress should follow project contract dates first.
    progress_start = project.start_date or timeline_start
    progress_end = project.end_date or timeline_end
    if progress_start and progress_end:
        expected_progress = compute_planned_progress_for_date(
            progress_start,
            progress_end,
            today,
        )

    progress_status = "ON TIME"

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

    progress_status = get_progress_only_status(
        expected_progress,
        actual_progress,
    )

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
        "viewer_mode": viewer_mode,
        "viewer_link": viewer_link,
    }
    return context


@login_required
def project_detail(request, pk):
    project = get_project_for_user(request.user, pk=pk)
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

                raw_value = (value or "").strip()
                if raw_value == "":
                    continue

                try:
                    actual_value = float(raw_value)
                except (TypeError, ValueError):
                    continue

                existing_equipment = ActivityEquipment.objects.filter(
                    id=int(equipment_id),
                    activity__project=project
                ).only("actual", "actual_updated_at").first()
                if (
                    actual_value <= 0
                    and existing_equipment
                    and (existing_equipment.actual or 0) > 0
                ):
                    # Keep previously achieved progress; do not regress to zero on later entries.
                    continue

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

                raw_value = (value or "").strip()
                if raw_value == "":
                    continue

                try:
                    actual_value = int(raw_value)
                except (TypeError, ValueError):
                    continue

                existing_manpower = ActivityManpower.objects.filter(
                    id=int(manpower_id),
                    activity__project=project
                ).only("actual", "actual_updated_at").first()
                if (
                    actual_value <= 0
                    and existing_manpower
                    and (existing_manpower.actual or 0) > 0
                ):
                    # Keep previously achieved progress; do not regress to zero on later entries.
                    continue

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

    viewer_link = request.build_absolute_uri(
        reverse("project_viewer", kwargs={"pk": project.pk, "token": project.share_token})
    )
    context = build_project_detail_context(
        project=project,
        issue_log_form=issue_log_form,
        open_reports_modal=open_reports_modal,
        open_equipment_modal=open_equipment_modal,
        equipment_open_view=equipment_open_view,
        viewer_mode=False,
        viewer_link=viewer_link,
    )
 
    return render(request, "core/project_detail.html", context)


def project_viewer(request, pk, token):
    project = get_object_or_404(Project, pk=pk, share_token=token)
    if request.method == "POST":
        return redirect("project_viewer", pk=pk, token=token)

    issue_log_form = ProjectIssueLogForm()
    open_reports_modal = request.GET.get("modal") == "reports"
    context = build_project_detail_context(
        project=project,
        issue_log_form=issue_log_form,
        open_reports_modal=open_reports_modal,
        open_equipment_modal=False,
        equipment_open_view="settings",
        viewer_mode=True,
        viewer_link="",
    )

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


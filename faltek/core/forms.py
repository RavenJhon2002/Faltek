from django import forms
from .models import Project, ProjectIssueLog

class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = [
            "name",
            "project_type",
            "location",
            "description",
            "start_date",
        ]
        widgets = {
            "start_date": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
        }

class BOQUploadForm(forms.Form):
    file = forms.FileField(label="Upload BOQ Excel File")

    def clean_file(self):
        uploaded = self.cleaned_data["file"]
        filename = (uploaded.name or "").lower()
        allowed_extensions = (".xlsx", ".xlsm", ".xltx", ".xltm")
        if not filename.endswith(allowed_extensions):
            raise forms.ValidationError(
                "Upload a valid Excel workbook (.xlsx, .xlsm, .xltx, .xltm)."
            )
        return uploaded


class ProjectIssueLogForm(forms.ModelForm):
    class Meta:
        model = ProjectIssueLog
        fields = ["report_date", "short_description", "image"]
        widgets = {
            "report_date": forms.DateInput(attrs={"type": "date", "class": "issue-input"}),
            "short_description": forms.Textarea(
                attrs={
                    "class": "issue-textarea",
                    "rows": 6,
                    "placeholder": "Describe the issue...",
                }
            ),
            "image": forms.ClearableFileInput(attrs={"class": "issue-file-input", "accept": "image/*"}),
        }

    def clean_image(self):
        image = self.cleaned_data.get("image")
        if not image:
            return image

        content_type = getattr(image, "content_type", "")
        if not content_type.startswith("image/"):
            raise forms.ValidationError("Please upload a valid image file.")

        return image


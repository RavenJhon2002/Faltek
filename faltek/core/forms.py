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

        # Some browsers/devices do not send a reliable MIME type.
        content_type = (getattr(image, "content_type", "") or "").lower()
        filename = (getattr(image, "name", "") or "").lower()
        allowed_extensions = (
            ".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".heic", ".heif"
        )

        is_image_mime = content_type.startswith("image/")
        is_image_extension = filename.endswith(allowed_extensions)
        if not (is_image_mime or is_image_extension):
            raise forms.ValidationError(
                "Please upload a valid image file (jpg, jpeg, png, gif, webp, bmp, heic, heif)."
            )

        max_bytes = 10 * 1024 * 1024  # 10 MB
        if image.size > max_bytes:
            raise forms.ValidationError("Image is too large. Maximum size is 10 MB.")

        return image


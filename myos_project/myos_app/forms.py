from django import forms

from .models import BucketGoal


class BucketGoalForm(forms.ModelForm):
    class Meta:
        model = BucketGoal
        fields = [
            "title",
            "category",
            "description",
            "target_year",
            "estimated_cost",
            "status",
            "priority",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["status"].required = False
        self.fields["priority"].required = False
        self.fields["target_year"].required = False
        self.fields["estimated_cost"].required = False

    def clean(self):
        cleaned = super().clean()
        status = cleaned.get("status") or BucketGoal.STATUS_NOT_STARTED
        cleaned["status"] = status
        if not cleaned.get("priority"):
            cleaned["priority"] = BucketGoal.PRIORITY_NORMAL
        progress = cleaned.get("progress")
        if progress is None and self.instance and self.instance.pk:
            progress = self.instance.progress
        if status == BucketGoal.STATUS_COMPLETED:
            cleaned["progress"] = 100
        elif progress is None:
            cleaned["progress"] = 60 if status == BucketGoal.STATUS_IN_PROGRESS else 0
        else:
            cleaned["progress"] = max(0, min(100, progress))
        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)
        if "progress" in self.cleaned_data:
            instance.progress = self.cleaned_data["progress"]
        if commit:
            instance.save()
        return instance

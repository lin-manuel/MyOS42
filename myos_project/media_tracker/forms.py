from django import forms

from .models import MediaItem, MediaProgress


class MediaItemForm(forms.ModelForm):
    class Meta:
        model = MediaItem
        fields = [
            "title",
            "category",
            "type",
            "genre",
            "studio",
            "country",
            "year",
            "platform",
            "duration",
            "total_seasons",
            "total_episodes",
            "episode_duration",
            "status",
        ]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "genre": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Action, Drama"}),
            "studio": forms.TextInput(attrs={"class": "form-control"}),
            "country": forms.TextInput(attrs={"class": "form-control"}),
            "year": forms.NumberInput(attrs={"class": "form-control", "min": 1888, "max": 2200}),
            "platform": forms.TextInput(attrs={"class": "form-control"}),
            "duration": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            "total_seasons": forms.NumberInput(attrs={"class": "form-control", "min": 1}),
            "total_episodes": forms.NumberInput(attrs={"class": "form-control", "min": 1}),
            "episode_duration": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            "category": forms.Select(attrs={"class": "form-control"}),
            "type": forms.Select(attrs={"class": "form-control"}),
            "status": forms.Select(attrs={"class": "form-control"}),
        }

    def clean(self):
        cleaned_data = super().clean()
        media_type = cleaned_data.get("type")
        duration = cleaned_data.get("duration")
        total_episodes = cleaned_data.get("total_episodes") or 1
        episode_duration = cleaned_data.get("episode_duration")

        if media_type == MediaItem.MediaType.MOVIE:
            if not duration:
                self.add_error("duration", "Movie duration is required for movie entries.")
            cleaned_data["total_seasons"] = 1
            cleaned_data["total_episodes"] = 1
        else:
            if total_episodes < 1:
                self.add_error("total_episodes", "Series/anime entries must have at least one episode.")
            if not episode_duration:
                self.add_error("episode_duration", "Episode duration is required for series entries.")
        return cleaned_data


class MediaProgressForm(forms.ModelForm):
    class Meta:
        model = MediaProgress
        fields = [
            "episodes_watched",
            "current_season",
            "current_episode",
            "date_watched",
            "completed",
            "rating",
            "notes",
        ]
        widgets = {
            "episodes_watched": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            "current_season": forms.NumberInput(attrs={"class": "form-control", "min": 1}),
            "current_episode": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            "date_watched": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "completed": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "rating": forms.NumberInput(attrs={"class": "form-control", "min": 1, "max": 10}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

    def __init__(self, *args, media_item=None, **kwargs):
        self.media_item = media_item
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        media_item = self.media_item or getattr(self.instance, "media_item", None)
        if not media_item:
            return cleaned_data

        episodes_watched = cleaned_data.get("episodes_watched", 0) or 0
        current_episode = cleaned_data.get("current_episode", 0) or 0

        if media_item.type == MediaItem.MediaType.MOVIE:
            cleaned_data["episodes_watched"] = 1 if cleaned_data.get("completed") else min(episodes_watched, 1)
            cleaned_data["current_season"] = 1
            cleaned_data["current_episode"] = 1 if cleaned_data.get("completed") else min(current_episode, 1)
        else:
            total = media_item.total_episodes or 0
            if total and episodes_watched > total:
                self.add_error("episodes_watched", f"Episodes watched cannot exceed total episodes ({total}).")
        return cleaned_data


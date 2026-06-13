from apps.diary.models import DiaryEntry


class DiaryService:
    @staticmethod
    def search(user, query, limit=50, scan_limit=500):
        normalized = (query or "").strip().lower()
        if not normalized:
            return DiaryEntry.objects.none()

        matched_ids = []
        candidates = DiaryEntry.objects.filter(user=user).order_by("-date", "-created_at")[:scan_limit]
        for entry in candidates:
            content = (entry.content or "").lower()
            mood = (entry.mood or "").lower()
            if normalized in content or normalized in mood:
                matched_ids.append(entry.id)
            if len(matched_ids) >= limit:
                break

        if not matched_ids:
            return DiaryEntry.objects.none()
        return DiaryEntry.objects.filter(id__in=matched_ids).order_by("-date", "-created_at")

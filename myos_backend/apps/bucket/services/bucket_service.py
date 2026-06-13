from apps.bucket.models import BucketItem


class BucketService:
    @staticmethod
    def completion_rate(user):
        qs = BucketItem.objects.filter(category__user=user)
        total = qs.count()
        done = qs.filter(status=BucketItem.STATUS_COMPLETED).count()
        return int((done / total) * 100) if total else 0

    @staticmethod
    def goals_per_year(user):
        rows = {}
        for item in BucketItem.objects.filter(category__user=user, target_date__isnull=False):
            year = item.target_date.year
            rows[year] = rows.get(year, 0) + 1
        return [{"year": year, "count": count} for year, count in sorted(rows.items())]

from .services.bucket_service import BucketService


def completion_rate(user):
    return BucketService.completion_rate(user)


def goals_per_year(user):
    return BucketService.goals_per_year(user)

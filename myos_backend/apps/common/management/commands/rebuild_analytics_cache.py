from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from apps.api.tasks import warm_dashboard_cache_for_user


class Command(BaseCommand):
    help = "Warm cached dashboard analytics for one user or the entire user base."

    def add_arguments(self, parser):
        parser.add_argument("--email", dest="email")

    def handle(self, *args, **options):
        users = get_user_model().objects.all()
        if options["email"]:
            users = users.filter(email=options["email"])
        total = 0
        for user in users.iterator():
            warm_dashboard_cache_for_user(user.pk)
            total += 1
        self.stdout.write(self.style.SUCCESS(f"Warmed analytics cache for {total} user(s)."))

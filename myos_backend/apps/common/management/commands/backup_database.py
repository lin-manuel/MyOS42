from pathlib import Path
import shutil

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Backup the local SQLite database to the provided file path."

    def add_arguments(self, parser):
        parser.add_argument("destination")

    def handle(self, *args, **options):
        database_name = settings.DATABASES["default"]["NAME"]
        if not str(database_name).endswith(".sqlite3"):
            raise CommandError("This command only supports SQLite backups.")
        source = Path(database_name)
        destination = Path(options["destination"])
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        self.stdout.write(f"Backed up {source} to {destination}")

from pathlib import Path
import shutil

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Restore the local SQLite database from the provided file path."

    def add_arguments(self, parser):
        parser.add_argument("source")

    def handle(self, *args, **options):
        database_name = settings.DATABASES["default"]["NAME"]
        if not str(database_name).endswith(".sqlite3"):
            raise CommandError("This command only supports SQLite restores.")
        source = Path(options["source"])
        if not source.exists():
            raise CommandError("Source backup does not exist.")
        shutil.copy2(source, Path(database_name))
        self.stdout.write(f"Restored database from {source}")

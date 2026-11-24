from datetime import date

from django.core.management.base import BaseCommand, CommandError

from apps.datasets.services.open_meteo_import import (
    OpenMeteoImportError,
    import_open_meteo_period,
)


class Command(BaseCommand):
    help = (
        "Idempotently import Open-Meteo archive daily mean temperature and "
        "humidity for a city-level area."
    )

    def add_arguments(self, parser):
        parser.add_argument("--area-id", type=int, default=1)
        parser.add_argument("--source-id", type=int)
        parser.add_argument("--date", help="Single ISO date YYYY-MM-DD")
        parser.add_argument("--start-date", help="Inclusive ISO start date")
        parser.add_argument("--end-date", help="Inclusive ISO end date")
        parser.add_argument("--latitude", type=float)
        parser.add_argument("--longitude", type=float)
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        try:
            if options["date"]:
                period_start = date.fromisoformat(options["date"])
                period_end = period_start
            else:
                if not options["start_date"] or not options["end_date"]:
                    raise CommandError(
                        "Provide --date or both --start-date and --end-date."
                    )
                period_start = date.fromisoformat(options["start_date"])
                period_end = date.fromisoformat(options["end_date"])
        except ValueError as error:
            raise CommandError("Dates must use YYYY-MM-DD.") from error
        try:
            summary = import_open_meteo_period(
                area_id=options["area_id"],
                period_start=period_start,
                period_end=period_end,
                latitude=options["latitude"],
                longitude=options["longitude"],
                source_id=options["source_id"],
                dry_run=options["dry_run"],
            )
        except OpenMeteoImportError as error:
            raise CommandError(str(error)) from error
        self.stdout.write(str(summary))

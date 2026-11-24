from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.cities.coordinates import MEERUT_CITY_POINT
from apps.cities.models import Area


class Command(BaseCommand):
    help = (
        "Set a documented representative city-level coordinate. Does not invent "
        "polygons or overwrite a different documented point unless --replace is set."
    )

    def add_arguments(self, parser):
        parser.add_argument("--area-id", type=int, default=1)
        parser.add_argument(
            "--replace",
            action="store_true",
            help="Replace existing coordinates with the documented Nominatim point.",
        )

    def handle(self, *args, **options):
        area = Area.objects.select_related("city").filter(pk=options["area_id"]).first()
        if area is None:
            raise CommandError("Area does not exist.")
        if area.city.name != "Meerut" or area.area_type != "city":
            raise CommandError(
                "This command currently documents the Meerut city-level Nominatim point only."
            )
        point = MEERUT_CITY_POINT
        if (
            area.latitude is not None
            and area.longitude is not None
            and not options["replace"]
            and (area.latitude, area.longitude)
            == (point["latitude"], point["longitude"])
        ):
            self.stdout.write("Documented Nominatim point is already stored.")
            return
        if (
            area.latitude is not None
            and area.longitude is not None
            and not options["replace"]
        ):
            self.stdout.write(
                "Existing coordinates "
                f"{area.latitude},{area.longitude} were left unchanged. "
                "Re-run with --replace to store the documented Nominatim city point "
                f"{point['latitude']},{point['longitude']}."
            )
            return
        with transaction.atomic():
            area.latitude = point["latitude"]
            area.longitude = point["longitude"]
            area.save()
        self.stdout.write(
            self.style.SUCCESS(
                f"Stored {area.area_name} representative point "
                f"{point['latitude']},{point['longitude']} from {point['source_name']} "
                f"(retrieved {point['retrieved_on']}; OSM id {point['osm_id']}). "
                f"{point['limitation']}"
            )
        )

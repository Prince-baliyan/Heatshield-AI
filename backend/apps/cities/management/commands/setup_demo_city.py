from django.core.management.base import BaseCommand
from django.db import transaction

from apps.cities.models import Area, City


class Command(BaseCommand):
    help = "Create or reuse the safe Meerut city-level demo configuration."

    def handle(self, *args, **options):
        with transaction.atomic():
            city, city_created = City.objects.get_or_create(
                name="Meerut",
                state_name="Uttar Pradesh",
                country_code="IN",
                defaults={"status": "ACTIVE"},
            )

            if city.status == "":
                city.status = "ACTIVE"
                city.save(update_fields=["status"])

            city.full_clean()

            area, area_created = Area.objects.get_or_create(
                city=city,
                area_name="Meerut City",
                defaults={
                    "area_code": None,
                    "area_type": "city",
                    "latitude": None,
                    "longitude": None,
                },
            )
            area.full_clean()

            if not area_created and area.area_type != "city":
                raise ValueError(
                    "Existing Meerut City area is not configured as a city-level area."
                )

        self.stdout.write(
            self.style.SUCCESS(
                "Demo configuration ready: Meerut / Meerut City "
                f"(city {'created' if city_created else 'existing'}, "
                f"area {'created' if area_created else 'existing'})."
            )
        )

from django.core.exceptions import ValidationError
from django.core.management import call_command
from decimal import Decimal
from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.indicators.models import IndicatorObservation
from .models import Area, City


class CityModelTests(SimpleTestCase):
    def test_str_and_clean_normalize_identity(self):
        city = City(
            name=" Meerut ",
            state_name=" Uttar Pradesh ",
            country_code="in",
            status="ACTIVE",
        )
        city.clean()

        self.assertEqual(str(city), "Meerut, Uttar Pradesh")
        self.assertEqual(city.country_code, "IN")

    def test_invalid_latitude_is_rejected(self):
        city = City(name="Meerut", state_name="Uttar Pradesh", country_code="IN")
        area = Area(city=city, area_name="Meerut city level", latitude=91)

        with self.assertRaises(ValidationError):
            area.clean()

    def test_city_area_type_is_accepted(self):
        area = Area(area_name="Meerut city level", area_type="city")
        area.clean()
        self.assertEqual(area.area_type, "city")

    def test_ward_area_type_is_accepted(self):
        area = Area(area_name="Verified ward", area_type="ward")
        area.clean()
        self.assertEqual(area.area_type, "ward")

    def test_unknown_area_type_is_rejected_by_clean(self):
        area = Area(area_name="Unknown unit", area_type="district")

        with self.assertRaises(ValidationError):
            area.clean()

    def test_unknown_area_type_is_rejected_by_save(self):
        area = Area(area_name="Unknown unit", area_type="district")

        with self.assertRaises(ValidationError):
            area.save()

    def test_longitude_range_is_rejected(self):
        area = Area(area_name="Meerut city level", longitude=181)

        with self.assertRaises(ValidationError):
            area.clean()

    def test_area_save_enforces_latitude_range(self):
        city = City(
            name="Meerut",
            state_name="Uttar Pradesh",
            country_code="IN",
            status="ACTIVE",
        )
        area = Area(
            city=city,
            area_name="Meerut City",
            area_type="city",
            latitude=Decimal("91"),
        )

        with self.assertRaises(ValidationError):
            area.save()


class CityDatabaseTests(TestCase):
    def test_city_identity_is_unique(self):
        City.objects.create(
            name="Meerut",
            state_name="Uttar Pradesh",
            country_code="IN",
            status="ACTIVE",
        )

        with self.assertRaises(ValidationError) as error:
            City.objects.create(
                name="Meerut",
                state_name="Uttar Pradesh",
                country_code="IN",
                status="ACTIVE",
            )

        self.assertIn("__all__", error.exception.message_dict)

    def test_city_save_requires_status(self):
        city = City(
            name="Meerut",
            state_name="Uttar Pradesh",
            country_code="IN",
            status=" ",
        )

        with self.assertRaises(ValidationError) as error:
            city.save()

        self.assertIn("status", error.exception.message_dict)


class DemoCitySetupTests(TestCase):
    def test_initial_setup_creates_city_and_city_level_area(self):
        call_command("setup_demo_city")

        city = City.objects.get(name="Meerut", state_name="Uttar Pradesh")
        area = Area.objects.get(city=city, area_name="Meerut City")

        self.assertEqual(city.country_code, "IN")
        self.assertEqual(city.status, "ACTIVE")
        self.assertEqual(area.area_type, "city")
        self.assertIsNone(area.area_code)
        self.assertIsNone(area.latitude)
        self.assertIsNone(area.longitude)

    def test_repeated_setup_does_not_create_duplicates(self):
        call_command("setup_demo_city")
        call_command("setup_demo_city")

        self.assertEqual(City.objects.filter(name="Meerut").count(), 1)
        self.assertEqual(
            Area.objects.filter(city__name="Meerut", area_name="Meerut City").count(),
            1,
        )

    def test_setup_does_not_overwrite_existing_city_or_area(self):
        city = City.objects.create(
            name="Meerut",
            state_name="Uttar Pradesh",
            country_code="IN",
            status="CUSTOM_STATUS",
        )
        area = Area.objects.create(
            city=city,
            area_name="Meerut City",
            area_type="city",
        )

        call_command("setup_demo_city")

        city.refresh_from_db()
        area.refresh_from_db()
        self.assertEqual(city.status, "CUSTOM_STATUS")
        self.assertEqual(area.area_type, "city")
        self.assertEqual(City.objects.count(), 1)
        self.assertEqual(Area.objects.count(), 1)

    def test_setup_creates_no_ward_or_observation_records(self):
        call_command("setup_demo_city")

        self.assertFalse(Area.objects.filter(area_type="ward").exists())
        self.assertFalse(IndicatorObservation.objects.exists())

    def test_setup_does_not_replace_an_existing_ward_named_meerut_city(self):
        city = City.objects.create(
            name="Meerut",
            state_name="Uttar Pradesh",
            country_code="IN",
            status="ACTIVE",
        )
        Area.objects.create(
            city=city,
            area_name="Meerut City",
            area_type="ward",
        )

        with self.assertRaises(ValueError):
            call_command("setup_demo_city")

        self.assertEqual(Area.objects.filter(area_type="ward").count(), 1)


class CityAreaAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.city = City.objects.create(
            name="Meerut",
            state_name="Uttar Pradesh",
            country_code="IN",
            status="ACTIVE",
        )
        self.area = Area.objects.create(
            city=self.city,
            area_name="Meerut City",
            area_type="city",
        )

    def test_city_list_success(self):
        response = self.client.get(reverse("city-list"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["name"], "Meerut")
        self.assertEqual(response.data["results"][0]["country_code"], "IN")

    def test_city_list_empty_database(self):
        Area.objects.all().delete()
        City.objects.all().delete()

        response = self.client.get(reverse("city-list"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 0)
        self.assertEqual(response.data["results"], [])

    def test_area_list_success_and_city_filter(self):
        response = self.client.get(
            reverse("area-list"),
            {"city_id": self.city.pk},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["area_name"], "Meerut City")
        self.assertEqual(response.data["results"][0]["city_id"], self.city.pk)
        self.assertEqual(response.data["results"][0]["city"]["name"], "Meerut")
        self.assertIn("assessment_ready", response.data["results"][0])
        self.assertIn("readiness_status", response.data["results"][0])
        self.assertIn("readiness_reasons", response.data["results"][0])

    def test_area_detail_success(self):
        response = self.client.get(reverse("area-detail", kwargs={"pk": self.area.pk}))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], self.area.pk)
        self.assertEqual(response.data["area_name"], "Meerut City")
        self.assertIn("assessment_ready", response.data)
        self.assertIn("readiness_status", response.data)
        self.assertIn("geometry_limitation", response.data)

    def test_area_detail_not_found(self):
        response = self.client.get(reverse("area-detail", kwargs={"pk": 999999}))

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data["error"]["code"], "AREA_NOT_FOUND")

    def test_area_list_empty_for_existing_city(self):
        Area.objects.all().delete()

        response = self.client.get(
            reverse("area-list"),
            {"city_id": self.city.pk},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 0)
        self.assertEqual(response.data["results"], [])

    def test_city_specific_area_list_empty_for_existing_city(self):
        Area.objects.all().delete()

        response = self.client.get(
            reverse("city-area-list", kwargs={"city_id": self.city.pk})
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 0)
        self.assertEqual(response.data["results"], [])

    def test_city_and_area_lists_support_pagination(self):
        for index in range(21):
            city = City.objects.create(
                name=f"City {index}",
                state_name="Test State",
                country_code="IN",
                status="ACTIVE",
            )
            Area.objects.create(
                city=city,
                area_name=f"Area {index}",
                area_type="city",
            )

        city_response = self.client.get(reverse("city-list"), {"page_size": 1})
        area_response = self.client.get(reverse("area-list"), {"page_size": 1})

        self.assertEqual(city_response.status_code, 200)
        self.assertEqual(city_response.data["count"], 22)
        self.assertEqual(len(city_response.data["results"]), 1)
        self.assertIsNotNone(city_response.data["next"])

        self.assertEqual(area_response.status_code, 200)
        self.assertEqual(area_response.data["count"], 22)
        self.assertEqual(len(area_response.data["results"]), 1)
        self.assertIsNotNone(area_response.data["next"])

    def test_city_area_list_unknown_city_returns_404(self):
        response = self.client.get(
            reverse("city-area-list", kwargs={"city_id": 999999})
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data["error"]["code"], "CITY_NOT_FOUND")

    def test_invalid_city_filter_is_rejected(self):
        response = self.client.get(
            reverse("area-list"),
            {"city_id": "invalid"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["error"]["code"], "INVALID_CITY_ID")

    def test_inactive_cities_and_their_areas_are_not_listed(self):
        inactive_city = City.objects.create(
            name="Inactive City",
            state_name="Test State",
            country_code="IN",
            status="INACTIVE",
        )
        Area.objects.create(
            city=inactive_city,
            area_name="Inactive Area",
            area_type="city",
        )

        city_response = self.client.get(reverse("city-list"))
        area_response = self.client.get(reverse("area-list"))
        city_area_response = self.client.get(
            reverse("city-area-list", kwargs={"city_id": inactive_city.pk})
        )

        self.assertEqual(city_response.data["count"], 1)
        self.assertNotIn(
            "Inactive City",
            [item["name"] for item in city_response.data["results"]],
        )
        self.assertEqual(area_response.data["count"], 1)
        self.assertNotIn(
            "Inactive Area",
            [item["area_name"] for item in area_response.data["results"]],
        )
        self.assertEqual(city_area_response.status_code, 404)

    def test_city_and_area_endpoints_are_read_only(self):
        for url in (
            reverse("city-list"),
            reverse("area-list"),
            reverse("city-area-list", kwargs={"city_id": self.city.pk}),
        ):
            post_response = self.client.post(url, {}, format="json")
            self.assertEqual(post_response.status_code, 405)


class SetAreaRepresentativePointCommandTests(TestCase):
    def setUp(self):
        self.city = City.objects.create(
            name="Meerut",
            state_name="Uttar Pradesh",
            country_code="IN",
            status="ACTIVE",
        )
        self.area = Area.objects.create(
            city=self.city,
            area_name="Meerut City",
            area_type="city",
        )

    def test_command_sets_documented_nominatim_coordinates(self):
        from apps.cities.coordinates import MEERUT_CITY_POINT

        call_command("set_area_representative_point", area_id=self.area.pk)

        self.area.refresh_from_db()
        self.assertEqual(self.area.latitude, MEERUT_CITY_POINT["latitude"])
        self.assertEqual(self.area.longitude, MEERUT_CITY_POINT["longitude"])

    def test_command_does_not_overwrite_different_coordinates_without_replace(self):
        self.area.latitude = Decimal("28.123456")
        self.area.longitude = Decimal("77.123456")
        self.area.save()

        call_command("set_area_representative_point", area_id=self.area.pk)

        self.area.refresh_from_db()
        self.assertEqual(self.area.latitude, Decimal("28.123456"))
        self.assertEqual(self.area.longitude, Decimal("77.123456"))

    def test_command_overwrites_coordinates_with_replace_flag(self):
        from apps.cities.coordinates import MEERUT_CITY_POINT

        self.area.latitude = Decimal("28.123456")
        self.area.longitude = Decimal("77.123456")
        self.area.save()

        call_command("set_area_representative_point", area_id=self.area.pk, replace=True)

        self.area.refresh_from_db()
        self.assertEqual(self.area.latitude, MEERUT_CITY_POINT["latitude"])
        self.assertEqual(self.area.longitude, MEERUT_CITY_POINT["longitude"])

    def test_command_rejects_non_meerut_city(self):
        other_city = City.objects.create(
            name="Agra",
            state_name="Uttar Pradesh",
            country_code="IN",
            status="ACTIVE",
        )
        other_area = Area.objects.create(
            city=other_city,
            area_name="Agra City",
            area_type="city",
        )

        with self.assertRaises(Exception):
            call_command("set_area_representative_point", area_id=other_area.pk)


class AreaComparisonAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.city = City.objects.create(
            name="Meerut",
            state_name="Uttar Pradesh",
            country_code="IN",
            status="ACTIVE",
        )
        self.area1 = Area.objects.create(
            city=self.city,
            area_name="Meerut City",
            area_type="city",
            latitude=Decimal("28.996330"),
            longitude=Decimal("77.706192"),
        )
        self.area2 = Area.objects.create(
            city=self.city,
            area_name="Meerut Cantt",
            area_type="city",
            latitude=Decimal("28.990000"),
            longitude=Decimal("77.700000"),
        )

    def test_successful_area_comparison_with_comma_separated_ids(self):
        response = self.client.get(
            reverse("area-compare"),
            {"area_ids": f"{self.area1.pk},{self.area2.pk}"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["comparison_count"], 2)
        self.assertEqual(len(response.data["results"]), 2)
        self.assertIn("caveats", response.data)

    def test_successful_area_comparison_with_multiple_params(self):
        response = self.client.get(
            f"{reverse('area-compare')}?area_id={self.area1.pk}&area_id={self.area2.pk}"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["comparison_count"], 2)

    def test_fewer_than_two_distinct_areas_returns_400(self):
        response = self.client.get(
            reverse("area-compare"),
            {"area_ids": f"{self.area1.pk}"},
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["error"]["code"], "INVALID_COMPARISON_REQUEST")

        duplicate_response = self.client.get(
            reverse("area-compare"),
            {"area_ids": f"{self.area1.pk},{self.area1.pk}"},
        )
        self.assertEqual(duplicate_response.status_code, 400)

    def test_invalid_area_id_format_returns_400(self):
        response = self.client.get(
            reverse("area-compare"),
            {"area_ids": f"{self.area1.pk},invalid"},
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["error"]["code"], "INVALID_COMPARISON_REQUEST")

    def test_unknown_area_id_returns_404(self):
        response = self.client.get(
            reverse("area-compare"),
            {"area_ids": f"{self.area1.pk},999999"},
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data["error"]["code"], "AREA_NOT_FOUND")

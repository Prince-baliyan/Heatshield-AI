from datetime import date, datetime
import json

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.test import SimpleTestCase, TestCase
from rest_framework.test import APIClient
from django.urls import reverse
from django.utils import timezone
from unittest.mock import patch, MagicMock

from apps.cities.models import Area, City
from apps.indicators.models import IndicatorObservation
from .models import DataSource, Dataset
from .providers.factory import get_weather_provider


class DatasetModelTests(SimpleTestCase):
    def test_demo_scenarios_return_their_curated_synthetic_values(self):
        expected = {
            "hot_dry": (42.0, 25.0, 0.0),
            "hot_humid": (39.0, 80.0, 2.0),
            "moderate": (28.0, 55.0, 5.0),
            "heavy_rainfall": (26.0, 90.0, 45.0),
        }
        provider = get_weather_provider("demo")

        for scenario_id, values in expected.items():
            with self.subTest(scenario=scenario_id):
                response = provider.fetch_weather("Meerut", scenario_id=scenario_id)
                observations = {
                    item["indicator_code"]: item
                    for item in response["observations"]
                }
                self.assertEqual(response["scenario_id"], scenario_id)
                self.assertEqual(response["data_class"], "illustrative")
                self.assertEqual(
                    (
                        observations["AIR_TEMPERATURE"]["value"],
                        observations["RELATIVE_HUMIDITY"]["value"],
                        observations["RAINFALL_24H"]["value"],
                    ),
                    values,
                )
                self.assertIn("Synthetic Demonstration", response["source"])

    def test_demo_provider_rejects_unknown_scenario(self):
        with self.assertRaisesRegex(ValueError, "Unsupported illustrative"):
            get_weather_provider("demo").fetch_weather(
                "Meerut",
                scenario_id="not-a-scenario",
            )

    def test_illustrative_dataset_str(self):
        dataset = Dataset(
            dataset_name="Meerut demo weather",
            data_class="illustrative",
        )

        self.assertEqual(str(dataset), "Meerut demo weather (illustrative)")

    def test_coverage_end_before_start_is_rejected(self):
        dataset = Dataset(
            dataset_name="Weather",
            data_class="observed",
            spatial_resolution="city",
            coverage_start="2026-11-22",
            coverage_end="2026-11-21",
        )

        with self.assertRaises(ValidationError):
            dataset.clean()

    def test_missing_data_is_distinct_from_zero(self):
        dataset = Dataset(
            dataset_name="Weather",
            data_class="observed",
            spatial_resolution="city",
        )
        self.assertIsNone(dataset.published_at)
        self.assertIsNone(dataset.coverage_start)

    def test_illustrative_data_class_is_allowed(self):
        dataset = Dataset(
            dataset_name="Illustrative weather",
            data_class="illustrative",
            spatial_resolution="illustrative_city_level",
            is_active=False,
        )
        dataset.clean()
        self.assertFalse(dataset.is_active)

    def test_datasource_save_enforces_required_names(self):
        source = DataSource(source_name=" ", owner_name="Owner")

        with self.assertRaises(ValidationError) as error:
            source.save()

        self.assertIn("source_name", error.exception.message_dict)

    def test_dataset_save_enforces_required_metadata(self):
        dataset = Dataset(
            dataset_name=" ",
            data_class="observed",
            spatial_resolution="city",
        )

        with self.assertRaises(ValidationError) as error:
            dataset.save()

        self.assertIn("dataset_name", error.exception.message_dict)

    def test_imd_provider_selection_is_explicitly_unavailable(self):
        with self.assertRaisesRegex(
            ValueError,
            "IMD weather provider is not implemented",
        ):
            get_weather_provider("imd")

    def test_demo_provider_is_curated_labelled_and_timestamped(self):
        response = get_weather_provider("demo").fetch_weather("Meerut")
        observations = {
            item["indicator_code"]: item for item in response["observations"]
        }

        self.assertEqual(response["data_class"], "illustrative")
        self.assertEqual(response["quality_status"], "ILLUSTRATIVE_NOT_OBSERVED")
        self.assertIn("Illustrative", response["source"])
        self.assertIsNotNone(datetime.fromisoformat(response["retrieved_at"]).tzinfo)
        self.assertEqual(observations["AIR_TEMPERATURE"]["value"], 38.0)
        self.assertEqual(observations["AIR_TEMPERATURE"]["unit"], "degree_celsius")
        self.assertEqual(
            observations["RELATIVE_HUMIDITY"]["measurement_period"],
            "illustrative_instantaneous_sample",
        )
        self.assertEqual(observations["RAINFALL_24H"]["value"], 0.0)
        self.assertEqual(observations["RAINFALL_24H"]["unit"], "mm")
        self.assertEqual(
            observations["RAINFALL_24H"]["measurement_period"],
            "illustrative_24h_sample",
        )


class WeatherDataAPITests(SimpleTestCase):
    def test_weather_endpoint_accepts_validated_demo_scenario(self):
        response = APIClient().get(
            reverse("weather-data"),
            {"location": "Meerut", "scenario": "hot_humid"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["scenario_id"], "hot_humid")
        self.assertEqual(
            [
                item["value"]
                for item in response.data["observations"]
            ],
            [39.0, 80.0, 2.0],
        )

    def test_weather_endpoint_rejects_unknown_demo_scenario(self):
        response = APIClient().get(
            reverse("weather-data"),
            {"location": "Meerut", "scenario": "unknown"},
        )
        self.assertEqual(response.status_code, 400)

    def test_unimplemented_imd_provider_returns_400(self):
        client = APIClient()

        with patch(
            "apps.datasets.views.get_weather_provider",
            side_effect=ValueError(
                "The IMD weather provider is not implemented."
            ),
        ):
            response = client.get(
                reverse("weather-data"),
                {"location": "Meerut"},
            )

        self.assertEqual(response.status_code, 400)
        self.assertIn("not implemented", response.data["error"])


class InventoryReadOnlyAPITests(TestCase):
    def setUp(self):
        self.username = "inventory-reader"
        self.password = "test-only-password"
        user = get_user_model().objects.create_user(
            username=self.username,
            password=self.password,
        )
        self.client = APIClient()
        self.client.force_authenticate(user=user)

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
        self.source = DataSource.objects.create(
            source_name="Test source",
            owner_name="Test owner",
            official_url="https://example.test/source",
            licence_terms="Internal test terms",
            approval_status="APPROVED",
        )
        self.dataset = Dataset.objects.create(
            source=self.source,
            dataset_name="Test weather dataset",
            data_class="illustrative",
            spatial_resolution="illustrative_city_level",
            retrieved_at=timezone.now(),
            file_hash="test-hash",
            transformation_notes="Internal test notes",
            is_active=True,
        )
        self.observation = IndicatorObservation.objects.create(
            area=self.area,
            dataset=self.dataset,
            indicator_code="RAINFALL_24H",
            period_start="2026-11-24",
            period_end="2026-11-24",
            raw_value_numeric="0",
            raw_unit="mm",
            quality_status="VALID",
            notes="Internal test notes",
        )

    def test_inventory_endpoints_require_an_authenticated_session(self):
        anonymous_client = APIClient()
        for endpoint in (
            "data-source-list",
            "dataset-list",
            "indicator-observation-list",
        ):
            with self.subTest(endpoint=endpoint):
                self.assertEqual(
                    anonymous_client.get(reverse(endpoint)).status_code,
                    401,
                )

    def test_list_endpoints_return_paginated_inventory_without_internal_fields(self):
        source_response = self.client.get(reverse("data-source-list"))
        dataset_response = self.client.get(reverse("dataset-list"))
        observation_response = self.client.get(
            reverse("indicator-observation-list")
        )

        self.assertEqual(source_response.status_code, 200)
        self.assertEqual(source_response.data["count"], 1)
        source = source_response.data["results"][0]
        self.assertEqual(source["source_name"], "Test source")
        self.assertEqual(source["dataset_count"], 1)
        self.assertNotIn("official_url", source)
        self.assertNotIn("licence_terms", source)

        self.assertEqual(dataset_response.status_code, 200)
        self.assertEqual(dataset_response.data["count"], 1)
        dataset = dataset_response.data["results"][0]
        self.assertEqual(dataset["source_name"], "Test source")
        self.assertEqual(dataset["data_class"], "illustrative")
        self.assertNotIn("file_hash", dataset)
        self.assertNotIn("transformation_notes", dataset)

        self.assertEqual(observation_response.status_code, 200)
        self.assertEqual(observation_response.data["count"], 1)
        observation = observation_response.data["results"][0]
        self.assertEqual(observation["area_name"], "Meerut City")
        self.assertEqual(observation["city_name"], "Meerut")
        self.assertEqual(str(observation["raw_value_numeric"]), "0.000000")
        self.assertEqual(observation["quality_status"], "VALID")
        self.assertNotIn("notes", observation)


class AdminDataManagementAPITests(TestCase):
    def setUp(self):
        self.username = "data-admin"
        self.password = "test-only-password"
        self.client = APIClient()
        self.student = get_user_model().objects.create_user(
            username="data-student",
            password="student-test-password",
        )
        self.admin = get_user_model().objects.create_user(
            username="data-admin",
            password="admin-test-password",
            is_staff=True,
        )
        city = City.objects.create(
            name="Meerut",
            state_name="Uttar Pradesh",
            country_code="IN",
            status="ACTIVE",
        )
        self.area = Area.objects.create(
            city=city,
            area_name="Meerut City",
            area_type="city",
        )
        self.admin.set_password(self.password)
        self.admin.save(update_fields=["password"])

    def create_observation_dataset(
        self,
        *,
        approval_status="APPROVED",
        is_active=True,
        spatial_resolution="city",
        data_class="derived",
    ):
        source = DataSource.objects.create(
            source_name=f"Source {approval_status} {is_active}",
            owner_name="Test owner",
            approval_status=approval_status,
        )
        return Dataset.objects.create(
            source=source,
            dataset_name=f"Dataset {approval_status} {is_active}",
            data_class=data_class,
            spatial_resolution=spatial_resolution,
            retrieved_at=timezone.now(),
            is_active=is_active,
        )

    def observation_payload(self, dataset, **overrides):
        payload = {
            "area": self.area.pk,
            "dataset": dataset.pk,
            "indicator_code": "AIR_TEMPERATURE",
            "period_start": "2026-11-24",
            "period_end": "2026-11-24",
            "raw_value_numeric": "34.5",
            "raw_value_text": None,
            "raw_unit": "degree_celsius",
            "quality_status": "VALID",
            "notes": "Test provenance",
        }
        payload.update(overrides)
        return payload

    def test_anonymous_requests_receive_401_and_student_writes_receive_403(self):
        endpoints = (
            "admin-data-source-list",
            "admin-dataset-list",
            "admin-observation-list",
            "admin-area-list",
        )
        for endpoint in endpoints:
            with self.subTest(endpoint=endpoint):
                self.assertEqual(
                    APIClient().get(reverse(endpoint)).status_code,
                    401,
                )

        self.client.force_authenticate(self.student)
        response = self.client.post(
            reverse("admin-data-source-list"),
            {
                "source_name": "Student write",
                "owner_name": "Student",
                "approval_status": "PENDING",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(DataSource.objects.filter(source_name="Student write").exists())

    def test_students_cannot_read_or_write_admin_endpoints(self):
        source = DataSource.objects.create(
            source_name="Approved source",
            owner_name="Owner",
            approval_status="APPROVED",
        )
        dataset = Dataset.objects.create(
            source=source,
            dataset_name="Approved dataset",
            data_class="observed",
            spatial_resolution="city",
            retrieved_at=timezone.now(),
            is_active=True,
        )
        observation = IndicatorObservation.objects.create(
            area=self.area,
            dataset=dataset,
            indicator_code="AIR_TEMPERATURE",
            period_start="2026-11-23",
            period_end="2026-11-23",
            raw_value_numeric="32",
            raw_unit="degree_celsius",
            quality_status="VALID",
        )
        self.client.force_authenticate(self.student)
        endpoints = (
            ("admin-data-source-list", {}),
            ("admin-data-source-detail", {"pk": source.pk}),
            ("admin-dataset-list", {}),
            ("admin-dataset-detail", {"pk": dataset.pk}),
            ("admin-observation-list", {}),
            ("admin-observation-detail", {"pk": observation.pk}),
        )

        for endpoint, kwargs in endpoints:
            with self.subTest(endpoint=endpoint, action="get"):
                self.assertEqual(
                    self.client.get(reverse(endpoint, kwargs=kwargs)).status_code,
                    403,
                )
            with self.subTest(endpoint=endpoint, action="write"):
                response = self.client.patch(
                    reverse(endpoint, kwargs=kwargs) if kwargs else reverse(endpoint),
                    {"source_name": "Student changed data"},
                    format="json",
                )
                self.assertEqual(response.status_code, 403)

    def test_admin_can_create_update_source_dataset_and_observation(self):
        self.client.force_authenticate(self.admin)
        source_response = self.client.post(
            reverse("admin-data-source-list"),
            {
                "source_name": "City Environmental Office",
                "owner_name": "Municipal Corporation",
                "official_url": "https://data.example.test",
                "licence_terms": "Public release",
                "approval_status": "PENDING",
            },
            format="json",
        )
        self.assertEqual(source_response.status_code, 201, source_response.data)
        source_id = source_response.data["id"]
        source_detail = reverse("admin-data-source-detail", kwargs={"pk": source_id})
        updated_source = self.client.patch(
            source_detail,
            {"approval_status": "APPROVED"},
            format="json",
        )
        self.assertEqual(updated_source.status_code, 200)
        self.assertEqual(updated_source.data["licence_terms"], "Public release")

        dataset_response = self.client.post(
            reverse("admin-dataset-list"),
            {
                "source": source_id,
                "dataset_name": "Daily air observations",
                "data_class": "observed",
                "spatial_resolution": "city",
                "retrieved_at": "2026-11-24T08:00:00+05:30",
                "is_active": True,
            },
            format="json",
        )
        self.assertEqual(dataset_response.status_code, 201, dataset_response.data)
        dataset_id = dataset_response.data["id"]
        dataset_detail = reverse("admin-dataset-detail", kwargs={"pk": dataset_id})
        observation_response = self.client.post(
            reverse("admin-observation-list"),
            {
                "area": self.area.pk,
                "dataset": dataset_id,
                "indicator_code": "AIR_TEMPERATURE",
                "period_start": "2026-11-23",
                "period_end": "2026-11-24",
                "raw_value_numeric": "34.5",
                "raw_unit": "degree_celsius",
                "quality_status": "VALID",
                "notes": "Entered by administrator",
            },
            format="json",
        )
        self.assertEqual(observation_response.status_code, 201, observation_response.data)
        observation_id = observation_response.data["id"]
        updated_observation = self.client.patch(
            reverse("admin-observation-detail", kwargs={"pk": observation_id}),
            {"raw_value_numeric": "35.0"},
            format="json",
        )
        self.assertEqual(updated_observation.status_code, 200)
        self.assertEqual(updated_observation.data["raw_value_numeric"], "35.000000")
        updated_dataset = self.client.patch(
            dataset_detail,
            {"is_active": False},
            format="json",
        )
        self.assertEqual(updated_dataset.status_code, 200)
        self.assertFalse(updated_dataset.data["is_active"])

    def test_observation_api_validates_supported_codes_units_values_and_periods(self):
        self.client.force_authenticate(self.admin)
        dataset = self.create_observation_dataset()
        invalid_payloads = (
            {"raw_unit": "kelvin"},
            {"indicator_code": "RELATIVE_HUMIDITY", "raw_unit": "degree_celsius"},
            {"indicator_code": "RAINFALL_24H", "raw_unit": "percent"},
            {"indicator_code": "UNSUPPORTED"},
            {"raw_value_numeric": None},
            {"raw_value_text": "34.5"},
            {"period_start": "2026-11-25", "period_end": "2026-11-24"},
        )

        for overrides in invalid_payloads:
            with self.subTest(overrides=overrides):
                response = self.client.post(
                    reverse("admin-observation-list"),
                    self.observation_payload(dataset, **overrides),
                    format="json",
                )
                self.assertEqual(response.status_code, 400, response.data)

        valid_humidity = self.client.post(
            reverse("admin-observation-list"),
            self.observation_payload(
                dataset,
                indicator_code="RELATIVE_HUMIDITY",
                raw_value_numeric="55",
                raw_unit="percent",
            ),
            format="json",
        )
        self.assertEqual(valid_humidity.status_code, 201, valid_humidity.data)

    def test_observation_api_requires_eligible_dataset_and_spatial_resolution(self):
        self.client.force_authenticate(self.admin)
        pending_dataset = self.create_observation_dataset(
            approval_status="PENDING",
        )
        inactive_dataset = self.create_observation_dataset(is_active=False)

        pending_response = self.client.post(
            reverse("admin-observation-list"),
            self.observation_payload(pending_dataset),
            format="json",
        )
        inactive_response = self.client.post(
            reverse("admin-observation-list"),
            self.observation_payload(inactive_dataset),
            format="json",
        )
        self.assertEqual(pending_response.status_code, 400)
        self.assertIn("approved source", str(pending_response.data))
        self.assertEqual(inactive_response.status_code, 400)
        self.assertIn("active dataset", str(inactive_response.data))

        ward = Area.objects.create(
            city=self.area.city,
            area_name="Meerut Ward 1",
            area_type="ward",
        )
        city_dataset = self.create_observation_dataset(spatial_resolution="city")
        response = self.client.post(
            reverse("admin-observation-list"),
            self.observation_payload(city_dataset, area=ward.pk),
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("City-level observations", str(response.data))

    def test_duplicate_observation_is_rejected_by_api_and_database_constraint(self):
        self.client.force_authenticate(self.admin)
        dataset = self.create_observation_dataset()
        payload = self.observation_payload(dataset)
        first = self.client.post(
            reverse("admin-observation-list"),
            payload,
            format="json",
        )
        duplicate = self.client.post(
            reverse("admin-observation-list"),
            payload,
            format="json",
        )
        self.assertEqual(first.status_code, 201, first.data)
        self.assertEqual(duplicate.status_code, 400)

        direct_duplicate = IndicatorObservation(
            area=self.area,
            dataset=dataset,
            indicator_code="AIR_TEMPERATURE",
            period_start="2026-11-24",
            period_end="2026-11-24",
            raw_value_numeric="34.5",
            raw_unit="degree_celsius",
            quality_status="VALID",
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                IndicatorObservation.objects.bulk_create([direct_duplicate])

    def test_admin_validation_filters_and_delete_is_not_available(self):
        self.client.force_authenticate(self.admin)
        invalid_source = self.client.post(
            reverse("admin-data-source-list"),
            {
                "source_name": "Invalid source",
                "owner_name": "Owner",
                "official_url": "not a URL",
                "approval_status": "UNSUPPORTED",
            },
            format="json",
        )
        self.assertEqual(invalid_source.status_code, 400)

        source = DataSource.objects.create(
            source_name="Approved registry",
            owner_name="Owner",
            approval_status="APPROVED",
        )
        list_response = self.client.get(
            reverse("admin-data-source-list"),
            {"search": "registry", "page_size": 5},
        )
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(list_response.data["count"], 1)
        detail = reverse("admin-data-source-detail", kwargs={"pk": source.pk})
        self.assertEqual(self.client.delete(detail).status_code, 405)

    def test_active_dataset_requires_an_approved_source(self):
        self.client.force_authenticate(self.admin)
        pending_source = DataSource.objects.create(
            source_name="Awaiting review",
            owner_name="Owner",
            approval_status="PENDING",
        )

        response = self.client.post(
            reverse("admin-dataset-list"),
            {
                "source": pending_source.pk,
                "dataset_name": "Ineligible active dataset",
                "data_class": "observed",
                "spatial_resolution": "city",
                "retrieved_at": "2026-11-24T08:00:00+05:30",
                "is_active": True,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("source", response.data)
        self.assertFalse(
            Dataset.objects.filter(dataset_name="Ineligible active dataset").exists()
        )

    def test_student_lists_expose_only_approved_public_data(self):
        pending = DataSource.objects.create(
            source_name="Pending registry",
            owner_name="Owner",
            approval_status="PENDING",
        )
        approved = DataSource.objects.create(
            source_name="Approved registry",
            owner_name="Owner",
            official_url="https://data.example.test",
            licence_terms="Restricted internal license text",
            approval_status="APPROVED",
        )
        active = Dataset.objects.create(
            source=approved,
            dataset_name="Public active dataset",
            data_class="observed",
            spatial_resolution="city",
            retrieved_at=timezone.now(),
            file_hash="private-hash",
            transformation_notes="private transformation details",
            is_active=True,
        )
        Dataset.objects.create(
            source=pending,
            dataset_name="Pending source dataset",
            data_class="observed",
            spatial_resolution="city",
            retrieved_at=timezone.now(),
            is_active=True,
        )
        Dataset.objects.create(
            source=approved,
            dataset_name="Inactive approved-source dataset",
            data_class="observed",
            spatial_resolution="city",
            retrieved_at=timezone.now(),
            is_active=False,
        )
        observation = IndicatorObservation.objects.create(
            area=self.area,
            dataset=active,
            indicator_code="AIR_TEMPERATURE",
            period_start="2026-11-23",
            period_end="2026-11-23",
            raw_value_numeric="33",
            raw_unit="degree_celsius",
            quality_status="VALID",
            notes="private note",
        )
        self.client.force_authenticate(self.student)

        sources = self.client.get(reverse("data-source-list"))
        datasets = self.client.get(reverse("dataset-list"))
        observations = self.client.get(reverse("indicator-observation-list"))
        self.assertEqual([row["id"] for row in sources.data["results"]], [approved.id])
        self.assertEqual(sources.data["results"][0]["dataset_count"], 1)
        self.assertEqual([row["id"] for row in datasets.data["results"]], [active.id])
        self.assertEqual(
            [row["id"] for row in observations.data["results"]],
            [observation.id],
        )
        self.assertNotIn("licence_terms", sources.data["results"][0])
        self.assertNotIn("file_hash", datasets.data["results"][0])
        self.assertNotIn("transformation_notes", datasets.data["results"][0])
        self.assertNotIn("notes", observations.data["results"][0])

    def test_inventory_endpoints_are_read_only(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            reverse("data-source-list"),
            {"source_name": "Unexpected"},
            format="json",
        )

        self.assertEqual(response.status_code, 405)
        self.assertEqual(DataSource.objects.count(), 0)
        self.assertEqual(Dataset.objects.count(), 0)
        self.assertEqual(IndicatorObservation.objects.count(), 0)

    def test_authenticated_session_can_read_inventory(self):
        session_client = APIClient()
        self.assertTrue(session_client.login(
            username=self.username,
            password=self.password,
        ))

        response = session_client.get(reverse("data-source-list"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 0)


class EmptyInventoryAPITests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(
            username="empty-inventory-reader",
            password="test-only-password",
        )
        self.client = APIClient()
        self.client.force_authenticate(user=user)

    def test_empty_inventory_lists_return_valid_paginated_responses(self):
        for endpoint in (
            "data-source-list",
            "dataset-list",
            "indicator-observation-list",
        ):
            with self.subTest(endpoint=endpoint):
                response = self.client.get(reverse(endpoint))
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.data["count"], 0)
                self.assertEqual(response.data["results"], [])


class OpenMeteoIngestionTests(TestCase):
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
            latitude="28.996330",
            longitude="77.706192",
        )
        self.source = DataSource.objects.create(
            source_name="Open-Meteo Weather API",
            owner_name="Open-Meteo",
            official_url="https://open-meteo.com",
            licence_terms="CC BY 4.0",
            approval_status="APPROVED",
        )
        self.sample_payload = {
            "latitude": 28.998,
            "longitude": 77.718,
            "daily_units": {
                "time": "iso8601",
                "temperature_2m_mean": "°C",
                "relative_humidity_2m_mean": "%",
            },
            "daily": {
                "time": ["2026-11-18", "2026-11-19"],
                "temperature_2m_mean": [28.5, 29.0],
                "relative_humidity_2m_mean": [55.0, 60.0],
            },
        }

    @patch("apps.datasets.services.open_meteo_import.urlopen")
    def test_successful_import_creates_dataset_and_observations(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(self.sample_payload).encode("utf-8")
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        from apps.datasets.services.open_meteo_import import import_open_meteo_period

        summary = import_open_meteo_period(
            area_id=self.area.pk,
            period_start=date(2026, 11, 18),
            period_end=date(2026, 11, 19),
        )

        self.assertEqual(summary["imported"], 4)
        self.assertEqual(summary["skipped_existing"], 0)
        self.assertEqual(summary["data_class"], "derived")

        dataset = Dataset.objects.get(pk=summary["dataset_id"])
        self.assertEqual(dataset.data_class, "derived")
        self.assertTrue(dataset.is_active)
        self.assertIn("Open-Meteo", dataset.dataset_name)

        observations = IndicatorObservation.objects.filter(dataset=dataset)
        self.assertEqual(observations.count(), 4)
        temp_obs = observations.filter(indicator_code="AIR_TEMPERATURE")
        self.assertEqual(temp_obs.count(), 2)
        for obs in temp_obs:
            self.assertEqual(obs.raw_unit, "degree_celsius")
            self.assertEqual(obs.quality_status, "VALID")

        humidity_obs = observations.filter(indicator_code="RELATIVE_HUMIDITY")
        self.assertEqual(humidity_obs.count(), 2)
        for obs in humidity_obs:
            self.assertEqual(obs.raw_unit, "percent")
            self.assertEqual(obs.quality_status, "VALID")

    @patch("apps.datasets.services.open_meteo_import.urlopen")
    def test_import_is_repeatable_and_idempotent(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(self.sample_payload).encode("utf-8")
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        from apps.datasets.services.open_meteo_import import import_open_meteo_period

        first_summary = import_open_meteo_period(
            area_id=self.area.pk,
            period_start=date(2026, 11, 18),
            period_end=date(2026, 11, 19),
        )
        self.assertEqual(first_summary["imported"], 4)

        second_summary = import_open_meteo_period(
            area_id=self.area.pk,
            period_start=date(2026, 11, 18),
            period_end=date(2026, 11, 19),
        )
        self.assertEqual(second_summary["imported"], 0)
        self.assertEqual(second_summary["skipped_existing"], 4)
        self.assertEqual(IndicatorObservation.objects.count(), 4)

    @patch("apps.datasets.services.open_meteo_import.urlopen")
    def test_dry_run_does_not_persist_records(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(self.sample_payload).encode("utf-8")
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        from apps.datasets.services.open_meteo_import import import_open_meteo_period

        summary = import_open_meteo_period(
            area_id=self.area.pk,
            period_start=date(2026, 11, 18),
            period_end=date(2026, 11, 19),
            dry_run=True,
        )

        self.assertTrue(summary["dry_run"])
        self.assertEqual(summary["imported"], 4)
        self.assertEqual(Dataset.objects.count(), 0)
        self.assertEqual(IndicatorObservation.objects.count(), 0)

    @patch("apps.datasets.services.open_meteo_import.urlopen")
    def test_missing_and_sentinel_values_are_skipped_without_fabrication(self, mock_urlopen):
        payload = {
            "latitude": 28.998,
            "longitude": 77.718,
            "daily_units": {
                "time": "iso8601",
                "temperature_2m_mean": "°C",
                "relative_humidity_2m_mean": "%",
            },
            "daily": {
                "time": ["2026-11-18", "2026-11-19"],
                "temperature_2m_mean": [28.5, -999],
                "relative_humidity_2m_mean": [None, 60.0],
            },
        }
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(payload).encode("utf-8")
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        from apps.datasets.services.open_meteo_import import import_open_meteo_period

        summary = import_open_meteo_period(
            area_id=self.area.pk,
            period_start=date(2026, 11, 18),
            period_end=date(2026, 11, 19),
        )

        self.assertEqual(summary["imported"], 2)
        self.assertEqual(summary["skipped_missing"], 2)
        self.assertEqual(IndicatorObservation.objects.count(), 2)

    @patch("apps.datasets.services.open_meteo_import.urlopen")
    def test_unexpected_temperature_unit_raises_error(self, mock_urlopen):
        bad_unit_payload = dict(self.sample_payload)
        bad_unit_payload["daily_units"] = {
            "time": "iso8601",
            "temperature_2m_mean": "°F",
            "relative_humidity_2m_mean": "%",
        }
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(bad_unit_payload).encode("utf-8")
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        from apps.datasets.services.open_meteo_import import OpenMeteoImportError, import_open_meteo_period

        with self.assertRaises(OpenMeteoImportError) as error:
            import_open_meteo_period(
                area_id=self.area.pk,
                period_start=date(2026, 11, 18),
                period_end=date(2026, 11, 19),
            )
        self.assertIn("Unexpected temperature unit", str(error.exception))

    def test_future_period_is_rejected(self):
        from apps.datasets.services.open_meteo_import import OpenMeteoImportError, import_open_meteo_period

        tomorrow = timezone.localdate() + timezone.timedelta(days=1)
        with self.assertRaises(OpenMeteoImportError) as error:
            import_open_meteo_period(
                area_id=self.area.pk,
                period_start=tomorrow,
                period_end=tomorrow,
            )
        self.assertIn("Future-dated periods are not supported", str(error.exception))

    @patch("apps.datasets.services.open_meteo_import.urlopen")
    def test_management_command_execution(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(self.sample_payload).encode("utf-8")
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        call_command(
            "import_open_meteo",
            area_id=self.area.pk,
            start_date="2026-11-18",
            end_date="2026-11-19",
        )

        self.assertEqual(IndicatorObservation.objects.count(), 4)

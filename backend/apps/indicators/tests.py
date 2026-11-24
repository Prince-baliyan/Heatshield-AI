from datetime import date, timedelta
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import SimpleTestCase, TestCase
from django.utils import timezone

from apps.cities.models import Area, City
from apps.datasets.models import DataSource, Dataset
from apps.cities.readiness import compute_area_readiness
from .models import IndicatorObservation


class IndicatorObservationModelTests(SimpleTestCase):
    def test_str_identifies_indicator_and_area(self):
        city = City(name="Meerut", state_name="Uttar Pradesh", country_code="IN")
        area = Area(city=city, area_name="Meerut city level")
        observation = IndicatorObservation(
            area=area,
            indicator_code="AIR_TEMPERATURE",
        )

        self.assertEqual(str(observation), "AIR_TEMPERATURE at Meerut city level")

    def test_period_end_before_start_is_rejected(self):
        observation = IndicatorObservation(
            indicator_code="AIR_TEMPERATURE",
            period_start="2026-11-22",
            period_end="2026-11-21",
            quality_status="VALID",
        )

        with self.assertRaises(ValidationError):
            observation.clean()

    def test_period_end_before_start_is_rejected_by_save(self):
        observation = IndicatorObservation(
            indicator_code="AIR_TEMPERATURE",
            period_start="2026-11-22",
            period_end="2026-11-21",
            quality_status="VALID",
        )

        with self.assertRaises(ValidationError) as error:
            observation.save()

        self.assertIn("period_end", error.exception.message_dict)

    def test_city_level_observation_on_city_area_is_accepted(self):
        city = City(name="Meerut", state_name="Uttar Pradesh", country_code="IN")
        city_area = Area(city=city, area_name="Meerut city level", area_type="city")
        dataset = Dataset(
            dataset_name="Demo weather",
            data_class="illustrative",
            spatial_resolution="illustrative_city_level",
        )
        observation = IndicatorObservation(
            area=city_area,
            dataset=dataset,
            indicator_code="AIR_TEMPERATURE",
            period_start="2026-11-22",
            period_end="2026-11-22",
            quality_status="VALID",
        )

        observation.clean()

    def test_city_level_observation_on_ward_is_rejected_by_clean(self):
        city = City(name="Meerut", state_name="Uttar Pradesh", country_code="IN")
        ward_area = Area(city=city, area_name="Verified ward", area_type="ward")
        dataset = Dataset(
            dataset_name="Demo weather",
            data_class="illustrative",
            spatial_resolution="city",
        )
        observation = IndicatorObservation(
            area=ward_area,
            dataset=dataset,
            indicator_code="AIR_TEMPERATURE",
            period_start="2026-11-22",
            period_end="2026-11-22",
            quality_status="VALID",
        )

        with self.assertRaises(ValidationError):
            observation.clean()

    def test_city_wide_resolution_is_rejected_on_ward(self):
        city = City(name="Meerut", state_name="Uttar Pradesh", country_code="IN")
        ward_area = Area(city=city, area_name="Verified ward", area_type="ward")
        dataset = Dataset(
            dataset_name="City-wide weather",
            data_class="illustrative",
            spatial_resolution="City-wide forecast",
        )
        observation = IndicatorObservation(
            area=ward_area,
            dataset=dataset,
            indicator_code="AIR_TEMPERATURE",
            period_start="2026-11-22",
            period_end="2026-11-22",
            quality_status="VALID",
        )

        with self.assertRaises(ValidationError):
            observation.clean()

    def test_city_level_observation_on_ward_is_rejected_by_save(self):
        city = City(name="Meerut", state_name="Uttar Pradesh", country_code="IN")
        ward_area = Area(city=city, area_name="Verified ward", area_type="ward")
        dataset = Dataset(
            dataset_name="Demo weather",
            data_class="illustrative",
            spatial_resolution="illustrative_city_level",
        )
        observation = IndicatorObservation(
            area=ward_area,
            dataset=dataset,
            indicator_code="AIR_TEMPERATURE",
        )

        with self.assertRaises(ValidationError):
            observation.save()

    def test_missing_numeric_observation_is_distinct_from_zero(self):
        observation = IndicatorObservation(
            indicator_code="RAINFALL_24H",
            period_start="2026-11-22",
            period_end="2026-11-22",
            raw_value_numeric=None,
            raw_value_text=None,
            quality_status="MISSING",
        )
        observation.clean()
        self.assertIsNone(observation.raw_value_numeric)

    def test_zero_numeric_observation_is_preserved(self):
        observation = IndicatorObservation(
            indicator_code="RAINFALL_24H",
            period_start="2026-11-22",
            period_end="2026-11-22",
            raw_value_numeric="0",
            quality_status="VALID",
        )
        observation.clean()
        self.assertEqual(str(observation.raw_value_numeric), "0")

    def test_text_observation_is_supported(self):
        observation = IndicatorObservation(
            indicator_code="HEAT_WARNING_LEVEL",
            period_start="2026-11-22",
            period_end="2026-11-22",
            raw_value_text="SEVERE",
            raw_unit="level",
            quality_status="VALID",
        )
        observation.clean()
        self.assertEqual(observation.raw_value_text, "SEVERE")


class IndicatorDataQualityDatabaseTests(TestCase):
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
            latitude=Decimal("28.996330"),
            longitude=Decimal("77.706192"),
        )
        self.source = DataSource.objects.create(
            source_name="Open-Meteo Weather API",
            owner_name="Open-Meteo",
            official_url="https://open-meteo.com",
            licence_terms="CC BY 4.0",
            approval_status="APPROVED",
        )
        self.dataset = Dataset.objects.create(
            source=self.source,
            dataset_name="Derived Weather",
            data_class="derived",
            spatial_resolution="city",
            retrieved_at=timezone.now(),
            is_active=True,
        )

    def test_duplicate_observation_period_is_rejected_by_unique_constraint(self):
        test_date = date(2026, 11, 20)
        IndicatorObservation.objects.create(
            area=self.area,
            dataset=self.dataset,
            indicator_code="AIR_TEMPERATURE",
            period_start=test_date,
            period_end=test_date,
            raw_value_numeric=Decimal("28.5"),
            raw_unit="degree_celsius",
            quality_status="VALID",
        )

        with self.assertRaises((IntegrityError, ValidationError)):
            IndicatorObservation.objects.create(
                area=self.area,
                dataset=self.dataset,
                indicator_code="AIR_TEMPERATURE",
                period_start=test_date,
                period_end=test_date,
                raw_value_numeric=Decimal("30.0"),
                raw_unit="degree_celsius",
                quality_status="VALID",
            )

    def test_missing_data_quality_status_is_preserved_and_never_treated_as_zero(self):
        test_date = date(2026, 11, 20)
        obs = IndicatorObservation.objects.create(
            area=self.area,
            dataset=self.dataset,
            indicator_code="AIR_TEMPERATURE",
            period_start=test_date,
            period_end=test_date,
            raw_value_numeric=None,
            raw_unit="degree_celsius",
            quality_status="MISSING",
        )
        obs.refresh_from_db()
        self.assertIsNone(obs.raw_value_numeric)
        self.assertEqual(obs.quality_status, "MISSING")

    def test_area_readiness_detects_freshness_and_period_alignment(self):
        today = timezone.localdate()
        aligned_date = today - timedelta(days=2)

        # Fresh and aligned
        temp = IndicatorObservation.objects.create(
            area=self.area,
            dataset=self.dataset,
            indicator_code="AIR_TEMPERATURE",
            period_start=aligned_date,
            period_end=aligned_date,
            raw_value_numeric=Decimal("28.0"),
            raw_unit="degree_celsius",
            quality_status="VALID",
        )
        humidity = IndicatorObservation.objects.create(
            area=self.area,
            dataset=self.dataset,
            indicator_code="RELATIVE_HUMIDITY",
            period_start=aligned_date,
            period_end=aligned_date,
            raw_value_numeric=Decimal("60.0"),
            raw_unit="percent",
            quality_status="VALID",
        )

        readiness = compute_area_readiness(self.area)
        self.assertTrue(readiness["is_assessment_ready"])
        self.assertEqual(readiness["freshness_status"], "FRESH")
        self.assertEqual(readiness["observation_age_days"], 2)
        self.assertEqual(readiness["readiness_reasons"], [])

    def test_area_readiness_flags_stale_data(self):
        today = timezone.localdate()
        stale_date = today - timedelta(days=10)

        IndicatorObservation.objects.create(
            area=self.area,
            dataset=self.dataset,
            indicator_code="AIR_TEMPERATURE",
            period_start=stale_date,
            period_end=stale_date,
            raw_value_numeric=Decimal("28.0"),
            raw_unit="degree_celsius",
            quality_status="VALID",
        )
        IndicatorObservation.objects.create(
            area=self.area,
            dataset=self.dataset,
            indicator_code="RELATIVE_HUMIDITY",
            period_start=stale_date,
            period_end=stale_date,
            raw_value_numeric=Decimal("60.0"),
            raw_unit="percent",
            quality_status="VALID",
        )

        readiness = compute_area_readiness(self.area)
        self.assertFalse(readiness["is_assessment_ready"])
        self.assertEqual(readiness["freshness_status"], "STALE")
        self.assertTrue(
            any("No fresh valid" in reason for reason in readiness["readiness_reasons"])
        )

    def test_area_readiness_flags_unaligned_periods(self):
        today = timezone.localdate()
        IndicatorObservation.objects.create(
            area=self.area,
            dataset=self.dataset,
            indicator_code="AIR_TEMPERATURE",
            period_start=today - timedelta(days=1),
            period_end=today - timedelta(days=1),
            raw_value_numeric=Decimal("28.0"),
            raw_unit="degree_celsius",
            quality_status="VALID",
        )
        IndicatorObservation.objects.create(
            area=self.area,
            dataset=self.dataset,
            indicator_code="RELATIVE_HUMIDITY",
            period_start=today - timedelta(days=2),
            period_end=today - timedelta(days=2),
            raw_value_numeric=Decimal("60.0"),
            raw_unit="percent",
            quality_status="VALID",
        )

        readiness = compute_area_readiness(self.area)
        self.assertFalse(readiness["is_assessment_ready"])
        self.assertTrue(
            any("do not align" in reason for reason in readiness["readiness_reasons"])
        )

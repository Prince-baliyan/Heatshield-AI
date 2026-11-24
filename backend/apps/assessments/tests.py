from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
from io import StringIO
from threading import Barrier
from types import SimpleNamespace
from unittest import skipUnless
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import close_old_connections, connection
from django.test import SimpleTestCase, TestCase, TransactionTestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient, APIRequestFactory, force_authenticate

from apps.cities.models import Area, City
from apps.datasets.models import DataSource, Dataset
from apps.datasets.providers.demo import DemoWeatherProvider
from apps.indicators.models import IndicatorObservation
from .engine import (
    AssessmentConfigurationError,
    AssessmentInput,
    MVP_CONFIGURATION,
    SCORING_CONFIGURATION_REGISTRY,
    assess_area,
    scoring_configuration_for,
    score_inputs,
)
from .models import (
    AssessmentIdempotencyRecord,
    AssessmentIndicator,
    AssessmentRecommendation,
    AssessmentRun,
    RecommendationRule,
)
from .recommendations import RuleConfigurationError, rule_matches
from .serializers import AssessmentRunSerializer
from .views import (
    AssessmentCollectionView,
    AssessmentPagination,
    _request_fingerprint,
)


class AssessmentModelTests(SimpleTestCase):
    def test_assessment_str(self):
        city = City(name="Meerut", state_name="Uttar Pradesh", country_code="IN")
        area = Area(city=city, area_name="Meerut city level")
        run = AssessmentRun(
            area=area,
            status="SCORED",
        )

        self.assertEqual(str(run), "Assessment for Meerut city level (SCORED)")

    def test_numeric_indicator_accepts_values_without_undocumented_limits(self):
        indicator = AssessmentIndicator(
            indicator_code="AIR_TEMPERATURE",
            normalized_value=Decimal("1.2000"),
            weight_used=Decimal("1.5000"),
            contribution=Decimal("1.8000"),
            quality_status="VALID",
            explanation="Provisional demonstration value.",
        )
        indicator.clean()

        self.assertEqual(indicator.normalized_value, Decimal("1.2000"))

    def test_empty_assessment_explanation_is_rejected_by_clean(self):
        indicator = AssessmentIndicator(
            indicator_code="AIR_TEMPERATURE",
            quality_status="VALID",
            explanation="   ",
        )

        with self.assertRaises(ValidationError):
            indicator.clean()

    def test_empty_assessment_explanation_is_rejected_by_save(self):
        indicator = AssessmentIndicator(
            indicator_code="AIR_TEMPERATURE",
            quality_status="VALID",
            explanation="",
        )

        with self.assertRaises(ValidationError):
            indicator.save()

    def test_json_recommendation_rule_is_preserved(self):
        rule = RecommendationRule(
            rule_code="HIGH_HEAT",
            title="High heat alert",
            condition_config={
                "all": [
                    {
                        "field": "risk_category",
                        "operator": "eq",
                        "value": "illustrative_high",
                    }
                ]
            },
            recommendation_text="Increase hydration and shade access.",
            priority="high",
            version="demo-v1",
        )
        rule.clean()

        self.assertEqual(
            rule.condition_config,
            {
                "all": [
                    {
                        "field": "risk_category",
                        "operator": "eq",
                        "value": "illustrative_high",
                    }
                ]
            },
        )

    def test_missing_recommendation_configuration_is_rejected_by_clean(self):
        rule = RecommendationRule(
            rule_code="HIGH_HEAT",
            title="High heat alert",
            condition_config=None,
            recommendation_text="Increase hydration and shade access.",
            priority="high",
            version="demo-v1",
        )

        with self.assertRaises(ValidationError):
            rule.clean()

    def test_empty_recommendation_configuration_is_rejected_by_clean(self):
        rule = RecommendationRule(
            rule_code="HIGH_HEAT",
            title="High heat alert",
            condition_config={},
            recommendation_text="Increase hydration and shade access.",
            priority="high",
            version="demo-v1",
        )

        with self.assertRaises(ValidationError):
            rule.clean()

    def test_empty_recommendation_configuration_is_rejected_by_save(self):
        rule = RecommendationRule(
            rule_code="HIGH_HEAT",
            title="High heat alert",
            condition_config={},
            recommendation_text="Increase hydration and shade access.",
            priority="high",
            version="demo-v1",
        )

        with self.assertRaises(ValidationError):
            rule.save()

    def test_valid_recommendation_configuration_is_accepted_by_save(self):
        rule = RecommendationRule(
            rule_code="HIGH_HEAT",
            title="High heat alert",
            condition_config={
                "all": [
                    {"field": "score", "operator": "gte", "value": 70}
                ]
            },
            recommendation_text="Increase hydration and shade access.",
            priority="high",
            version="demo-v1",
        )

        rule.clean()
        self.assertEqual(
            rule.condition_config,
            {"all": [{"field": "score", "operator": "gte", "value": 70}]},
        )

    def test_invalid_recommendation_configuration_is_rejected(self):
        rule = RecommendationRule(
            rule_code="BAD_RULE",
            title="Bad configuration",
            condition_config={"score": {"gte": 70}},
            recommendation_text="Review the area.",
            priority="medium",
            version="v1",
        )

        with self.assertRaises(ValidationError):
            rule.clean()

    def test_numeric_fields_have_no_undocumented_business_limits(self):
        run = AssessmentRun(
            method_version="method-v1",
            configuration_version="config-v1",
            score=Decimal("125.00"),
            data_coverage=Decimal("150.00"),
            data_class="observed",
            status="SCORED",
        )
        run.clean()

    def test_assessment_run_save_enforces_model_validation(self):
        run = AssessmentRun(
            method_version=" ",
            configuration_version="config-v1",
            data_class="observed",
            status="SCORED",
            run_at=timezone.now(),
        )

        with self.assertRaises(ValidationError) as error:
            run.save()

        self.assertIn("method_version", error.exception.message_dict)

    def test_assessment_recommendation_save_enforces_applied_version(self):
        recommendation = AssessmentRecommendation(rule_version_applied=" ")

        with self.assertRaises(ValidationError) as error:
            recommendation.save()

        self.assertIn("rule_version_applied", error.exception.message_dict)

    def test_idempotency_record_validates_key_and_fingerprint(self):
        record = AssessmentIdempotencyRecord(
            key="assessment:retry-1",
            request_fingerprint="a" * 64,
        )
        record.clean()

        record.key = "Assessment:Retry-1"
        record.clean()
        self.assertEqual(record.key, "assessment:retry-1")

        record.key = "invalid key"
        with self.assertRaises(ValidationError) as error:
            record.clean()

        self.assertIn("key", error.exception.message_dict)

    def test_idempotency_fingerprint_is_canonical_for_validated_payload(self):
        first = _request_fingerprint({"area_id": 3, "source": "observations"})
        second = _request_fingerprint({"source": "observations", "area_id": 3})

        self.assertEqual(first, second)


class AssessmentEngineTests(SimpleTestCase):
    def _valid_inputs(self):
        return [
            AssessmentInput(
                code="AIR_TEMPERATURE",
                numeric_value=Decimal("38"),
                text_value=None,
                unit="degree_celsius",
                quality_status="VALID",
                data_class="observed",
                provenance="Test source / test dataset",
                period="2026-11-22 to 2026-11-22",
            ),
            AssessmentInput(
                code="RELATIVE_HUMIDITY",
                numeric_value=Decimal("55"),
                text_value=None,
                unit="percent",
                quality_status="VALID",
                data_class="observed",
                provenance="Test source / test dataset",
                period="2026-11-22 to 2026-11-22",
            ),
        ]

    def test_valid_inputs_produce_deterministic_score(self):
        inputs = self._valid_inputs()

        first = score_inputs(inputs)
        second = score_inputs(inputs)

        self.assertEqual(first.status, "SCORED")
        self.assertEqual(first.score, Decimal("58.00"))
        self.assertEqual(first.data_coverage, Decimal("100.00"))
        self.assertEqual(first.risk_category, "illustrative_moderate")
        self.assertEqual(first, second)
        self.assertEqual(first.data_class, "observed")
        self.assertTrue(any("provisional" in warning for warning in first.warnings))

    def test_missing_indicator_yields_insufficient_data_and_coverage(self):
        result = score_inputs(
            self._valid_inputs()[:1],
        )

        self.assertEqual(result.status, "INSUFFICIENT_DATA")
        self.assertIsNone(result.score)
        self.assertIsNone(result.risk_category)
        self.assertEqual(result.data_coverage, Decimal("70.00"))
        self.assertEqual(result.missing_indicators, ("RELATIVE_HUMIDITY",))

    def test_invalid_stale_and_low_confidence_observations_are_excluded(self):
        for quality_status in ("INVALID", "STALE", "LOW_CONFIDENCE", "PENDING_REVIEW"):
            with self.subTest(quality_status=quality_status):
                inputs = self._valid_inputs()
                inputs[0] = AssessmentInput(
                    **{
                        **inputs[0].__dict__,
                        "quality_status": quality_status,
                    }
                )
                result = score_inputs(inputs)

                self.assertEqual(result.status, "INSUFFICIENT_DATA")
                self.assertIsNone(result.score)
                self.assertEqual(result.data_coverage, Decimal("30.00"))

    def test_out_of_bounds_value_is_invalid_not_clipped(self):
        inputs = self._valid_inputs()
        inputs[0] = AssessmentInput(
            **{**inputs[0].__dict__, "numeric_value": Decimal("50")}
        )

        result = score_inputs(inputs)

        self.assertEqual(result.status, "INSUFFICIENT_DATA")
        self.assertEqual(result.indicators[0].quality_status, "INVALID")
        self.assertIsNone(result.indicators[0].normalized_value)

    def test_wrong_unit_is_excluded(self):
        inputs = self._valid_inputs()
        inputs[0] = AssessmentInput(
            **{**inputs[0].__dict__, "unit": "kelvin"}
        )

        result = score_inputs(inputs)

        self.assertEqual(result.status, "INSUFFICIENT_DATA")
        self.assertEqual(result.indicators[0].quality_status, "INVALID")

    def test_illustrative_low_confidence_inputs_are_labelled_and_scored(self):
        inputs = [
            AssessmentInput(
                **{
                    **item.__dict__,
                    "quality_status": "LOW_CONFIDENCE",
                    "data_class": "illustrative",
                }
            )
            for item in self._valid_inputs()
        ]

        result = score_inputs(inputs)

        self.assertEqual(result.status, "SCORED")
        self.assertEqual(result.data_class, "illustrative")
        self.assertTrue(
            all("Illustrative only" in item.explanation for item in result.indicators)
        )

    def test_no_usable_observations_have_unavailable_provenance(self):
        result = score_inputs([])

        self.assertEqual(result.status, "INSUFFICIENT_DATA")
        self.assertEqual(result.data_class, "unavailable")
        self.assertEqual(result.data_coverage, Decimal("0.00"))
        self.assertIsNone(result.score)
        self.assertTrue(
            all(item.quality_status == "MISSING" for item in result.indicators)
        )

    def test_input_classification_uses_only_eligible_inputs(self):
        for data_class in ("observed", "derived", "illustrative"):
            with self.subTest(data_class=data_class):
                inputs = [
                    replace(item, data_class=data_class)
                    for item in self._valid_inputs()
                ]
                if data_class == "illustrative":
                    inputs = [
                        replace(item, quality_status="LOW_CONFIDENCE")
                        for item in inputs
                    ]

                self.assertEqual(score_inputs(inputs).data_class, data_class)

        mixed = self._valid_inputs()
        mixed[1] = replace(mixed[1], data_class="derived")
        self.assertEqual(score_inputs(mixed).data_class, "mixed")

        unusable = self._valid_inputs()
        unusable = [
            replace(item, quality_status="INVALID")
            for item in unusable
        ]
        self.assertEqual(score_inputs(unusable).data_class, "unavailable")

    def test_configuration_fingerprint_and_registry_preserve_settings(self):
        changed = replace(
            MVP_CONFIGURATION,
            indicators=(
                replace(
                    MVP_CONFIGURATION.indicators[0],
                    weight=Decimal("0.60"),
                ),
                MVP_CONFIGURATION.indicators[1],
            ),
        )

        self.assertNotEqual(
            changed.configuration_version,
            MVP_CONFIGURATION.configuration_version,
        )
        self.assertEqual(
            SCORING_CONFIGURATION_REGISTRY[
                MVP_CONFIGURATION.configuration_version
            ].as_snapshot(),
            MVP_CONFIGURATION.as_snapshot(),
        )
        self.assertEqual(
            scoring_configuration_for(
                "demo-weather-provisional-v1"
            ).indicators[0].weight,
            Decimal("0.70"),
        )
        self.assertNotEqual(
            scoring_configuration_for(
                "demo-weather-provisional-v1"
            ).configuration_version,
            changed.configuration_version,
        )
        self.assertEqual(len(MVP_CONFIGURATION.configuration_version), 40)

    def test_negative_indicator_weight_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "weight"):
            replace(
                MVP_CONFIGURATION,
                indicators=(
                    replace(
                        MVP_CONFIGURATION.indicators[0],
                        weight=Decimal("-0.10"),
                    ),
                    MVP_CONFIGURATION.indicators[1],
                ),
            )

    def test_zero_total_indicator_weight_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "positive total weight"):
            replace(
                MVP_CONFIGURATION,
                indicators=(
                    replace(
                        MVP_CONFIGURATION.indicators[0],
                        weight=Decimal("0"),
                    ),
                    replace(
                        MVP_CONFIGURATION.indicators[1],
                        weight=Decimal("0"),
                    ),
                ),
            )

    def test_invalid_normalization_bounds_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "bounds"):
            replace(
                MVP_CONFIGURATION,
                indicators=(
                    replace(
                        MVP_CONFIGURATION.indicators[0],
                        lower_bound=Decimal("45"),
                        upper_bound=Decimal("25"),
                    ),
                    MVP_CONFIGURATION.indicators[1],
                ),
            )

    def test_invalid_minimum_coverage_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Minimum coverage"):
            replace(MVP_CONFIGURATION, minimum_coverage=Decimal("101"))

    def test_pagination_limits_are_documented_defaults(self):
        self.assertEqual(AssessmentPagination.page_size, 20)
        self.assertEqual(AssessmentPagination.page_size_query_param, "page_size")
        self.assertEqual(AssessmentPagination.max_page_size, 100)

    def test_serializer_hides_legacy_observed_fallback_without_snapshots(self):
        run = SimpleNamespace(
            data_class="observed",
            assessment_indicators=SimpleNamespace(all=lambda: []),
            status="INSUFFICIENT_DATA",
        )
        serializer = AssessmentRunSerializer()

        self.assertEqual(serializer.get_data_class(run), "unavailable")
        self.assertIn(
            "data class is unavailable",
            " ".join(serializer.get_warnings(run)),
        )

    @patch("apps.assessments.engine.get_weather_provider")
    def test_demo_assessment_rejects_non_city_level_provider_data(self, get_provider):
        area = Area(
            city=City(name="Meerut", state_name="Uttar Pradesh", country_code="IN"),
            area_name="Meerut city level",
            area_type="city",
        )
        get_provider.return_value.fetch_weather.return_value = {
            "data_class": "illustrative",
            "spatial_resolution": "ward",
            "observations": [],
        }

        with self.assertRaises(AssessmentConfigurationError):
            assess_area(area, source="demo")


class RecommendationEvaluatorTests(SimpleTestCase):
    def test_matching_rule_configuration(self):
        config = {
            "all": [
                {"field": "score", "operator": "gte", "value": 60},
                {
                    "field": "data_class",
                    "operator": "eq",
                    "value": "illustrative",
                },
            ]
        }
        context = {
            "score": Decimal("70"),
            "data_class": "illustrative",
            "indicators": {},
        }

        self.assertTrue(rule_matches(config, context))

    def test_non_matching_rule_configuration(self):
        config = {
            "any": [
                {"field": "score", "operator": "gte", "value": 80},
                {"field": "status", "operator": "eq", "value": "NOT_READY"},
            ]
        }
        context = {
            "score": Decimal("70"),
            "status": "SCORED",
            "indicators": {},
        }

        self.assertFalse(rule_matches(config, context))

    def test_indicator_condition_uses_structured_context(self):
        config = {
            "all": [
                {
                    "field": "indicators.AIR_TEMPERATURE.normalized_value",
                    "operator": "gt",
                    "value": "0.5",
                }
            ]
        }
        context = {
            "indicators": {
                "AIR_TEMPERATURE": {"normalized_value": Decimal("0.65")}
            }
        }

        self.assertTrue(rule_matches(config, context))

    def test_invalid_operator_is_rejected_without_evaluation(self):
        with self.assertRaises(RuleConfigurationError):
            rule_matches(
                {
                    "all": [
                        {
                            "field": "score",
                            "operator": "python_eval",
                            "value": "__import__('os')",
                        }
                    ]
                },
                {"score": 70, "indicators": {}},
            )

    def test_invalid_field_is_rejected(self):
        with self.assertRaises(RuleConfigurationError):
            rule_matches(
                {"all": [{"field": "unknown", "operator": "eq", "value": "x"}]},
                {},
            )


class AssessmentAPIValidationTests(SimpleTestCase):
    def setUp(self):
        self.factory = APIRequestFactory()

    def test_invalid_source_is_rejected_before_area_lookup(self):
        request = self.factory.post(
            "/api/v1/assessments/",
            {"area_id": 1, "source": "imd"},
            format="json",
        )
        force_authenticate(request, user=type("User", (), {"is_authenticated": True})())

        response = AssessmentCollectionView.as_view()(request)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["error"]["code"], "INVALID_REQUEST")

    def test_assessment_write_requires_authentication(self):
        request = self.factory.post(
            "/api/v1/assessments/",
            {"area_id": 1, "source": "demo"},
            format="json",
        )

        response = AssessmentCollectionView.as_view()(request)

        self.assertEqual(response.status_code, 401)

class AssessmentPersistenceTests(TestCase):
    def setUp(self):
        self.city = City.objects.create(
            name="Meerut",
            state_name="Uttar Pradesh",
            country_code="IN",
            status="ACTIVE",
        )
        self.area = Area.objects.create(
            city=self.city,
            area_name="Meerut city level",
            area_type="city",
        )
        self.source = DataSource.objects.create(
            source_name="Assessment test source",
            owner_name="Test owner",
            approval_status="APPROVED",
        )
        self.dataset = Dataset.objects.create(
            source=self.source,
            dataset_name="Assessment test dataset",
            data_class="observed",
            spatial_resolution="city",
            retrieved_at=timezone.now(),
            is_active=True,
        )

    def add_observation(
        self,
        code,
        value,
        unit,
        *,
        quality_status="VALID",
        period_start="2026-11-22",
        period_end="2026-11-22",
    ):
        return IndicatorObservation.objects.create(
            area=self.area,
            dataset=self.dataset,
            indicator_code=code,
            period_start=period_start,
            period_end=period_end,
            raw_value_numeric=value,
            raw_unit=unit,
            quality_status=quality_status,
        )

    def add_valid_observations(self):
        self.add_observation("AIR_TEMPERATURE", "38", "degree_celsius")
        self.add_observation("RELATIVE_HUMIDITY", "55", "percent")

    def test_historical_assessments_are_not_overwritten(self):
        self.add_valid_observations()

        first = assess_area(self.area, source="observations")
        second = assess_area(self.area, source="observations")

        self.assertNotEqual(first.pk, second.pk)
        self.assertEqual(AssessmentRun.objects.filter(area=self.area).count(), 2)

    def test_configuration_snapshot_is_immutable_after_creation(self):
        run = assess_area(self.area, source="observations")

        run.configuration_snapshot = {"changed": True}
        with self.assertRaises(ValidationError):
            run.save()

    def test_duplicate_recommendation_application_is_rejected(self):
        run = AssessmentRun.objects.create(
            area=self.area,
            method_version="method-v1",
            configuration_version="config-v1",
            data_class="observed",
            status="INSUFFICIENT_DATA",
            run_at=timezone.now(),
        )
        rule = RecommendationRule.objects.create(
            rule_code="UNIQUE_RULE",
            title="Unique rule",
            condition_config={
                "all": [{"field": "status", "operator": "eq", "value": "INSUFFICIENT_DATA"}]
            },
            recommendation_text="Review data.",
            priority="medium",
            version="v1",
            is_active=True,
        )
        AssessmentRecommendation.objects.create(
            assessment_run=run,
            recommendation_rule=rule,
            rule_version_applied="v1",
            rule_snapshot={
                "rule_code": rule.rule_code,
                "title": rule.title,
                "recommendation_text": rule.recommendation_text,
                "priority": rule.priority,
                "version": rule.version,
            },
        )

        duplicate = AssessmentRecommendation(
            assessment_run=run,
            recommendation_rule=rule,
            rule_version_applied="v1",
            rule_snapshot={},
        )
        with self.assertRaises(ValidationError):
            duplicate.save()

    def test_recommendation_snapshot_is_immutable_after_creation(self):
        run = AssessmentRun.objects.create(
            area=self.area,
            method_version="method-v1",
            configuration_version="config-v1",
            data_class="observed",
            status="INSUFFICIENT_DATA",
            run_at=timezone.now(),
        )
        rule = RecommendationRule.objects.create(
            rule_code="SNAPSHOT_RULE",
            title="Snapshot rule",
            condition_config={
                "all": [{"field": "status", "operator": "eq", "value": "INSUFFICIENT_DATA"}]
            },
            recommendation_text="Review data.",
            priority="medium",
            version="v1",
            is_active=True,
        )
        recommendation = AssessmentRecommendation.objects.create(
            assessment_run=run,
            recommendation_rule=rule,
            rule_version_applied="v1",
            rule_snapshot={"title": "Original"},
        )

        recommendation.rule_snapshot = {"title": "Changed"}
        with self.assertRaises(ValidationError):
            recommendation.save()

    @patch(
        "apps.assessments.recommendations.evaluate_and_store_recommendations",
        side_effect=RuntimeError("test recommendation failure"),
    )
    def test_assessment_creation_rolls_back_on_recommendation_failure(
        self,
        evaluate_recommendations,
    ):
        self.add_valid_observations()

        with self.assertRaisesRegex(RuntimeError, "test recommendation failure"):
            assess_area(self.area, source="observations")

        self.assertEqual(AssessmentRun.objects.filter(area=self.area).count(), 0)
        self.assertEqual(AssessmentIndicator.objects.count(), 0)
        evaluate_recommendations.assert_called_once()

    def test_invalid_latest_observation_is_excluded(self):
        self.add_observation("AIR_TEMPERATURE", "38", "degree_celsius")
        self.add_observation(
            "AIR_TEMPERATURE",
            "50",
            "degree_celsius",
            quality_status="INVALID",
            period_start="2026-11-23",
            period_end="2026-11-23",
        )
        self.add_observation("RELATIVE_HUMIDITY", "55", "percent")

        run = assess_area(self.area, source="observations")

        self.assertEqual(run.status, "INSUFFICIENT_DATA")
        self.assertIsNone(run.score)
        self.assertEqual(
            run.assessment_indicators.get(
                indicator_code="AIR_TEMPERATURE"
            ).quality_status,
            "INVALID",
        )

    def test_inactive_dataset_observations_are_not_used(self):
        self.add_valid_observations()
        self.dataset.is_active = False
        self.dataset.save()

        run = assess_area(self.area, source="observations")

        self.assertEqual(run.status, "INSUFFICIENT_DATA")
        self.assertEqual(run.data_coverage, Decimal("0.00"))
        self.assertEqual(run.data_class, "unavailable")

    def test_unapproved_source_observations_are_not_used(self):
        self.add_valid_observations()
        self.source.approval_status = "PENDING"
        self.source.save()

        run = assess_area(self.area, source="observations")

        self.assertEqual(run.status, "INSUFFICIENT_DATA")
        self.assertEqual(run.data_coverage, Decimal("0.00"))
        self.assertEqual(run.data_class, "unavailable")

    def test_mismatched_latest_observation_periods_are_not_combined(self):
        today = timezone.localdate()
        yesterday = today - timedelta(days=1)
        self.add_observation(
            "AIR_TEMPERATURE",
            "38",
            "degree_celsius",
            period_start=today,
            period_end=today,
        )
        self.add_observation(
            "RELATIVE_HUMIDITY",
            "55",
            "percent",
            period_start=yesterday,
            period_end=yesterday,
        )

        run = assess_area(self.area, source="observations")
        serialized = AssessmentRunSerializer(run).data

        self.assertEqual(run.status, "INSUFFICIENT_DATA")
        self.assertIsNone(run.score)
        self.assertEqual(run.data_coverage, Decimal("0.00"))
        self.assertTrue(
            any("Stored observation periods do not match" in item
                for item in serialized["warnings"])
        )
        self.assertTrue(
            all(item.normalized_value is None for item in run.assessment_indicators.all())
        )

    @override_settings(MAX_OBSERVATION_AGE_DAYS=7)
    def test_stale_observations_are_excluded_from_stored_assessment(self):
        stale_date = timezone.localdate() - timedelta(days=8)
        self.add_observation(
            "AIR_TEMPERATURE",
            "38",
            "degree_celsius",
            period_start=stale_date,
            period_end=stale_date,
        )
        self.add_observation(
            "RELATIVE_HUMIDITY",
            "55",
            "percent",
            period_start=stale_date,
            period_end=stale_date,
        )

        run = assess_area(self.area, source="observations")
        serialized = AssessmentRunSerializer(run).data

        self.assertEqual(run.status, "INSUFFICIENT_DATA")
        self.assertIsNone(run.score)
        self.assertTrue(
            all(
                item.quality_status == "STALE"
                for item in run.assessment_indicators.all()
            )
        )
        self.assertTrue(
            any("beyond the configured 7-day maximum age" in item
                for item in serialized["warnings"])
        )

    def test_valid_matched_period_derived_observations_can_be_scored(self):
        self.dataset.data_class = "derived"
        self.dataset.save()
        period = timezone.localdate()
        self.add_observation(
            "AIR_TEMPERATURE",
            "38",
            "degree_celsius",
            period_start=period,
            period_end=period,
        )
        self.add_observation(
            "RELATIVE_HUMIDITY",
            "55",
            "percent",
            period_start=period,
            period_end=period,
        )

        run = assess_area(self.area, source="observations")

        self.assertEqual(run.status, "SCORED")
        self.assertEqual(run.data_class, "derived")
        self.assertEqual(run.data_coverage, Decimal("100.00"))
        self.assertEqual(run.score, Decimal("58.00"))

    def test_rainfall_observation_is_not_included_in_scoring(self):
        self.add_valid_observations()
        self.add_observation("RAINFALL_24H", "3", "mm")

        run = assess_area(self.area, source="observations")

        self.assertEqual(run.status, "SCORED")
        self.assertEqual(run.assessment_indicators.count(), 2)
        self.assertFalse(
            run.assessment_indicators.filter(indicator_code="RAINFALL_24H").exists()
        )

    @patch("apps.assessments.engine.get_weather_provider")
    def test_illustrative_dataset_is_excluded_from_stored_assessment(self, get_provider):
        self.dataset.data_class = "illustrative"
        self.dataset.save()
        self.add_valid_observations()

        run = assess_area(self.area, source="observations")
        serialized = AssessmentRunSerializer(run).data

        self.assertEqual(run.status, "INSUFFICIENT_DATA")
        self.assertEqual(run.data_class, "unavailable")
        self.assertIsNone(run.score)
        self.assertTrue(
            any("Illustrative dataset observations were excluded" in item
                for item in serialized["warnings"])
        )
        get_provider.assert_not_called()

    def test_assessment_persists_configuration_snapshot(self):
        run = assess_area(self.area, source="observations")

        self.assertEqual(
            run.configuration_snapshot["configuration_version"],
            run.configuration_version,
        )
        self.assertEqual(
            run.configuration_snapshot,
            MVP_CONFIGURATION.as_snapshot(),
        )
        self.assertEqual(
            run.configuration_snapshot["method_version"],
            run.method_version,
        )
        self.assertEqual(
            run.configuration_snapshot["indicators"][0]["weight"],
            "0.70",
        )

    def test_recommendations_respect_priority_version_and_are_idempotent(self):
        self.add_valid_observations()
        low_rule = RecommendationRule.objects.create(
            rule_code="LOW_RULE",
            title="Lower priority",
            condition_config={
                "all": [{"field": "score", "operator": "gte", "value": 50}]
            },
            recommendation_text="Review the area.",
            priority="low",
            version="low-v1",
            is_active=True,
        )
        high_rule = RecommendationRule.objects.create(
            rule_code="HIGH_RULE",
            title="Higher priority",
            condition_config={
                "all": [{"field": "score", "operator": "gte", "value": 50}]
            },
            recommendation_text="Provide shade.",
            priority="high",
            version="high-v2",
            is_active=True,
        )
        RecommendationRule.objects.create(
            rule_code="INACTIVE_RULE",
            title="Inactive",
            condition_config={
                "all": [{"field": "score", "operator": "gte", "value": 0}]
            },
            recommendation_text="No action.",
            priority="high",
            version="v1",
            is_active=False,
        )

        run = assess_area(self.area, source="observations")
        self.assertEqual(run.status, "SCORED")
        first_recommendations = list(
            run.assessment_recommendations.select_related("recommendation_rule")
            .order_by("created_at", "pk")
        )
        self.assertEqual(
            [item.recommendation_rule_id for item in first_recommendations],
            [high_rule.pk, low_rule.pk],
        )
        self.assertEqual(first_recommendations[0].rule_version_applied, "high-v2")
        self.assertTrue(first_recommendations[0].trigger_explanation)
        self.assertEqual(
            first_recommendations[0].rule_snapshot["recommendation_text"],
            "Provide shade.",
        )

        from .recommendations import evaluate_and_store_recommendations

        evaluate_and_store_recommendations(run)
        self.assertEqual(
            AssessmentRecommendation.objects.filter(assessment_run=run).count(),
            2,
        )


class RecommendationRuleSetupTests(TestCase):
    def test_setup_command_creates_valid_active_rules(self):
        call_command("setup_recommendation_rules", stdout=StringIO())

        rules = list(RecommendationRule.objects.order_by("rule_code"))
        self.assertEqual(len(rules), 4)
        self.assertTrue(all(rule.is_active for rule in rules))
        for rule in rules:
            with self.subTest(rule=rule.rule_code):
                rule.full_clean()
                self.assertEqual(rule.version, "1.0.0")
                self.assertTrue(rule.title)
                self.assertTrue(rule.recommendation_text)

    def test_setup_command_is_duplicate_safe_and_does_not_overwrite(self):
        call_command("setup_recommendation_rules", stdout=StringIO())
        rule = RecommendationRule.objects.get(
            rule_code="HIGH_TEMPERATURE_AWARENESS"
        )
        rule.title = "Locally reviewed title"
        rule.version = "1.2.0"
        rule.is_active = False
        rule.save()

        call_command("setup_recommendation_rules", stdout=StringIO())

        self.assertEqual(RecommendationRule.objects.count(), 4)
        rule.refresh_from_db()
        self.assertEqual(rule.title, "Locally reviewed title")
        self.assertEqual(rule.version, "1.2.0")
        self.assertFalse(rule.is_active)


class AssessmentAPITests(TestCase):
    @patch("apps.assessments.engine.get_weather_provider")
    def test_stored_observation_mode_does_not_fall_back_to_demo(self, get_provider):
        response = self.client.post(
            reverse("assessment-list"),
            {"area_id": self.area.pk, "source": "observations"},
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["status"], "INSUFFICIENT_DATA")
        self.assertEqual(response.data["data_class"], "unavailable")
        get_provider.assert_not_called()

    @patch("apps.assessments.engine.get_weather_provider")
    def test_demo_assessment_handles_missing_provider_indicators(self, get_provider):
        get_provider.return_value.fetch_weather.return_value = {
            "source": "Synthetic test scenario",
            "data_class": "illustrative",
            "location": "Meerut",
            "spatial_resolution": "illustrative_city_level",
            "retrieved_at": "2026-11-24T00:00:00+00:00",
            "quality_status": "ILLUSTRATIVE_NOT_OBSERVED",
            "observations": [
                {
                    "indicator_code": "AIR_TEMPERATURE",
                    "value": 38,
                    "unit": "degree_celsius",
                }
            ],
        }

        response = self.client.post(
            reverse("assessment-list"),
            {
                "area_id": self.area.pk,
                "source": "demo",
                "scenario": "moderate",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        indicators = {
            item["indicator_code"]: item
            for item in response.data["indicators"]
        }
        self.assertIsNone(indicators["RELATIVE_HUMIDITY"]["input_value_numeric"])
        self.assertIsNone(indicators["RELATIVE_HUMIDITY"]["normalized_value"])

    @patch("apps.assessments.engine.get_weather_provider")
    def test_demo_scenario_values_are_used_and_persisted(self, get_provider):
        get_provider.return_value = DemoWeatherProvider()
        scenarios = {
            "hot_dry": (42, 25, 0, "INSUFFICIENT_DATA"),
            "hot_humid": (39, 80, 2, "SCORED"),
            "moderate": (28, 55, 5, "SCORED"),
            "heavy_rainfall": (26, 90, 45, "SCORED"),
        }

        for scenario_id, (temperature, humidity, rainfall, expected_status) in scenarios.items():
            with self.subTest(scenario=scenario_id):
                response = self.client.post(
                    reverse("assessment-list"),
                    {
                        "area_id": self.area.pk,
                        "source": "demo",
                        "scenario": scenario_id,
                    },
                    format="json",
                )
                self.assertEqual(response.status_code, 201)
                self.assertEqual(response.data["status"], expected_status)
                self.assertEqual(response.data["data_class"], "illustrative")
                indicators = {
                    item["indicator_code"]: item
                    for item in response.data["indicators"]
                }
                self.assertEqual(
                    Decimal(indicators["AIR_TEMPERATURE"]["input_value_numeric"]),
                    Decimal(temperature),
                )
                self.assertEqual(
                    Decimal(indicators["RELATIVE_HUMIDITY"]["input_value_numeric"]),
                    Decimal(humidity),
                )
                snapshot = response.data["configuration_snapshot"]["input_snapshot"]
                self.assertEqual(snapshot["scenario_id"], scenario_id)
                self.assertEqual(snapshot["scenario_name"], DemoWeatherProvider().fetch_weather(
                    "Meerut",
                    scenario_id=scenario_id,
                )["scenario_name"])
                self.assertEqual(
                    snapshot["observations"][2]["value"],
                    rainfall,
                )

    def test_demo_scenario_is_rejected_for_stored_observation_source(self):
        response = self.client.post(
            reverse("assessment-list"),
            {
                "area_id": self.area.pk,
                "source": "observations",
                "scenario": "moderate",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    @patch("apps.assessments.engine.get_weather_provider")
    def test_session_login_can_create_assessment_with_csrf(self, get_provider):
        get_provider.return_value = DemoWeatherProvider()
        user = get_user_model().objects.create_user(
            username="session-assessment-tester",
            password="session-test-password-2026",
        )
        session_client = APIClient(enforce_csrf_checks=True)
        csrf = session_client.get(reverse("auth-csrf"))
        self.assertEqual(csrf.status_code, 200)

        login = session_client.post(
            reverse("auth-login"),
            {
                "username": user.username,
                "password": "session-test-password-2026",
            },
            format="json",
            HTTP_X_CSRFTOKEN=csrf.data["csrfToken"],
        )
        self.assertEqual(login.status_code, 200)
        self.assertIn("sessionid", session_client.cookies)

        missing_csrf = session_client.post(
            reverse("assessment-list"),
            {"area_id": self.area.pk, "source": "demo"},
            format="json",
        )
        self.assertEqual(missing_csrf.status_code, 403)

        created = session_client.post(
            reverse("assessment-list"),
            {"area_id": self.area.pk, "source": "demo"},
            format="json",
            HTTP_X_CSRFTOKEN=login.data["csrfToken"],
        )
        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.data["data_class"], "illustrative")

    def setUp(self):
        self.city = City.objects.create(
            name="Meerut",
            state_name="Uttar Pradesh",
            country_code="IN",
            status="ACTIVE",
        )
        self.area = Area.objects.create(
            city=self.city,
            area_name="Meerut city level",
            area_type="city",
        )
        self.client = APIClient()
        user = get_user_model().objects.create_user(
            username="assessment-tester",
            password="test-password",
        )
        self.user = user
        self.client.force_authenticate(user=user)

    @patch("apps.assessments.engine.get_weather_provider")
    def test_create_demo_assessment_and_retrieve_history_and_detail(self, get_provider):
        get_provider.return_value = DemoWeatherProvider()
        response = self.client.post(
            reverse("assessment-list"),
            {"area_id": self.area.pk, "source": "demo"},
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["status"], "SCORED")
        self.assertEqual(response.data["data_class"], "illustrative")
        self.assertEqual(response.data["score"], "58.00")
        self.assertEqual(
            response.data["configuration_snapshot"]["configuration_version"],
            response.data["configuration_version"],
        )
        self.assertTrue(any("Illustrative" in warning for warning in response.data["warnings"]))
        self.assertEqual(len(response.data["indicators"]), 2)

        detail = self.client.get(
            reverse("assessment-detail", kwargs={"pk": response.data["id"]})
        )
        self.assertEqual(detail.status_code, 200)
        history = self.client.get(
            reverse("area-assessment-history", kwargs={"area_id": self.area.pk})
        )
        self.assertEqual(history.status_code, 200)
        self.assertEqual(len(history.data["results"]), 1)
        self.assertEqual(response.data["recommendations"], [])

        recommendation_response = self.client.get(
            reverse(
                "assessment-recommendations",
                kwargs={"pk": response.data["id"]},
            )
        )
        self.assertEqual(recommendation_response.status_code, 200)
        self.assertEqual(
            recommendation_response.data,
            {"assessment_id": response.data["id"], "results": []},
        )

    def test_observation_request_without_usable_inputs_reports_unavailable(self):
        response = self.client.post(
            reverse("assessment-list"),
            {"area_id": self.area.pk, "source": "observations"},
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["status"], "INSUFFICIENT_DATA")
        self.assertEqual(response.data["data_coverage"], "0.00")
        self.assertEqual(response.data["data_class"], "unavailable")
        self.assertIsNone(response.data["score"])
        self.assertTrue(
            any(
                "data class is unavailable" in warning
                for warning in response.data["warnings"]
            )
        )

    @patch("apps.assessments.engine.get_weather_provider")
    def test_setup_rules_are_listed_and_attached_with_explanations(
        self,
        get_provider,
    ):
        call_command("setup_recommendation_rules", stdout=StringIO())
        get_provider.return_value = DemoWeatherProvider()

        active_rules = self.client.get(
            reverse("recommendation-rule-list")
        )
        self.assertEqual(active_rules.status_code, 200)
        self.assertEqual(len(active_rules.data["results"]), 4)
        self.assertTrue(
            all(item["version"] == "1.0.0" for item in active_rules.data["results"])
        )

        created = self.client.post(
            reverse("assessment-list"),
            {"area_id": self.area.pk, "source": "demo"},
            format="json",
        )
        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.data["data_class"], "illustrative")
        recommendations = created.data["recommendations"]
        self.assertEqual(
            [item["rule_code"] for item in recommendations],
            [
                "HIGH_TEMPERATURE_AWARENESS",
                "MODERATE_CATEGORY_MONITORING",
            ],
        )
        self.assertEqual(
            [item["priority"] for item in recommendations],
            ["high", "medium"],
        )
        self.assertTrue(
            all(item["rule_version_applied"] == "1.0.0" for item in recommendations)
        )
        self.assertTrue(
            all(
                item["content_snapshot_available"]
                and "matched:" in item["trigger_explanation"]
                for item in recommendations
            )
        )

        applied = self.client.get(
            reverse(
                "assessment-recommendations",
                kwargs={"pk": created.data["id"]},
            )
        )
        self.assertEqual(applied.status_code, 200)
        self.assertEqual(applied.data["results"], recommendations)

    def test_insufficient_data_gets_data_gap_recommendation(self):
        call_command("setup_recommendation_rules", stdout=StringIO())
        created = self.client.post(
            reverse("assessment-list"),
            {"area_id": self.area.pk, "source": "observations"},
            format="json",
        )

        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.data["status"], "INSUFFICIENT_DATA")
        self.assertEqual(
            [item["rule_code"] for item in created.data["recommendations"]],
            ["INSUFFICIENT_DATA_AWARENESS"],
        )
        self.assertIsNone(created.data["score"])
        self.assertEqual(created.data["data_class"], "unavailable")

    def test_assessment_list_uses_page_number_pagination(self):
        with patch("apps.assessments.engine.get_weather_provider") as get_provider:
            get_provider.return_value = DemoWeatherProvider()
            for _ in range(3):
                response = self.client.post(
                    reverse("assessment-list"),
                    {"area_id": self.area.pk, "source": "demo"},
                    format="json",
                )
                self.assertEqual(response.status_code, 201)

        response = self.client.get(
            reverse("assessment-list"),
            {"page_size": 1},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 3)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertIsNotNone(response.data["next"])

        history = self.client.get(
            reverse("area-assessment-history", kwargs={"area_id": self.area.pk}),
            {"page_size": 1},
        )
        self.assertEqual(history.status_code, 200)
        self.assertEqual(history.data["count"], 3)
        self.assertEqual(len(history.data["results"]), 1)

    def test_assessment_list_reuses_prefetched_recommendations(self):
        for _ in range(3):
            AssessmentRun.objects.create(
                area=self.area,
                user=self.user,
                method_version="method-v1",
                configuration_version="config-v1",
                data_coverage=Decimal("0.00"),
                data_class="observed",
                status="INSUFFICIENT_DATA",
                run_at=timezone.now(),
            )

        with self.assertNumQueries(4):
            response = self.client.get(reverse("assessment-list"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 3)

    @patch("apps.assessments.engine.get_weather_provider")
    def test_recommendation_endpoint_returns_applied_rule_version(self, get_provider):
        get_provider.return_value = DemoWeatherProvider()
        rule = RecommendationRule.objects.create(
            rule_code="DEMO_RULE",
            title="Demo response",
            condition_config={
                "all": [
                    {"field": "score", "operator": "gte", "value": 50}
                ]
            },
            recommendation_text="Review shade and hydration options.",
            priority="medium",
            version="demo-v4",
            is_active=True,
        )
        create_response = self.client.post(
            reverse("assessment-list"),
            {"area_id": self.area.pk, "source": "demo"},
            format="json",
        )
        self.assertEqual(create_response.status_code, 201)

        response = self.client.get(
            reverse(
                "assessment-recommendations",
                kwargs={"pk": create_response.data["id"]},
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["rule_version_applied"], "demo-v4")
        self.assertEqual(response.data["results"][0]["rule_code"], rule.rule_code)
        self.assertEqual(response.data["results"][0]["title"], "Demo response")
        self.assertEqual(
            response.data["results"][0]["recommendation_text"],
            "Review shade and hydration options.",
        )
        self.assertTrue(
            response.data["results"][0]["content_snapshot_available"]
        )

        rule.title = "Edited later"
        rule.recommendation_text = "Changed after the assessment."
        rule.priority = "low"
        rule.version = "demo-v5"
        rule.save()

        history = self.client.get(
            reverse(
                "assessment-recommendations",
                kwargs={"pk": create_response.data["id"]},
            )
        )
        self.assertEqual(history.data["results"][0]["title"], "Demo response")
        self.assertEqual(
            history.data["results"][0]["recommendation_text"],
            "Review shade and hydration options.",
        )
        self.assertEqual(history.data["results"][0]["priority"], "medium")
        self.assertEqual(history.data["results"][0]["rule_version_applied"], "demo-v4")

    def test_legacy_recommendations_do_not_use_current_rule_content(self):
        run = AssessmentRun.objects.create(
            area=self.area,
            user=self.user,
            method_version="method-v1",
            configuration_version="config-v1",
            data_class="unavailable",
            status="INSUFFICIENT_DATA",
            run_at=timezone.now(),
        )
        rule = RecommendationRule.objects.create(
            rule_code="LEGACY_RULE",
            title="Current mutable title",
            condition_config={
                "all": [{"field": "score", "operator": "gte", "value": 50}]
            },
            recommendation_text="Current mutable recommendation.",
            priority="high",
            version="v2",
        )
        AssessmentRecommendation.objects.create(
            assessment_run=run,
            recommendation_rule=rule,
            rule_version_applied="v1",
            rule_snapshot=None,
        )

        response = self.client.get(
            reverse("assessment-recommendations", kwargs={"pk": run.pk})
        )

        self.assertEqual(response.status_code, 200)
        recommendation = response.data["results"][0]
        self.assertFalse(recommendation["content_snapshot_available"])
        self.assertIsNone(recommendation["title"])
        self.assertIsNone(recommendation["recommendation_text"])
        self.assertIsNone(recommendation["priority"])

    def test_invalid_area_returns_not_found(self):
        response = self.client.post(
            reverse("assessment-list"),
            {"area_id": 999999, "source": "demo"},
            format="json",
        )

        self.assertEqual(response.status_code, 404)

    def test_invalid_source_returns_bad_request(self):
        response = self.client.post(
            reverse("assessment-list"),
            {"area_id": self.area.pk, "source": "imd"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)

    def test_assessment_write_requires_authentication(self):
        self.client.force_authenticate(user=None)
        response = self.client.post(
            reverse("assessment-list"),
            {"area_id": self.area.pk, "source": "demo"},
            format="json",
        )

        self.assertEqual(response.status_code, 401)

    def test_anonymous_assessment_history_and_detail_are_private(self):
        run = AssessmentRun.objects.create(
            area=self.area,
            user=self.user,
            method_version="method-v1",
            configuration_version="config-v1",
            data_class="observed",
            status="INSUFFICIENT_DATA",
            run_at=timezone.now(),
        )
        self.client.force_authenticate(user=None)

        list_response = self.client.get(reverse("assessment-list"))
        detail_response = self.client.get(
            reverse("assessment-detail", kwargs={"pk": run.pk})
        )
        history_response = self.client.get(
            reverse("area-assessment-history", kwargs={"area_id": self.area.pk})
        )
        latest_response = self.client.get(
            reverse("area-latest-assessment", kwargs={"area_id": self.area.pk})
        )
        recommendations_response = self.client.get(
            reverse("assessment-recommendations", kwargs={"pk": run.pk})
        )

        self.assertEqual(list_response.status_code, 401)
        self.assertEqual(detail_response.status_code, 401)
        self.assertEqual(history_response.status_code, 401)
        self.assertEqual(latest_response.status_code, 401)
        self.assertEqual(recommendations_response.status_code, 401)

    def test_cross_user_assessment_detail_is_not_found(self):
        run = AssessmentRun.objects.create(
            area=self.area,
            user=self.user,
            method_version="method-v1",
            configuration_version="config-v1",
            data_class="observed",
            status="INSUFFICIENT_DATA",
            run_at=timezone.now(),
        )
        second_user = get_user_model().objects.create_user(
            username="second-assessment-owner",
            password="test-only-password",
        )
        second_client = APIClient()
        second_client.force_authenticate(user=second_user)

        detail = second_client.get(
            reverse("assessment-detail", kwargs={"pk": run.pk})
        )
        history = second_client.get(
            reverse("area-assessment-history", kwargs={"area_id": self.area.pk})
        )
        latest = second_client.get(
            reverse("area-latest-assessment", kwargs={"area_id": self.area.pk})
        )
        recommendations = second_client.get(
            reverse("assessment-recommendations", kwargs={"pk": run.pk})
        )

        self.assertEqual(detail.status_code, 404)
        self.assertEqual(history.data["count"], 0)
        self.assertEqual(latest.status_code, 404)
        self.assertEqual(recommendations.status_code, 404)

    @patch("apps.assessments.engine.get_weather_provider")
    def test_idempotent_retry_replays_the_same_assessment(self, get_provider):
        get_provider.return_value = DemoWeatherProvider()
        request_data = {"area_id": self.area.pk, "source": "demo"}

        first = self.client.post(
            reverse("assessment-list"),
            request_data,
            format="json",
            HTTP_IDEMPOTENCY_KEY="assessment-retry-1",
        )
        replay = self.client.post(
            reverse("assessment-list"),
            request_data,
            format="json",
            HTTP_IDEMPOTENCY_KEY="ASSESSMENT-RETRY-1",
        )

        self.assertEqual(first.status_code, 201)
        self.assertEqual(replay.status_code, 200)
        self.assertEqual(first.data["id"], replay.data["id"])
        self.assertEqual(replay["Idempotency-Replayed"], "true")
        self.assertEqual(AssessmentRun.objects.count(), 1)

    @patch("apps.assessments.engine.get_weather_provider")
    def test_idempotency_keys_are_scoped_to_the_authenticated_user(self, get_provider):
        get_provider.return_value = DemoWeatherProvider()
        second_user = get_user_model().objects.create_user(
            username="second-assessment-tester",
            password="test-password",
        )
        second_client = APIClient()
        second_client.force_authenticate(user=second_user)

        first = self.client.post(
            reverse("assessment-list"),
            {"area_id": self.area.pk, "source": "demo"},
            format="json",
            HTTP_IDEMPOTENCY_KEY="user-scoped-key",
        )
        second = second_client.post(
            reverse("assessment-list"),
            {"area_id": self.area.pk, "source": "demo"},
            format="json",
            HTTP_IDEMPOTENCY_KEY="user-scoped-key",
        )

        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 201)
        self.assertNotEqual(first.data["id"], second.data["id"])
        self.assertEqual(AssessmentRun.objects.count(), 2)

    @patch("apps.assessments.engine.get_weather_provider")
    def test_idempotency_key_reuse_with_different_payload_conflicts(
        self,
        get_provider,
    ):
        get_provider.return_value = DemoWeatherProvider()
        first = self.client.post(
            reverse("assessment-list"),
            {"area_id": self.area.pk, "source": "demo"},
            format="json",
            HTTP_IDEMPOTENCY_KEY="assessment-retry-2",
        )
        conflict = self.client.post(
            reverse("assessment-list"),
            {"area_id": self.area.pk, "source": "observations"},
            format="json",
            HTTP_IDEMPOTENCY_KEY="assessment-retry-2",
        )

        self.assertEqual(first.status_code, 201)
        self.assertEqual(conflict.status_code, 409)
        self.assertEqual(
            conflict.data["error"]["code"],
            "IDEMPOTENCY_KEY_REUSED",
        )
        self.assertEqual(AssessmentRun.objects.count(), 1)

    def test_invalid_idempotency_key_is_rejected(self):
        response = self.client.post(
            reverse("assessment-list"),
            {"area_id": self.area.pk, "source": "observations"},
            format="json",
            HTTP_IDEMPOTENCY_KEY="invalid key",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data["error"]["code"],
            "INVALID_IDEMPOTENCY_KEY",
        )

    @patch(
        "apps.assessments.models.AssessmentIdempotencyRecord.save",
        side_effect=RuntimeError("idempotency persistence failure"),
    )
    @patch("apps.assessments.engine.get_weather_provider")
    def test_idempotency_persistence_failure_rolls_back_assessment(
        self,
        get_provider,
        save_record,
    ):
        get_provider.return_value = DemoWeatherProvider()

        with self.assertRaisesRegex(RuntimeError, "idempotency persistence failure"):
            self.client.post(
                reverse("assessment-list"),
                {"area_id": self.area.pk, "source": "demo"},
                format="json",
                HTTP_IDEMPOTENCY_KEY="rollback-assessment",
            )

        self.assertEqual(AssessmentRun.objects.count(), 0)
        self.assertEqual(AssessmentIndicator.objects.count(), 0)
        self.assertEqual(AssessmentRecommendation.objects.count(), 0)
        self.assertEqual(AssessmentIdempotencyRecord.objects.count(), 0)
        save_record.assert_called_once()

    @patch("apps.assessments.engine.get_weather_provider")
    def test_demo_assessment_rejects_non_meerut_city(self, get_provider):
        city = City.objects.create(
            name="Other City",
            state_name="Example State",
            country_code="IN",
            status="ACTIVE",
        )
        area = Area.objects.create(
            city=city,
            area_name="Other city level",
            area_type="city",
        )
        get_provider.return_value = DemoWeatherProvider()

        response = self.client.post(
            reverse("assessment-list"),
            {"area_id": area.pk, "source": "demo"},
            format="json",
        )

        self.assertEqual(response.status_code, 422)


@skipUnless(
    connection.features.has_select_for_update,
    "This concurrency test requires database row-level SELECT FOR UPDATE locks.",
)
class ConcurrentRecommendationTests(TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        city = City.objects.create(
            name="Meerut",
            state_name="Uttar Pradesh",
            country_code="IN",
            status="ACTIVE",
        )
        area = Area.objects.create(
            city=city,
            area_name="Meerut city level",
            area_type="city",
        )
        self.run = AssessmentRun.objects.create(
            area=area,
            method_version="method-v1",
            configuration_version="config-v1",
            score=Decimal("70.00"),
            data_coverage=Decimal("100.00"),
            data_class="observed",
            status="SCORED",
            run_at=timezone.now(),
        )
        RecommendationRule.objects.create(
            rule_code="CONCURRENT_RULE",
            title="Concurrent recommendation",
            condition_config={
                "all": [{"field": "score", "operator": "gte", "value": 50}]
            },
            recommendation_text="Review the area.",
            priority="high",
            version="v1",
            is_active=True,
        )

    def test_concurrent_evaluation_does_not_duplicate_recommendations(self):
        from .recommendations import evaluate_and_store_recommendations

        barrier = Barrier(2)
        run_id = self.run.pk

        def evaluate():
            close_old_connections()
            try:
                run = AssessmentRun.objects.get(pk=run_id)
                barrier.wait(timeout=10)
                evaluate_and_store_recommendations(run)
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(lambda _: evaluate(), range(2)))

        self.assertEqual(results, [None, None])
        self.assertEqual(
            AssessmentRecommendation.objects.filter(
                assessment_run_id=run_id
            ).count(),
            1,
        )


@skipUnless(
    connection.features.has_select_for_update,
    "This concurrency test requires database row-level SELECT FOR UPDATE locks.",
)
class ConcurrentAssessmentIdempotencyTests(TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        city = City.objects.create(
            name="Meerut",
            state_name="Uttar Pradesh",
            country_code="IN",
            status="ACTIVE",
        )
        self.area = Area.objects.create(
            city=city,
            area_name="Meerut city level",
            area_type="city",
        )
        self.user = get_user_model().objects.create_user(
            username="idempotency-tester",
            password="test-password",
        )

    def test_concurrent_same_key_requests_create_one_assessment(self):
        from .engine import assess_area as create_assessment

        barrier = Barrier(2)
        url = reverse("assessment-list")

        def synchronized_assessment(
            area,
            *,
            source,
            scenario_id=None,
            user=None,
            assessment_mode="current",
        ):
            barrier.wait(timeout=10)
            return create_assessment(
                area,
                source=source,
                scenario_id=scenario_id,
                user=user,
                assessment_mode=assessment_mode,
            )

        def post_assessment():
            close_old_connections()
            try:
                client = APIClient()
                client.force_authenticate(user=self.user)
                response = client.post(
                    url,
                    {"area_id": self.area.pk, "source": "observations"},
                    format="json",
                    HTTP_IDEMPOTENCY_KEY="concurrent-assessment-1",
                )
                return response.status_code, response.data["id"]
            finally:
                close_old_connections()

        with patch(
            "apps.assessments.views.assess_area",
            side_effect=synchronized_assessment,
        ):
            with ThreadPoolExecutor(max_workers=2) as executor:
                results = list(executor.map(lambda _: post_assessment(), range(2)))

        self.assertCountEqual([status_code for status_code, _ in results], [200, 201])
        self.assertEqual(len({run_id for _, run_id in results}), 1)
        self.assertEqual(AssessmentRun.objects.count(), 1)
        self.assertEqual(AssessmentIdempotencyRecord.objects.count(), 1)


class AssessmentExportAPITests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="export-owner",
            password="test-only-password",
        )
        self.other_user = get_user_model().objects.create_user(
            username="other-user",
            password="test-only-password",
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

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
        self.run = AssessmentRun.objects.create(
            area=self.area,
            user=self.user,
            method_version="weighted-relative-index-v1",
            configuration_version="config-v1",
            score=Decimal("45.50"),
            risk_category="illustrative_moderate",
            data_coverage=Decimal("100.00"),
            data_class="derived",
            status="SCORED",
            run_at=timezone.now(),
        )
        self.indicator = AssessmentIndicator.objects.create(
            assessment_run=self.run,
            indicator_code="AIR_TEMPERATURE",
            input_value_numeric=Decimal("30.0"),
            normalized_value=Decimal("0.25"),
            weight_used=Decimal("0.70"),
            contribution=Decimal("0.175"),
            quality_status="VALID",
            explanation="Temperature observation",
        )

    def test_csv_export_returns_csv_file_with_expected_headers(self):
        url = reverse("assessment-export", kwargs={"pk": self.run.pk})
        response = self.client.get(
            url,
            {"format": "csv"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv; charset=utf-8")
        self.assertIn(f'attachment; filename="heatshield-assessment-{self.run.pk}.csv"', response["Content-Disposition"])
        content = response.content.decode("utf-8")
        self.assertIn("HeatShield AI — Assessment Report", content)
        self.assertIn("Meerut City", content)
        self.assertIn("45.50", content)
        self.assertIn("AIR_TEMPERATURE", content)
        self.assertIn("Disclaimers & Limitations", content)

    def test_html_export_returns_printable_html_report(self):
        response = self.client.get(
            reverse("assessment-export", kwargs={"pk": self.run.pk}),
            {"format": "html"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/html; charset=utf-8")
        content = response.content.decode("utf-8")
        self.assertIn("HeatShield AI Assessment Report", content)
        self.assertIn("45.50", content)
        self.assertIn("AIR_TEMPERATURE", content)
        self.assertIn("window.print()", content)

    def test_anonymous_export_returns_401(self):
        self.client.force_authenticate(user=None)
        response = self.client.get(
            reverse("assessment-export", kwargs={"pk": self.run.pk}),
        )
        self.assertEqual(response.status_code, 401)

    def test_cross_user_export_returns_404(self):
        self.client.force_authenticate(user=self.other_user)
        response = self.client.get(
            reverse("assessment-export", kwargs={"pk": self.run.pk}),
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data["error"]["code"], "ASSESSMENT_NOT_FOUND")

    def test_invalid_export_format_returns_400(self):
        response = self.client.get(
            reverse("assessment-export", kwargs={"pk": self.run.pk}),
            {"format": "invalid_format"},
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["error"]["code"], "INVALID_EXPORT_FORMAT")

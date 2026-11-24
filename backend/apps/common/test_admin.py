from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.assessments.models import (
    AssessmentIdempotencyRecord,
    AssessmentIndicator,
    AssessmentRecommendation,
    AssessmentRun,
    RecommendationRule,
)
from apps.cities.models import Area, City
from apps.datasets.models import DataSource, Dataset
from apps.indicators.models import IndicatorObservation


ADMIN_MODELS = (
    City,
    Area,
    DataSource,
    Dataset,
    IndicatorObservation,
    AssessmentRun,
    AssessmentIndicator,
    RecommendationRule,
    AssessmentRecommendation,
    AssessmentIdempotencyRecord,
)

CHANGE_LIST_FILTERS = {
    City: {"country_code__exact": "IN", "status__exact": "ACTIVE"},
    Area: {"city__id__exact": "1", "area_type__exact": "city"},
    DataSource: {"approval_status__exact": "APPROVED"},
    Dataset: {"data_class__exact": "illustrative", "is_active__exact": "1"},
    IndicatorObservation: {
        "quality_status__exact": "VALID",
        "period_end__gte": "2026-01-01",
    },
    AssessmentRun: {"status__exact": "SCORED", "data_class__exact": "observed"},
    AssessmentIndicator: {
        "quality_status__exact": "VALID",
        "assessment_run__status__exact": "SCORED",
    },
    RecommendationRule: {"priority__exact": "high", "is_active__exact": "1"},
    AssessmentRecommendation: {"recommendation_rule__priority__exact": "high"},
    AssessmentIdempotencyRecord: {},
}


class DjangoAdminTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.admin_user = User.objects.create_superuser(
            username="admin-test",
            email="admin-test@example.test",
            password="test-password-only-for-test-db",
        )
        cls.regular_user = User.objects.create_user(
            username="regular-test",
            email="regular-test@example.test",
            password="test-password-only-for-test-db",
        )

    def test_expected_custom_models_are_registered_once(self):
        self.assertEqual(len(ADMIN_MODELS), 10)
        for model in ADMIN_MODELS:
            with self.subTest(model=model.__name__):
                self.assertTrue(admin.site.is_registered(model))

    def test_admin_requires_staff_access(self):
        self.client.force_login(self.regular_user)
        response = self.client.get(reverse("admin:index"))
        self.assertEqual(response.status_code, 302)

        self.client.logout()
        response = self.client.post(
            reverse("admin:login"),
            {
                "username": "admin-test",
                "password": "test-password-only-for-test-db",
                "next": reverse("admin:index"),
            },
        )
        self.assertEqual(response.status_code, 302)
        response = self.client.get(reverse("admin:index"))
        self.assertEqual(response.status_code, 200)

    def test_all_custom_changelists_load_with_search_and_filters(self):
        self.client.force_login(self.admin_user)
        for model in ADMIN_MODELS:
            changelist_url = reverse(
                f"admin:{model._meta.app_label}_{model._meta.model_name}_changelist"
            )
            query = {"q": "1", **CHANGE_LIST_FILTERS[model]}
            with self.subTest(model=model.__name__):
                response = self.client.get(changelist_url, query)
                self.assertEqual(response.status_code, 200)

    def test_datetime_changelists_load_with_safe_date_filters(self):
        self.client.force_login(self.admin_user)
        datetime_filters = (
            (AssessmentRun, "run_at"),
            (Dataset, "retrieved_at"),
            (AssessmentRecommendation, "created_at"),
        )
        for model, field_name in datetime_filters:
            with self.subTest(model=model.__name__):
                model_admin = admin.site._registry[model]
                self.assertIsNone(getattr(model_admin, "date_hierarchy", None))
                self.assertIn(
                    (field_name, admin.DateFieldListFilter),
                    model_admin.list_filter,
                )
                changelist_url = reverse(
                    f"admin:{model._meta.app_label}_{model._meta.model_name}_changelist"
                )
                response = self.client.get(
                    changelist_url,
                    {f"{field_name}__gte": "2026-11-24"},
                )
                self.assertEqual(response.status_code, 200)

    def test_date_field_hierarchy_changelist_loads(self):
        self.client.force_login(self.admin_user)
        model_admin = admin.site._registry[IndicatorObservation]
        self.assertEqual(model_admin.date_hierarchy, "period_end")
        response = self.client.get(
            reverse("admin:indicators_indicatorobservation_changelist")
        )
        self.assertEqual(response.status_code, 200)

    def test_historical_assessment_admins_are_read_only(self):
        historical_models = (
            AssessmentRun,
            AssessmentIndicator,
            AssessmentRecommendation,
            AssessmentIdempotencyRecord,
        )
        for model in historical_models:
            with self.subTest(model=model.__name__):
                model_admin = admin.site._registry[model]
                self.assertFalse(model_admin.has_add_permission(None))
                self.assertFalse(model_admin.has_delete_permission(None))
                readonly_fields = set(model_admin.readonly_fields)
                if model is not AssessmentIdempotencyRecord:
                    self.assertTrue(
                        {field.name for field in model._meta.fields}
                        <= readonly_fields
                    )
                else:
                    self.assertIn("request_fingerprint", model_admin.exclude)
                    self.assertNotIn("request_fingerprint", model_admin.readonly_fields)
                    self.assertTrue(
                        {"id", "user", "key", "assessment_run"} <= readonly_fields
                    )

        self.assertIn(
            "configuration_snapshot",
            admin.site._registry[AssessmentRun].readonly_fields,
        )
        self.assertIn(
            "rule_snapshot",
            admin.site._registry[AssessmentRecommendation].readonly_fields,
        )

    def test_assessment_admin_rejects_add_and_ignores_change_attempts(self):
        city = City.objects.create(
            name="Admin Test City",
            state_name="Test State",
            country_code="IN",
            status="ACTIVE",
        )
        area = Area.objects.create(
            city=city,
            area_name="Admin Test Area",
            area_type="city",
        )
        assessment = AssessmentRun.objects.create(
            area=area,
            method_version="test-method-v1",
            configuration_version="test-config-v1",
            configuration_snapshot={"version": "original"},
            score="42.00",
            data_class="observed",
            status="SCORED",
            run_at=timezone.now(),
        )

        self.client.force_login(self.admin_user)
        add_url = reverse("admin:assessments_assessmentrun_add")
        self.assertEqual(self.client.get(add_url).status_code, 403)

        change_url = reverse(
            "admin:assessments_assessmentrun_change",
            args=(assessment.pk,),
        )
        response = self.client.post(
            change_url,
            {
                "score": "99.99",
                "status": "REVIEW_REQUIRED",
                "configuration_snapshot": '{"version": "changed"}',
                "_save": "Save",
            },
        )
        self.assertEqual(response.status_code, 302)

        assessment.refresh_from_db()
        self.assertEqual(assessment.score, 42)
        self.assertEqual(
            assessment.configuration_snapshot,
            {"version": "original"},
        )
        self.assertEqual(assessment.status, "SCORED")

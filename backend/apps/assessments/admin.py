from django.contrib import admin

from .models import (
    AssessmentIdempotencyRecord,
    AssessmentIndicator,
    AssessmentRecommendation,
    AssessmentRun,
    RecommendationRule,
)


class HistoricalRecordAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return self.has_view_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(AssessmentRun)
class AssessmentRunAdmin(HistoricalRecordAdmin):
    list_display = (
        "id",
        "area",
        "score",
        "risk_category",
        "data_coverage",
        "status",
        "run_at",
    )
    search_fields = ("=id", "area__area_name", "area__city__name", "risk_category")
    list_filter = (
        "status",
        "risk_category",
        "data_class",
        "area__city",
        ("run_at", admin.DateFieldListFilter),
    )
    ordering = ("-run_at",)
    list_select_related = ("area", "area__city")
    list_per_page = 50
    show_full_result_count = False
    readonly_fields = (
        "id",
        "area",
        "user",
        "method_version",
        "configuration_version",
        "configuration_snapshot",
        "assessment_warnings",
        "score",
        "risk_category",
        "data_coverage",
        "data_class",
        "status",
        "run_at",
    )


@admin.register(AssessmentIndicator)
class AssessmentIndicatorAdmin(HistoricalRecordAdmin):
    list_display = (
        "assessment_run",
        "indicator_code",
        "normalized_value",
        "contribution",
        "quality_status",
    )
    search_fields = (
        "indicator_code",
        "assessment_run__area__area_name",
        "assessment_run__area__city__name",
        "assessment_run__risk_category",
    )
    list_filter = ("quality_status", "assessment_run__status")
    ordering = ("indicator_code",)
    list_select_related = ("assessment_run", "assessment_run__area")
    list_per_page = 50
    show_full_result_count = False
    readonly_fields = tuple(field.name for field in AssessmentIndicator._meta.fields)


@admin.register(RecommendationRule)
class RecommendationRuleAdmin(admin.ModelAdmin):
    list_display = ("rule_code", "title", "priority", "version", "is_active")
    search_fields = ("rule_code", "title")
    list_filter = ("priority", "is_active")
    ordering = ("priority", "rule_code")
    readonly_fields = ("id",)


@admin.register(AssessmentRecommendation)
class AssessmentRecommendationAdmin(HistoricalRecordAdmin):
    list_display = (
        "assessment_run",
        "recommendation_rule",
        "rule_version_applied",
        "created_at",
    )
    search_fields = (
        "recommendation_rule__rule_code",
        "recommendation_rule__title",
        "assessment_run__area__area_name",
    )
    list_filter = (
        "recommendation_rule__priority",
        ("created_at", admin.DateFieldListFilter),
    )
    ordering = ("-created_at",)
    list_select_related = (
        "assessment_run",
        "assessment_run__area",
        "recommendation_rule",
    )
    list_per_page = 50
    show_full_result_count = False
    readonly_fields = tuple(
        field.name for field in AssessmentRecommendation._meta.fields
    )


@admin.register(AssessmentIdempotencyRecord)
class AssessmentIdempotencyRecordAdmin(HistoricalRecordAdmin):
    list_display = ("id", "user", "key", "assessment_run")
    search_fields = (
        "user__username",
        "user__email",
        "key",
        "assessment_run__id",
    )
    ordering = ("-id",)
    list_select_related = ("user", "assessment_run", "assessment_run__area")
    list_per_page = 50
    show_full_result_count = False
    readonly_fields = ("id", "user", "key", "assessment_run")
    exclude = ("request_fingerprint",)
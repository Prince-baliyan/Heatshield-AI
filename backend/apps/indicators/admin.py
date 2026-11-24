from django.contrib import admin

from .models import IndicatorObservation


@admin.register(IndicatorObservation)
class IndicatorObservationAdmin(admin.ModelAdmin):
    list_display = (
        "area",
        "dataset",
        "indicator_code",
        "period_start",
        "period_end",
        "quality_status",
    )
    search_fields = (
        "indicator_code",
        "area__area_name",
        "area__city__name",
        "dataset__dataset_name",
        "dataset__source__source_name",
    )
    list_filter = (
        "quality_status",
        ("period_start", admin.DateFieldListFilter),
        ("period_end", admin.DateFieldListFilter),
    )
    ordering = ("-period_end", "indicator_code")
    list_select_related = ("area", "area__city", "dataset", "dataset__source")
    list_per_page = 50
    show_full_result_count = False
    date_hierarchy = "period_end"
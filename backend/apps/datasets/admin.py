from django.contrib import admin

from .models import DataSource, Dataset


@admin.register(DataSource)
class DataSourceAdmin(admin.ModelAdmin):
    list_display = ("source_name", "owner_name", "approval_status", "created_at")
    search_fields = ("source_name", "owner_name")
    list_filter = ("approval_status",)
    ordering = ("source_name",)
    readonly_fields = ("created_at",)


@admin.register(Dataset)
class DatasetAdmin(admin.ModelAdmin):
    list_display = (
        "dataset_name",
        "source",
        "data_class",
        "spatial_resolution",
        "is_active",
        "retrieved_at",
    )
    search_fields = ("dataset_name", "source__source_name")
    list_filter = (
        "data_class",
        "is_active",
        "source",
        ("retrieved_at", admin.DateFieldListFilter),
    )
    ordering = ("-retrieved_at", "dataset_name")
    list_select_related = ("source",)
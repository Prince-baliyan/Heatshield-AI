from django.contrib import admin

from .models import Area, City


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ("name", "state_name", "country_code", "status", "created_at")
    search_fields = ("name", "state_name")
    list_filter = ("country_code", "status")
    ordering = ("country_code", "state_name", "name")
    readonly_fields = ("created_at",)


@admin.register(Area)
class AreaAdmin(admin.ModelAdmin):
    list_display = (
        "area_name",
        "area_code",
        "city",
        "area_type",
        "latitude",
        "longitude",
    )
    search_fields = ("area_name", "area_code", "city__name", "city__state_name")
    list_filter = ("city", "area_type")
    ordering = ("city__name", "area_name")
    list_select_related = ("city",)
    readonly_fields = ("created_at",)
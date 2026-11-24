from django.urls import path

from .views import (
    AreaComparisonView,
    AreaDetailView,
    AreaListView,
    CityAreaListView,
    CityListView,
)


urlpatterns = [
    path("cities/", CityListView.as_view(), name="city-list"),
    path("areas/", AreaListView.as_view(), name="area-list"),
    path("areas/compare/", AreaComparisonView.as_view(), name="area-compare"),
    path("areas/<int:pk>/", AreaDetailView.as_view(), name="area-detail"),
    path(
        "cities/<int:city_id>/areas/",
        CityAreaListView.as_view(),
        name="city-area-list",
    ),
]

from django.urls import path

from .views import (
    AdminAreaListView,
    DataSourceAdminViewSet,
    DataSourceListView,
    DatasetAdminViewSet,
    DatasetListView,
    IndicatorObservationAdminViewSet,
    IndicatorObservationListView,
    WeatherDataView,
)

urlpatterns = [
    path("weather/", WeatherDataView.as_view(), name="weather-data"),
    path("admin/areas/", AdminAreaListView.as_view(), name="admin-area-list"),
    path("data-sources/", DataSourceListView.as_view(), name="data-source-list"),
    path("datasets/", DatasetListView.as_view(), name="dataset-list"),
    path(
        "observations/",
        IndicatorObservationListView.as_view(),
        name="indicator-observation-list",
    ),
    path(
        "admin/data-sources/",
        DataSourceAdminViewSet.as_view({"get": "list", "post": "create"}),
        name="admin-data-source-list",
    ),
    path(
        "admin/data-sources/<int:pk>/",
        DataSourceAdminViewSet.as_view(
            {"get": "retrieve", "put": "update", "patch": "partial_update"}
        ),
        name="admin-data-source-detail",
    ),
    path(
        "admin/datasets/",
        DatasetAdminViewSet.as_view({"get": "list", "post": "create"}),
        name="admin-dataset-list",
    ),
    path(
        "admin/datasets/<int:pk>/",
        DatasetAdminViewSet.as_view(
            {"get": "retrieve", "put": "update", "patch": "partial_update"}
        ),
        name="admin-dataset-detail",
    ),
    path(
        "admin/observations/",
        IndicatorObservationAdminViewSet.as_view({"get": "list", "post": "create"}),
        name="admin-observation-list",
    ),
    path(
        "admin/observations/<int:pk>/",
        IndicatorObservationAdminViewSet.as_view(
            {"get": "retrieve", "put": "update", "patch": "partial_update"}
        ),
        name="admin-observation-detail",
    ),
]

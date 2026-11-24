from rest_framework.authentication import SessionAuthentication
from rest_framework.generics import ListAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny, BasePermission, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from django.db import models
from django.db.models import Count, Q

from apps.cities.models import Area
from apps.cities.serializers import AreaSerializer
from apps.indicators.models import IndicatorObservation
from .models import DataSource, Dataset
from .providers.factory import get_weather_provider
from .serializers import (
    DataSourceAdminSerializer,
    DataSourceListSerializer,
    DatasetAdminSerializer,
    DatasetListSerializer,
    IndicatorObservationAdminSerializer,
    IndicatorObservationListSerializer,
)


class InventoryPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class IsHeatShieldAdmin(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and (request.user.is_staff or request.user.is_superuser)
        )


class ReadOnlyInventoryListView(ListAPIView):
    authentication_classes = (SessionAuthentication,)
    permission_classes = (IsAuthenticated,)
    pagination_class = InventoryPagination

    def get_authenticate_header(self, request):
        return "Session"


class DataSourceListView(ReadOnlyInventoryListView):
    serializer_class = DataSourceListSerializer

    def get_queryset(self):
        queryset = DataSource.objects.annotate(
            dataset_count=Count(
                "datasets",
                filter=Q(
                    datasets__is_active=True,
                    datasets__source__approval_status__iexact="APPROVED",
                ),
                distinct=True,
            )
        )
        if not (self.request.user.is_staff or self.request.user.is_superuser):
            queryset = queryset.filter(approval_status__iexact="APPROVED")
        status_filter = self.request.query_params.get("approval_status")
        search = self.request.query_params.get("search", "").strip()
        if status_filter:
            queryset = queryset.filter(approval_status__iexact=status_filter)
        if search:
            queryset = queryset.filter(
                models.Q(source_name__icontains=search)
                | models.Q(owner_name__icontains=search)
            )
        return queryset.order_by("source_name", "pk")


class DatasetListView(ReadOnlyInventoryListView):
    serializer_class = DatasetListSerializer

    def get_queryset(self):
        queryset = Dataset.objects.select_related("source")
        if not (self.request.user.is_staff or self.request.user.is_superuser):
            queryset = queryset.filter(
                is_active=True,
                source__approval_status__iexact="APPROVED",
            )
        search = self.request.query_params.get("search", "").strip()
        source_id = self.request.query_params.get("source_id")
        data_class = self.request.query_params.get("data_class")
        is_active = self.request.query_params.get("is_active")
        if search:
            queryset = queryset.filter(
                models.Q(dataset_name__icontains=search)
                | models.Q(source__source_name__icontains=search)
            )
        if source_id:
            queryset = queryset.filter(source_id=source_id)
        if data_class:
            queryset = queryset.filter(data_class=data_class)
        if is_active in {"true", "false"} and (
            self.request.user.is_staff or self.request.user.is_superuser
        ):
            queryset = queryset.filter(is_active=is_active == "true")
        return queryset.order_by("-retrieved_at", "dataset_name", "pk")


class IndicatorObservationListView(ReadOnlyInventoryListView):
    serializer_class = IndicatorObservationListSerializer

    def get_queryset(self):
        queryset = IndicatorObservation.objects.select_related(
            "area__city", "dataset", "dataset__source"
        )
        if not (self.request.user.is_staff or self.request.user.is_superuser):
            queryset = queryset.filter(
                dataset__is_active=True,
                dataset__source__approval_status__iexact="APPROVED",
            )
        search = self.request.query_params.get("search", "").strip()
        area_id = self.request.query_params.get("area_id")
        dataset_id = self.request.query_params.get("dataset_id")
        indicator_code = self.request.query_params.get("indicator_code")
        quality_status = self.request.query_params.get("quality_status")
        period_start = self.request.query_params.get("period_start")
        period_end = self.request.query_params.get("period_end")
        if search:
            queryset = queryset.filter(
                models.Q(indicator_code__icontains=search)
                | models.Q(area__area_name__icontains=search)
                | models.Q(area__city__name__icontains=search)
                | models.Q(dataset__dataset_name__icontains=search)
            )
        if area_id:
            queryset = queryset.filter(area_id=area_id)
        if dataset_id:
            queryset = queryset.filter(dataset_id=dataset_id)
        if indicator_code:
            queryset = queryset.filter(indicator_code=indicator_code)
        if quality_status:
            queryset = queryset.filter(quality_status=quality_status)
        if period_start:
            queryset = queryset.filter(period_start__gte=period_start)
        if period_end:
            queryset = queryset.filter(period_end__lte=period_end)
        return queryset.order_by("-period_end", "indicator_code", "pk")


class AdminDataViewSet(ModelViewSet):
    authentication_classes = (SessionAuthentication,)
    permission_classes = (IsHeatShieldAdmin,)
    pagination_class = InventoryPagination
    http_method_names = ("get", "post", "put", "patch", "head", "options")
    search_fields = ()

    def get_authenticate_header(self, request):
        return "Session"

    def apply_search(self, queryset, fields):
        search = self.request.query_params.get("search", "").strip()
        if not search:
            return queryset
        query = models.Q()
        for field in fields:
            query |= models.Q(**{f"{field}__icontains": search})
        return queryset.filter(query)


class DataSourceAdminViewSet(AdminDataViewSet):
    serializer_class = DataSourceAdminSerializer

    def get_queryset(self):
        return self.apply_search(
            DataSource.objects.all(),
            ("source_name", "owner_name", "approval_status"),
        ).order_by("source_name", "pk")


class DatasetAdminViewSet(AdminDataViewSet):
    serializer_class = DatasetAdminSerializer

    def get_queryset(self):
        queryset = Dataset.objects.select_related("source")
        queryset = self.apply_search(
            queryset,
            ("dataset_name", "source__source_name"),
        )
        source_id = self.request.query_params.get("source_id")
        data_class = self.request.query_params.get("data_class")
        is_active = self.request.query_params.get("is_active")
        if source_id:
            queryset = queryset.filter(source_id=source_id)
        if data_class:
            queryset = queryset.filter(data_class=data_class)
        if is_active in {"true", "false"}:
            queryset = queryset.filter(is_active=is_active == "true")
        return queryset.order_by("-retrieved_at", "dataset_name", "pk")


class IndicatorObservationAdminViewSet(AdminDataViewSet):
    serializer_class = IndicatorObservationAdminSerializer

    def get_queryset(self):
        queryset = IndicatorObservation.objects.select_related(
            "area__city", "dataset", "dataset__source"
        )
        queryset = self.apply_search(
            queryset,
            (
                "indicator_code",
                "area__area_name",
                "area__city__name",
                "dataset__dataset_name",
            ),
        )
        filters = {
            "area_id": "area_id",
            "dataset_id": "dataset_id",
            "indicator_code": "indicator_code",
            "quality_status": "quality_status",
        }
        for parameter, field in filters.items():
            value = self.request.query_params.get(parameter)
            if value:
                queryset = queryset.filter(**{field: value})
        period_start = self.request.query_params.get("period_start")
        period_end = self.request.query_params.get("period_end")
        if period_start:
            queryset = queryset.filter(period_start__gte=period_start)
        if period_end:
            queryset = queryset.filter(period_end__lte=period_end)
        return queryset.order_by("-period_end", "indicator_code", "pk")


class AdminAreaListView(ListAPIView):
    authentication_classes = (SessionAuthentication,)
    permission_classes = (IsHeatShieldAdmin,)
    pagination_class = InventoryPagination
    serializer_class = AreaSerializer

    def get_authenticate_header(self, request):
        return "Session"

    def get_queryset(self):
        return Area.objects.select_related("city").order_by("city__name", "area_name")

    def get_authenticate_header(self, request):
        return "Session"


class WeatherDataView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        location = request.query_params.get("location", "Meerut").strip()
        scenario_id = request.query_params.get("scenario", "standard")

        if not location:
            return Response(
                {"error": "Location is required."},
                status=400,
            )

        try:
            provider = get_weather_provider()
            weather_data = provider.fetch_weather(
                location,
                scenario_id=scenario_id,
            )
            return Response(weather_data)
        except (ValueError, ImportError) as error:
            return Response({"error": str(error)}, status=400)

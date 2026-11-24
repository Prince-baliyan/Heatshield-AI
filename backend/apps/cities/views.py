from django.db.models import Prefetch
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.indicators.models import IndicatorObservation

from .models import Area, City
from .serializers import AreaSerializer, CitySerializer


def _area_queryset():
    return Area.objects.select_related("city").prefetch_related(
        Prefetch(
            "indicator_observations",
            queryset=IndicatorObservation.objects.select_related(
                "dataset",
                "dataset__source",
            ),
            to_attr="_readiness_rows",
        )
    )


def _error(code, message, http_status, details=None):
    error = {"code": code, "message": message}
    if details is not None:
        error["details"] = details
    return Response({"error": error}, status=http_status)


class CityAreaPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class CityListView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        queryset = (
            City.objects.filter(status="ACTIVE")
            .order_by("country_code", "state_name", "name")
        )
        paginator = CityAreaPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        serializer = CitySerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class AreaListView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        city_id = request.query_params.get("city_id")
        queryset = (
            _area_queryset()
            .filter(city__status="ACTIVE")
            .order_by("city", "area_name")
        )

        if city_id is not None:
            if not city_id.isdecimal() or int(city_id) < 1:
                return _error(
                    "INVALID_CITY_ID",
                    "city_id must be a positive integer.",
                    status.HTTP_400_BAD_REQUEST,
                )
            queryset = queryset.filter(city_id=int(city_id))

        paginator = CityAreaPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        serializer = AreaSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class CityAreaListView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request, city_id):
        city = City.objects.filter(pk=city_id, status="ACTIVE").first()
        if city is None:
            return _error(
                "CITY_NOT_FOUND",
                "The requested city does not exist.",
                status.HTTP_404_NOT_FOUND,
            )

        queryset = _area_queryset().filter(city=city).order_by("area_name")
        paginator = CityAreaPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        serializer = AreaSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class AreaDetailView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request, pk):
        area = _area_queryset().filter(pk=pk, city__status="ACTIVE").first()
        if area is None:
            return _error(
                "AREA_NOT_FOUND",
                "The requested area does not exist.",
                status.HTTP_404_NOT_FOUND,
            )
        serializer = AreaSerializer(area)
        return Response(serializer.data)


class AreaComparisonView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        raw_ids = request.query_params.getlist("area_id")
        if not raw_ids:
            param = request.query_params.get("area_ids", "")
            raw_ids = [p.strip() for p in param.split(",") if p.strip()]

        area_ids = []
        for val in raw_ids:
            if not val.isdecimal() or int(val) < 1:
                return _error(
                    "INVALID_COMPARISON_REQUEST",
                    f"Invalid area ID: {val!r}. All area IDs must be positive integers.",
                    status.HTTP_400_BAD_REQUEST,
                )
            area_ids.append(int(val))

        unique_ids = list(dict.fromkeys(area_ids))
        if len(unique_ids) < 2:
            return _error(
                "INVALID_COMPARISON_REQUEST",
                "At least two distinct valid area IDs are required for comparison.",
                status.HTTP_400_BAD_REQUEST,
            )

        areas = list(
            _area_queryset()
            .filter(pk__in=unique_ids, city__status="ACTIVE")
        )
        found_ids = {a.pk for a in areas}
        missing = [aid for aid in unique_ids if aid not in found_ids]
        if missing:
            return _error(
                "AREA_NOT_FOUND",
                f"Area(s) not found: {missing}.",
                status.HTTP_404_NOT_FOUND,
            )

        areas_by_id = {a.pk: a for a in areas}
        ordered_areas = [areas_by_id[aid] for aid in unique_ids]

        from apps.assessments.models import AssessmentRun
        user = request.user if request.user and request.user.is_authenticated else None

        comparison_results = []
        for area in ordered_areas:
            serialized_area = AreaSerializer(area).data
            assessment_qs = AssessmentRun.objects.filter(area=area)
            if user and not (user.is_staff or user.is_superuser):
                assessment_qs = assessment_qs.filter(user=user)
            elif not user:
                assessment_qs = assessment_qs.none()

            latest_run = assessment_qs.order_by("-run_at", "-pk").first()
            assessment_data = None
            if latest_run is not None:
                from apps.assessments.serializers import AssessmentRunSerializer
                assessment_data = AssessmentRunSerializer(latest_run).data

            comparison_results.append({
                "area": serialized_area,
                "latest_assessment": assessment_data,
            })

        from decimal import Decimal
        scored = [
            item for item in comparison_results
            if item["latest_assessment"] and item["latest_assessment"]["score"] is not None
        ]
        scored_sorted = sorted(
            scored,
            key=lambda x: Decimal(str(x["latest_assessment"]["score"])),
            reverse=True,
        )
        ranking = [
            {
                "rank": idx + 1,
                "area_id": item["area"]["id"],
                "area_name": item["area"]["area_name"],
                "score": item["latest_assessment"]["score"],
                "risk_category": item["latest_assessment"]["risk_category"],
            }
            for idx, item in enumerate(scored_sorted)
        ]

        return Response({
            "comparison_count": len(ordered_areas),
            "results": comparison_results,
            "vulnerability_ranking": ranking,
            "caveats": (
                "Comparative rankings use deterministic relative index scores. "
                "Assessments are scoped to the user's authenticated runs. "
                "Physical measurements are not directly comparable without normalization; "
                "no values are imputed for missing data."
            ),
        })

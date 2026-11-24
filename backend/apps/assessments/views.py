import csv
import hashlib
import io
import json
import logging
import re

from django.core.exceptions import ValidationError
from django.db import DatabaseError, IntegrityError, transaction
from django.db.models import Case, IntegerField, Prefetch, Value, When
from django.http import HttpResponse
from rest_framework import status
from rest_framework.authentication import BasicAuthentication, SessionAuthentication
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.cities.models import Area
from .engine import AssessmentConfigurationError, assess_area
from .models import (
    AssessmentIdempotencyRecord,
    AssessmentRun,
    RecommendationRule,
)
from .serializers import (
    AssessmentRecommendationSerializer,
    AssessmentRunSerializer,
    CreateAssessmentSerializer,
    RecommendationRuleSerializer,
    ordered_recommendation_queryset,
)


logger = logging.getLogger(__name__)
IDEMPOTENCY_KEY_PATTERN = re.compile(r"^[A-Za-z0-9._~:-]{1,128}$")


def _request_fingerprint(validated_data):
    canonical_payload = json.dumps(
        validated_data,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical_payload).hexdigest()


def _error(code, message, http_status, details=None):
    error = {"code": code, "message": message}
    if details is not None:
        error["details"] = details
    return Response({"error": error}, status=http_status)


def _assessment_queryset():
    return (
        AssessmentRun.objects.select_related("area", "area__city")
        .prefetch_related(
            "assessment_indicators",
            Prefetch(
                "assessment_recommendations",
                queryset=ordered_recommendation_queryset(),
                to_attr="_ordered_assessment_recommendations",
            ),
        )
    )


class AssessmentPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class AssessmentAPIView(APIView):
    authentication_classes = (BasicAuthentication, SessionAuthentication)

    def paginated_response(self, queryset, request):
        paginator = AssessmentPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        serializer = AssessmentRunSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def handle_exception(self, exc):
        if isinstance(exc, DatabaseError):
            logger.exception("Database error while handling an assessment API request.")
            return _error(
                "DATABASE_UNAVAILABLE",
                "The assessment service is temporarily unavailable.",
                status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return super().handle_exception(exc)


class AssessmentCollectionView(AssessmentAPIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        if request.user.is_staff or request.user.is_superuser:
            queryset = _assessment_queryset()
        else:
            queryset = _assessment_queryset().filter(user=request.user)
        area_id = request.query_params.get("area_id")
        if area_id is not None:
            if not area_id.isdecimal() or int(area_id) < 1:
                return _error(
                    "INVALID_AREA_ID",
                    "area_id must be a positive integer.",
                    status.HTTP_400_BAD_REQUEST,
                )
            queryset = queryset.filter(area_id=int(area_id))
        runs = queryset.order_by("-run_at", "-pk")
        return self.paginated_response(runs, request)

    def post(self, request):
        serializer = CreateAssessmentSerializer(data=request.data)
        if not serializer.is_valid():
            return _error(
                "INVALID_REQUEST",
                "Assessment request validation failed.",
                status.HTTP_400_BAD_REQUEST,
                serializer.errors,
            )
        idempotency_key = request.headers.get("Idempotency-Key")
        if idempotency_key is not None and not IDEMPOTENCY_KEY_PATTERN.fullmatch(
            idempotency_key
        ):
            return _error(
                "INVALID_IDEMPOTENCY_KEY",
                "Idempotency-Key must contain 1-128 URL-safe characters.",
                status.HTTP_400_BAD_REQUEST,
            )
        if idempotency_key is not None:
            idempotency_key = idempotency_key.lower()
        fingerprint = _request_fingerprint(serializer.validated_data)
        if idempotency_key is not None:
            existing_record = (
                AssessmentIdempotencyRecord.objects.select_related("assessment_run")
                .filter(user=request.user, key=idempotency_key)
                .first()
            )
            if existing_record is not None:
                return self._replay_or_conflict(existing_record, fingerprint)
        area = (
            Area.objects.select_related("city")
            .filter(pk=serializer.validated_data["area_id"])
            .first()
        )
        if area is None:
            return _error(
                "AREA_NOT_FOUND",
                "The requested area does not exist.",
                status.HTTP_404_NOT_FOUND,
            )
        try:
            if idempotency_key is None:
                run = assess_area(
                    area,
                    source=serializer.validated_data["source"],
                    scenario_id=serializer.validated_data.get("scenario"),
                    user=request.user,
                    assessment_mode=serializer.validated_data["assessment_mode"],
                )
            else:
                with transaction.atomic():
                    run = assess_area(
                        area,
                        source=serializer.validated_data["source"],
                        scenario_id=serializer.validated_data.get("scenario"),
                        user=request.user,
                        assessment_mode=serializer.validated_data["assessment_mode"],
                    )
                    AssessmentIdempotencyRecord.objects.create(
                        user=request.user,
                        key=idempotency_key,
                        request_fingerprint=fingerprint,
                        assessment_run=run,
                    )
        except AssessmentConfigurationError as error:
            return _error(
                "ASSESSMENT_NOT_AVAILABLE",
                str(error),
                status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        except ValidationError as error:
            if idempotency_key is not None:
                existing_record = (
                    AssessmentIdempotencyRecord.objects.select_related("assessment_run")
                    .filter(user=request.user, key=idempotency_key)
                    .first()
                )
                if existing_record is not None:
                    return self._replay_or_conflict(existing_record, fingerprint)
            return _error(
                "INVALID_ASSESSMENT",
                "The selected area or assessment inputs are invalid.",
                status.HTTP_400_BAD_REQUEST,
                error.message_dict if hasattr(error, "message_dict") else error.messages,
            )
        except IntegrityError:
            if idempotency_key is None:
                logger.exception("Integrity error while creating an assessment.")
                return _error(
                    "DATABASE_UNAVAILABLE",
                    "The assessment could not be saved.",
                    status.HTTP_503_SERVICE_UNAVAILABLE,
                )
            existing_record = (
                AssessmentIdempotencyRecord.objects.select_related("assessment_run")
                .filter(user=request.user, key=idempotency_key)
                .first()
            )
            if existing_record is None:
                logger.exception("Integrity error while creating an assessment.")
                return _error(
                    "DATABASE_UNAVAILABLE",
                    "The assessment could not be saved.",
                    status.HTTP_503_SERVICE_UNAVAILABLE,
                )
            return self._replay_or_conflict(existing_record, fingerprint)
        except DatabaseError:
            logger.exception("Database error while creating assessment.")
            return _error(
                "DATABASE_UNAVAILABLE",
                "The assessment could not be saved.",
                status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        run = _assessment_queryset().get(pk=run.pk)
        return Response(
            AssessmentRunSerializer(run).data,
            status=status.HTTP_201_CREATED,
        )

    def _replay_or_conflict(self, record, fingerprint):
        if record.request_fingerprint != fingerprint:
            return _error(
                "IDEMPOTENCY_KEY_REUSED",
                "This Idempotency-Key was already used with a different request.",
                status.HTTP_409_CONFLICT,
            )
        run = _assessment_queryset().get(pk=record.assessment_run_id)
        response = Response(AssessmentRunSerializer(run).data, status=status.HTTP_200_OK)
        response["Idempotency-Replayed"] = "true"
        return response


class AssessmentDetailView(AssessmentAPIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, pk):
        queryset = _assessment_queryset()
        if not (request.user.is_staff or request.user.is_superuser):
            queryset = queryset.filter(user=request.user)
        run = queryset.filter(pk=pk).first()
        if run is None:
            return _error(
                "ASSESSMENT_NOT_FOUND",
                "The requested assessment does not exist.",
                status.HTTP_404_NOT_FOUND,
            )
        return Response(AssessmentRunSerializer(run).data)


class AssessmentRecommendationListView(AssessmentAPIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, pk):
        queryset = AssessmentRun.objects.all()
        if not (request.user.is_staff or request.user.is_superuser):
            queryset = queryset.filter(user=request.user)
        run = queryset.filter(pk=pk).first()
        if run is None:
            return _error(
                "ASSESSMENT_NOT_FOUND",
                "The requested assessment does not exist.",
                status.HTTP_404_NOT_FOUND,
            )
        recommendations = ordered_recommendation_queryset().filter(assessment_run=run)
        return Response(
            {
                "assessment_id": run.pk,
                "results": AssessmentRecommendationSerializer(
                    recommendations,
                    many=True,
                ).data,
            }
        )


class AssessmentHistoryView(AssessmentAPIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, area_id):
        if not Area.objects.filter(pk=area_id).exists():
            return _error(
                "AREA_NOT_FOUND",
                "The requested area does not exist.",
                status.HTTP_404_NOT_FOUND,
            )
        queryset = _assessment_queryset().filter(area_id=area_id)
        if not (request.user.is_staff or request.user.is_superuser):
            queryset = queryset.filter(user=request.user)
        runs = queryset.order_by("-run_at", "-pk")
        return self.paginated_response(runs, request)


class LatestAreaAssessmentView(AssessmentAPIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, area_id):
        area = Area.objects.filter(pk=area_id).first()
        if area is None:
            return _error(
                "AREA_NOT_FOUND",
                "The requested area does not exist.",
                status.HTTP_404_NOT_FOUND,
            )
        queryset = _assessment_queryset().filter(area=area)
        if not (request.user.is_staff or request.user.is_superuser):
            queryset = queryset.filter(user=request.user)
        run = queryset.order_by("-run_at", "-pk").first()
        if run is None:
            return _error(
                "ASSESSMENT_NOT_FOUND",
                "No assessment exists for the requested area.",
                status.HTTP_404_NOT_FOUND,
            )
        return Response(AssessmentRunSerializer(run).data)


class RecommendationRuleListView(AssessmentAPIView):
    permission_classes = (AllowAny,)

    def get(self, request):
        rules = RecommendationRule.objects.filter(is_active=True).order_by(
            Case(
                When(priority="high", then=Value(0)),
                When(priority="medium", then=Value(1)),
                When(priority="low", then=Value(2)),
                default=Value(3),
                output_field=IntegerField(),
            ),
            "rule_code",
        )
        return Response(
            {"results": RecommendationRuleSerializer(rules, many=True).data}
        )


class AssessmentExportView(AssessmentAPIView):
    permission_classes = (IsAuthenticated,)

    def perform_content_negotiation(self, request, force=False):
        from rest_framework.renderers import JSONRenderer
        return JSONRenderer(), "application/json"

    def get(self, request, pk):
        queryset = _assessment_queryset()
        if not (request.user.is_staff or request.user.is_superuser):
            queryset = queryset.filter(user=request.user)
        run = queryset.filter(pk=pk).first()
        if run is None:
            return _error(
                "ASSESSMENT_NOT_FOUND",
                "The requested assessment does not exist.",
                status.HTTP_404_NOT_FOUND,
            )

        export_format = request.query_params.get("format", "csv").lower()
        if export_format not in ("csv", "html", "pdf"):
            return _error(
                "INVALID_EXPORT_FORMAT",
                "Supported export formats are 'csv' and 'html'.",
                status.HTTP_400_BAD_REQUEST,
            )

        if export_format == "csv":
            response = HttpResponse(content_type="text/csv; charset=utf-8")
            response["Content-Disposition"] = (
                f'attachment; filename="heatshield-assessment-{run.pk}.csv"'
            )
            writer = csv.writer(response)

            writer.writerow(["# HeatShield AI — Assessment Report"])
            writer.writerow(["Assessment ID", run.pk])
            writer.writerow(["Area", run.area.area_name])
            writer.writerow([
                "City",
                f"{run.area.city.name}, {run.area.city.state_name} ({run.area.city.country_code})",
            ])
            coords = (
                f"{run.area.latitude}, {run.area.longitude}"
                if run.area.latitude is not None
                else "Not stored"
            )
            writer.writerow(["Representative Coordinates", coords])
            writer.writerow(["Vulnerability Score", run.score if run.score is not None else "—"])
            writer.writerow(["Risk Category", run.risk_category or "—"])
            writer.writerow(["Status", run.status])
            writer.writerow(["Data Class", run.data_class])
            writer.writerow([
                "Data Coverage (%)",
                f"{run.data_coverage}%" if run.data_coverage is not None else "—",
            ])
            writer.writerow(["Assessment Timestamp", run.run_at.isoformat()])
            writer.writerow(["Method Version", run.method_version])
            writer.writerow(["Configuration Version", run.configuration_version])
            writer.writerow([])

            writer.writerow(["# Indicator Breakdown"])
            writer.writerow([
                "Indicator Code",
                "Input Numeric Value",
                "Normalized Value",
                "Weight",
                "Contribution",
                "Quality Status",
                "Explanation",
            ])
            for ind in run.assessment_indicators.all():
                val = (
                    ind.input_value_numeric
                    if ind.input_value_numeric is not None
                    else (ind.input_value_text or "—")
                )
                writer.writerow([
                    ind.indicator_code,
                    val,
                    ind.normalized_value if ind.normalized_value is not None else "—",
                    ind.weight_used if ind.weight_used is not None else "—",
                    ind.contribution if ind.contribution is not None else "—",
                    ind.quality_status,
                    ind.explanation,
                ])
            writer.writerow([])

            writer.writerow(["# Action Recommendations"])
            writer.writerow([
                "Priority",
                "Rule Code",
                "Title",
                "Recommendation Guidance",
                "Trigger Explanation",
            ])
            recommendations = getattr(
                run,
                "_ordered_assessment_recommendations",
                run.assessment_recommendations.all(),
            )
            for rec in recommendations:
                snapshot = rec.rule_snapshot or {}
                writer.writerow([
                    snapshot.get(
                        "priority",
                        rec.recommendation_rule.priority
                        if rec.recommendation_rule
                        else "—",
                    ),
                    snapshot.get(
                        "rule_code",
                        rec.recommendation_rule.rule_code
                        if rec.recommendation_rule
                        else "—",
                    ),
                    snapshot.get(
                        "title",
                        rec.recommendation_rule.title
                        if rec.recommendation_rule
                        else "—",
                    ),
                    snapshot.get(
                        "recommendation_text",
                        rec.recommendation_rule.recommendation_text
                        if rec.recommendation_rule
                        else "—",
                    ),
                    rec.trigger_explanation or "—",
                ])
            writer.writerow([])

            writer.writerow(["# Disclaimers & Limitations"])
            writer.writerow([
                "Methodology Disclaimer",
                "Provisional heat-impact decision-support demonstration. "
                "Not scientifically validated for clinical diagnosis, casualty prediction, or emergency dispatch.",
            ])
            writer.writerow([
                "Geometry Limitation",
                "Point markers represent populated-place coordinates only; "
                "ward boundary polygons are neither stored nor invented.",
            ])
            return response

        # HTML / Printable report
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>HeatShield AI Report - Assessment #{run.pk}</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; color: #1e293b; background: #fff; margin: 0; padding: 2rem; }}
    @media print {{ body {{ padding: 0; }} .no-print {{ display: none; }} }}
    .header {{ border-bottom: 2px solid #0284c7; padding-bottom: 1rem; margin-bottom: 1.5rem; display: flex; justify-content: space-between; align-items: flex-start; }}
    .title {{ font-size: 1.5rem; font-weight: 700; color: #0f172a; margin: 0; }}
    .subtitle {{ font-size: 0.875rem; color: #64748b; margin-top: 0.25rem; }}
    .grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; margin-bottom: 1.5rem; }}
    .metric-card {{ border: 1px solid #e2e8f0; border-radius: 0.5rem; padding: 0.75rem 1rem; }}
    .metric-label {{ font-size: 0.75rem; color: #64748b; text-transform: uppercase; }}
    .metric-value {{ font-size: 1.25rem; font-weight: 700; color: #0f172a; margin-top: 0.25rem; }}
    table {{ width: 100%; border-collapse: collapse; margin-bottom: 1.5rem; font-size: 0.875rem; }}
    th, td {{ border: 1px solid #e2e8f0; padding: 0.5rem 0.75rem; text-align: left; }}
    th {{ background: #f8fafc; font-weight: 600; color: #475569; }}
    .section-title {{ font-size: 1.125rem; font-weight: 600; color: #0f172a; margin-top: 1.5rem; margin-bottom: 0.75rem; }}
    .disclaimer {{ background: #fffbeb; border: 1px solid #fef3c7; border-radius: 0.5rem; padding: 0.75rem 1rem; font-size: 0.75rem; color: #92400e; margin-top: 2rem; }}
    .print-btn {{ background: #0284c7; color: #fff; border: none; padding: 0.5rem 1rem; border-radius: 0.375rem; font-size: 0.875rem; font-weight: 500; cursor: pointer; }}
  </style>
</head>
<body>
  <div class="header">
    <div>
      <h1 class="title">HeatShield AI Assessment Report</h1>
      <p class="subtitle">{run.area.area_name} ({run.area.city.name}, {run.area.city.state_name}) · Generated {run.run_at.strftime('%Y-%m-%d %H:%M UTC')}</p>
    </div>
    <div class="no-print">
      <button class="print-btn" onclick="window.print()">Print / Save as PDF</button>
    </div>
  </div>

  <div class="grid">
    <div class="metric-card">
      <div class="metric-label">Vulnerability Score</div>
      <div class="metric-value">{run.score if run.score is not None else '—'}</div>
    </div>
    <div class="metric-card">
      <div class="metric-label">Risk Category</div>
      <div class="metric-value" style="font-size: 1rem;">{(run.risk_category or '—').replace('_', ' ').title()}</div>
    </div>
    <div class="metric-card">
      <div class="metric-label">Status</div>
      <div class="metric-value" style="font-size: 1rem;">{run.status.replace('_', ' ')}</div>
    </div>
    <div class="metric-card">
      <div class="metric-label">Data Coverage</div>
      <div class="metric-value">{f"{run.data_coverage}%" if run.data_coverage is not None else '—'}</div>
    </div>
  </div>

  <h2 class="section-title">Contributing Indicators</h2>
  <table>
    <thead>
      <tr>
        <th>Indicator</th>
        <th>Input Value</th>
        <th>Normalized (0–1)</th>
        <th>Weight</th>
        <th>Contribution</th>
        <th>Quality Status</th>
      </tr>
    </thead>
    <tbody>
      {''.join(f'''<tr>
        <td><strong>{ind.indicator_code}</strong></td>
        <td>{ind.input_value_numeric if ind.input_value_numeric is not None else (ind.input_value_text or '—')}</td>
        <td>{ind.normalized_value if ind.normalized_value is not None else '—'}</td>
        <td>{ind.weight_used if ind.weight_used is not None else '—'}</td>
        <td>{ind.contribution if ind.contribution is not None else '—'}</td>
        <td>{ind.quality_status}</td>
      </tr>''' for ind in run.assessment_indicators.all())}
    </tbody>
  </table>

  <h2 class="section-title">Mitigation & Action Recommendations</h2>
  <table>
    <thead>
      <tr>
        <th>Priority</th>
        <th>Action</th>
        <th>Description</th>
        <th>Diagnostic Trigger</th>
      </tr>
    </thead>
    <tbody>
      {''.join(f'''<tr>
        <td><strong>{(rec.rule_snapshot or {{}}).get('priority', rec.recommendation_rule.priority if rec.recommendation_rule else '—').upper()}</strong></td>
        <td>{(rec.rule_snapshot or {{}}).get('title', rec.recommendation_rule.title if rec.recommendation_rule else '—')}</td>
        <td>{(rec.rule_snapshot or {{}}).get('recommendation_text', rec.recommendation_rule.recommendation_text if rec.recommendation_rule else '—')}</td>
        <td style="font-size: 0.75rem; color: #64748b;">{rec.trigger_explanation or '—'}</td>
      </tr>''' for rec in getattr(run, '_ordered_assessment_recommendations', run.assessment_recommendations.all()))}
    </tbody>
  </table>

  <div class="disclaimer">
    <strong>Decision-Support Notice & Limitations:</strong>
    This document is produced by HeatShield AI ({run.method_version}) as a provisional decision-support prototype.
    It does not constitute clinical medical advice, mortality forecasting, or automated municipal dispatch.
    Representative coordinates ({run.area.latitude or '—'}, {run.area.longitude or '—'}) denote populated-place points only;
    municipal and ward polygons are not stored and are never invented.
  </div>
</body>
</html>"""
        response = HttpResponse(html, content_type="text/html; charset=utf-8")
        return response

from django.conf import settings
from django.utils import timezone

from apps.indicators.models import IndicatorObservation


REQUIRED_INDICATORS = ("AIR_TEMPERATURE", "RELATIVE_HUMIDITY")
REQUIRED_UNITS = {
    "AIR_TEMPERATURE": "degree_celsius",
    "RELATIVE_HUMIDITY": "percent",
}


def _observation_rows(area):
    cached = getattr(area, "_readiness_rows", None)
    if cached is not None:
        return list(cached)
    return list(
        IndicatorObservation.objects.filter(area=area).select_related(
            "dataset",
            "dataset__source",
        )
    )


def _dataset_eligible(row):
    dataset = row.dataset
    source = dataset.source
    return (
        dataset.is_active
        and dataset.data_class in {"observed", "derived"}
        and (source.approval_status or "").strip().upper() == "APPROVED"
    )


def compute_area_readiness(area):
    max_age = getattr(settings, "MAX_OBSERVATION_AGE_DAYS", 7)
    today = timezone.localdate()
    reasons = []
    if area.latitude is None or area.longitude is None:
        reasons.append("Representative coordinate is unavailable.")

    rows = [row for row in _observation_rows(area) if _dataset_eligible(row)]
    by_code = {}
    for row in rows:
        if row.indicator_code in REQUIRED_INDICATORS:
            by_code.setdefault(row.indicator_code, []).append(row)

    if not by_code.get("AIR_TEMPERATURE"):
        reasons.append("AIR_TEMPERATURE is missing.")
    if not by_code.get("RELATIVE_HUMIDITY"):
        reasons.append("RELATIVE_HUMIDITY is missing.")

    periods = {
        code: {(row.period_start, row.period_end) for row in values}
        for code, values in by_code.items()
    }
    if periods.get("AIR_TEMPERATURE") and periods.get("RELATIVE_HUMIDITY"):
        if not (periods["AIR_TEMPERATURE"] & periods["RELATIVE_HUMIDITY"]):
            reasons.append("Temperature and humidity periods do not align.")

    usable_by_code = {}
    for code, values in by_code.items():
        usable = [
            row
            for row in values
            if row.quality_status == "VALID"
            and row.raw_value_numeric is not None
            and row.raw_unit == REQUIRED_UNITS[code]
            and row.period_end is not None
            and row.period_end <= today
            and (today - row.period_end).days <= max_age
        ]
        usable_by_code[code] = usable
        if not usable and code in REQUIRED_INDICATORS:
            reasons.append(f"No fresh valid {code} observation is available.")

    aligned_period = None
    if usable_by_code.get("AIR_TEMPERATURE") and usable_by_code.get(
        "RELATIVE_HUMIDITY"
    ):
        temp_periods = {
            (row.period_start, row.period_end)
            for row in usable_by_code["AIR_TEMPERATURE"]
        }
        humidity_periods = {
            (row.period_start, row.period_end)
            for row in usable_by_code["RELATIVE_HUMIDITY"]
        }
        shared = temp_periods & humidity_periods
        if shared:
            aligned_period = max(shared, key=lambda item: item[1])

    available = [
        code
        for code in REQUIRED_INDICATORS
        if usable_by_code.get(code)
    ]
    missing = [code for code in REQUIRED_INDICATORS if code not in available]

    valid_rows = [
        row
        for values in by_code.values()
        for row in values
        if row.quality_status == "VALID"
        and row.raw_value_numeric is not None
        and row.raw_unit == REQUIRED_UNITS.get(row.indicator_code)
        and row.period_end is not None
        and row.period_end <= today
    ]

    latest_end = None
    latest_start = None
    if aligned_period:
        latest_start, latest_end = aligned_period
    elif valid_rows:
        latest = max(valid_rows, key=lambda row: (row.period_end, row.pk))
        latest_start, latest_end = latest.period_start, latest.period_end

    age_days = None
    if latest_end is not None:
        age_days = (today - latest_end).days

    if not valid_rows:
        freshness_status = "MISSING"
    elif age_days is not None and age_days > max_age:
        freshness_status = "STALE"
    else:
        freshness_status = "FRESH"

    ready = not reasons
    return {
        "assessment_ready": ready,
        "is_assessment_ready": ready,
        "readiness_status": "READY" if ready else "NOT_READY",
        "readiness_reasons": reasons,
        "available_indicators": available,
        "missing_indicators": missing,
        "latest_observation_period": (
            {
                "start": latest_start.isoformat() if latest_start else None,
                "end": latest_end.isoformat() if latest_end else None,
            }
            if latest_start or latest_end
            else None
        ),
        "observation_age_days": age_days,
        "max_observation_age_days": max_age,
        "freshness_status": freshness_status,
    }

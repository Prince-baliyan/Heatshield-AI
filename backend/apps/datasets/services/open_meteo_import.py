from decimal import Decimal, InvalidOperation
from urllib.parse import urlencode
from urllib.request import urlopen
import hashlib
import json

from django.db import transaction
from django.utils import timezone

from apps.cities.models import Area
from apps.indicators.models import IndicatorObservation
from apps.datasets.models import DataSource, Dataset


VARIABLE_MAP = {
    "temperature_2m_mean": ("AIR_TEMPERATURE", "degree_celsius"),
    "relative_humidity_2m_mean": ("RELATIVE_HUMIDITY", "percent"),
}
ARCHIVE_ENDPOINT = "https://archive-api.open-meteo.com/v1/archive"


class OpenMeteoImportError(ValueError):
    pass


def fetch_open_meteo_daily(latitude, longitude, period_start, period_end):
    params = {
        "latitude": str(latitude),
        "longitude": str(longitude),
        "start_date": period_start.isoformat(),
        "end_date": period_end.isoformat(),
        "daily": "temperature_2m_mean,relative_humidity_2m_mean",
        "timezone": "Asia/Kolkata",
    }
    url = ARCHIVE_ENDPOINT + "?" + urlencode(params)
    try:
        with urlopen(url, timeout=30) as response:
            body = response.read()
    except Exception as error:
        raise OpenMeteoImportError(
            f"Open-Meteo request failed: {error}"
        ) from error
    try:
        payload = json.loads(body)
    except json.JSONDecodeError as error:
        raise OpenMeteoImportError("Open-Meteo returned invalid JSON.") from error
    return payload, body, url


def import_open_meteo_period(
    *,
    area_id,
    period_start,
    period_end,
    latitude=None,
    longitude=None,
    source_id=None,
    dry_run=False,
):
    area = Area.objects.select_related("city").filter(pk=area_id).first()
    if area is None:
        raise OpenMeteoImportError("Area does not exist.")
    if area.area_type != "city":
        raise OpenMeteoImportError("The import currently supports city-level areas only.")
    if period_end < period_start:
        raise OpenMeteoImportError("Period end cannot precede period start.")
    if period_end > timezone.localdate():
        raise OpenMeteoImportError("Future-dated periods are not supported.")

    if latitude is None:
        latitude = area.latitude
    if longitude is None:
        longitude = area.longitude
    if latitude is None or longitude is None:
        raise OpenMeteoImportError(
            "A representative latitude and longitude are required before import."
        )

    source = (
        DataSource.objects.filter(pk=source_id).first()
        if source_id is not None
        else DataSource.objects.filter(
            source_name__iexact="Open-Meteo Weather API",
            approval_status__iexact="APPROVED",
        ).first()
    )
    if source is None:
        raise OpenMeteoImportError("Approved Open-Meteo source was not found.")

    payload, body, url = fetch_open_meteo_daily(
        latitude,
        longitude,
        period_start,
        period_end,
    )
    daily = payload.get("daily")
    units = payload.get("daily_units")
    if not isinstance(daily, dict) or not isinstance(units, dict):
        raise OpenMeteoImportError("Open-Meteo response is missing daily values.")
    dates = daily.get("time")
    if not isinstance(dates, list):
        raise OpenMeteoImportError("Open-Meteo response is missing dates.")
    if units.get("temperature_2m_mean") != "°C":
        raise OpenMeteoImportError("Unexpected temperature unit.")
    if units.get("relative_humidity_2m_mean") != "%":
        raise OpenMeteoImportError("Unexpected relative humidity unit.")

    imported = 0
    skipped_existing = 0
    skipped_missing = 0
    dataset_name = (
        f"Open-Meteo Daily Archive - {area.area_name} - "
        f"{period_start.isoformat()} to {period_end.isoformat()}"
    )
    notes = (
        "Open-Meteo historical archive API (https://open-meteo.com/en/docs/"
        "historical-weather-api); daily mean 2 m temperature and 2 m relative "
        "humidity; Asia/Kolkata; ERA5/model reanalysis-derived data, not a "
        f"direct ground-station measurement; requested {latitude},{longitude}; "
        f"API-resolved {payload.get('latitude')},{payload.get('longitude')}; "
        f"retrieval source {url}"
    )
    with transaction.atomic():
        dataset, created = Dataset.objects.get_or_create(
            source=source,
            dataset_name=dataset_name,
            defaults={
                "data_class": "derived",
                "spatial_resolution": "city-level model grid point",
                "published_at": period_end,
                "coverage_start": period_start,
                "coverage_end": period_end,
                "retrieved_at": timezone.now(),
                "file_hash": hashlib.sha256(body).hexdigest(),
                "transformation_notes": notes,
                "is_active": True,
            },
        )
        if not created and not dry_run:
            dataset.retrieved_at = timezone.now()
            dataset.file_hash = hashlib.sha256(body).hexdigest()
            dataset.transformation_notes = notes
            dataset.coverage_start = period_start
            dataset.coverage_end = period_end
            dataset.save()
        if not dry_run:
            dataset.full_clean()

        for offset, date_text in enumerate(dates):
            try:
                date = timezone.datetime.fromisoformat(date_text).date()
            except (TypeError, ValueError) as error:
                raise OpenMeteoImportError(
                    f"Invalid date returned by Open-Meteo: {date_text}"
                ) from error
            if date < period_start or date > period_end:
                raise OpenMeteoImportError(
                    f"Open-Meteo returned an out-of-range date: {date_text}"
                )
            for variable, (indicator_code, raw_unit) in VARIABLE_MAP.items():
                values = daily.get(variable)
                if not isinstance(values, list) or offset >= len(values):
                    raise OpenMeteoImportError(
                        f"Missing {variable} value for {date_text}."
                    )
                raw_value = values[offset]
                if raw_value is None or raw_value == -999:
                    skipped_missing += 1
                    continue
                try:
                    numeric_value = Decimal(str(raw_value))
                except (InvalidOperation, ValueError) as error:
                    raise OpenMeteoImportError(
                        f"Invalid numeric {variable} value: {raw_value}"
                    ) from error
                if not numeric_value.is_finite():
                    raise OpenMeteoImportError(
                        f"Non-finite {variable} value: {raw_value}"
                    )
                if dry_run:
                    imported += 1
                    continue
                _observation, created_obs = IndicatorObservation.objects.get_or_create(
                    area=area,
                    dataset=dataset,
                    indicator_code=indicator_code,
                    period_start=date,
                    period_end=date,
                    defaults={
                        "raw_value_numeric": numeric_value,
                        "raw_unit": raw_unit,
                        "quality_status": "VALID",
                        "notes": (
                            f"Open-Meteo archive {variable}; date {date_text}; "
                            "Asia/Kolkata; model/reanalysis-derived, not a direct "
                            "station observation; "
                            f"requested {latitude},{longitude}; "
                            f"API-resolved {payload.get('latitude')},"
                            f"{payload.get('longitude')}."
                        ),
                    },
                )
                if created_obs:
                    imported += 1
                else:
                    skipped_existing += 1

        if dry_run:
            transaction.set_rollback(True)

    return {
        "area": area.area_name,
        "dataset": dataset.dataset_name,
        "dataset_id": None if dry_run else dataset.pk,
        "dataset_created": created,
        "period_start": period_start.isoformat(),
        "period_end": period_end.isoformat(),
        "latitude": str(latitude),
        "longitude": str(longitude),
        "api_resolved_latitude": payload.get("latitude"),
        "api_resolved_longitude": payload.get("longitude"),
        "imported": imported,
        "skipped_existing": skipped_existing,
        "skipped_missing": skipped_missing,
        "dry_run": dry_run,
        "source": source.source_name,
        "licence": source.licence_terms,
        "request_url": url,
        "data_class": "derived",
    }

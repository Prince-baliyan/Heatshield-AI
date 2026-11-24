"""Deterministic, explicitly provisional scoring for the MVP weather demo."""

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import hashlib
import json
from typing import Any

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.assessments.models import AssessmentIndicator, AssessmentRun
from apps.cities.models import Area
from apps.indicators.models import (
    IndicatorObservation,
    is_city_level_resolution,
    validate_observation_area_resolution,
)
from apps.datasets.providers.factory import get_weather_provider


INPUT_DATA_CLASSES = {"observed", "derived", "illustrative"}
RUN_DATA_CLASSES = INPUT_DATA_CLASSES | {"mixed", "unavailable"}
QUALITY_STATUSES = {
    "VALID",
    "MISSING",
    "INVALID",
    "STALE",
    "LOW_CONFIDENCE",
    "NOT_APPLICABLE",
    "PENDING_REVIEW",
}


@dataclass(frozen=True)
class IndicatorDefinition:
    code: str
    label: str
    unit: str
    lower_bound: Decimal
    upper_bound: Decimal
    weight: Decimal


@dataclass(frozen=True)
class ScoringConfiguration:
    method_version: str
    indicators: tuple[IndicatorDefinition, ...]
    minimum_coverage: Decimal
    low_category_ceiling: Decimal
    moderate_category_ceiling: Decimal
    low_category: str = "illustrative_low"
    moderate_category: str = "illustrative_moderate"
    high_category: str = "illustrative_high"

    def __post_init__(self) -> None:
        if not (self.method_version or "").strip():
            raise ValueError("Scoring method version is required.")
        if not self.indicators:
            raise ValueError("Scoring configuration must contain indicators.")

        total_weight = Decimal("0")
        for indicator in self.indicators:
            if not (indicator.code or "").strip():
                raise ValueError("Scoring indicator code is required.")
            if not (indicator.unit or "").strip():
                raise ValueError(
                    f"Scoring indicator {indicator.code!r} must have a unit."
                )
            try:
                lower_bound = Decimal(str(indicator.lower_bound))
                upper_bound = Decimal(str(indicator.upper_bound))
                weight = Decimal(str(indicator.weight))
            except (InvalidOperation, ValueError):
                raise ValueError(
                    f"Scoring indicator {indicator.code!r} has a non-numeric value."
                ) from None
            if not lower_bound.is_finite():
                raise ValueError(
                    f"Scoring indicator {indicator.code!r} has an invalid lower bound."
                )
            if not upper_bound.is_finite():
                raise ValueError(
                    f"Scoring indicator {indicator.code!r} has an invalid upper bound."
                )
            if lower_bound >= upper_bound:
                raise ValueError(
                    f"Scoring indicator {indicator.code!r} bounds are invalid."
                )
            if not weight.is_finite() or weight < 0:
                raise ValueError(
                    f"Scoring indicator {indicator.code!r} weight must be non-negative."
                )
            total_weight += weight

        if total_weight <= 0:
            raise ValueError("Scoring configuration must have positive total weight.")
        try:
            minimum_coverage = Decimal(str(self.minimum_coverage))
            low_category_ceiling = Decimal(str(self.low_category_ceiling))
            moderate_category_ceiling = Decimal(
                str(self.moderate_category_ceiling)
            )
        except (InvalidOperation, ValueError):
            raise ValueError("Scoring coverage and category values must be numeric.") from None
        if not minimum_coverage.is_finite():
            raise ValueError("Minimum coverage must be finite.")
        if not Decimal("0") <= minimum_coverage <= Decimal("100"):
            raise ValueError("Minimum coverage must be between 0 and 100.")
        if not all(
            threshold.is_finite()
            for threshold in (
                low_category_ceiling,
                moderate_category_ceiling,
            )
        ):
            raise ValueError("Category thresholds must be finite.")
        if not (
            Decimal("0")
            <= low_category_ceiling
            <= moderate_category_ceiling
            <= Decimal("100")
        ):
            raise ValueError("Category thresholds must be ordered between 0 and 100.")

    @property
    def configuration_version(self) -> str:
        settings = {
            "method_version": self.method_version,
            "indicators": [
                {
                    "code": indicator.code,
                    "label": indicator.label,
                    "unit": indicator.unit,
                    "lower_bound": str(indicator.lower_bound),
                    "upper_bound": str(indicator.upper_bound),
                    "weight": str(indicator.weight),
                }
                for indicator in self.indicators
            ],
            "minimum_coverage": str(self.minimum_coverage),
            "low_category_ceiling": str(self.low_category_ceiling),
            "moderate_category_ceiling": str(self.moderate_category_ceiling),
            "category_labels": [
                self.low_category,
                self.moderate_category,
                self.high_category,
            ],
            "normalization": "(value - lower_bound) / (upper_bound - lower_bound)",
            "rounding": "ROUND_HALF_UP",
        }
        canonical_settings = json.dumps(
            settings,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        fingerprint = hashlib.sha256(canonical_settings).hexdigest()
        return f"cfg-{fingerprint[:36]}"

    def as_snapshot(self) -> dict[str, Any]:
        return {
            "configuration_version": self.configuration_version,
            "method_version": self.method_version,
            "indicators": [
                {
                    "code": indicator.code,
                    "label": indicator.label,
                    "unit": indicator.unit,
                    "lower_bound": str(indicator.lower_bound),
                    "upper_bound": str(indicator.upper_bound),
                    "weight": str(indicator.weight),
                }
                for indicator in self.indicators
            ],
            "minimum_coverage": str(self.minimum_coverage),
            "category_thresholds": {
                self.low_category: str(self.low_category_ceiling),
                self.moderate_category: str(self.moderate_category_ceiling),
                self.high_category: None,
            },
            "normalization": "(value - lower_bound) / (upper_bound - lower_bound)",
            "rounding": "ROUND_HALF_UP",
        }


@dataclass(frozen=True)
class AssessmentInput:
    code: str
    numeric_value: Decimal | None
    text_value: str | None
    unit: str | None
    quality_status: str
    data_class: str | None
    provenance: str
    period: str


@dataclass(frozen=True)
class IndicatorResult:
    code: str
    numeric_value: Decimal | None
    text_value: str | None
    normalized_value: Decimal | None
    weight_used: Decimal | None
    contribution: Decimal | None
    quality_status: str
    explanation: str


@dataclass(frozen=True)
class AssessmentResult:
    status: str
    score: Decimal | None
    risk_category: str | None
    data_coverage: Decimal
    data_class: str
    indicators: tuple[IndicatorResult, ...]
    missing_indicators: tuple[str, ...]
    warnings: tuple[str, ...]


MVP_CONFIGURATION = ScoringConfiguration(
    method_version="weighted-relative-index-v1",
    indicators=(
        IndicatorDefinition(
            code="AIR_TEMPERATURE",
            label="Air temperature",
            unit="degree_celsius",
            lower_bound=Decimal("25"),
            upper_bound=Decimal("45"),
            weight=Decimal("0.70"),
        ),
        IndicatorDefinition(
            code="RELATIVE_HUMIDITY",
            label="Relative humidity",
            unit="percent",
            lower_bound=Decimal("30"),
            upper_bound=Decimal("90"),
            weight=Decimal("0.30"),
        ),
    ),
    minimum_coverage=Decimal("100.00"),
    low_category_ceiling=Decimal("33.33"),
    moderate_category_ceiling=Decimal("66.67"),
)
LEGACY_DEMO_CONFIGURATION_V1 = ScoringConfiguration(
    method_version="weighted-relative-index-v1",
    indicators=(
        IndicatorDefinition(
            code="AIR_TEMPERATURE",
            label="Air temperature",
            unit="degree_celsius",
            lower_bound=Decimal("25"),
            upper_bound=Decimal("45"),
            weight=Decimal("0.70"),
        ),
        IndicatorDefinition(
            code="RELATIVE_HUMIDITY",
            label="Relative humidity",
            unit="percent",
            lower_bound=Decimal("30"),
            upper_bound=Decimal("90"),
            weight=Decimal("0.30"),
        ),
    ),
    minimum_coverage=Decimal("100.00"),
    low_category_ceiling=Decimal("33.33"),
    moderate_category_ceiling=Decimal("66.67"),
)
INDICATOR_DEFINITIONS = MVP_CONFIGURATION.indicators
DEFINITIONS_BY_CODE = {definition.code: definition for definition in INDICATOR_DEFINITIONS}
SCORING_CONFIGURATION_REGISTRY = {
    MVP_CONFIGURATION.configuration_version: MVP_CONFIGURATION,
    # Keep historical configurations separate from the active mutable source definition.
    "demo-weather-provisional-v1": LEGACY_DEMO_CONFIGURATION_V1,
}


class AssessmentConfigurationError(ValueError):
    """Raised when an assessment input cannot be represented safely."""


def scoring_configuration_for(version: str) -> ScoringConfiguration:
    try:
        return SCORING_CONFIGURATION_REGISTRY[version]
    except KeyError as error:
        raise AssessmentConfigurationError(
            f"Scoring configuration {version!r} is not available."
        ) from error


def _decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    if not result.is_finite():
        return None
    return result


def _latest_observation_inputs(
    area: Area,
    assessment_mode: str = "current",
) -> tuple[list[AssessmentInput], bool, tuple[str, ...]]:
    eligible_rows = list(
        IndicatorObservation.objects.filter(
            area=area,
            indicator_code__in=DEFINITIONS_BY_CODE,
            dataset__is_active=True,
            dataset__source__approval_status__iexact="APPROVED",
        )
        .select_related("dataset", "dataset__source")
        .order_by(
            "indicator_code",
            "-period_end",
            "-period_start",
            "-dataset__retrieved_at",
            "-pk",
        )
    )
    rows = [
        row
        for row in eligible_rows
        if row.dataset.data_class in {"observed", "derived"}
    ]
    illustrative_count = sum(
        row.dataset.data_class == "illustrative" for row in eligible_rows
    )
    latest: dict[str, IndicatorObservation] = {}
    for row in rows:
        latest.setdefault(row.indicator_code, row)

    max_age_days = (
        getattr(settings, "MAX_OBSERVATION_AGE_DAYS", 7)
        if assessment_mode == "current"
        else getattr(settings, "HISTORICAL_OBSERVATION_MAX_AGE_DAYS", 365)
    )
    if not isinstance(max_age_days, int) or max_age_days < 0:
        raise AssessmentConfigurationError(
            "MAX_OBSERVATION_AGE_DAYS must be a non-negative integer."
        )
    today = timezone.localdate()
    warnings: list[str] = []
    if illustrative_count:
        warnings.append(
            "Illustrative dataset observations were excluded from stored assessment inputs."
        )

    inputs: list[AssessmentInput] = []
    for definition in MVP_CONFIGURATION.indicators:
        row = latest.get(definition.code)
        if row is None:
            inputs.append(
                AssessmentInput(
                    code=definition.code,
                    numeric_value=None,
                    text_value=None,
                    unit=None,
                    quality_status="MISSING",
                    data_class=None,
                    provenance="No active dataset observation was found.",
                    period="",
                )
            )
            continue

        dataset_class = row.dataset.data_class
        try:
            validate_observation_area_resolution(area, row.dataset)
        except ValidationError as error:
            raise AssessmentConfigurationError(
                f"Dataset for {definition.code} has incompatible spatial resolution."
            ) from error
        quality_status = row.quality_status
        if quality_status not in QUALITY_STATUSES:
            quality_status = "PENDING_REVIEW"
        if row.period_start is None or row.period_end is None:
            quality_status = "STALE"
            warnings.append(
                f"{definition.code} was excluded because its observation period is incomplete."
            )
        elif row.period_end > today:
            quality_status = "INVALID"
            warnings.append(
                f"{definition.code} was excluded because its period ends in the future."
            )
        elif (today - row.period_end).days > max_age_days:
            quality_status = "STALE"
            warnings.append(
                f"{definition.code} was excluded because its period ended "
                f"{(today - row.period_end).days} days ago, beyond the configured "
                f"{max_age_days}-day maximum age."
            )
        period = (
            f"{row.period_start.isoformat()} to {row.period_end.isoformat()}"
            if row.period_start is not None and row.period_end is not None
            else ""
        )
        inputs.append(
            AssessmentInput(
                code=row.indicator_code,
                numeric_value=row.raw_value_numeric,
                text_value=row.raw_value_text,
                unit=row.raw_unit,
                quality_status=quality_status,
                data_class=dataset_class,
                provenance=(
                    f"{row.dataset.source.source_name} / {row.dataset.dataset_name}"
                ),
                period=period,
            )
        )

    latest_periods = {
        code: (row.period_start, row.period_end)
        for code, row in latest.items()
    }
    configured_codes = tuple(
        definition.code for definition in MVP_CONFIGURATION.indicators
    )
    periods_aligned = True
    if all(code in latest_periods for code in configured_codes):
        periods_aligned = (
            latest_periods[configured_codes[0]] == latest_periods[configured_codes[1]]
        )
        if not periods_aligned:
            warnings.append(
                "Stored observation periods do not match: "
                f"{configured_codes[0]} covers "
                f"{latest_periods[configured_codes[0]][0]} to "
                f"{latest_periods[configured_codes[0]][1]}, while "
                f"{configured_codes[1]} covers "
                f"{latest_periods[configured_codes[1]][0]} to "
                f"{latest_periods[configured_codes[1]][1]}. "
                "No score was produced."
            )
    elif any(
        code in latest_periods
        and (
            latest_periods[code][0] is None
            or latest_periods[code][1] is None
        )
        for code in configured_codes
    ):
        periods_aligned = False

    return inputs, periods_aligned, tuple(warnings)


def _demo_provider_inputs(
    area: Area,
    scenario_id: str | None = None,
) -> tuple[list[AssessmentInput], dict[str, Any]]:
    if area.area_type != "city":
        raise AssessmentConfigurationError(
            "Demo weather assessment requires a city-level area."
        )
    if area.city.name.casefold() != "meerut":
        raise AssessmentConfigurationError(
            "Illustrative demo weather is currently available only for Meerut."
        )

    try:
        payload = get_weather_provider().fetch_weather(
            area.city.name,
            scenario_id=scenario_id,
        )
    except (ImportError, ValueError) as error:
        raise AssessmentConfigurationError(
            "The configured weather provider is unavailable for assessment."
        ) from error
    if not isinstance(payload, dict):
        raise AssessmentConfigurationError(
            "The configured weather provider returned an invalid response."
        )
    if payload.get("data_class") != "illustrative":
        raise AssessmentConfigurationError(
            "The configured provider did not identify its data as illustrative."
        )
    spatial_resolution = payload.get("spatial_resolution")
    if not isinstance(spatial_resolution, str) or not is_city_level_resolution(
        spatial_resolution
    ):
        raise AssessmentConfigurationError(
            "The configured provider did not identify its data as city-level."
        )

    raw_observations = payload.get("observations")
    if not isinstance(raw_observations, list):
        raise AssessmentConfigurationError(
            "The configured weather provider returned invalid observations."
        )
    observations = {}
    for observation in raw_observations:
        if not isinstance(observation, dict):
            continue
        code = observation.get("indicator_code")
        if isinstance(code, str) and code in DEFINITIONS_BY_CODE:
            observations[code] = observation
    inputs: list[AssessmentInput] = []
    for definition in MVP_CONFIGURATION.indicators:
        observation = observations.get(definition.code)
        if observation is None:
            inputs.append(
                AssessmentInput(
                    code=definition.code,
                    numeric_value=None,
                    text_value=None,
                    unit=None,
                    quality_status="MISSING",
                    data_class=None,
                    provenance=str(payload.get("source", "Demo provider")),
                    period="illustrative sample",
                )
            )
            continue

        value = _decimal(observation.get("value"))
        quality_status = "LOW_CONFIDENCE"
        if value is None:
            quality_status = "INVALID"
        inputs.append(
            AssessmentInput(
                code=definition.code,
                numeric_value=value,
                text_value=None,
                unit=observation.get("unit"),
                quality_status=quality_status,
                data_class="illustrative",
                provenance=str(payload.get("source", "Demo provider")),
                period=str(observation.get("measurement_period", "illustrative sample")),
            )
        )
    return inputs, payload


def _source_is_eligible(item: AssessmentInput) -> bool:
    if item.quality_status == "VALID":
        return True
    return (
        item.data_class == "illustrative"
        and item.quality_status == "LOW_CONFIDENCE"
    )


def score_inputs(
    inputs: list[AssessmentInput],
    *,
    configuration: ScoringConfiguration = MVP_CONFIGURATION,
    periods_aligned: bool = True,
    additional_warnings: tuple[str, ...] = (),
) -> AssessmentResult:
    for item in inputs:
        if item.data_class is None:
            if item.quality_status != "MISSING":
                raise AssessmentConfigurationError(
                    "Only missing assessment inputs may have an unknown data class."
                )
        elif item.data_class not in INPUT_DATA_CLASSES:
            raise AssessmentConfigurationError(
                "Assessment inputs contain an unsupported data class."
            )
    inputs_by_code = {item.code: item for item in inputs}

    results: list[IndicatorResult] = []
    missing: list[str] = []
    configured_codes = ", ".join(
        definition.code for definition in configuration.indicators
    )
    warnings: list[str] = list(additional_warnings) + [
        f"Only {configured_codes} contribute; other indicators are not scored."
    ]
    eligible_weight = Decimal("0")
    weighted_total = Decimal("0")
    used_data_classes: set[str] = set()

    for definition in configuration.indicators:
        item = inputs_by_code.get(definition.code)
        if item is None:
            item = AssessmentInput(
                code=definition.code,
                numeric_value=None,
                text_value=None,
                unit=None,
                quality_status="MISSING",
                data_class=None,
                provenance="No input provided.",
                period="",
            )

        quality_status = item.quality_status
        normalized: Decimal | None = None
        weight_used: Decimal | None = None
        contribution: Decimal | None = None
        explanation = (
            f"{definition.label}: {item.provenance}; "
            f"data class {item.data_class or 'unavailable'}; "
            f"period {item.period or 'unspecified'}."
        )

        if not periods_aligned:
            if quality_status != "MISSING":
                quality_status = "INVALID"
                warnings.append(
                    f"{definition.code} excluded because exact stored periods do not match."
                )
            explanation += " Not scored because required stored periods do not align."
            if quality_status == "MISSING":
                missing.append(definition.code)
        elif quality_status == "MISSING":
            missing.append(definition.code)
        elif not _source_is_eligible(item):
            warnings.append(
                f"{definition.code} excluded because quality status is {quality_status}."
            )
        elif item.numeric_value is None:
            quality_status = "INVALID"
            warnings.append(f"{definition.code} excluded because it has no numeric value.")
        elif item.unit != definition.unit:
            quality_status = "INVALID"
            warnings.append(
                f"{definition.code} excluded because unit {item.unit!r} "
                f"does not match {definition.unit!r}."
            )
        elif not definition.lower_bound <= item.numeric_value <= definition.upper_bound:
            quality_status = "INVALID"
            warnings.append(
                f"{definition.code} excluded because it is outside the provisional "
                f"normalization bounds."
            )
        else:
            normalized = (
                (item.numeric_value - definition.lower_bound)
                / (definition.upper_bound - definition.lower_bound)
            ).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
            weight_used = definition.weight
            contribution = (normalized * definition.weight).quantize(
                Decimal("0.0001"),
                rounding=ROUND_HALF_UP,
            )
            eligible_weight += definition.weight
            weighted_total += normalized * definition.weight
            if item.data_class is not None:
                used_data_classes.add(item.data_class)
            if item.data_class == "illustrative":
                explanation += " Illustrative only; not a measured observation."

        results.append(
            IndicatorResult(
                code=definition.code,
                numeric_value=item.numeric_value,
                text_value=item.text_value,
                normalized_value=normalized,
                weight_used=weight_used,
                contribution=contribution,
                quality_status=quality_status,
                explanation=explanation,
            )
        )

    data_class = (
        next(iter(used_data_classes))
        if len(used_data_classes) == 1
        else "mixed"
        if used_data_classes
        else "unavailable"
    )
    total_weight = sum(
        (definition.weight for definition in configuration.indicators),
        start=Decimal("0"),
    )
    if total_weight <= 0:
        raise AssessmentConfigurationError(
            "Scoring configuration must have a positive total indicator weight."
        )
    coverage = (
        (eligible_weight / total_weight) * Decimal("100")
    ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if eligible_weight == 0 or coverage < configuration.minimum_coverage:
        warnings.append(
            "No score is produced unless every configured indicator is eligible."
        )
        return AssessmentResult(
            status="INSUFFICIENT_DATA",
            score=None,
            risk_category=None,
            data_coverage=coverage,
            data_class=data_class,
            indicators=tuple(results),
            missing_indicators=tuple(missing),
            warnings=tuple(warnings),
        )

    score = ((weighted_total / eligible_weight) * Decimal("100")).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP,
    )
    category = (
        configuration.low_category
        if score < configuration.low_category_ceiling
        else configuration.moderate_category
        if score < configuration.moderate_category_ceiling
        else configuration.high_category
    )
    if data_class == "illustrative":
        warnings.append(
            "Illustrative values and provisional thresholds; not an observed risk assessment."
        )
    else:
        warnings.append(
            "Scoring bounds, weights, and categories are provisional and not scientifically validated."
        )
    return AssessmentResult(
        status="SCORED",
        score=score,
        risk_category=category,
        data_coverage=coverage,
        data_class=data_class,
        indicators=tuple(results),
        missing_indicators=tuple(missing),
        warnings=tuple(warnings),
    )


def assess_area(
    area: Area,
    *,
    source: str,
    scenario_id: str | None = None,
    user=None,
    assessment_mode: str = "current",
) -> AssessmentRun:
    validate_area_for_assessment(area)
    provider_snapshot = None
    if source == "demo":
        inputs, provider_payload = _demo_provider_inputs(area, scenario_id)
        provider_snapshot = {
            "provider": provider_payload.get("source"),
            "data_class": provider_payload.get("data_class"),
            "location": provider_payload.get("location"),
            "spatial_resolution": provider_payload.get("spatial_resolution"),
            "retrieved_at": provider_payload.get("retrieved_at"),
            "quality_status": provider_payload.get("quality_status"),
            "scenario_id": provider_payload.get("scenario_id"),
            "scenario_name": provider_payload.get("scenario_name"),
            "observations": provider_payload.get("observations"),
        }
    elif source == "observations":
        if scenario_id is not None:
            raise AssessmentConfigurationError(
                "A demo scenario cannot be used with stored observations."
            )
        inputs, periods_aligned, input_warnings = _latest_observation_inputs(
            area,
            assessment_mode=assessment_mode,
        )
    else:
        raise AssessmentConfigurationError("Assessment source must be demo or observations.")

    if source == "demo":
        periods_aligned = True
        input_warnings = ()
    result = score_inputs(
        inputs,
        periods_aligned=periods_aligned,
        additional_warnings=input_warnings,
    )
    if result.data_class not in RUN_DATA_CLASSES:
        raise AssessmentConfigurationError(
            f"Unsupported assessment data class: {result.data_class!r}."
        )
    configuration_snapshot = MVP_CONFIGURATION.as_snapshot()
    if provider_snapshot is not None:
        configuration_snapshot["input_snapshot"] = provider_snapshot
    with transaction.atomic():
        run = AssessmentRun.objects.create(
            area=area,
            user=user,
            method_version=MVP_CONFIGURATION.method_version,
            configuration_version=MVP_CONFIGURATION.configuration_version,
            configuration_snapshot=configuration_snapshot,
            assessment_warnings=list(result.warnings),
            score=result.score,
            risk_category=result.risk_category,
            data_coverage=result.data_coverage,
            data_class=result.data_class,
            status=result.status,
            run_at=timezone.now(),
        )
        indicator_snapshots = [
            AssessmentIndicator(
                assessment_run=run,
                indicator_code=item.code,
                input_value_numeric=item.numeric_value,
                input_value_text=item.text_value,
                normalized_value=item.normalized_value,
                weight_used=item.weight_used,
                contribution=item.contribution,
                quality_status=item.quality_status,
                explanation=item.explanation,
            )
            for item in result.indicators
        ]
        for indicator_snapshot in indicator_snapshots:
            indicator_snapshot.full_clean()
        AssessmentIndicator.objects.bulk_create(indicator_snapshots)
        from .recommendations import evaluate_and_store_recommendations

        evaluate_and_store_recommendations(run, data_class=result.data_class)
    return run


def validate_area_for_assessment(area: Area) -> None:
    if area.area_type not in {"city", "ward"}:
        raise ValidationError(
            {"area": "Area must have a verified city or ward type before assessment."}
        )

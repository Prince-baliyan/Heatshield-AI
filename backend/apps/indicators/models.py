from django.core.exceptions import ValidationError
from django.db import models

from apps.cities.models import Area
from apps.datasets.models import Dataset


def is_city_level_resolution(spatial_resolution: str) -> bool:
    normalized = spatial_resolution.strip().lower().replace("-", "_").replace(" ", "_")
    return (
        normalized == "city"
        or "city_level" in normalized
        or "city_wide" in normalized
        or "citywide" in normalized
    )


def is_ward_level_resolution(spatial_resolution: str) -> bool:
    normalized = spatial_resolution.strip().lower().replace("-", "_").replace(" ", "_")
    return (
        normalized == "ward"
        or "ward_level" in normalized
        or "ward_wide" in normalized
    )


def validate_observation_area_resolution(area: Area, dataset: Dataset) -> None:
    if is_city_level_resolution(dataset.spatial_resolution) and area.area_type != "city":
        raise ValidationError(
            {
                "area": (
                    "City-level observations may only be attached "
                    "to an Area with area_type='city'."
                )
            }
        )
    if is_ward_level_resolution(dataset.spatial_resolution) and area.area_type != "ward":
        raise ValidationError(
            {
                "area": (
                    "Ward-level observations may only be attached "
                    "to an Area with area_type='ward'."
                )
            }
        )


class IndicatorObservation(models.Model):
    QUALITY_STATUS_CHOICES = (
        ("VALID", "Valid"),
        ("MISSING", "Missing"),
        ("INVALID", "Invalid"),
        ("STALE", "Stale"),
        ("LOW_CONFIDENCE", "Low confidence"),
        ("NOT_APPLICABLE", "Not applicable"),
        ("PENDING_REVIEW", "Pending review"),
    )

    area = models.ForeignKey(
        Area,
        on_delete=models.PROTECT,
        related_name="indicator_observations",
    )
    dataset = models.ForeignKey(
        Dataset,
        on_delete=models.PROTECT,
        related_name="indicator_observations",
    )
    indicator_code = models.CharField(max_length=100)
    period_start = models.DateField()
    period_end = models.DateField()
    raw_value_numeric = models.DecimalField(
        max_digits=16,
        decimal_places=6,
        null=True,
        blank=True,
    )
    raw_value_text = models.TextField(null=True, blank=True)
    raw_unit = models.CharField(max_length=60, null=True, blank=True)
    quality_status = models.CharField(
        max_length=30,
        choices=QUALITY_STATUS_CHOICES,
    )
    notes = models.TextField(null=True, blank=True)

    class Meta:
        db_table = "indicator_observations"
        indexes = [
            models.Index(
                fields=("area", "indicator_code"),
                name="ix_observation_area_code",
            )
        ]
        constraints = [
            models.UniqueConstraint(
                fields=(
                    "area",
                    "dataset",
                    "indicator_code",
                    "period_start",
                    "period_end",
                ),
                name="uq_obs_area_dataset_period",
            )
        ]
        ordering = ("-period_end", "indicator_code")

    def _validate_spatial_assignment(self):
        area = getattr(self, "area", None)
        dataset = getattr(self, "dataset", None)
        if area is None or dataset is None:
            return
        validate_observation_area_resolution(area, dataset)

    def clean(self):
        super().clean()
        self.indicator_code = (self.indicator_code or "").strip()
        if not self.indicator_code:
            raise ValidationError(
                {"indicator_code": "Indicator code is required."}
            )
        if (
            self.period_start is not None
            and self.period_end is not None
            and self.period_end < self.period_start
        ):
            raise ValidationError(
                {"period_end": "Period end cannot precede period start."}
            )
        if self.raw_value_text is not None:
            self.raw_value_text = self.raw_value_text.strip() or None
        self._validate_spatial_assignment()
        if self.dataset_id:
            if not self.dataset.is_active:
                raise ValidationError(
                    {"dataset": "Observations require an active dataset."}
                )
            if self.dataset.source.approval_status.strip().upper() != "APPROVED":
                raise ValidationError(
                    {
                        "dataset": (
                            "Observations require a dataset linked to an approved source."
                        )
                    }
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.indicator_code} at {self.area.area_name}"

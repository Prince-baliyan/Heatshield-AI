import re

from django.conf import settings
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.db import models

from apps.cities.models import Area


class AssessmentRun(models.Model):
    DATA_CLASS_CHOICES = (
        ("observed", "Observed"),
        ("derived", "Derived"),
        ("illustrative", "Illustrative"),
        ("mixed", "Mixed"),
        ("unavailable", "Unavailable"),
    )
    STATUS_CHOICES = (
        ("SCORED", "Scored"),
        ("INSUFFICIENT_DATA", "Insufficient data"),
        ("NOT_READY", "Not ready"),
        ("REVIEW_REQUIRED", "Review required"),
    )

    area = models.ForeignKey(
        Area,
        on_delete=models.PROTECT,
        related_name="assessment_runs",
    )
    user = models.ForeignKey(
        get_user_model(),
        on_delete=models.PROTECT,
        related_name="assessment_runs",
        null=True,
        blank=True,
    )
    method_version = models.CharField(max_length=40)
    configuration_version = models.CharField(max_length=40)
    configuration_snapshot = models.JSONField(null=True, blank=True)
    assessment_warnings = models.JSONField(null=True, blank=True)
    score = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
    )
    risk_category = models.CharField(max_length=30, null=True, blank=True)
    data_coverage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
    )
    data_class = models.CharField(max_length=20, choices=DATA_CLASS_CHOICES)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES)
    run_at = models.DateTimeField()

    class Meta:
        db_table = "assessment_runs"
        indexes = [
            models.Index(
                fields=("area", "run_at"),
                name="ix_assessment_area_run",
            )
        ]
        ordering = ("-run_at",)

    def clean(self):
        super().clean()
        self.method_version = (self.method_version or "").strip()
        self.configuration_version = (self.configuration_version or "").strip()
        if not self.method_version:
            raise ValidationError(
                {"method_version": "Method version is required."}
            )
        if not self.configuration_version:
            raise ValidationError(
                {"configuration_version": "Configuration version is required."}
            )
        if self.configuration_snapshot is not None and not isinstance(
            self.configuration_snapshot, dict
        ):
            raise ValidationError(
                {"configuration_snapshot": "Configuration snapshot must be a JSON object."}
            )
        if self.assessment_warnings is not None and (
            not isinstance(self.assessment_warnings, list)
            or not all(isinstance(item, str) for item in self.assessment_warnings)
        ):
            raise ValidationError(
                {"assessment_warnings": "Assessment warnings must be a list of strings."}
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        if self.pk:
            previous = type(self).objects.only(
                "configuration_snapshot",
                "assessment_warnings",
            ).get(pk=self.pk)
            if previous.configuration_snapshot != self.configuration_snapshot:
                raise ValidationError(
                    {
                        "configuration_snapshot": (
                            "Configuration snapshots are immutable after creation."
                        )
                    }
                )
            if previous.assessment_warnings != self.assessment_warnings:
                raise ValidationError(
                    {
                        "assessment_warnings": (
                            "Assessment warnings are immutable after creation."
                        )
                    }
                )
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Assessment for {self.area.area_name} ({self.status})"


class AssessmentIndicator(models.Model):
    QUALITY_STATUS_CHOICES = (
        ("VALID", "Valid"),
        ("MISSING", "Missing"),
        ("INVALID", "Invalid"),
        ("STALE", "Stale"),
        ("LOW_CONFIDENCE", "Low confidence"),
        ("NOT_APPLICABLE", "Not applicable"),
        ("PENDING_REVIEW", "Pending review"),
    )

    assessment_run = models.ForeignKey(
        AssessmentRun,
        on_delete=models.CASCADE,
        related_name="assessment_indicators",
    )
    indicator_code = models.CharField(max_length=100)
    input_value_numeric = models.DecimalField(
        max_digits=16,
        decimal_places=6,
        null=True,
        blank=True,
    )
    input_value_text = models.TextField(null=True, blank=True)
    normalized_value = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        null=True,
        blank=True,
    )
    weight_used = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        null=True,
        blank=True,
    )
    contribution = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        null=True,
        blank=True,
    )
    quality_status = models.CharField(
        max_length=30,
        choices=QUALITY_STATUS_CHOICES,
    )
    explanation = models.TextField()

    class Meta:
        db_table = "assessment_indicators"
        ordering = ("indicator_code",)

    def clean(self):
        super().clean()
        self.indicator_code = (self.indicator_code or "").strip()
        if not self.indicator_code:
            raise ValidationError(
                {"indicator_code": "Indicator code is required."}
            )
        self.explanation = (self.explanation or "").strip()
        if not self.explanation:
            raise ValidationError(
                {"explanation": "Assessment indicator explanation is required."}
            )
        if self.input_value_text is not None:
            self.input_value_text = self.input_value_text.strip() or None

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.indicator_code}: {self.assessment_run_id}"


class RecommendationRule(models.Model):
    PRIORITY_CHOICES = (
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
    )

    rule_code = models.CharField(max_length=100)
    title = models.CharField(max_length=180)
    condition_config = models.JSONField()
    recommendation_text = models.TextField()
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES)
    version = models.CharField(max_length=40)
    is_active = models.BooleanField(default=False)

    class Meta:
        db_table = "recommendation_rules"
        ordering = ("priority", "rule_code")

    def clean(self):
        super().clean()
        self.rule_code = (self.rule_code or "").strip()
        self.title = (self.title or "").strip()
        self.version = (self.version or "").strip()
        if not self.rule_code:
            raise ValidationError({"rule_code": "Rule code is required."})
        if not self.title:
            raise ValidationError({"title": "Rule title is required."})
        if not (self.recommendation_text or "").strip():
            raise ValidationError(
                {"recommendation_text": "Recommendation text is required."}
            )
        if not self.version:
            raise ValidationError({"version": "Rule version is required."})
        if not isinstance(self.condition_config, dict) or not self.condition_config:
            raise ValidationError(
                {
                    "condition_config": (
                        "Recommendation rule configuration must be a non-empty JSON object."
                    )
                }
            )
        from .recommendations import validate_rule_for_save

        validate_rule_for_save(self.condition_config)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.rule_code} v{self.version}"


class AssessmentRecommendation(models.Model):
    assessment_run = models.ForeignKey(
        AssessmentRun,
        on_delete=models.CASCADE,
        related_name="assessment_recommendations",
    )
    recommendation_rule = models.ForeignKey(
        RecommendationRule,
        on_delete=models.PROTECT,
        related_name="assessment_recommendations",
    )
    rule_version_applied = models.CharField(max_length=40)
    rule_snapshot = models.JSONField(null=True, blank=True)
    trigger_explanation = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "assessment_recommendations"
        ordering = ("-created_at",)

    def clean(self):
        super().clean()
        self.rule_version_applied = (self.rule_version_applied or "").strip()
        if not self.rule_version_applied:
            raise ValidationError(
                {"rule_version_applied": "Applied rule version is required."}
            )
        if self.rule_snapshot is not None and not isinstance(self.rule_snapshot, dict):
            raise ValidationError(
                {"rule_snapshot": "Recommendation snapshot must be a JSON object."}
            )
        if (
            self.pk is None
            and self.assessment_run_id
            and self.recommendation_rule_id
            and type(self).objects.filter(
                assessment_run_id=self.assessment_run_id,
                recommendation_rule_id=self.recommendation_rule_id,
            ).exists()
        ):
            raise ValidationError(
                "This recommendation rule is already applied to the assessment."
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        if self.pk:
            previous = type(self).objects.only("rule_snapshot").get(pk=self.pk)
            if previous.rule_snapshot != self.rule_snapshot:
                raise ValidationError(
                    {
                        "rule_snapshot": (
                            "Recommendation snapshots are immutable after creation."
                        )
                    }
                )
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.assessment_run_id}: {self.recommendation_rule.rule_code}"


class AssessmentIdempotencyRecord(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="assessment_idempotency_records",
    )
    key = models.CharField(max_length=128)
    request_fingerprint = models.CharField(max_length=64)
    assessment_run = models.OneToOneField(
        AssessmentRun,
        on_delete=models.CASCADE,
        related_name="idempotency_record",
    )

    class Meta:
        db_table = "assessment_idempotency_records"
        constraints = [
            models.UniqueConstraint(
                fields=("user", "key"),
                name="uq_assess_idem_user_key",
            )
        ]

    def clean(self):
        super().clean()
        self.key = (self.key or "").lower()
        if not re.fullmatch(r"[A-Za-z0-9._~:-]{1,128}", self.key or ""):
            raise ValidationError(
                {"key": "Idempotency key must be 1-128 URL-safe characters."}
            )
        if not re.fullmatch(r"[0-9a-f]{64}", self.request_fingerprint or ""):
            raise ValidationError(
                {"request_fingerprint": "Request fingerprint must be a SHA-256 hex digest."}
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Assessment idempotency record for user {self.user_id}"

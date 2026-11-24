from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import URLValidator
from django.db import IntegrityError, transaction
from rest_framework import serializers

from apps.indicators.models import IndicatorObservation
from .models import DataSource, Dataset


APPROVAL_STATUSES = ("PENDING", "APPROVED", "REJECTED")
SUPPORTED_INDICATOR_UNITS = {
    "AIR_TEMPERATURE": {"degree_celsius"},
    "RELATIVE_HUMIDITY": {"percent"},
    "RAINFALL_24H": {"mm"},
}


class ValidatedModelSerializer(serializers.ModelSerializer):
    def to_internal_value(self, data):
        if hasattr(data, "keys"):
            unexpected = set(data.keys()) - set(self.fields)
            if unexpected:
                raise serializers.ValidationError(
                    {"non_field_errors": ["Unexpected fields are not allowed."]}
                )
        return super().to_internal_value(data)

    def create(self, validated_data):
        instance = self.Meta.model(**validated_data)
        try:
            instance.full_clean()
            instance.save()
        except DjangoValidationError as error:
            raise serializers.ValidationError(
                getattr(error, "message_dict", {"non_field_errors": error.messages})
            ) from error
        return instance

    def update(self, instance, validated_data):
        for field, value in validated_data.items():
            setattr(instance, field, value)
        try:
            instance.full_clean()
            instance.save()
        except DjangoValidationError as error:
            raise serializers.ValidationError(
                getattr(error, "message_dict", {"non_field_errors": error.messages})
            ) from error
        return instance


class DataSourceListSerializer(serializers.ModelSerializer):
    dataset_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = DataSource
        fields = (
            "id",
            "source_name",
            "owner_name",
            "approval_status",
            "created_at",
            "dataset_count",
        )
        read_only_fields = fields


class DataSourceAdminSerializer(ValidatedModelSerializer):
    approval_status = serializers.ChoiceField(choices=APPROVAL_STATUSES)

    class Meta:
        model = DataSource
        fields = (
            "id",
            "source_name",
            "owner_name",
            "official_url",
            "licence_terms",
            "approval_status",
            "created_at",
        )
        read_only_fields = ("id", "created_at")

    def validate_official_url(self, value):
        if value:
            try:
                URLValidator(schemes=("http", "https"))(value)
            except DjangoValidationError as error:
                raise serializers.ValidationError(error.messages) from error
        return value


class DatasetListSerializer(serializers.ModelSerializer):
    source_name = serializers.CharField(source="source.source_name", read_only=True)

    class Meta:
        model = Dataset
        fields = (
            "id",
            "dataset_name",
            "source_name",
            "data_class",
            "spatial_resolution",
            "published_at",
            "coverage_start",
            "coverage_end",
            "retrieved_at",
            "is_active",
        )
        read_only_fields = fields


class DatasetAdminSerializer(ValidatedModelSerializer):
    source_name = serializers.CharField(source="source.source_name", read_only=True)
    source_approval_status = serializers.CharField(
        source="source.approval_status",
        read_only=True,
    )

    class Meta:
        model = Dataset
        fields = (
            "id",
            "source",
            "source_name",
            "source_approval_status",
            "dataset_name",
            "data_class",
            "spatial_resolution",
            "published_at",
            "coverage_start",
            "coverage_end",
            "retrieved_at",
            "file_hash",
            "transformation_notes",
            "is_active",
        )
        read_only_fields = ("id", "source_name", "source_approval_status")

    def validate(self, attrs):
        attrs = super().validate(attrs)
        source = attrs.get("source", getattr(self.instance, "source", None))
        is_active = attrs.get(
            "is_active",
            getattr(self.instance, "is_active", False),
        )
        if (
            is_active
            and source is not None
            and source.approval_status.strip().upper() != "APPROVED"
        ):
            raise serializers.ValidationError(
                {"source": "Active datasets require an approved data source."}
            )
        return attrs


class IndicatorObservationListSerializer(serializers.ModelSerializer):
    area_name = serializers.CharField(source="area.area_name", read_only=True)
    city_name = serializers.CharField(source="area.city.name", read_only=True)
    dataset_name = serializers.CharField(source="dataset.dataset_name", read_only=True)
    data_class = serializers.CharField(source="dataset.data_class", read_only=True)

    class Meta:
        model = IndicatorObservation
        fields = (
            "id",
            "area_name",
            "city_name",
            "dataset_name",
            "data_class",
            "indicator_code",
            "period_start",
            "period_end",
            "raw_value_numeric",
            "raw_value_text",
            "raw_unit",
            "quality_status",
        )
        read_only_fields = fields


class IndicatorObservationAdminSerializer(ValidatedModelSerializer):
    area_name = serializers.CharField(source="area.area_name", read_only=True)
    city_name = serializers.CharField(source="area.city.name", read_only=True)
    dataset_name = serializers.CharField(source="dataset.dataset_name", read_only=True)
    data_class = serializers.CharField(source="dataset.data_class", read_only=True)

    class Meta:
        model = IndicatorObservation
        fields = (
            "id",
            "area",
            "area_name",
            "city_name",
            "dataset",
            "dataset_name",
            "data_class",
            "indicator_code",
            "period_start",
            "period_end",
            "raw_value_numeric",
            "raw_value_text",
            "raw_unit",
            "quality_status",
            "notes",
        )
        read_only_fields = ("id", "area_name", "city_name", "dataset_name", "data_class")

    def validate_indicator_code(self, value):
        code = value.strip().upper()
        if code not in SUPPORTED_INDICATOR_UNITS:
            raise serializers.ValidationError("Unsupported indicator code.")
        return code

    def validate(self, attrs):
        attrs = super().validate(attrs)
        observation = self.instance or IndicatorObservation()
        values = {
            "area": attrs.get("area", getattr(observation, "area", None)),
            "dataset": attrs.get("dataset", getattr(observation, "dataset", None)),
            "indicator_code": attrs.get(
                "indicator_code", getattr(observation, "indicator_code", "")
            ),
            "period_start": attrs.get(
                "period_start", getattr(observation, "period_start", None)
            ),
            "period_end": attrs.get(
                "period_end", getattr(observation, "period_end", None)
            ),
            "raw_value_numeric": attrs.get(
                "raw_value_numeric", getattr(observation, "raw_value_numeric", None)
            ),
            "raw_value_text": attrs.get(
                "raw_value_text", getattr(observation, "raw_value_text", None)
            ),
            "raw_unit": attrs.get("raw_unit", getattr(observation, "raw_unit", None)),
            "quality_status": attrs.get(
                "quality_status", getattr(observation, "quality_status", "")
            ),
        }
        code = values["indicator_code"]
        allowed_units = SUPPORTED_INDICATOR_UNITS.get(code)
        if allowed_units is None:
            raise serializers.ValidationError(
                {"indicator_code": "Unsupported indicator code."}
            )
        if (
            values["raw_value_numeric"] is not None
            and values["raw_value_text"] not in (None, "")
        ):
            raise serializers.ValidationError(
                {"raw_value_text": "Provide a numeric or text value, not both."}
            )
        if code in {"AIR_TEMPERATURE", "RELATIVE_HUMIDITY"}:
            if (
                values["quality_status"] != "MISSING"
                and values["raw_value_numeric"] is None
            ):
                raise serializers.ValidationError(
                    {
                        "raw_value_numeric": (
                            "A numeric value is required for this indicator."
                        )
                    }
                )
            if values["raw_value_text"] not in (None, ""):
                raise serializers.ValidationError(
                    {"raw_value_text": "Scoring indicators require a numeric value."}
                )
        elif (
            values["quality_status"] != "MISSING"
            and values["raw_value_numeric"] is None
            and not values["raw_value_text"]
        ):
            raise serializers.ValidationError(
                {"raw_value_numeric": "A value is required unless quality is MISSING."}
            )
        if (
            values["raw_value_numeric"] is not None
            and values["raw_unit"] not in allowed_units
        ):
            raise serializers.ValidationError(
                {"raw_unit": f"{code} requires unit {', '.join(sorted(allowed_units))}."}
            )
        if values["quality_status"] == "VALID" and (
            values["raw_value_numeric"] is None
            or values["raw_unit"] not in allowed_units
        ):
            raise serializers.ValidationError(
                {
                    "quality_status": (
                        "VALID requires a numeric value and its supported unit."
                    )
                }
            )
        if (
            values["period_start"] is not None
            and values["period_end"] is not None
            and values["period_end"] < values["period_start"]
        ):
            raise serializers.ValidationError(
                {"period_end": "Period end cannot precede period start."}
            )
        if values["area"] is not None and values["dataset"] is not None:
            try:
                observation.area = values["area"]
                observation.dataset = values["dataset"]
                observation._validate_spatial_assignment()
            except DjangoValidationError as error:
                raise serializers.ValidationError(
                    getattr(error, "message_dict", {"area": error.messages})
                ) from error
        dataset = values["dataset"]
        if dataset is not None:
            if not dataset.is_active:
                raise serializers.ValidationError(
                    {"dataset": "Observations require an active dataset."}
                )
            if dataset.source.approval_status.strip().upper() != "APPROVED":
                raise serializers.ValidationError(
                    {"dataset": "Observations require a dataset linked to an approved source."}
                )
        if all(
            values[field] is not None
            for field in ("area", "dataset", "indicator_code", "period_start", "period_end")
        ):
            duplicate_query = IndicatorObservation.objects.filter(
                area=values["area"],
                dataset=values["dataset"],
                indicator_code=code,
                period_start=values["period_start"],
                period_end=values["period_end"],
            )
            if self.instance is not None:
                duplicate_query = duplicate_query.exclude(pk=self.instance.pk)
            if duplicate_query.exists():
                raise serializers.ValidationError(
                    {
                        "non_field_errors": [
                            "An observation already exists for this area, dataset, "
                            "indicator and period."
                        ]
                    }
                )
        return attrs

    def create(self, validated_data):
        try:
            with transaction.atomic():
                return super().create(validated_data)
        except IntegrityError as error:
            raise serializers.ValidationError(
                    {
                        "non_field_errors": [
                            "An observation already exists for this area, dataset, "
                            "indicator and period."
                        ]
                    }
                ) from error

    def update(self, instance, validated_data):
        try:
            with transaction.atomic():
                return super().update(instance, validated_data)
        except IntegrityError as error:
            raise serializers.ValidationError(
                    {
                        "non_field_errors": [
                            "An observation already exists for this area, dataset, "
                            "indicator and period."
                        ]
                    }
                ) from error

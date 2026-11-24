from apps.cities.models import Area
from rest_framework import serializers

from .models import (
    AssessmentIndicator,
    AssessmentRecommendation,
    AssessmentRun,
    RecommendationRule,
)


class CreateAssessmentSerializer(serializers.Serializer):
    area_id = serializers.IntegerField(min_value=1)
    source = serializers.ChoiceField(
        choices=(("observations", "Stored observations"), ("demo", "Illustrative demo")),
        default="observations",
    )
    scenario = serializers.ChoiceField(
        choices=(
            ("standard", "Standard illustration"),
            ("hot_dry", "Hot and dry"),
            ("hot_humid", "Hot and humid"),
            ("moderate", "Moderate conditions"),
            ("heavy_rainfall", "Heavy rainfall illustration"),
        ),
        required=False,
        allow_null=True,
    )
    assessment_mode = serializers.ChoiceField(
        choices=(("current", "Current conditions"), ("historical", "Historical case study")),
        default="current",
    )

    def validate(self, attrs):
        if attrs.get("source") == "observations" and attrs.get("scenario") is not None:
            raise serializers.ValidationError(
                {"scenario": "A demo scenario is only valid for demo assessments."}
            )
        if attrs.get("source") == "demo" and attrs.get("assessment_mode") == "historical":
            raise serializers.ValidationError(
                {"assessment_mode": "Historical mode is only valid for stored observations."}
            )
        return attrs


class AreaSummarySerializer(serializers.ModelSerializer):
    city_name = serializers.CharField(source="city.name", read_only=True)

    class Meta:
        model = Area
        fields = ("id", "area_name", "area_type", "city_name")


class AssessmentIndicatorSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssessmentIndicator
        fields = (
            "indicator_code",
            "input_value_numeric",
            "input_value_text",
            "normalized_value",
            "weight_used",
            "contribution",
            "quality_status",
            "explanation",
        )


class AssessmentRecommendationSerializer(serializers.ModelSerializer):
    rule_code = serializers.SerializerMethodField()
    title = serializers.SerializerMethodField()
    priority = serializers.SerializerMethodField()
    recommendation_text = serializers.SerializerMethodField()
    content_snapshot_available = serializers.SerializerMethodField()

    class Meta:
        model = AssessmentRecommendation
        fields = (
            "id",
            "rule_code",
            "title",
            "priority",
            "recommendation_text",
            "rule_version_applied",
            "trigger_explanation",
            "created_at",
            "content_snapshot_available",
        )

    def _snapshot_value(self, obj, key):
        if not isinstance(obj.rule_snapshot, dict):
            return None
        return obj.rule_snapshot.get(key)

    def get_rule_code(self, obj):
        return self._snapshot_value(obj, "rule_code")

    def get_title(self, obj):
        return self._snapshot_value(obj, "title")

    def get_priority(self, obj):
        return self._snapshot_value(obj, "priority")

    def get_recommendation_text(self, obj):
        return self._snapshot_value(obj, "recommendation_text")

    def get_content_snapshot_available(self, obj):
        return isinstance(obj.rule_snapshot, dict)


def ordered_recommendation_queryset():
    return AssessmentRecommendation.objects.order_by("pk")


class AssessmentRunSerializer(serializers.ModelSerializer):
    area = AreaSummarySerializer(read_only=True)
    data_class = serializers.SerializerMethodField()
    indicators = AssessmentIndicatorSerializer(
        source="assessment_indicators",
        many=True,
        read_only=True,
    )
    recommendations = serializers.SerializerMethodField()
    score_type = serializers.SerializerMethodField()
    category_is_provisional = serializers.SerializerMethodField()
    warnings = serializers.SerializerMethodField()

    class Meta:
        model = AssessmentRun
        fields = (
            "id",
            "area",
            "status",
            "score_type",
            "score",
            "risk_category",
            "category_is_provisional",
            "data_coverage",
            "data_class",
            "method_version",
            "configuration_version",
            "configuration_snapshot",
            "run_at",
            "indicators",
            "recommendations",
            "warnings",
        )

    def get_score_type(self, obj):
        return "relative_heat_vulnerability_index"

    def get_category_is_provisional(self, obj):
        return obj.risk_category is not None

    def get_data_class(self, obj):
        if obj.data_class == "unavailable":
            return "unavailable"
        indicators = obj.assessment_indicators.all()
        if not any(indicator.normalized_value is not None for indicator in indicators):
            return "unavailable"
        return obj.data_class

    def get_recommendations(self, obj):
        recommendations = getattr(
            obj,
            "_ordered_assessment_recommendations",
            None,
        )
        if recommendations is None:
            recommendations = ordered_recommendation_queryset().filter(
                assessment_run=obj
            )
        return AssessmentRecommendationSerializer(recommendations, many=True).data

    def get_warnings(self, obj):
        data_class = self.get_data_class(obj)
        warnings = list(getattr(obj, "assessment_warnings", None) or [])
        standard_warnings = [
            "Scoring bounds, weights, minimum coverage, and categories are provisional; "
            "the index is not scientifically validated.",
            "Only AIR_TEMPERATURE and RELATIVE_HUMIDITY contribute; unconfigured indicators "
            "such as rainfall are not scored.",
        ]
        if data_class == "illustrative":
            standard_warnings.insert(
                0,
                "Illustrative demo inputs; this is not an observed weather assessment.",
            )
        if data_class == "unavailable":
            standard_warnings.insert(
                0,
                "No usable assessment inputs were available; data class is unavailable.",
            )
        if obj.status == "INSUFFICIENT_DATA":
            standard_warnings.append(
                "No numeric score or category is available because configured coverage "
                "requirements were not met."
            )
        return list(dict.fromkeys(warnings + standard_warnings))


class RecommendationRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = RecommendationRule
        fields = (
            "id",
            "rule_code",
            "title",
            "condition_config",
            "recommendation_text",
            "priority",
            "version",
        )

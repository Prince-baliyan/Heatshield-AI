from django.core.management.base import BaseCommand
from django.db import transaction

from apps.assessments.models import RecommendationRule


RECOMMENDATION_RULES = (
    {
        "rule_code": "HIGH_TEMPERATURE_AWARENESS",
        "title": "Temperature awareness",
        "condition_config": {
            "all": [
                {
                    "field": "indicators.AIR_TEMPERATURE.normalized_value",
                    "operator": "gte",
                    "value": "0.65",
                },
                {
                    "field": "indicators.AIR_TEMPERATURE.quality_status",
                    "operator": "in",
                    "value": ["VALID", "LOW_CONFIDENCE"],
                },
            ]
        },
        "recommendation_text": (
            "The temperature input met this provisional awareness trigger. "
            "Share local heat-safety guidance, encourage access to shade and "
            "drinking water, and follow official local advisories. This is "
            "general public awareness, not medical advice."
        ),
        "priority": "high",
        "version": "1.0.0",
        "is_active": True,
    },
    {
        "rule_code": "INSUFFICIENT_DATA_AWARENESS",
        "title": "Assessment data is incomplete",
        "condition_config": {
            "all": [
                {
                    "field": "status",
                    "operator": "eq",
                    "value": "INSUFFICIENT_DATA",
                }
            ]
        },
        "recommendation_text": (
            "This assessment did not meet its configured data-coverage "
            "requirement. Do not interpret the missing score as evidence of "
            "low risk; review data availability before drawing conclusions."
        ),
        "priority": "high",
        "version": "1.0.0",
        "is_active": True,
    },
    {
        "rule_code": "MODERATE_CATEGORY_MONITORING",
        "title": "Monitor the provisional category",
        "condition_config": {
            "all": [
                {"field": "status", "operator": "eq", "value": "SCORED"},
                {
                    "field": "risk_category",
                    "operator": "eq",
                    "value": "illustrative_moderate",
                },
            ]
        },
        "recommendation_text": (
            "This run falls in the engine's provisional moderate category. "
            "Consider reviewing updated inputs and official local advisories; "
            "this category is not a validated risk classification."
        ),
        "priority": "medium",
        "version": "1.0.0",
        "is_active": True,
    },
    {
        "rule_code": "HUMIDITY_COMFORT_AWARENESS",
        "title": "Humidity awareness",
        "condition_config": {
            "all": [
                {
                    "field": "indicators.RELATIVE_HUMIDITY.normalized_value",
                    "operator": "gte",
                    "value": "0.50",
                },
                {
                    "field": "indicators.RELATIVE_HUMIDITY.quality_status",
                    "operator": "in",
                    "value": ["VALID", "LOW_CONFIDENCE"],
                },
            ]
        },
        "recommendation_text": (
            "The humidity input met this provisional awareness trigger. "
            "Share current local weather and comfort guidance, considering "
            "humidity together with temperature and official advisories. "
            "This is general public awareness, not medical advice."
        ),
        "priority": "low",
        "version": "1.0.0",
        "is_active": True,
    },
)


class Command(BaseCommand):
    help = "Create missing, versioned public-awareness recommendation rules."

    def handle(self, *args, **options):
        created_codes = []
        existing_codes = []
        with transaction.atomic():
            for rule_values in RECOMMENDATION_RULES:
                rule, created = RecommendationRule.objects.get_or_create(
                    rule_code=rule_values["rule_code"],
                    defaults={
                        key: value
                        for key, value in rule_values.items()
                        if key != "rule_code"
                    },
                )
                if created:
                    created_codes.append(rule.rule_code)
                else:
                    existing_codes.append(rule.rule_code)

        self.stdout.write(
            self.style.SUCCESS(
                f"Recommendation rules ready: {len(created_codes)} created, "
                f"{len(existing_codes)} already existed and were left unchanged."
            )
        )

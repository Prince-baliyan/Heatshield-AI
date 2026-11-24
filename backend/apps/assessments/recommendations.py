import json
import logging
import re
from decimal import Decimal, InvalidOperation
from typing import Any

from django.core.exceptions import ValidationError
from django.db import transaction

from .models import (
    AssessmentIndicator,
    AssessmentRecommendation,
    AssessmentRun,
    RecommendationRule,
)


logger = logging.getLogger(__name__)
PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}
ALLOWED_FIELDS = {
    "score",
    "data_coverage",
    "risk_category",
    "data_class",
    "status",
}
INDICATOR_FIELD_PATTERN = re.compile(
    r"^indicators\.([A-Z][A-Z0-9_]*)\.(normalized_value|quality_status)$"
)
ALLOWED_OPERATORS = {"eq", "ne", "gt", "gte", "lt", "lte", "in"}


class RuleConfigurationError(ValueError):
    """Raised when a recommendation rule uses an unsupported JSON structure."""


def _validate_condition(condition: Any) -> None:
    if not isinstance(condition, dict) or set(condition) != {
        "field",
        "operator",
        "value",
    }:
        raise RuleConfigurationError(
            "Each condition must contain exactly field, operator, and value."
        )
    field = condition["field"]
    if not isinstance(field, str) or not (
        field in ALLOWED_FIELDS or INDICATOR_FIELD_PATTERN.fullmatch(field)
    ):
        raise RuleConfigurationError(f"Unsupported condition field: {field!r}.")
    operator = condition["operator"]
    if not isinstance(operator, str) or operator not in ALLOWED_OPERATORS:
        raise RuleConfigurationError(f"Unsupported condition operator: {operator!r}.")
    value = condition["value"]
    if operator == "in":
        if not isinstance(value, list) or not value:
            raise RuleConfigurationError("The 'in' operator requires a non-empty list.")
    elif operator in {"gt", "gte", "lt", "lte"}:
        try:
            parsed = Decimal(str(value))
        except (InvalidOperation, ValueError):
            raise RuleConfigurationError(
                f"The {operator!r} operator requires a numeric value."
            ) from None
        if not parsed.is_finite():
            raise RuleConfigurationError(
                f"The {operator!r} operator requires a finite numeric value."
            )


def validate_condition_config(config: Any) -> tuple[str, list[dict[str, Any]]]:
    if not isinstance(config, dict) or len(config) != 1:
        raise RuleConfigurationError(
            "Configuration must contain exactly one of 'all' or 'any'."
        )
    logical_operator, conditions = next(iter(config.items()))
    if logical_operator not in {"all", "any"}:
        raise RuleConfigurationError(
            "Configuration must contain exactly one of 'all' or 'any'."
        )
    if not isinstance(conditions, list) or not conditions:
        raise RuleConfigurationError(
            f"The {logical_operator!r} condition list must not be empty."
        )
    for condition in conditions:
        _validate_condition(condition)
    return logical_operator, conditions


def _context_for_run(
    run: AssessmentRun,
    *,
    data_class: str | None = None,
) -> dict[str, Any]:
    indicators = {
        item.indicator_code: {
            "normalized_value": item.normalized_value,
            "quality_status": item.quality_status,
        }
        for item in run.assessment_indicators.all()
    }
    return {
        "score": run.score,
        "data_coverage": run.data_coverage,
        "risk_category": run.risk_category,
        "data_class": data_class or run.data_class,
        "status": run.status,
        "indicators": indicators,
    }


def _lookup(context: dict[str, Any], field: str) -> Any:
    if field in ALLOWED_FIELDS:
        return context.get(field)
    match = INDICATOR_FIELD_PATTERN.fullmatch(field)
    if match is None:
        return None
    code, attribute = match.groups()
    return context["indicators"].get(code, {}).get(attribute)


def _numeric_pair(left: Any, right: Any) -> tuple[Decimal, Decimal] | None:
    try:
        pair = Decimal(str(left)), Decimal(str(right))
    except (InvalidOperation, ValueError):
        return None
    return pair if all(value.is_finite() for value in pair) else None


def _equal(left: Any, right: Any) -> bool:
    pair = _numeric_pair(left, right)
    if pair is not None:
        return pair[0] == pair[1]
    return str(left) == str(right)


def _matches_condition(context: dict[str, Any], condition: dict[str, Any]) -> bool:
    actual = _lookup(context, condition["field"])
    expected = condition["value"]
    operator = condition["operator"]
    if actual is None:
        return False
    if operator == "eq":
        return _equal(actual, expected)
    if operator == "ne":
        return not _equal(actual, expected)
    if operator == "in":
        return any(_equal(actual, value) for value in expected)

    pair = _numeric_pair(actual, expected)
    if pair is None:
        raise RuleConfigurationError(
            f"Field {condition['field']!r} is not numeric for {operator!r}."
        )
    left, right = pair
    return {
        "gt": left > right,
        "gte": left >= right,
        "lt": left < right,
        "lte": left <= right,
    }[operator]


def rule_matches(config: Any, context: dict[str, Any]) -> bool:
    return bool(_matching_conditions(config, context))


def _matching_conditions(
    config: Any,
    context: dict[str, Any],
) -> tuple[dict[str, Any], ...]:
    logical_operator, conditions = validate_condition_config(config)
    matched = []
    for condition in conditions:
        if not _matches_condition(context, condition):
            if logical_operator == "all":
                return ()
            continue
        matched.append(condition)
        if logical_operator == "any":
            return tuple(matched)
    return tuple(matched)


def _trigger_explanation(
    rule: RecommendationRule,
    matched_conditions: tuple[dict[str, Any], ...],
) -> str:
    conditions = "; ".join(
        f"{condition['field']} {condition['operator']} "
        f"{json.dumps(condition['value'], sort_keys=True)}"
        for condition in matched_conditions
    )
    return (
        f"Rule {rule.rule_code} v{rule.version} matched: {conditions}."
    )


def evaluate_and_store_recommendations(
    run: AssessmentRun,
    *,
    data_class: str | None = None,
) -> list[AssessmentRecommendation]:
    with transaction.atomic():
        locked_run = AssessmentRun.objects.select_for_update().get(pk=run.pk)
        existing_rule_ids = set(
            AssessmentRecommendation.objects.filter(
                assessment_run=locked_run
            ).values_list("recommendation_rule_id", flat=True)
        )
        context = _context_for_run(locked_run, data_class=data_class)
        rules = list(RecommendationRule.objects.filter(is_active=True))
        rules.sort(
            key=lambda rule: (
                PRIORITY_ORDER.get(rule.priority, len(PRIORITY_ORDER)),
                rule.pk,
            )
        )
        created: list[AssessmentRecommendation] = []
        seen_rule_ids = set(existing_rule_ids)

        for rule in rules:
            if rule.pk in seen_rule_ids:
                continue
            try:
                matched_conditions = _matching_conditions(
                    rule.condition_config,
                    context,
                )
            except RuleConfigurationError as error:
                logger.warning(
                    "Skipping invalid recommendation rule id=%s: %s",
                    rule.pk,
                    error,
                )
                continue
            if not matched_conditions:
                continue
            recommendation = AssessmentRecommendation.objects.create(
                assessment_run=locked_run,
                recommendation_rule=rule,
                rule_version_applied=rule.version,
                rule_snapshot={
                    "rule_code": rule.rule_code,
                    "title": rule.title,
                    "recommendation_text": rule.recommendation_text,
                    "priority": rule.priority,
                    "version": rule.version,
                },
                trigger_explanation=_trigger_explanation(
                    rule,
                    matched_conditions,
                ),
            )
            created.append(recommendation)
            seen_rule_ids.add(rule.pk)
        return created


def validate_rule_for_save(config: Any) -> None:
    try:
        validate_condition_config(config)
    except RuleConfigurationError as error:
        raise ValidationError({"condition_config": str(error)}) from error

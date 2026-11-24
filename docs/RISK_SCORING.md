# Risk Scoring Framework

**Status:** Provisional implementation documented below; no production weights, cut-offs, or scientifically validated risk categories have been approved.

## MVP provisional weather configuration

The current backend implements a deterministic, provisional configuration so the assessment workflow can be demonstrated without presenting it as validated science. Its method version is `weighted-relative-index-v1`; its configuration version is a fingerprint of the method, indicators, bounds, weights, coverage requirement, thresholds, normalization, and rounding settings. The fingerprint changes when those settings change. Each new assessment stores the exact configuration snapshot alongside its version; existing assessments created before this field was added have a null snapshot. The methodology remains provisional and is not scientifically validated.

| Indicator | Unit | Provisional normalization bounds | Direction | Provisional weight |
|---|---|---:|---|---:|
| `AIR_TEMPERATURE` | `degree_celsius` | 25 to 45 | Direct | 0.70 |
| `RELATIVE_HUMIDITY` | `percent` | 30 to 90 | Direct | 0.30 |

### Critical Methodology Limitation: Temperature Variable & Normalization Bounds

> [!WARNING]
> **Methodology Limitation — Variable & Normalization Bounds Unvalidated:**
> 1. **Underlying Variable:** The stored observation ingestion pipeline (`apps/datasets/services/open_meteo_import.py`) ingests Open-Meteo's `temperature_2m_mean` (daily 24-hour mean temperature at 2 meters above ground) and maps it to `AIR_TEMPERATURE`.
> 2. **Unvalidated Bounds:** The provisional normalization bounds [25.0 °C, 45.0 °C] were calibrated around daytime ambient heat exposure / heat-wave conditions. They have **not been scientifically or epidemiologically validated for 24-hour daily mean temperature**.
> 3. **Winter Incompatibility & Safe Failure:** In temperate or winter conditions (such as late November in Meerut, where authentic daily mean temperatures range from 18.0 °C to 19.5 °C), observations fall below the 25.0 °C lower bound. The engine treats out-of-bound inputs as `INVALID` rather than clipping them, correctly producing `INSUFFICIENT_DATA` with the warning: *"AIR_TEMPERATURE excluded because it is outside the provisional normalization bounds."*
> 4. **Methodology Policy:** Scoring thresholds, input variables, freshness limits, and weights must not be relaxed or altered without an approved domain methodology decision backed by reference literature. Post-hackathon options include either re-calibrating bounds for daily mean temperature or ingesting `temperature_2m_max` (daily maximum temperature).

For each configured indicator, the implementation computes \(z=(x-L)/(U-L)\). It does not clip out-of-range values; those inputs are marked `INVALID` and excluded. An input is eligible only when its unit matches the configured unit and its quality is `VALID`; `LOW_CONFIDENCE` is eligible only for `illustrative` data and is clearly labelled. `MISSING`, `INVALID`, `STALE`, `NOT_APPLICABLE`, and `PENDING_REVIEW` do not contribute.

Coverage is the weight of eligible configured indicators divided by the total configured weight, multiplied by 100. The current minimum coverage is 100%, so an incomplete input set produces `INSUFFICIENT_DATA` with no score or category. Zero-valued data remains distinct from missing data.

The score is \(100 \times \sum(w_i z_i)/\sum(w_i)\), rounded half-up to two decimal places. The implementation uses explicitly provisional category labels `illustrative_low` (<33.33), `illustrative_moderate` (33.33 to <66.67), and `illustrative_high` (>=66.67). These boundaries are demonstration assumptions only, not validated heat-risk levels.

Only the two configured weather indicators are scored. Rainfall and other unconfigured indicators do not contribute. The weather configuration, its assumptions, and its status must be reviewed before operational use; observed data does not make the provisional index scientifically validated.

The engine classifies provenance from eligible inputs actually used: one class remains `observed`, `derived`, or `illustrative`; multiple classes become `mixed`; no eligible inputs become `unavailable`. The stored assessment run and API both use `unavailable` when no eligible inputs were used. Historical records whose stored field contains a legacy placeholder are still reported as `unavailable` when their indicator snapshots contain no normalized values; do not treat that legacy placeholder as evidence that observations were present.

Recommendation outputs are snapshotted on each new assessment, including rule code, title, recommendation text, priority, and applied version. Editing a recommendation rule therefore does not change content or priority returned for newly snapshotted historical recommendations. Earlier recommendation records have no recoverable content snapshot and are returned with `content_snapshot_available: false` rather than being represented using the current rule definition.

The repeatable `python manage.py setup_recommendation_rules` command creates missing, active, versioned public-awareness rules using the existing `all`/`any` condition schema and supported operators. Existing rules with the same code are left unchanged. The configured examples cover provisional temperature and humidity input triggers, the provisional moderate category, and insufficient-data awareness. Rule conditions and thresholds are demonstrations, not medical guidance or scientifically validated alert criteria. Each applied recommendation snapshots its rule content and version, and its trigger explanation lists the matched condition(s).

Stored observation freshness uses `MAX_OBSERVATION_AGE_DAYS` (default 7), measured from `period_end` to Django's current local date. Records older than that limit are treated as stale and do not contribute. A missing period end is never treated as fresh, and future-dated periods are invalid for stored observations. Configure the limit to match the approved source cadence; increasing it permits historical results but does not make old data current. Periods are date-only, so intraday freshness cannot be represented.

Stored scoring requires the selected temperature and humidity observations to have the exact same `period_start` and `period_end`. The engine prefers the newest eligible shared period. If no eligible shared period exists, it returns `INSUFFICIENT_DATA` and a warning rather than combining different periods. Illustrative datasets are excluded from stored-observation assessments.

## 1. What the score means

The MVP score is a **relative heat-vulnerability index** for comparing supported analysis areas under a specific set of indicators, datasets, time periods, and configuration.

It is not:
- A measured air temperature or land-surface temperature.
- A weather forecast or heatwave probability.
- A probability of illness, hospitalisation, or death.
- A causal estimate of the effect of a mitigation action.
- A guarantee that one area is safer than another in every circumstance.

Use the label “relative vulnerability index” in product copy until the method has been independently validated for a stronger claim.

## 2. Required configuration before scoring

The following must be explicitly approved and versioned:

| Configuration item | Required decision | Current status |
|---|---|---|
| Indicator catalogue | Which indicators are included and why | Provisional weather subset implemented; production catalogue `OPEN` |
| Indicator definition | Exact formula, source fields, unit, geography, period | Provisional units implemented; production definitions `OPEN` |
| Direction | Whether higher raw value increases or decreases vulnerability | Provisional direct direction for both configured indicators |
| Normalization bounds | Reference lower/upper values and treatment of outliers | Provisional bounds above; production bounds `OPEN` |
| Weights | Non-negative weights and rationale; sum convention | Provisional 0.70/0.30 weights; production rationale `OPEN` |
| Freshness policy | Maximum acceptable age by indicator | `OPEN_PER_INDICATOR` |
| Minimum coverage | Minimum eligible weight/indicator coverage for a score | Provisional 100%; production policy `OPEN` |
| Category thresholds | Boundaries and rationale for any displayed labels | Provisional demo labels above; production thresholds `OPEN` |
| Validation evidence | Expert review, sensitivity analysis, and comparison evidence | `OPEN` |

Do not choose weights or thresholds merely to produce visually balanced map colours.

## 3. Proposed calculation

For each eligible indicator \(i\), transform its raw value \(x_{a,i}\) for area \(a\) into a normalized value between 0 and 1:

\[
z_{a,i} = \frac{x_{a,i} - L_i}{U_i - L_i}
\]

For an inverse-direction indicator:

\[
z_{a,i}^{*} = 1 - z_{a,i}
\]

For a direct-direction indicator:

\[
z_{a,i}^{*} = z_{a,i}
\]

Then calculate:

\[
\text{Score}_a =
100 \times
\frac{\sum_{i \in I_a} w_i z_{a,i}^{*}}
{\sum_{i \in I_a} w_i}
\]

where:
- \(I_a\) contains only indicators eligible for that area and run.
- \(w_i\) is the approved weight for indicator \(i\).
- \(L_i, U_i\) are approved normalization bounds.
- \(z_{a,i}^{*}\) is the direction-adjusted normalized value.

The result is on a 0–100 scale only if all included normalized values are within 0–1. Bounds, clipping policy, and handling of values outside bounds must be explicitly specified and tested. If the denominator is zero, do not calculate a score.

## 4. Missing-data and coverage policy

### Default MVP rules

1. Missing is not zero.
2. Invalid observations are excluded.
3. Records marked stale are excluded; no age-based stale threshold is implemented.
4. `NOT_APPLICABLE` inputs are excluded from eligible weight, but the approved denominator treatment is unresolved. The current provisional calculation retains their configured weight in the denominator, lowering coverage.
5. Do not impute values in the MVP.
6. Never show a numeric score when the current 100% minimum coverage rule is not met.

A proposed weighted coverage measure is:

\[
\text{Coverage}_a =
\frac{\sum_{i \in V_a} w_i}
{\sum_{i \in E} w_i}
\times 100
\]

where:
- \(V_a\) is the set of configured indicators with valid, sufficiently fresh observations for area \(a\).
- \(E\) is the full configured set of expected indicators for the assessment.

This formula is a candidate definition. The team must decide how `NOT_APPLICABLE` indicators are treated in the expected set and whether all configured indicators are mandatory. The provisional implementation currently requires every configured indicator to be eligible. Display the indicator availability list so the percentage is interpretable.

### Output states

- `SCORED`: coverage and quality gates passed.
- `INSUFFICIENT_DATA`: not enough eligible data to produce a defensible score.
- `NOT_READY`: city/area or source requirements are not met.
- `REVIEW_REQUIRED`: data or configuration failed a review gate.

Never replace these states with a fabricated score. In the current API, missing or unusable inputs create an `INSUFFICIENT_DATA` run with a null score/category and `201`; the run is retained for audit. This behavior is provisional and does not imply the minimum-coverage or `NOT_APPLICABLE` policy is approved for operational use.

## 5. Risk categories

Category labels such as `Low`, `Moderate`, `High`, and `Very High` are **not approved**. Do not hard-code thresholds yet.

If categories are needed for a demo, use clearly labelled provisional thresholds stored in configuration, show “illustrative only,” and do not imply scientific validation. Prefer showing the numeric index, coverage, and indicator breakdown without categorical labels until thresholds are justified.

## 6. Illustrative example (synthetic only)

The following values demonstrate arithmetic, not a recommended indicator set or actual city data.

Assume two fictional indicators:
- Indicator A: normalized, direction-adjusted value = 0.80; illustrative weight = 0.60.
- Indicator B: normalized, direction-adjusted value = 0.40; illustrative weight = 0.40.

\[
S = 100 \times ((0.60 \times 0.80) + (0.40 \times 0.40)) = 64
\]

The result `64` is a synthetic example only. It is not a HeatShield AI threshold, a validated risk rating, or an observed measurement.

## 7. Sensitivity and robustness checks

Before approving weights and thresholds:

- Test whether small weight changes materially reorder areas.
- Compare alternative normalization bounds.
- Examine the effect of excluding each indicator in turn.
- Check whether missingness is concentrated in particular areas.
- Verify that comparisons use compatible geography and time periods.
- Have a domain-informed reviewer assess whether the outputs are plausible and not misleading.

If rankings are highly sensitive to a particular choice, disclose that limitation and avoid strong comparative claims.

## 8. API/output contract fields

Suggested response fields (names are provisional):

```json
{
  "status": "SCORED",
  "score_type": "relative_heat_vulnerability_index",
  "score": 64.0,
  "coverage_percent": 80.0,
  "method_version": "0.1",
  "configuration_version": "draft-0.1",
  "category": null,
  "indicators": [],
  "missing_indicators": [],
  "limitations": [
    "Illustrative values only; not an observed city assessment."
  ]
}
```

This is a contract illustration, not a real assessment result. Do not return example values as live data.

## 9. Approval checklist

A scoring configuration may move from `DRAFT` to `APPROVED_FOR_DEMO` only when:

- [ ] Every included indicator has a verified source and definition.
- [ ] Units, geography, period, direction, and freshness policy are documented.
- [ ] Normalization bounds and outlier behaviour are justified.
- [ ] Weights have a written rationale and sum convention.
- [ ] Missing-data and minimum-coverage rules are implemented and tested.
- [ ] Category thresholds are either omitted or explicitly marked provisional.
- [ ] Synthetic data is visibly labelled wherever used.
- [ ] A reviewer has checked limitations and example outputs.

`APPROVED_FOR_DEMO` does not mean scientifically validated or approved for public-sector operational decisions.

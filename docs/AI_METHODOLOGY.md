# AI Methodology

**MVP position:** HeatShield AI will begin with a transparent, deterministic, indicator-based assessment. It will not claim to predict heat illness, mortality, outages, or future temperatures.

## 1. Why deterministic scoring first

A trained machine-learning model requires an appropriate target label, representative training data, sufficient sample size, and a defensible evaluation design. These have not yet been established for this project. A model trained on synthetic or sparse data would create false confidence.

Therefore:

- Use verified observed datasets and documented transformations.
- Calculate an explainable relative vulnerability index.
- Show indicator contributions, coverage, data age, and caveats.
- Defer supervised ML until a suitable labelled dataset and validation plan exist.
- Do not describe a weighted index as an AI prediction.

## 2. Processing pipeline

1. **Source registration:** verify owner, official source, terms, geography, and access.
2. **Raw ingestion:** preserve source file/API response and retrieval metadata.
3. **Validation:** check schema, types, units, duplicates, valid ranges, dates, and geography.
4. **Geographic alignment:** map records to the approved analysis units using a documented method. Do not assume boundaries match.
5. **Temporal alignment:** select compatible periods or disclose mismatches. Avoid combining measurements from unrelated seasons without justification.
6. **Indicator transformation:** calculate only documented indicators from source fields; retain method and version.
7. **Freshness and quality checks:** mark missing, stale, invalid, or low-confidence observations.
8. **Normalization:** transform valid values to a common scale and orient them so larger values consistently mean greater vulnerability.
9. **Scoring:** apply the approved weights and coverage rules.
10. **Explanation:** return the score, category (if thresholds are approved), indicator contributions, data coverage, and limitations.
11. **Presentation:** show the map and tables only at the supported geographic resolution.

## 3. Normalization

For a numeric indicator with a defensible observed range:

\[
z_i = \frac{x_i - L_i}{U_i - L_i}
\]

where \(L_i\) and \(U_i\) are approved lower and upper bounds. Bounds should come from a documented domain rationale or a stable reference distribution, not arbitrary values selected to make a map look varied.

For an indicator where lower raw values imply greater vulnerability, reverse the direction:

\[
z_i^{*} = 1 - z_i
\]

For an indicator where higher raw values imply greater vulnerability:

\[
z_i^{*} = z_i
\]

If \(U_i = L_i\), the indicator has no variation under those bounds and must not be divided by zero. Flag it as non-informative for that run or apply a separately approved rule.

Outliers, skewed distributions, categorical indicators, and changing reference ranges need indicator-specific policies. Do not silently clip or transform values.

## 4. Missing data and coverage

- Never replace missing values with zero.
- Never infer that a missing facility, sensor, or population record means the real-world quantity is zero.
- Exclude missing, invalid, and disallowed stale observations from the score calculation.
- Recalculate the denominator using only eligible configured indicators, while separately reporting coverage against the full intended indicator set.
- If coverage is below the approved minimum, return `INSUFFICIENT_DATA` rather than a misleading score.
- Do not impute values in the MVP unless a specific method is justified, separately evaluated, and clearly disclosed.
- If some areas have different indicator availability, disclose that comparisons may not be like-for-like.

Coverage thresholds and stale-data rules must be defined per indicator and approved before implementation.

## 5. Scoring model

For area \(a\), let \(I_a\) be the set of eligible indicators with valid observations, \(z_{a,i}^{*}\) the direction-adjusted normalized value, and \(w_i\) the approved non-negative weight.

\[
S_a = 100 \times
\frac{\sum_{i \in I_a} w_i z_{a,i}^{*}}
{\sum_{i \in I_a} w_i}
\]

This is a relative composite index on a 0–100 scale when the configured normalized inputs are in 0–1. It is not a probability or a physical temperature.

Return `INSUFFICIENT_DATA` if the eligible weight denominator is zero or the approved coverage rule is not met. The precise coverage rule, weights, indicator set, and category thresholds are configuration decisions, not settled scientific constants.

## 6. Explainability requirements

For every scored area, expose:

- Overall score and method/configuration version.
- Each indicator's raw value and unit (where permitted), normalized value, direction, weight, and contribution.
- Dataset/source name and observation period.
- Quality status and freshness.
- Coverage ratio and missing indicators.
- Any exclusions or transformations.
- A plain-language explanation that does not claim causation.

A high score means higher relative vulnerability under the configured index; it does not establish that a particular person will experience harm.

## 7. Role of machine learning and language models

### Machine learning

Consider scikit-learn only after the team has:
- A valid labelled outcome or target.
- Adequate, representative observations.
- A documented train/validation/test strategy that avoids geographic or temporal leakage.
- Baseline comparison and suitable metrics.
- Bias, uncertainty, and generalisation checks.

Until then, ML is out of MVP scope.

### Language model (optional future feature)

An LLM may convert already-calculated results into readable explanations or summaries. It must receive structured, trusted score outputs and must not invent measurements, fill missing data, alter scores, or make unsupported causal claims. Every numeric statement must be traceable to the computed result.

## 8. Validation plan

Before public claims or operational use:

- Unit-test normalization, direction reversal, weights, coverage, and zero-denominator handling.
- Test missing, stale, invalid, duplicate, and outlier records.
- Recompute the same run from the same input and configuration to verify reproducibility.
- Compare outputs with domain-expert review and independent reference information where available.
- Perform sensitivity analysis to show how rankings change when weights or bounds change.
- Document limitations and version all approved configurations.

## 9. Method governance

Each assessment must store `method_version`, `configuration_version`, run timestamp, dataset identifiers, and quality summary. Any change to indicator definitions, bounds, weights, or thresholds requires a new configuration version and a short change note.

# Test Strategy

**Purpose:** Define how HeatShield AI will be tested before implementation begins.

## 1. Testing principles

- Test calculations independently from API and UI.
- Test failure and missing-data cases, not only successful examples.
- Use deterministic fixtures with fixed expected outputs.
- Keep synthetic fixtures clearly named and isolated from verified datasets.
- Never use a passing software test as evidence that the scientific method is valid.
- Record test commands and results for each release candidate.

## 2. Test layers

| Layer | What to test | Examples |
|---|---|---|
| Unit | Small deterministic functions | Normalization, direction reversal, weighted score, coverage |
| Model | Database constraints and relationships | Foreign keys, uniqueness, required provenance |
| Import/validation | Source file parsing and quality checks | Missing columns, invalid units, duplicate rows, malformed dates |
| API | Contract, permissions, status codes | City list, area list, assessment status, validation errors |
| Frontend component | Visible states and interactions | Loading, empty, error, insufficient-data state |
| Integration | Database + API + scoring | Import observations then retrieve reproducible assessment |
| End-to-end | User's main demo workflow | Select city, view areas, open area detail, inspect score explanation |
| Security | Configuration and access boundaries | Secret handling, admin permissions, unsafe inputs |
| Manual acceptance | Usability and demo readiness | Map/list clarity, labels, provenance and caveats |

## 3. Minimum scoring test cases

1. All configured indicators valid: score matches hand-calculated expected result.
2. Inverse-direction indicator: normalized orientation is reversed correctly.
3. Missing indicator: missing value is not treated as zero.
4. Invalid indicator: excluded and visible in quality output.
5. Stale observation: follows the configured freshness policy.
6. Zero eligible weight: returns `INSUFFICIENT_DATA`, not a numeric score.
7. Coverage below threshold: returns `INSUFFICIENT_DATA`.
8. Constant normalization range (`upper == lower`): no division by zero.
9. Value outside approved bounds: follows the documented policy.
10. Weight validation: negative weights and invalid totals are rejected.
11. Reproducibility: same inputs and configuration produce the same output.
12. Versioning: changing configuration creates a distinct assessment version.

## 4. Data validation tests

- Required columns exist.
- Data types and units match the dataset specification.
- Duplicate records are detected using an explicit natural key.
- Geographic identifiers map to known analysis units.
- Dates fall within the declared coverage period.
- Null, zero, and not-applicable values remain distinct.
- Source metadata and retrieval timestamp are retained.
- Imported record counts and rejected row counts are reported.

## 5. API and frontend tests

Verify the API returns documented response fields and status codes. Test empty city lists, unknown IDs, unavailable assessments, insufficient-data responses, and validation failures.

The frontend must not:
- Display `null` as zero.
- Display a numeric score for an insufficient-data response.
- Show synthetic data without an obvious demo label.
- Present provisional categories as validated risk classifications.
- Imply unsupported street-level precision.

## 6. Demo acceptance path

A release candidate should support this repeatable path:

1. Start MySQL 8.0 and backend using the documented setup.
2. Apply migrations and load the approved demo fixture.
3. Start the frontend.
4. Open the configured demo city.
5. Select an analysis area.
6. Inspect score, indicator contributions, data coverage, sources, and limitations.
7. Select an area with intentionally incomplete data and confirm the UI displays `INSUFFICIENT_DATA`.
8. Reset and repeat the demo successfully.

## 7. Release test report

For each release candidate record:
- Commit hash / version.
- Environment and dependency versions.
- Test command.
- Passed, failed, skipped counts.
- Known failures and accepted limitations.
- Dataset/fixture identifiers.
- Reviewer and test date.

## 8. Scientific and domain validation

Software tests verify that code follows the specified method. They do not validate the choice of indicators, weights, thresholds, or the real-world meaning of the index. These require documented rationale, sensitivity analysis, and appropriate domain-informed review.

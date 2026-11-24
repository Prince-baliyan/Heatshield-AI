# MVP Scope — 28 November 2026 Demo

## Objective

Deliver one reliable end-to-end demonstration of area-level heat-impact assessment. Prefer a narrow working workflow over multiple incomplete features.

## Must-have (P0)

1. Configurable city/area catalogue; enable only entries with known data coverage.
2. Map view showing configured areas or representative points.
3. Area-level transparent indicator score/category.
4. Visible explanation of score drivers.
5. Data source, freshness, coverage and sample-data disclosure.
6. Small set of response suggestions linked to assessment drivers.
7. Empty, insufficient-data, invalid-selection and error states.
8. Reproducible demo dataset and documented run instructions.

## Should-have (P1, only after P0 is stable)

Area comparison; basic indicator charts; export/print area summary; simple risk/dimension filters.

## Stretch (P2)

What-if scenarios; more cities; automated ingestion/scheduled refresh; advanced geospatial analysis; ML model only if labelled data and evaluation are suitable.

## Explicit exclusions

No unsupported exact street-level temperature claims; no illness/death/hospital-demand prediction; no presenting illustrative values as observations; no automated resource dispatch or official alerts; no untested external API dependency without fallback.

## Demo data policy

Classify every record as:
- **Observed/source-derived:** traceable to source and transformation.
- **Derived:** calculated from documented source fields with recorded method.
- **Sample/illustrative:** created for workflow demonstration and visibly labelled.

Preserve provenance when combining data classes.

## Definition of done

Project starts using documented commands; user completes main area-assessment workflow; scores are deterministic for fixed inputs and tested; UI explains drivers and limitations; insufficient data cannot produce a misleading score; team can repeat demo from a clean setup.

## Scope control

Defer non-P0 features until P0 acceptance criteria pass. Under time pressure, reduce city count, indicator count or visualisations before weakening data transparency or test coverage.

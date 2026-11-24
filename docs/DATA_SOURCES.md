# Data Sources

**Project:** HeatShield AI
**Status:** Candidate source register — verification required
**Purpose:** Record where each input dataset may come from and prevent the implementation from depending on imaginary, inaccessible, or unlicensed APIs.

> No source in this document is confirmed as integrated. Before use, verify the exact dataset, geographic coverage, update frequency, access method, terms/licence, and whether redistribution or derived use is permitted.

## 1. Source acceptance rules

A dataset may be marked `APPROVED_FOR_MVP` only after the team has:

1. Opened the official source page or obtained the dataset from its owner.
2. Confirmed that the dataset actually contains the required fields and geography.
3. Checked access conditions, licence/terms, attribution, and redistribution restrictions.
4. Recorded its date range, publication/update date, spatial resolution, and known limitations.
5. Tested a small sample and documented its quality.
6. Confirmed that it can be refreshed or clearly labelled as a one-time snapshot.

Do not treat a portal, organisation, map viewer, or research report as proof that a downloadable dataset or public API exists.

## 2. Candidate source register

| Candidate source / owner | Possible relevance | What must be verified before use | Current status |
|---|---|---|---|
| India Meteorological Department (IMD) | Official weather and climate observations, warnings, or summaries | Exact product, station/grid coverage, historical access, API/download method, usage terms, update cadence, spatial representativeness | `TO_VERIFY` |
| ISRO / Bhuvan | Satellite-derived and geospatial layers, land-use/land-cover context | Exact layer, date, resolution, download/service availability, licence and permitted derived use | `TO_VERIFY` |
| Census of India / Office of the Registrar General & Census Commissioner | Population and household context | Relevant census tables, geography compatibility, vintage, download terms, and whether newer official data exists | `TO_VERIFY` |
| Google Earth Engine data catalogue | Potential access to satellite and environmental datasets | Dataset-specific licence, access/account requirements, export limits, spatial/temporal suitability, and whether use is allowed for the project | `TO_VERIFY` |
| RMI India Foundation / heat-risk research publications | Methodological context and potential indicator definitions | Whether a public dataset is actually provided; distinguish research reports from machine-readable data; verify reuse terms | `TO_VERIFY` |
| Municipal / state open-data portals | Local infrastructure, public facilities, ward boundaries, or civic indicators | Exact portal and dataset, authority, completeness, freshness, geography, licence, and stable access | `TO_VERIFY` |
| OpenStreetMap | Candidate public facility / road / building context | Tag completeness, extraction method, ODbL obligations, attribution, date of extract, and local coverage | `TO_VERIFY` |

The table lists investigation leads, not guaranteed sources. No API endpoint is specified because none has been verified for this project.

## 3. Source verification register

Create one row per actual dataset. Keep evidence such as official page URL, download date, licence text, and a sample file in the project’s data audit folder.

| Field | Required value | Verified Entry: Open-Meteo Weather API |
|---|---|---|
| `source_id` | Stable internal identifier | `open_meteo_historical_weather` |
| `owner_name` | Publishing authority / data owner | `Open-Meteo` |
| `dataset_name` | Exact dataset title | `Open-Meteo Historical Weather API` |
| `official_url` | Official landing page or documented endpoint | `https://open-meteo.com` |
| `access_method` | Download / documented API / authorised request / manual file | Documented public REST API (`https://archive-api.open-meteo.com/v1/archive`) |
| `licence_terms` | Exact licence or terms URL and a short interpretation | Creative Commons Attribution 4.0 International (CC BY 4.0). Attribution to Open-Meteo required. Free non-commercial and educational use permitted within rate limits. |
| `geographic_coverage` | Country, state, city, ward, grid, station, or other unit | Global grid; interpolated to Meerut, Uttar Pradesh, India (28.996330, 77.706192) |
| `spatial_resolution` | Actual unit/resolution; do not infer | City-level model grid point (~11 km ERA5/reanalysis grid) |
| `temporal_coverage` | Start/end dates or snapshot date | 1940 to recent (typically 2–5 days lag for reanalysis) |
| `update_frequency` | Published frequency or `UNKNOWN` | Daily |
| `retrieved_at` | Date/time the team obtained it | `2026-11-24T18:24:42+05:30` |
| `file_format` | CSV, GeoJSON, GeoTIFF, API response, etc. | JSON (`application/json`) |
| `quality_notes` | Missingness, duplicates, known bias, and validation performed | Daily mean 2 m temperature (`temperature_2m_mean` in °C) and 2 m relative humidity (`relative_humidity_2m_mean` in %). Reanalysis/model-derived data, not a direct IMD ground-station measurement. |
| `approval_status` | `TO_VERIFY`, `TESTED`, `APPROVED_FOR_MVP`, `REJECTED` | `APPROVED_FOR_MVP` |
| `reviewed_by` | Team member | Lead Full-Stack Engineer |
| `evidence_location` | Path to saved evidence / sample | `backend/apps/datasets/services/open_meteo_import.py`; live test call verified |

## 4. Data acquisition fallback

Use the first feasible option that passes the source acceptance rules:

1. Official documented API, if its existence, access, terms, and response schema are verified.
2. Official downloadable file, if its licence permits the intended use.
3. Authorised data request or a documented manual export, if permitted.
4. A small, manually curated dataset for a controlled demonstration, with provenance and collection date.
5. Synthetic demonstration data only when clearly labelled `SYNTHETIC — NOT OBSERVED`; never present it as a real city measurement.

If a source cannot be verified, leave that indicator unavailable. Do not replace it with a fabricated endpoint or silently scrape a site contrary to its terms.

The current demo provider is explicitly illustrative and does not represent IMD or
other verified observations. Provider selection to `imd` is not a real integration:
the backend currently returns a safe `400` provider-not-implemented error until a
verified provider implementation is approved and tested.

## 5. Data storage and provenance

For every imported dataset, retain:

- Original file or immutable raw snapshot where terms permit.
- Source register entry and licence evidence.
- Retrieval timestamp and source publication date (if supplied).
- Import script/version and transformation notes.
- Validation report and row counts.
- A checksum where practical.
- Link from each derived observation to its source dataset and source record or spatial/time key.

Never overwrite raw data during cleaning. Store cleaned/derived data separately.

## 6. City enablement gate

A city is eligible for an MVP assessment only when:

- Its boundary or analysis units are available and legally usable, or the demo explicitly uses a documented alternative geography.
- Required indicator datasets cover those units sufficiently.
- The selected time periods are compatible or their mismatch is disclosed.
- Missingness and source quality are reported.
- The team can explain the meaning and limitations of the resulting score.

If these conditions are not met, keep the city in `NOT_READY` status and use a clearly labelled synthetic/demo dataset for UI testing only.

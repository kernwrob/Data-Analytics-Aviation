# Optional aircraft metadata and model extension

## Current pinned version — 12 November 2026

| Item | Value |
|---|---|
| File | OpenSky monthly **complete** dump `aircraft-database-complete-2025-08.csv` |
| Requested URL | `https://opensky-network.org/datasets/metadata/aircraft-database-complete-2025-08.csv` (`metadata_url` in `config.json`) |
| Resolved URL | `https://s3.opensky-network.org/data-samples/metadata/aircraft-database-complete-2025-08.csv` |
| Retrieved | 12 November 2026, 19:31:56 UTC, with `python src/collect.py metadata` (manifest entry written) |
| Server Last-Modified | Fri, 22 Aug 2025 15:06:02 GMT |
| Size | 107,956,517 bytes |
| SHA-256 | `41309cab2a092afc90304631532b3b9a7ce1e501ba003d9590c2ab84208daa3c` |
| Local path | `data/raw/aircraft_metadata/20261112T193156505671Z.csv` (not in Git; shared via the group folder, issue #14) |
| Records | 616,675 (every record has all 32 fields; 68 records contain line breaks inside quoted fields) |
| Invalid/blank keys | 27 |
| Duplicate valid keys | 0 |
| Conflicting keys (typecode / description) | 0 / 0 |
| Unique keys retained | 616,648 |

**Why we switched.** The OpenSky [README of the metadata folder](https://s3.opensky-network.org/data-samples/metadata/README.TXT) states that the daily snapshot `aircraftDatabase.csv` (our first file, Last-Modified 4 Nov 2024) and the monthly `aircraftDatabase-YYYY-MM.csv` files are **incomplete**, while the monthly `aircraft-database-complete-YYYY-MM.csv` dumps are complete. A listing of the bucket on 12.11.2026 shows 2025-08 as the newest complete dump (the previous complete dumps are 2025-02 and 2025-01). Our first file was also only available on one group member's Windows laptop.

**Format differences.** The complete dump quotes with `'` instead of `"`, uses camelCase names (`manufacturerName`) and calls the ICAO description `icaoAircraftClass`. `read_metadata_csv()` in `src/aircraft_metadata.py` takes the quote character from the first byte and normalizes the column names (lower case, `icaoaircraftclass` → `icaoaircrafttype`); both formats are covered by an offline test. The dump also has a `timestamp` column. The duplicate rule (most complete record, then record order) is unchanged; with 0 duplicates it has no effect on this file.

**Pinning.** `config.json` names the file and its SHA-256 (`metadata_file`, `metadata_sha256`). `prepare.py` stops with a clear message if the file is missing or its checksum differs, so a teammate cannot silently use another version. An empty `metadata_file` keeps the earlier behaviour: empty metadata table, every observation `Unbekannt`. The checksum lives in the config because a later `rsync` of `data/raw` from the collector replaces the local `manifest.jsonl` and with it the download entry; `src/export_data.py` therefore copies the pinned file by its config path and checksum.

**Coverage on the first main-collection data (12.11.2026).**

| Data | Observations matched | Aircraft matched | Matched observations with a typecode in the table |
|---|---:|---:|---:|
| Main analysis (2 snapshots with the current box) | 108 / 122 = 88.5 % | 68 / 77 = 88.3 % | 99.1 % |
| Exploratory, all 13 snapshots incl. the old box | 571 / 657 = 86.9 % | 200 / 226 = 88.5 % | 98.9 % |

For comparison: the first file matched 67.3 % of the pilot observations (October). The numbers are different samples and only indicate the order of magnitude.

## Aircraft category by typecode (from 12 November 2026)

Schema frozen on 12.11.2026 before inspecting main-collection results (`DECISIONS.md`). Categories: Kurzstrecke (narrowbody jets), Regionaljet, Langstrecke (widebody jets), Turboprop (multi-engine turboprops and PC-12), Business-Jet, Sonstige (piston, helicopters, gliders, military and special types), Unbekannt.

1. Typecode found in `data/reference/typecode_category.csv` (versioned; columns `typecode,category,example_model,source_note`) → its category, `category_source = typecode`.
2. Otherwise the ICAO description: `L?T` → Turboprop; `L?P`, `H??`, `G??` → Sonstige (`category_source = icao_description`). Jets without a known typecode are **not** guessed.
3. Otherwise, without a metadata match, or when duplicate records disagree on typecode or description → **Unbekannt** (`category_source = none`). Unbekannt is never merged with Sonstige.

The table contains every example of the schema plus every typecode seen in the first 13 main-collection snapshots (140 typecodes). Uncertain types carry a short reason in `source_note` (e.g. A306 widebody freighter → Langstrecke, CRJ2 also covers the Challenger 850, PC-6 Turbo Porter → Sonstige). The typecode wins over the description where both exist; one observed example is G200 (Gulfstream business jet) whose description in the dump is `L1P` (single piston).

In SQLite, `typecode_categories` holds the table and the view `observations_enriched` derives `aircraft_category` and `category_source` by SQL join plus the same fallback rules. `prepare.py` stops if the SQL result differs from the Python result stored in `aircraft_metadata` for any observation. The view also shows `adsb_category_label` (ADS-B emitter category, e.g. 6 = Heavy), as a **cross-check only**: on 12.11. it was 0 («No information») for most observations; where it was set, Heavy matched Langstrecke 7/7 and Large matched Kurzstrecke 7/7. Audits: `category_audit` (observations and aircraft per category and source), `metadata_integration_audit.typecode_mapped_fraction`, and `outputs/tables/unmapped_typecodes.csv` (typecodes not in the table, with counts). New typecodes may be added to the table during collection, without changing categories and never based on speed results.

---

## History (first version, 1 October 2026 – 12 November 2026)

The sections below describe the first pinned file and the earlier description-based categories (`Jet landplane` …, `unknown/other`). They are kept unchanged as history and no longer describe the current code.

## Reference and provenance

Downloaded 1 October 2026 at 13:58:42 UTC (15:58:42 Zurich). Requested [official CSV](https://opensky-network.org/datasets/metadata/aircraftDatabase.csv), which redirected to `https://s3.opensky-network.org/data-samples/metadata/aircraftDatabase.csv`. The original is `data/raw/aircraft_metadata/20261001T135842635480Z.csv`; its source URL, resolved URL, UTC retrieval, 94,509,542-byte size, server Last-Modified and SHA-256 are recorded in `data/raw/manifest.jsonl`.

The server Last-Modified is **4 November 2024**, not October 2026. [OpenSky documents](https://opensky-network.org/data/aircraft) that this mixed-source reference is out of date and offered without guarantees. Retrieval date is not the validity date of individual records. Identifier reallocation, missing registrations and stale aircraft attributes remain possible. Keep enrichment descriptive and optional.

Available fields are: `icao24`, `registration`, `manufacturericao`, `manufacturername`, `model`, `typecode`, `serialnumber`, `linenumber`, `icaoaircrafttype`, `operator`, `operatorcallsign`, `operatoricao`, `operatoriata`, `owner`, `testreg`, `registered`, `reguntil`, `status`, `built`, `firstflightdate`, `seatconfiguration`, `engines`, `modes`, `adsb`, `acars`, `notes`, `categoryDescription`. Many are sparse; registry dates do not establish that a tracking report represents a flight by that operator.

We retain manufacturer name, model, typecode and ICAO description in a separate SQLite `aircraft_metadata` table. Owner, registration, operator and serial fields are not added to analysis tables. See `SHARING.md` before sharing the original CSV.

## Keys, duplicates and preservation

Normalize both sources' ICAO24 to stripped lowercase strings. A metadata key must be six hexadecimal characters. The observed download has:

| Check | Count |
|---|---:|
| Raw metadata records | 520,000 |
| Invalid/blank keys excluded from metadata | 23 |
| Duplicate valid keys | 8 |
| Extra duplicate records removed | 8 |
| Keys with conflicting nonblank descriptive fields | 3 |
| Unique metadata keys retained | 519,969 |

For each duplicate key, choose the record with the most populated fields among the four retained attributes. Break a tie by the original CSV record order. Do not synthesize a new aircraft by mixing attributes from different rows. The selection is a reproducibility rule, not evidence of truth or recency. All candidates, completeness counts, selected flags and conflict flags are saved in `data/processed/metadata_duplicate_candidates.csv`. `metadata_source_record` is the one-based CSV data-record number, not necessarily a physical line number.

Conflicting ICAO description codes force `unknown/other` category even if one descriptive record is selected. In this downloaded file the three conflicting keys differ in model labels; the audit retains the uncertainty. A unique index enforces one metadata row per ICAO24.

The many-to-one **left join** attaches descriptive fields while retaining every observation. `observations` remains the original analysis table; the SQL view `observations_enriched` joins the separate metadata table. Before/after row counts and observation keys are verified. All original observation columns were compared to a preserved pre-enrichment database and were identical across all 4,115 rows.

The first dated metadata file is pinned, as with airports. Do not silently replace it during modeling. If metadata is absent, preparation creates an empty reference table and the same enriched view with unknown categories; original EDA/models still work, and the optional category comparison is skipped. An existing malformed metadata file causes an explicit error rather than silently claiming enrichment worked.

## Actual coverage on the stopped pilot

| Unit | Matched / total | Coverage |
|---|---:|---:|
| Retained observations | 2,768 / 4,115 | 67.27% |
| Distinct aircraft, counted directly | 659 / 968 | 68.08% |

The 1,347 unmatched observations are retained. A matching key can still have missing type/model fields: coverage of populated categories differs from key-match coverage. `metadata_integration_audit.csv` gives exact fractions. `aircraft_types.csv` lists type/model combinations; `aircraft_type_counts.csv` groups typecodes without fragmenting model-name variants; `aircraft_categories.csv` reports broad categories. Notebook 01 adds a SQL descriptive table and audit display.

## Conservative broad categories

Use a fixed finite mapping of the reference's `icaoaircrafttype` description codes, based on [ICAO Doc 8643](https://www.icao.int/operational-safety/Designators-and-indicators) and its [type-description report](https://cfapps.icao.int/doc8643/reports/Doc8643-Ed39/Part2-By%20Type%20Designator%28Decode%29.pdf). This is different from `typecode` (e.g. A320), and from the mostly absent `categoryDescription` emitter/weight field.

| Input codes | Category |
|---|---|
| L1J, L2J, L3J, L4J | Jet landplane |
| L1T, L2T, L4T | Turboprop landplane |
| L1P, L2P, L4P | Piston landplane |
| H1T, H2T, H3T, H1P, H2P | Helicopter |
| Missing, unmapped or conflicting description | unknown/other |

This deliberately small mapping leaves unusual airframes and unsupported descriptions unknown. It is not a verified operational category, flight phase, passenger-service label or size class. The current category table contains 2,181 jet, 187 turboprop, 115 piston, 185 helicopter and 1,447 unknown/other observations. Do not drop the unknown group to improve model metrics.

## Aircraft category in the models (since 17.11.2026, CC-9)

The aircraft category is model **C** in the unified model chain of `src/model_comparison.py` (0 mean, A altitude knot, B + zone/airport/distance/flight phase, C + category, D + wind, RF comparison; see `DECISIONS.md`, «Model specification for the research question»). All models use the identical training and test rows of the same splits (later days; held-out aircraft). Missing metadata stays `Unbekannt` as its own level, never dropped; the one-hot encoding is learned on training rows only, and a category not seen in training is encoded like the reference category. `src/inference.py` additionally tests aircraft category × altitude with cluster-robust standard errors (categories with fewer than 20 aircraft are left out and listed). Nothing has run on main-collection data yet (7-date guard). Static metadata availability may differ by aircraft mix, and a held-out-aircraft split answers a different question from later-day performance; report both rather than claiming that category gains prove a causal effect.

*History: until 17.11.2026 notebook 02 compared A (geometric altitude), B (distance, latitude/longitude, near indicator, altitude × near) and C (B + broad category) on near/far only.*

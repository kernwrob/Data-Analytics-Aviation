# Optional aircraft metadata and model extension

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

## Optional A/B/C evaluation

Notebook 02 retains its baseline, original spatial regression, random forest and original diagnostics. Its appended optional cells compare three fixed linear models using `src/model_comparison.py`:

- A: geometric altitude only;
- B: existing altitude, airport distance, latitude/longitude, near indicator and altitude×near interaction;
- C: B plus broad aircraft category.

All three reuse identical observation keys in the existing temporal train/test frames and, separately, the existing aircraft-held-out frames. No complete-case metadata subset or new split is introduced. C learns numeric imputation/scaling and one-hot encoding using training data only; unseen test categories are ignored safely, and missing metadata remains unknown/other. Every model reports the same test sample sizes, MAE/RMSE in m/s and R-squared by near/far/overall.

An offline test verifies unseen-category handling; the seven-date guard also applies to this extension. The comparison has **not** run on the one-date pilot. Run it once sufficient multi-day data are available. Static metadata availability may differ by aircraft mix, and a held-out-aircraft split answers a different question from later-day performance; report both rather than claiming that category gains prove a causal effect.

# Decision log

Confirmed: aircraft movements; three students; six or more weeks.

| Date | Decision | Reason | Owner | Evidence / lecturer response |
|---|---|---|---|---|
| Pending | Final research question | Airport/feature-set/generalization comparisons | All | Pending |
| 2026-11-12 | Collection: old MacBook at Matteo, 24/7, every 5 min, 12.11. 19:30 → 26.11. 19:30 (Europe/Zurich), enlarged bounding box | Reliable repeated group-owned collection; full coverage around all three airports | Matteo (collector and daily monitoring) | See «Main collection» and «Bounding box enlarged» below, issue #47 |
| 2026-11-12 | Aircraft category by typecode (7 fixed categories incl. Unbekannt), frozen before inspecting main-collection results; metadata pinned to the 2025-08 complete dump | Lecturer wants the category central; old mapping was too coarse | Matteo (proposal), to be acknowledged by all | See «Aircraft metadata version and aircraft category» below, issue #12 |
| 2026-11-17 | Cleaning order, plausibility thresholds, buffer around 10 neighbouring airports (15 km, up to 3,000 m above the airport, exclude), flight phase ±2.5 m/s, altitude geo else baro | Review 15.11. (H2, H4, M3, NEU-3); CC-10 | Matteo (proposal), **proposed, to be acknowledged by the group** | See «Cleaning stages, plausibility thresholds, …» below, issue #13 |
| 2026-11-17 | Model specification: altitude knot at 3,000 m, flight phase as control, OLS interaction test with cluster-robust SE, models 0/A–D/RF on all three zones, leakage demo | Slides 9 and 11; review 15.11. (K3, H1, H3, M5); CC-8, CC-9 | Matteo (proposal), **proposed, to be acknowledged by the group** | See «Model specification for the research question» below, issues #18, #19 |
| Pending | 30/60 km cutoffs and freshness rule | Freeze before inspecting final results | All | Pilot review |
| Pending | Analysis date rule for exploratory correlation | Avoid selecting a date for a desired p-value | Student C | Pending |
| Pending | SQLite plus optional PostgreSQL | Resolve conflicting minimum and bonus wording | All | Pending |
| Pending | Names, language, deadline | Final deliverables | All | Pending |

Record scope changes and why. Do not silently overwrite decisions after seeing test results.

## Technical progress — 1 October 2026

Local Python setup and anonymous source retrieval were verified. A bounded one-day collection pilot was registered for this machine, repeating every five minutes and expiring on 2 October; see `PILOT.md` and `outputs/pilot/schedule.json`. Original 30/60 km cutoffs, 60-second freshness and the spatial extent were used unchanged for the pilot. They are not yet frozen for final analysis. `requirements-lock.txt` records the tested environment. Group ownership, final collection dates and all scientific/lecturer decisions in the table remain pending.

## Follow-up work — 1 October 2026

| Decision/action | Reason and evidence | Status |
|---|---|---|
| End the technical pilot after sufficient approximately two-hour checks | Explicit user request supersedes the original one-day recommendation; 32 aligned scheduled responses, no scheduled gaps, integrity/join checks pass | Specific pilot disabled/stopped at 15:56:57 Zurich; originals/config retained; no new files after subsequent former ticks |
| Preserve normal laptop sleep/power behavior | User travels; downtime is missing observations | Main Start/Pause/Resume utility prepared; no main task registered, dates/duration await the group |
| Add optional pinned OpenSky aircraft metadata | Explain aircraft mix while preserving existing airport/speed analysis | 520,000 source records audited; 67.27% observation / 68.08% aircraft key coverage; left join preserves 4,115 rows |
| Use deterministic duplicate selection and unknown/other | No trustworthy recency field for choosing conflicting records; avoid unsupported categories | Most complete retained attributes, original record order tie-break; candidates/conflicts logged; fixed conservative description mapping documented |
| Prepare optional A/B/C category comparison | Isolate additional category information using the same observations and splits | Defined and tested for unseen categories; not run on pilot-only data |
| Private GitHub for code; restricted university folder for dated data | Separate code history from growing datasets and environments | Local Git/index prepared; author, private remote, collaborator usernames and folder location still needed; nothing uploaded |

Primary question, 30/60 km cutoffs, freshness, analysis-date rule, PostgreSQL choice and final deliverable decisions remain pending. Public code publication is a later authorized step. See `COLLABORATION.md`, `COLLECTION.md`, `METADATA.md` and `SHARING.md` for concrete workflows and conditions.

## Handover recheck — 1 October 2026

The pilot task remains disabled (last run 15:55:40 Zurich, result 0), and no main collection task is registered. The prepared repository still has no commit author or remote; account details and the restricted university folder are needed to finish access. README setup now distinguishes the collector from teammates using exports. Dataset switching must preserve the previous folder and copy a complete replacement into an analysis clone, because merging raw folders would change the agreed sample. No additional live collection was started.

## Airport-context review — 13 October 2026

The user identified omitted neighbouring airports as a possible problem. A read-only pilot audit confirms that 94 current far reports are within 30 km of Malpensa and 49 within 30 km of Bergamo; Frankfurt's closest pilot report is 225.7 km away. Proximity is not evidence of a verified flight phase or airport effect. See `outputs/pilot/airport_proximity_review.md` for airport-set sensitivity counts.

Proposed, not adopted: make the main question the incremental value of spatial context and optional category beyond altitude, with a stronger altitude-only baseline and the existing separate later-day/held-out-aircraft evaluations. Retain named-airport distances and add regional airport context using a documented inclusion rule and boundary buffer. Group/lecturer review is needed before changing classifications; existing config and database remain intact.

The user supplied the course evaluation text, preserved in `COURSE_EVALUATION.md`. The concept has a ten-minute slot and eight evaluation criteria, with formal topic approval at that presentation. Its grade weighting is not specified in the excerpt; do not assume it is ungraded.

## Collector fix — 22 October 2026

| Decision/action | Reason and evidence | Status |
|---|---|---|
| Request `extended=1` for every snapshot and log `category_present` | The lecturer wants aircraft category central to the analysis; the ADS-B emitter category is only returned with `extended=1`. One manual snapshot: 167/167 vectors with 18 fields, 162 with category 0 (no information) | Proposed by Matteo in PR `fix/sammler-extended`; must be merged before main collection starts |
| Use the ADS-B category only as a cross-check | Category 0 dominates the first live check; the typecode-based category (planned) remains the analysis variable | Pending group review with main-collection data |
| Keep `category` as a fixed column in `observations` | Pilot-only (17-field) data previously produced no `category` column at all; it is now always present and empty for old vectors | Covered by offline tests |

## Main collection — 12 November 2026

| Decision/action | Reason and evidence | Status |
|---|---|---|
| Collect on the old MacBook Pro (A1502, macOS Monterey 12.7.6, user `Sammler`, automatic login, no system sleep on power) with `scripts/collection_mac.sh` | One stable, always-on device at home; a travelling laptop would cause gaps | Set up 11–12 Nov (see `SETUP_MACBOOK.md`); the Windows collector stays off |
| 24/7, one snapshot every 5 minutes, anonymous API, `extended=1` | Matches the plan announced to the lecturers. 288 requests per day fit the 400 anonymous credits per day; a request costs 1 credit while the box is ≤ 25 square degrees ([OpenSky REST API](https://openskynetwork.github.io/opensky-api/rest.html)) | Running |
| Duration 14 days: 12.11.2026 19:30 → 26.11.2026 19:30 Europe/Zurich (18:30 → 18:30 UTC) | Enough for the minimum criteria and for finishing the analysis by end of November. Extending to about 10 December was considered and rejected (issue #47) | Running, ends automatically |
| Daily monitoring by Matteo (`collection_mac.sh status`, also via SSH from his work Mac); gaps are noted with their reason | Collection gaps must be explained in the final report | Ongoing |
| First check 12.11. 20:08 Europe/Zurich: 9 successful snapshots (1 setup test + 8 scheduled from 19:30), 0 failures, 84 aircraft in the 20:05 snapshot | — | OK |

## Bounding box enlarged — 12 November 2026

**Problem.** The original box (45.7–48.0 °N, 5.8–10.6 °E) was too tight around two of the three airports. Distance from the airport to the nearest edge: Geneva 24 km (west) and 60 km (south), Basel 46 km (north), Zurich 60 km (north). Share of each zone inside the box: Geneva near zone (0–30 km) 95 %, Geneva middle ring (30–60 km) 68 %, Basel middle ring 91 %, Zurich 100 %. Traffic west of Geneva over France (approaches and departures towards the south-west) was therefore missing, which made the airport comparison asymmetric.

**Decision.** New box **45.6–48.2 °N, 5.2–10.6 °E** (`config.json`), 14.04 square degrees. Minimum distance to an edge is now 82 km for Zurich (north), 70 km for Geneva (west) and 68 km for Basel (north), so the near zone and the 30–60 km ring are fully inside for all three airports. The box stays below 25 square degrees, so each request still costs 1 credit and the daily budget is unchanged.

**How it was applied.** On the collector: `pause` → `git pull` → `resume`. The deadline (26.11. 19:30) is unchanged. The exact switch time is the first manifest entry with `"lomin": 5.2` in `params`; every snapshot stores its box in the manifest, so the change is fully traceable.

**Analysis rule.** Snapshots taken with the old box (12.11. from 19:30 until the switch, roughly 1–2 hours) stay in `data/raw` but are excluded from the main analysis, so that every analysed snapshot covers the same area. The exclusion is based on the `params` in the manifest and is counted in the integration audit (issue: «Kartenausschnitt vergrössern»). The weather grid in `src/weather.py` follows the box in `config.json` automatically (more grid points). Pilot data from 1.10. and 22.10. used the old box and remain exploratory only.

**Status.** Decided by Matteo on 12.11.2026 before any main-collection results were inspected; to be acknowledged by the group.

**Implementation (12.11.2026, CC-7).** `prepare.py` reads `data/raw/manifest.jsonl` and keeps only snapshot files whose `params` bbox equals the `bbox` in `config.json` (`"require_current_bbox": true`). Files without a successful manifest entry are excluded as well, because their area is unknown. Counts are in `snapshot_bbox_audit` and in the integration audit (`raw_all_snapshots` → `current_bbox`). First run: 13 snapshots, 11 with the old box (777 state vectors) excluded, 2 kept (203 state vectors), 0 without manifest entry. Setting the flag to `false` loads every snapshot for exploratory work only.

## Aircraft metadata version and aircraft category — 12 November 2026

| Decision/action | Reason and evidence | Status |
|---|---|---|
| Pin the OpenSky dump `aircraft-database-complete-2025-08.csv` (SHA-256 in `config.json`) instead of `aircraftDatabase.csv` of 4 Nov 2024 | OpenSky's README calls the daily dump incomplete and the monthly «complete» dumps complete; 2025-08 is the newest complete one. Match rate on the first main data 88.5 % of observations (pilot with the old file: 67.3 %). Details in `METADATA.md` | Done by Matteo (CC-7, #12); file goes to Kevin and Robin via the shared folder (#14) |
| **Aircraft category by typecode** with the fixed categories Kurzstrecke, Regionaljet, Langstrecke, Turboprop, Business-Jet, Sonstige, Unbekannt. Order: typecode table `data/reference/typecode_category.csv` → ICAO description (`L?T` → Turboprop; `L?P`, `H??`, `G??` → Sonstige; jets not guessed) → Unbekannt. Conflicting duplicates (typecode or description) → Unbekannt. Unbekannt is never merged with Sonstige | The description-only mapping put A320, B777 and Citation into one class («Jet landplane»); the lecturer wants the aircraft category to be central. The ADS-B emitter category is mostly 0 and stays a cross-check | **Frozen before inspecting main-collection results** (only typecode frequencies were looked at, no speeds). Status: to be acknowledged by the group |
| Typecodes may be added to the table while data come in (from `outputs/tables/unmapped_typecodes.csv`); the categories themselves and their definitions do not change | Keeps coverage high as new aircraft appear, without tuning categories to results | Rule for the group |
| Replace the label `unknown/other` by `Unbekannt` everywhere in code and notebooks | One consistent label for «no or insufficient metadata» | Done |

## Cleaning stages, plausibility thresholds, neighbour-airport buffer and flight phase — 17 November 2026 (CC-10, #13)

**Status: Proposed 17.11.2026 by Matteo, to be acknowledged by the group.** Set before any main-collection results were inspected (only 2 local snapshots with the final box, used to test the code). All values live in `config.json`; changing one is a config change that must be logged here.

**Order of the cleaning stages** (one row each in `integration_audit`, with `rows` after the stage and `lost` = rows it removed; the stages add up from `raw` to the final table):
`raw` → `airborne` (`on_ground` false) → `required_fields_present` → `valid_and_fresh` → `plausible_altitude` → `plausible_speed` → `plausible_vertical_rate` → `unique_aircraft_position_timestamp` → `airport_join` → `neighbour_airport_buffer`.
The ground filter now runs before the required-field check. Before, ground reports without `geo_altitude` were counted as «required field missing» (review 15.11., NEU-3: 74 of 75 such rows on 12.11. were on the ground). A new table `missing_fields_audit` counts missing values per column for all raw rows and for airborne rows only, before any filter.

| Item | Proposed value | Reason |
|---|---|---|
| Altitude | `altitude_m` = `geo_altitude`, else `baro_altitude`; `altitude_source` = geo/baro. `altitude_m` is required, `geo_altitude` no longer | Keeps airborne reports that only lack the GNSS height. The analysis, the models and the wind join use `altitude_m`. Barometric altitude is a pressure altitude and can deviate by a few hundred metres; the share is visible in notebook 01 |
| Altitude range | −300 to 15,500 m (inclusive) | Below −300 m only errors (lowest airport in the box ≈ 200 m); 15,500 m ≈ 51,000 ft, the ceiling of the highest-flying business jets |
| Ground speed range | 0 to 350 m/s (1,260 km/h) | Subsonic airliners plus a strong jet-stream tailwind stay well below; higher values are position/velocity errors |
| Vertical rate | \|vertical_rate\| ≤ 40 m/s (≈ 7,900 ft/min); missing rate is **kept** | Airliners climb/descend at up to ~20 m/s, emergency descents ~30 m/s; larger values are sensor glitches. A missing rate is not an error |
| Flight phase | `climb` > +2.5 m/s, `descent` < −2.5 m/s, otherwise `level` (±2.5 inclusive); missing rate → `unknown` | 2.5 m/s ≈ 500 ft/min: above the noise of level flight, below normal climb/descent rates |
| Neighbouring airports | LIMC, LIME, EDNY, LSZB, LSZA, LSGS, LFLB, LFLP, **LSZR**, **EDJA** (coordinates from the pinned OurAirports file, like the main airports) | Commercial airports inside the box (review 15.11., H4). EDSB is outside the box (48.78 °N). LSZR (St. Gallen-Altenrhein) and EDJA (Memmingen) are added because OurAirports lists scheduled service and both lie inside the box; **the group should confirm these two** |
| Buffer radius | 15 km | About the final approach from the final approach fix (on a 3° glide path an aircraft 15 km out is ~800 m above the runway) plus the initial climb. Half of the 30 km near zone, because the neighbours (except LIMC/LIME) have far less traffic. Checked in the sensitivity analysis (CC-12) |
| Buffer height | Only rows at most 3,000 m above the neighbouring airport (`max_height_above_airport_m`) | See «Buffer height» below; overflights at cruise level are not airport traffic |
| Buffer mode | `exclude` (default) or `own_zone` (rows stay with `zone = "neighbour"`) | `exclude` keeps «far = en-route» clean; `own_zone` allows the CC-12 comparison without rebuilding |
| Precedence | Rows within 30 km of ZRH/GVA/BSL (near zone) are **never** buffered | Annecy (LFLP) is only 34 km from Geneva, so its buffer reaches 19 km from GVA. These rows are in airport proximity anyway; the frozen 30/60 km zones and the nearest-main-airport assignment stay unchanged |
| Airport short name | `airport` = IATA code from the pinned OurAirports file (ZRH, GVA, BSL), next to `airport_ident` | Readable labels in tables and slides without a hard-coded mapping |

**Buffer height (proposed 17.11.2026, CC-8/CC-9 step 0).** A row is buffered only if it is inside the radius **and** at most `max_height_above_airport_m` = **3,000 m** above the neighbouring airport (`altitude_m` minus `elevation_ft` × 0.3048 from the pinned OurAirports file; a missing elevation stops `prepare.py`). Reason: the buffer is meant for approaches and departures of the neighbouring airport. With the purely horizontal buffer, cruise overflights were removed too (local test data: 9 rows removed, 6 of them more than 3,000 m above the airport, e.g. 11,400 m above LSZA). With the limit, 3 rows are removed and the 6 overflights stay. 3,000 m is the same knot as on slide 9 (below it, speed is limited and approach/departure profiles dominate). `altitude_m` is a GNSS or barometric height, the elevation is above mean sea level; differences of some tens of metres are ignored. Notebook 01 counts the rows kept only because of the height limit. **Status: Proposed 17.11.2026, to be acknowledged by the group.** LSZR and EDJA in the list still need the group's confirmation.

## Model specification for the research question — 17 November 2026 (CC-8, CC-9, #18, #19)

**Status: Proposed 17.11.2026 by Matteo, to be acknowledged by the group.** Announced on slides 9 and 11 of the concept presentation. Specified and tested on synthetic data only; fixed **before** any model was fitted on main-collection data (the 7-date guard stays; locally there is one observed date). All values in `config.json`.

| Item | Proposed specification | Reason |
|---|---|---|
| Altitude form | Piecewise linear with one knot at `altitude_knot_m` = **3,000 m**: `alt_low_km` = min(altitude, 3,000)/1,000, `alt_high_km` = max(altitude − 3,000, 0)/1,000 (`src/features.py`) | Ground speed rises steeply in the climb and flattens towards cruise; a straight line is misspecified (review H1). 3,000 m ≈ FL100, below which the 250 kt limit applies (slide 9). Coefficients read directly as km/h per 1,000 m below/above the knot |
| Second knot | `altitude_knot2_m` = `null` (off). Decided **only** from the shape of the residual profile of the main model (`ols_residual_profile.csv`, arc above ~10 km), never from p-values or test scores, and logged here before it is used | Aircraft cruise at a near-constant Mach number, so a plateau near cruise level is physically plausible, but cannot be judged before the 14 days exist |
| Flight phase | `C(flight_phase)` (climb/level/descent/unknown, CC-10) as a **control** in the OLS models and in B–D | Near the airports climbing and descending aircraft at the same altitude fly at different speeds (slide 9) |
| Hypothesis 1 test (CC-8) | OLS on all observations (near/middle/far): `speed_kmh ~ (alt_low_km + alt_high_km) * C(zone, Treatment('far')) + C(airport) + C(flight_phase)`, standard errors clustered by `icao24`, t with (aircraft − 1) df. Hypothesis 1 = `alt_*_km:…[T.near]` > 0; joint Wald test near vs far (2 coefficients) and all zones (4). Slopes per zone with 95 % CI from coefficient contrasts. Variants: (a) near zone only, airport × altitude (reference ZRH); (b) aircraft category × altitude with the main controls (reference Kurzstrecke). Levels with fewer than `inference.min_aircraft_per_level` = 20 aircraft are left out and listed (`src/inference.py`) | Answers part 1 of the question with a p-value (review K3). Positions of one aircraft are not independent, so ordinary SE would be far too small. 20 aircraft per level keeps the cluster-robust intervals usable |
| Prediction models (CC-9) | Target `speed_kmh`. 0 mean; A knot; B = A + zone dummies, zone × knot terms, airport, `distance_km`, flight phase; C = B + aircraft category; D = C + tail/crosswind; RF on B's inputs + latitude/longitude (comparison). One-hot with `drop="first"` (alphabetical reference), all preprocessing fitted on training rows only. Defined only in `src/model_comparison.py`; notebook 02 imports them | One definition instead of two (review H1/M5). Latitude/longitude as linear terms are meaningless (a speed trend from west to east), so only the forest gets them |
| Zones in the models | **All three zones** (near, middle, far); RMSE per zone. Before: near and far only | Same data as the OLS model; more observations; the middle ring is part of the transition the question is about |
| Splits | Later days (first 70 % of dates train; main result, hypothesis 2), other aircraft (30 % of aircraft held out, `random_state=42`), and a random row split **only as a leakage demonstration** («Demonstration, nicht Ergebnis»), never reported as performance | Review H3. On synthetic data the random split makes the random forest look 25–30 % better than for unseen aircraft; linear models barely profit |
| Uncertainty of RMSE | 95 % bootstrap interval resampling whole test aircraft (200 samples) | Repeated positions of one aircraft are not independent |
| R² | Not compared between zones (only RMSE/MAE in km/h) | The spread of speeds differs by zone, so the same error gives a different R² |
| Software | `statsmodels` 0.14.6 (+ `patsy` 1.0.3) in `requirements.txt` and the lockfile | 0.15 adds another dependency (`formulaic`); 0.14.6 runs on Python 3.10–3.13 |


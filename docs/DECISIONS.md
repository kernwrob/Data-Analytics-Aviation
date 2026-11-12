# Decision log

Confirmed: aircraft movements; three students; six or more weeks.

| Date | Decision | Reason | Owner | Evidence / lecturer response |
|---|---|---|---|---|
| Pending | Final research question | Airport/feature-set/generalization comparisons | All | Pending |
| 2026-11-12 | Collection: old MacBook at Matteo, 24/7, every 5 min, 12.11. 19:30 → 26.11. 19:30 (Europe/Zurich), enlarged bounding box | Reliable repeated group-owned collection; full coverage around all three airports | Matteo (collector and daily monitoring) | See «Main collection» and «Bounding box enlarged» below, issue #47 |
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

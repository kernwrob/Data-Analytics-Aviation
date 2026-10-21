# Local setup and collection pilot — 1 October 2026

## Completed technical pilot and stop verification

The follow-up request shortened this to an approximately two-hour **technical** pilot. It passed and was disabled/stopped at **15:56:57 Zurich on 1 October 2026**. The original task/configuration and all data are preserved. The two-hour point had already passed, so no future stop task was necessary. Checks after multiple former five-minute trigger times still found 35 snapshot files; `AircraftProject-CollectionPilot` remained disabled. `AircraftProject-MainCollection` has not been registered. No aircraft collector remains active.

| Measured item | Result |
|---|---|
| First successful retrieval | 1 October 13:07:49 Zurich / 11:07:49 UTC |
| Latest successful retrieval | 1 October 15:55:41 Zurich / 13:55:41 UTC |
| Successful snapshot responses | 35: three manual startup/task checks plus 32 aligned scheduled responses |
| Scheduled slots from 13:20:39 until stop | 32; all had successful aligned responses; no failed, empty, deferred or no-collection slots |
| Snapshot failures across all attempts | 1 initial sandbox connection failure, before the scheduled window |
| Airport-source failures | 1 initial sandbox connection failure; later download succeeded |
| Successful empty snapshots | 0 |
| Scheduled request interval min / median / max | 299.00 / 300.01 / 301.15 seconds |
| Overall successful-start interval range | 141.62–339.08 seconds, including irregular manual startup checks |
| Raw / required-fields / retained observations | 5,664 / 4,253 / 4,115 |
| Distinct retained aircraft, counted directly | 968 |
| Near observations / distinct aircraft | 778 / 466 |
| Middle observations / distinct aircraft | 1,139 / 580 |
| Far observations / distinct aircraft | 2,198 / 847 |

The task event-history channel was disabled. The 32 scheduled responses are inferred by aligning request-start timestamps to the saved five-minute trigger within 90 seconds, not by inventing task-history events. The last recorded task result was 0. No scheduled ticks are missing in this observed pilot window. The 339-second startup interval occurs before regular scheduled collection, not during it.

`outputs/pilot/scheduled_coverage.csv` distinguishes successful, failed, deferred and no-collection slots; successful empties have their own flag. `sampling_intervals.csv`, `coverage_summary.json` and `coverage.png` show intervals and coverage. An offline fixture verifies that failure, successful empty response and a slot with no collection remain separate. Missing periods are missing observations, never inferred zero air traffic.

Both airport and optional metadata joins preserve all 4,115 rows and unique keys. All raw checksums and SQLite integrity pass. Details of metadata matching and the optional comparison are in `METADATA.md`. Main laptop controls are in `COLLECTION.md`; group access/export instructions are in `COLLABORATION.md`. Main dates/duration and scientific choices remain pending.

Follow-up verification passes 17 focused offline checks. The metadata-free SQLite fixture exposed that SQLite transaction contexts do not automatically close file handles; explicit connection closing now fixes Windows cleanup in the builder and notebook reads. Syntax/notebook validation and the pilot model guard pass. The main schedule utility was syntax/object/status checked, but no main task was registered because dates/duration have not been chosen. A local dated export was generated and rebuilt successfully; no cloud transfer or repository publication occurred.

The earlier setup notes below are retained as history; their proposed one-day endpoint and preliminary counts have been superseded by this completed technical pilot.

The project plan, README and decision log were read before changes. The project remains a three-student study over six or more weeks. The research question, cutoffs, ownership, lecturer approval, deadline and language still need group decisions; technical setup does not approve them.

## What has actually been checked

- Python 3.13.15 works through `python`; the installed `py` launcher reports no installed Python. A project-local `.venv` was created and the ten requested packages plus dependencies were installed. `pip check` passes. `requirements-lock.txt` records exact installed versions for Windows/Python 3.13 reproduction.
- Anonymous OpenSky and OurAirports downloads both returned HTTP 200. No OAuth credentials were present. OAuth has not been tested.
- The first two OpenSky downloads were retrieved at 13:07:49 and 13:12:39 Europe/Zurich (11:07:49 and 11:12:39 UTC). These are manual startup checks about five minutes apart, not a completed one-day pilot.
- Across those two snapshots: 291 raw position reports; 220 with required fields; 219 after freshness/validity checks; 219 after deduplication and integration. All 71 reports missing required fields lacked geometric altitude. One additional report was excluded by the validity/freshness rule. No join rows were gained, lost or unmatched.
- Near: 41 observations / 39 distinct aircraft; middle: 56 / 49; far: 122 / 94. Aircraft can appear in multiple groups; do not add group aircraft counts to obtain a total. These counts meet the plan's example 30-aircraft near/far scope criterion but do not establish statistical power or adequate shared altitude support.
- Raw-file SHA-256 checks pass. The three selected airport keys are unique and have coordinates. SQLite integrity, unique observation keys, cleaning invariants and join completeness pass.
- All three notebooks pass structural validation and code syntax checks. The modeling setup/coverage cell was executed and correctly refused evaluation with fewer than seven observed UTC dates. No models were fitted. Complete notebook execution, final EDA, statistics and clusters are still pending.
- Seven offline collector tests pass, including empty responses, malformed HTTP-200 payloads, network errors, OAuth failure, HTTP 429, and retry deadlines across scheduled invocations. Test fixtures use temporary directories and are never project evidence.

The initial sandbox blocked one airport request and one snapshot request before either reached the service. These remain in the manifest as connection failures. The network-enabled attempts succeeded. Include those startup failures in the acquisition audit, but distinguish the local access restriction from an OpenSky service outage.

At the 13:23 local report build, including the unattended verification and first regular scheduled run, **four successful snapshots contained 608 raw reports, 450 retained observations and 193 distinct retained aircraft**. Near/middle/far retained observations were 78/104/268; distinct aircraft were 63/76/154. The join still gained/lost zero rows with zero unmatched records, and all five raw files (four snapshots plus airport CSV) matched their checksums. These are dated pilot counts; ongoing collection will change the generated report after it is rebuilt.

## Historical bounded one-day pilot setup

`scripts/start_pilot.ps1` registered `AircraftProject-CollectionPilot` for the current Windows user at limited privileges. Its first scheduled run is **1 October 2026 at 13:20:39 Europe/Zurich**; repetition expires **2 October 2026 at 13:20:39**. Exact timestamps and paths are in `outputs/pilot/schedule.json`. This task repeats every five minutes for 24 hours; it is not a 14-day collector.

The task runs the project-local `pythonw.exe` and the absolute `src/collect.py` path, with the project as working directory. `pythonw.exe` avoids opening a console every five minutes; the manifest records outcomes. Concurrent instances are ignored; each invocation has a two-minute limit. No automatic catch-up or wake setting is enabled. Keep the machine awake, online and signed in; connect power. Missed trigger times cannot be recovered as equivalent current snapshots later.

The collector makes one request per invocation and does not automatically retry. On HTTP 429 it records the retry header and skips scheduled requests until that deadline; without a usable header it pauses for a day. Deferred runs are separately reported. Do not start another scheduled collector or change IP to evade quotas.

Monitor in PowerShell from the project folder:

```powershell
Get-ScheduledTask -TaskName 'AircraftProject-CollectionPilot'
Get-ScheduledTaskInfo -TaskName 'AircraftProject-CollectionPilot'
Get-Content data/raw/manifest.jsonl -Tail 5
.venv\Scripts\python.exe src/prepare.py
.venv\Scripts\python.exe src/pilot_report.py
```

After a new snapshot, `prepare.py` rebuilds SQLite and the audit files from all local snapshots. `pilot_report.py` rebuilds `outputs/pilot/report.md`, `hourly_coverage.csv`, `zone_summary.csv`, `altitude_band_coverage.csv` and `file_integrity.csv`. The processed database does not update just because raw snapshots arrive. Review the manifest as well as the scheduled task result: a cooldown is a successful process exit without a new API request.

To stop the pilot early:

```powershell
Stop-ScheduledTask -TaskName 'AircraftProject-CollectionPilot'
Disable-ScheduledTask -TaskName 'AircraftProject-CollectionPilot'
```

The trigger expires after one day; the task registration remains for inspection. The start script refuses to overwrite an existing task. A later 14-day schedule needs a named owner, dates, reviewed pilot coverage and a single collector, as described in the plan.

Unattended launch was tested with a one-off task start at approximately 13:18, and the regular 13:20:39 trigger also completed. `outputs/pilot/task_verification.json` records task result 0, a five-minute interval, one-day duration, two-minute execution limit and `IgnoreNew` overlap handling. `outputs/pilot/task.xml` preserves the task configuration. The extra startup check is visible in the manifest; it is not part of a perfectly regular five-minute series. Longer reliability is still unverified.

## How to defend the methods

1. **Sampling:** “We collected current regional position reports every five minutes. Our unit is an aircraft report, not a flight. Sparse sampling can miss brief movements; missing collection periods are explicitly reported.” The scope is the configured rectangle around Switzerland, including nearby foreign airspace.
2. **Provenance:** “We preserved original response bytes and logged request bounds, UTC retrieval time, HTTP outcome, response timestamp, row count and SHA-256. The first airport reference is pinned so later source changes do not silently alter enrichment.” A checksum detects local changes; it does not prove that a source measurement is accurate.
3. **Cleaning:** “We recorded missingness before deletion, retained airborne reports with position, ground speed and geometric altitude, checked both position and last-contact age against 60 seconds relative to the source snapshot, then deduplicated ICAO24 plus position timestamp.” The audit is sequential: a row excluded at an early step is not counted again at later steps. Review missing-altitude bias and unusual values before final interpretation.
4. **Integration:** “We calculated great-circle distance to Zurich, Geneva and Basel, selected the closest of those three, and joined airport metadata by its unique identifier.” A complete join checks the implementation; it does not identify an aircraft's departure or destination. Basel is in France. Near <=30 km, middle >30 and <60 km, and far >=60 km remain provisional study definitions.
5. **Comparability:** “We inspected fixed 1,000 m altitude bins for near/far coverage before interpreting speed differences.” Min/max overlap alone is weak evidence. Sparse bins and different altitude composition can explain apparent proximity differences. These pilot reporting bins do not replace the notebook's planned EDA bands or authorize model/threshold tuning.
6. **Evaluation later:** “We will compare a mean baseline, altitude-only regression and spatial models on later held-out dates, and separately test transfer to held-out aircraft. Speed-derived inputs are excluded and preprocessing is fit on training data.” Repeated observations are dependent; more reports do not automatically mean more independent aircraft. The pilot is a pipeline check, not model evidence.

## Historical one-day recommendation and next decision

After the scheduled pilot ends, rebuild preparation/report outputs and examine attempts versus successes, empty responses, unobserved hours, missingness, distinct aircraft by group/airport and populated shared altitude bands. Document whether the machine stayed awake. Do not describe a day as complete just because its UTC date appears once.

If access and coverage are adequate, freeze the question and primary thresholds, name the collection owner and arrange approximately 14 complete days. The modeling notebook's seven-date guard is a minimum implementation condition, not proof of adequate collection. Extend collection or revise scope transparently if group coverage is thin.

Official documentation checked on 1 October 2026: [OpenSky REST schema, OAuth and credit limits](https://openskynetwork.github.io/opensky-api/rest.html), [OurAirports downloads](https://ourairports.com/data/). The configured box is 11.04 square degrees: the documented cost is one credit per request, and a five-minute schedule uses 288 requests/day against a 400-credit anonymous quota shared by IP. The first successful response reported 399 credits remaining. This is feasible budgeting, not a guarantee of service reliability. OpenSky's terms page could not be retrieved by the documentation browser; redistribution review remains pending before publishing raw data.

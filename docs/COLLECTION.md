# Main collection on a travelling laptop

The technical pilot passed and was stopped on 1 October at 15:56:57 Europe/Zurich. The original pilot task is disabled and preserved. Main collection has **not** been started: choose the start date, duration and owner first.

**Change on 22 October 2026 (ADS-B category):** snapshot requests now send `extended=1`, so OpenSky returns 18 instead of 17 fields per state vector; field 18 is the ADS-B emitter `category`. Each successful manifest entry logs `category_present`, the share of vectors with 18 fields. Raw responses are still saved unchanged and nothing is filtered during collection; `prepare.py` reads old 17-field pilot files with an empty `category`. A first manual check returned 167 vectors, all with 18 fields, but 162 reported category 0 (no information), so the ADS-B category serves as a cross-check, not as the aircraft category itself. **Before Start (or Resume), the collection laptop must run `git switch main` and `git pull origin main`**; the scheduled task calls `src/collect.py` from this folder, and no new packages are needed.

## Commands

From this project folder, inspect status:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/collection.ps1 -Action Status
```

To start, choose a **future** timestamp with the correct timezone offset and a duration in days. The following date is only an example, not a group decision:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/collection.ps1 -Action Start -StartAt "2026-10-03T09:00:00+02:00" -Days 14
```

Pause and resume the same window:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/collection.ps1 -Action Pause
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/collection.ps1 -Action Resume
```

Pause disables and stops only `AircraftProject-MainCollection`; data are preserved. Resume registers the next tick five minutes ahead (or at the original future start if later), keeping the original deadline. It does not extend the end date or recover missed observations. An expired window needs a new chosen Start/duration. Prior task configurations and control events are retained under `data/raw/schedules/` and `data/raw/collection_control.jsonl`. No second collector is started if the main task is already enabled, and Start refuses an enabled pilot.

## Sleep, shutdown, internet and battery

The inspected pilot task used `InteractiveToken`, `IgnoreNew` overlapping instances, a two-minute execution limit, battery starts allowed, and no stopping merely because battery power began. `StartWhenAvailable` and `WakeToRun` were false/default. Task Scheduler's operational event history was disabled, so the pilot report infers scheduled runs from timestamps aligned to expected slots rather than claiming a complete event-history record.

Main collection also runs at limited privileges in your signed-in session, allows battery runs, ignores overlapping instances, limits each run to two minutes and does **not** wake the laptop. Normal sleep, power plans, lid behavior and shutdown settings are unchanged. When asleep or shut down, no observations are collected. After reboot, sign in; the task cannot run in an absent interactive session. A locked signed-in session can still run tasks.

Main collection sets `StartWhenAvailable=true` with an explicit end boundary to support delayed starts after missed triggers. [Microsoft documents](https://learn.microsoft.com/en-us/windows/win32/taskschd/tasksettings-startwhenavailable) that such runs can be queued with a default delay of ten minutes. A delayed invocation fetches the current state only; it does not recreate historical snapshots. A recent-request guard suppresses extra requests inside the five-minute cadence, allowing ten seconds of scheduler jitter. An end guard suppresses a late queued invocation after the chosen deadline.

After travel/reboot, inspect Status and the manifest. If you deliberately paused the task, run Resume; reboot does not reverse a deliberate pause. If the task is enabled, give the next eligible tick time to run and inspect the manifest; do not create another task. Resume after a deliberate Pause provides a fresh bounded trigger if needed. Actual sleep/reboot behavior has not been simulated on your laptop; verify the first few runs after travel.

If the laptop is awake but internet is unavailable, the request fails, a credential-free failure entry is written, and the next scheduled tick tries again. HTTP 429 instead creates a persisted cooldown honoring the supplied deadline; no usable header means a one-day pause. No catch-up loop attempts to fill the gap. On battery, the five-minute task still runs while the system is awake; travel downtime counts as missing observations. More calendar days do not necessarily mean more observed hours, and travelling between IPs must not be used to bypass limits.

## Daily monitoring and methods

```powershell
Get-Content data/raw/manifest.jsonl -Tail 5
.venv\Scripts\python.exe src/prepare.py
.venv\Scripts\python.exe src/pilot_report.py
```

Preparation rebuilds the database; raw collection alone does not update it. The pilot report's `scheduled_coverage.csv` is specific to the stopped pilot window. Its all-local-data tables and `sampling_intervals.csv` grow if main collection adds files. For main EDA, use the acquisition-log hourly plot in notebook 01 and inspect actual timestamp gaps and control events; dates with one response are not complete days.

Successful responses, failed requests, deferred requests and intervals with no invocation are different. A successful empty response describes OpenSky's available reports at that instant. Downtime is missing data, never zero traffic. Keep five-minute sampling and report coverage by local hour/day so travel-related missingness is visible. If travel repeatedly removes important hours, extend the chosen collection after review or nominate another single stable collector; do not run competing machines.

`scripts/start_pilot.ps1` is preserved as the historical pilot setup utility; do not use it to resume the main study.

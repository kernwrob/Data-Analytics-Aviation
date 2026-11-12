# Main collection on a travelling laptop

**Status 12 November 2026: the main collection is running** on the old MacBook Pro at Matteo's home (`scripts/collection_mac.sh`), every 5 minutes from 12.11. 19:30 to 26.11. 19:30 Europe/Zurich. The bounding box was enlarged on the first evening to 45.6–48.2 °N, 5.2–10.6 °E. Details and reasons: `DECISIONS.md` («Main collection» and «Bounding box enlarged»). The Windows collector stays off.

The technical pilot passed and was stopped on 1 October at 15:56:57 Europe/Zurich. The original pilot task is disabled and preserved.

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

## Collecting on a Mac (`scripts/collection_mac.sh`)

Added 11 November 2026. The Mac script is the counterpart of `collection.ps1` with the same actions and the same files (`data/raw/main_schedule.json`, `data/raw/collection_control.jsonl`, `data/raw/schedules/`). It registers a per-user launchd agent (`ch.zhaw.aircraftproject.maincollection`) that runs `src/collect.py snapshot --scheduled --until-utc …` every five minutes at :00, :05, … . Ticks before the chosen start are skipped; `--until-utc` stops after the deadline; the recency guard in `collect.py` suppresses extra requests after the Mac wakes up. Python comes from the project `.venv` (`.venv/bin/python`).

```bash
chmod +x scripts/collection_mac.sh          # once, if Git did not keep the flag
scripts/collection_mac.sh status
scripts/collection_mac.sh start --start-at 2026-11-12T09:00:00+01:00 --days 14   # example only
scripts/collection_mac.sh pause
scripts/collection_mac.sh resume
```

Like on Windows, the Mac is **not** woken up: sleep, closed lid on battery, logout or shutdown mean missing observations. A locked screen is fine. To keep it collecting, leave the Mac open and on power and enable *System Settings → Battery → Options → Prevent automatic sleeping on power adapter when the display is off* (or run `caffeinate -s` in a Terminal while collecting). Output is logged to `data/raw/logs/collector_mac.log`. Daily check: `scripts/collection_mac.sh status` and `tail -n 5 data/raw/manifest.jsonl`.

## Switching the collector between Windows and Mac

There is always **one** live `data/raw` folder and **one** active collector. The folder travels with the collector, so no datasets ever need to be merged:

1. On the current computer: `Pause` (Windows) or `pause` (Mac), and check Status says it is no longer running.
2. Copy the whole `data/raw` folder to the other computer (ZIP via USB stick or the restricted OneDrive folder), replacing its `data/raw`. Keep the ZIP until the next export.
3. On the other computer: `git pull`, then `Resume` / `resume`. The original deadline in `main_schedule.json` is kept; `start` refuses to open a new window while the old one is still valid.
4. Note the handover (time, from → to) in `docs/DECISIONS.md` or the group chat. The gap between pause and resume is missing data, not zero traffic, and is visible in the manifest and control log.

Never resume on the second computer before the first one is paused.

## Current main collection (from 12 November 2026)

| Item | Value |
|---|---|
| Device | Old MacBook Pro (A1502), macOS Monterey 12.7.6, user `Sammler`, automatic login, FileVault off, no system sleep on power (`pmset -c sleep 0`), display off after 10 min |
| Repository on the collector | `~/Developer/Data-Analytics-Aviation`, branch `matteo/Data-Analytics-Aviation` (same collector code as `main`) |
| Window | 12.11.2026 19:30 → 26.11.2026 19:30 Europe/Zurich, every 5 minutes, anonymous, `extended=1` |
| Bounding box | 45.6–48.2 °N, 5.2–10.6 °E from the switch on 12.11. (before: 45.7–48.0 °N, 5.8–10.6 °E) |
| Expected volume | 288 snapshots per day, about 4,000 in total |
| Monitoring | Matteo, daily |

Daily check from another Mac in the same home network (the collector has *Remote Login* enabled for the user `Sammler`; the `.local` name does not resolve in this network, so use the IP address and update it if the router assigns a new one):

```bash
ssh sammler@192.168.0.59 "cd ~/Developer/Data-Analytics-Aviation && scripts/collection_mac.sh status"
```

Good: `ENABLED`, the last manifest entry is a `snapshot` with `success` and at most 5–10 minutes old (times are UTC). Several `failure` entries in a row: send the last lines of `data/raw/manifest.jsonl` and `data/raw/logs/collector_mac.log` to the group.

Changing the collector code or `config.json` during the collection always follows the same order, so there is never a second collector and the deadline stays the same:

```bash
cd ~/Developer/Data-Analytics-Aviation
scripts/collection_mac.sh pause
git pull --ff-only
scripts/collection_mac.sh resume
scripts/collection_mac.sh status
```

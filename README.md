# Aircraft movements around Switzerland: project starter

**Status: technical pilot passed and stopped; optional aircraft metadata integrated; main collection awaits group dates.**
On 1 October 2026 the stopped pilot produced 35 successful snapshots: 5,664 raw reports, 4,115 retained observations and 968 distinct aircraft. Its specific scheduled task is disabled and preserved. See `docs/PILOT.md` and `outputs/pilot/report.md` for evidence. Metadata matches 67.27% of retained observations and 68.08% of aircraft; unmatched rows remain. No project models have been fitted and no final findings are claimed. The old group's data are not reused.

Read `PROJECT_PLAN.md` first. The group has three students and at least six weeks available. The selected direction is aircraft movements. Confirm the exact deadline and presentation language.

## Local setup (Windows / VS Code)

For a new local copy, open a terminal in this folder and install the environment:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Teammates should then follow `docs/COLLABORATION.md` to obtain a dated export, rebuild SQLite and select the notebook kernel. Only the designated collector downloads new source data. The following commands document the initial source setup, which is already complete on this laptop; do not repeat them to resume collection:

```powershell
.venv\Scripts\python.exe src/collect.py airports
.venv\Scripts\python.exe src/collect.py snapshot
.venv\Scripts\python.exe src/collect.py metadata
.venv\Scripts\python.exe src/prepare.py
.venv\Scripts\python.exe src/pilot_report.py
```

Anonymous collection is supported. For authenticated access, create your own OpenSky OAuth client and set `OPENSKY_CLIENT_ID` and `OPENSKY_CLIENT_SECRET` as environment variables before running. Never put secrets in notebooks, GitHub, screenshots, or the AI log. Basic username/password authentication from the old example is obsolete.

On the tested machine, `python` works while `py -0p` reports no installed Pythons. Setup has already created `.venv`; use its executable directly. For a clean reproduction with Python 3.13 on Windows, install `requirements-lock.txt` instead of the version ranges. Do not recreate the environment just to collect another snapshot.

Metadata is optional; skip its download if unavailable. Original dated files and SHA-256 acquisition records are preserved. The official metadata is out of date (server timestamp November 2024); see `docs/METADATA.md` for fields, duplicate resolution, coverage and limitations.

Main collection has not been started. Choose its date, duration and designated computer after reviewing the pilot. `scripts/collection.ps1` provides Start, Pause, Resume and Status; see `docs/COLLECTION.md` for exact commands and travelling-laptop behavior. It keeps five-minute sampling, uses absolute paths and preserves normal sleep/shutdown behavior. Offline/sleep periods are missing observations. After reboot sign in and inspect the manifest; deliberate pauses require Resume. Do not launch competing collectors. Failure entries record status and retry information without credentials.

After collecting enough observations:

```powershell
.venv\Scripts\python.exe src/prepare.py
.venv\Scripts\python.exe -m jupyterlab
```

Open notebooks in order and select the `.venv` kernel. The modeling notebook requires at least seven observed UTC dates, and recommends 14 complete collection days. It deliberately refuses to turn a single snapshot into a final evaluation.

## Contents

- `PROJECT_PLAN.md`: recommended question, alternative aircraft questions, grading map, timeline, roles, risks, completion criteria.
- `config.json`: spatial extent, airport selection, distance thresholds, freshness threshold.
- `src/collect.py`: retrieves one OpenSky snapshot or airport reference file, with source manifest and SHA-256.
- `src/prepare.py`: cleans observations, spatially assigns an airport, performs an audited SQL join, writes SQLite and audit tables.
- `src/aircraft_metadata.py`: normalizes metadata keys, resolves/audits duplicates and validates a row-preserving left join.
- `src/model_comparison.py`: optional fixed A/B/C regression comparison on the original evaluation frames, retaining unknown categories.
- `src/export_data.py`: freezes a dated, checksum-verified data package and rebuilds its SQLite database without changing originals or uploading.
- `src/pilot_report.py`: verifies raw-file checksums and reports collection attempts, hourly coverage, cleaning and proximity/altitude coverage.
- `docs/PILOT.md`: completed technical pilot evidence and methods explanation; earlier one-day setup is retained as history.
- `docs/COLLECTION.md`, `docs/METADATA.md`, `docs/COLLABORATION.md`, `docs/SHARING.md`: collection controls, optional enrichment, private GitHub/team exports and source conditions.
- `notebooks/01_data_and_eda.ipynb`: SQL, descriptive analysis, group comparisons, maps.
- `notebooks/02_models.ipynb`: baseline, altitude regression, spatial regression, random forest; later-day and held-out-aircraft evaluations.
- `notebooks/03_statistics_and_clusters.ipynb`: exploratory correlation with p-values and standardized k-means.
- `docs/AI_USAGE_LOG.csv`, `docs/DECISIONS.md`, `docs/FINAL_CHECKLIST.md`: fill as work progresses.
- `presentation/VIDEO_OUTLINE.md`: final 15-minute presentation structure.

## Verification and limits

Windows setup, anonymous scheduled downloads, cleaning, row-preserving airport/metadata joins and SQLite integrity have been checked locally. Focused offline tests (`.venv\Scripts\python.exe -m unittest discover -s tests -v`) cover collection failures, coverage states, optional metadata and unseen categories; fixtures are not project evidence. OAuth, actual sleep/reboot recovery, extended collection, final multi-day model evaluation and lecturer acceptance remain unverified. `requirements-lock.txt` records the tested environment.

SQLite has been built from pilot data. PostgreSQL is a planned optional extension, not already implemented. Maps and EDA can be explored on the pilot; modeling still requires at least seven observed dates. A final presentation must use real generated outputs and group-approved interpretations.

For public GitHub, publish code and documentation first. Decide what raw OpenSky data can be redistributed under its terms before adding datasets. Deliver required data on Moodle in accordance with those terms and course instructions. Do not upload credentials found in the reference files.

## Three-student access and dated exports

A local Git repository on `main` is prepared; no remote or author identity was supplied, so no commit/push or invitations have occurred. See `docs/COLLABORATION.md` for private repository creation, invitations, cloning, environment/kernel selection, data placement, branches and pull requests. Keep one collector and independent local copies for the other students.

```powershell
.venv\Scripts\python.exe src/export_data.py
```

The command creates a dated folder, ZIP and ZIP checksum under ignored `exports/`. Use the latest agreed export in a restricted university OneDrive/Teams folder under `docs/SHARING.md`; the command uploads nothing. Source terms and citation instructions accompany the package. Raw data, databases, environments, caches and exports are excluded from Git. Public code publication remains a later grading-bonus decision.

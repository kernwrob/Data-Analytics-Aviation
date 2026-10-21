# Returning to the aircraft project

Checked 13 October 2026 against the local manifest, SQLite database, configuration, notebooks and scheduled task. The cloud handover is context about prior decisions; it does not prove implementation or lecturer approval.

## What is working

The collector requests structured JSON from the OpenSky API every five minutes. This is API collection: it does not extract data from website pages. Original responses and a source/checksum manifest are preserved. Preparation cleans the reports, calculates distance to the nearest of LSZH/LSGG/LFSB, joins downloaded OurAirports attributes and builds SQLite. Optional aircraft metadata are left-joined by ICAO24, retaining unmatched reports.

The 1 October pilot contains 35 successful snapshots, 5,664 raw reports and 4,115 retained observations from 968 distinct aircraft. Its task remains disabled; no main collection task exists. No observations have accumulated during the project break. Near/middle/far contain 778/1,139/2,198 observations. Their distinct-aircraft counts overlap. One row is one aircraft position report, not a complete flight.

## Explore the existing data now

Notebook `notebooks/01_data_and_eda.ipynb` can run on the pilot. Select `.venv` as the kernel and run cells in order. It reads SQLite, displays data-quality/count tables, draws distributions and an altitude-speed plot, and creates a geographical map. Add `data.head(10)` in a temporary cell to inspect rows; `data.info()` shows columns and types. Units are metres and metres/second; `speed_kmh` is also available.

The notebook's exploratory cells were run successfully on 13 October without saving private outputs into the shared notebook. Generated artifacts:

- `outputs/figures/aircraft_map.html`: open in a browser; 1,500 sampled reports, airport markers and proximity colors. Tiles/scripts require internet.
- `outputs/figures/altitude_speed.png`: each point is a retained report, colored by proximity group.
- `outputs/figures/group_distributions.png`: group speed and altitude distributions, normalized within groups.
- `outputs/figures/collection_coverage.png`: attempts/successes during the observed pilot hours, not coverage over the intervening project break.
- `outputs/tables/altitude_band_comparison.csv`: counts and descriptive speeds within comparable altitude bands.

These are exploratory pilot outputs. Repeated points from the same aircraft are dependent. Near airports does not establish a landing/approach; overflights are present. Altitude distributions differ, so an overall group speed difference alone cannot isolate proximity. The rectangle includes foreign airspace. Neither two-hour coverage nor 968 aircraft establishes generalization across days.

## Discuss the concept with the professors

Suggested pitch: "We collect our own five-minute aircraft snapshots around Switzerland and join airport reference data. We ask how the altitude-ground-speed relationship differs near Zurich, Geneva and Basel versus farther away, and whether spatial information improves estimation on later days and on other aircraft. A short technical pilot has verified collection and integration. We will now agree the definitions and collection period before final evaluation."

Show the proposed question, a workflow diagram, the pilot counts, the map and one exploratory plot. Label charts as pilot evidence, not final findings. Proposed models are altitude-only, altitude plus spatial features, and optionally the same spatial model plus aircraft category; compare on identical evaluation observations. The earlier-date/later-date split and a separate split holding out aircraft answer different generalization questions. Final modeling remains blocked by the deliberate seven-observed-date minimum; roughly 14 days is a planning target, not a course mandate.

Ask the professors to confirm topic approval; whether the API collection and downloaded reference joins meet their requirements; the proposed comparisons and evaluation; an acceptable collection period/coverage; SQLite minimum versus PostgreSQL bonus; and the concept/final deadlines, presentation expectations and grading rules. The course text supplied later on 13 October specifies eight concept evaluation criteria and a ten-minute slot, but does not state its grade weighting; see `COURSE_EVALUATION.md`.

After feedback, record agreed choices in `docs/DECISIONS.md`, choose one collector and main start/duration, and use `docs/COLLECTION.md`. Main collection has not been started by this reorientation work. GitHub/team-folder details remain pending, but the local pilot is ready to demonstrate.

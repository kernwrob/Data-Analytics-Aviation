# Optional source: modelled wind (Open-Meteo)

Added 11 November 2026 (issue #36; the group decision on using wind is tracked in #22).

## Why

Ground speed = airspeed + wind along the track. At cruise altitude the wind over Switzerland often reaches 30–50 m/s, so part of the altitude–ground-speed pattern (and of the near/far difference) is wind, not aircraft behaviour. The wind join lets the analysis separate the two.

## Source

Open-Meteo **Historical Forecast API** (`https://historical-forecast-api.open-meteo.com/v1/forecast`), hourly, on pressure levels 1000–200 hPa: wind speed (m/s), wind direction (degrees, direction the wind comes **from**) and geopotential height (m). Free for non-commercial use; values are model output, not measurements at the aircraft. Data for past days can be fetched at any time, so this does not need to run during collection.

## Fetch

Needs internet; run from the project folder in any clone with the raw snapshots (also works on the collector, which only has `requests` installed):

```bash
python src/weather.py fetch                              # every complete UTC day found in data/raw/opensky
python src/weather.py fetch --start 2026-11-12 --end 2026-11-25
```

One request per UTC day for a 0.5° grid over the collection rectangle (50 points) and 10 pressure levels. Raw responses are saved unchanged in `data/raw/weather/` and logged in `data/raw/manifest.jsonl` (`source: "weather"`), so `export_data.py` freezes them with the other sources. Days that already have a successful download with the same grid/levels are skipped; the current (incomplete) UTC day is never fetched. Failures are logged and can simply be retried.

Settings live in `config.json` under `"weather"`. Changing them means a new download, so freeze them before the final export.

## Join (in `src/prepare.py`)

For every cleaned observation:

1. **Time:** nearest full UTC hour of `time_position`.
2. **Place:** nearest grid point (model cell returned by Open-Meteo).
3. **Height:** the pressure level whose geopotential height is closest to `geo_altitude`. The vertical mismatch is stored as `wind_level_gap_m` (geoid/ellipsoid differences of ~50 m are ignored).

Derived columns, all in m/s: `tailwind_ms` (+ = wind pushes along the track), `crosswind_ms` (+ = pushes to the right), `airspeed_est_ms` (ground velocity minus wind vector). Missing `true_track` gives empty components.

The join is a row-preserving left join keyed by `(icao24, time_position)`: table `observation_wind`, view `observations_with_wind`, audit `weather_integration_audit` (match fraction, median level gap, share of gaps > 500 m). Without weather files every observation stays, with `wind_matched = 0`. The long weather table is stored as `weather_levels` for SQL queries.

## Limitations to state

- Model wind on a ~0.5° grid and hourly, not the wind the aircraft actually experienced.
- Nearest level, no vertical interpolation; check `wind_level_gap_m` (aircraft above ~12 km lie above the 200 hPa level).
- `airspeed_est_ms` is an estimate (true airspeed approximation), not reported by OpenSky.
- Do not use future weather information for a later-day prediction claim unless the same information would be available at prediction time; here wind is a descriptive covariate.

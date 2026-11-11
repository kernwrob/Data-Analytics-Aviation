# Optional source: modelled wind (Open-Meteo)

Added 11 November 2026 (issue #36; the group decision on using wind is tracked in #22).

## Why

Ground speed = airspeed + wind along the track. At cruise altitude the wind over Switzerland often reaches 30–50 m/s, so part of the altitude–ground-speed pattern (and of the near/far difference) is wind, not aircraft behaviour. The wind join lets the analysis separate the two.

## Source

Open-Meteo **Historical Forecast API** (`https://historical-forecast-api.open-meteo.com/v1/forecast`), hourly, on 11 pressure levels from 1000 to 150 hPa (about 0.1–13.5 km): wind speed (m/s), wind direction (degrees, direction the wind comes **from**) and geopotential height (m). Free for non-commercial use; values are model output, not measurements at the aircraft. Data for past days can be fetched at any time, so this does not need to run during collection.

## Fetch

Needs internet; run from the project folder in any clone with the raw snapshots (also works on the collector, which only has `requests` installed):

```bash
python src/weather.py fetch                              # every complete UTC day found in data/raw/opensky
python src/weather.py fetch --start 2026-11-12 --end 2026-11-25
```

One request per UTC day for a 0.5° grid over the collection rectangle (50 points) and 11 pressure levels. Raw responses are saved unchanged in `data/raw/weather/` and logged in `data/raw/manifest.jsonl` (`source: "weather"`), so `export_data.py` freezes them with the other sources. Days that already have a successful download with the same grid/levels are skipped; the current (incomplete) UTC day is never fetched. Failures are logged and can simply be retried.

Settings live in `config.json` under `"weather"`. Changing them means a new download, so freeze them before the final export.

## Join (in `src/prepare.py`)

For every cleaned observation:

1. **Time:** nearest full UTC hour of `time_position`.
2. **Place:** nearest grid point (model cell returned by Open-Meteo).
3. **Height:** linear interpolation between the two pressure levels whose geopotential heights bracket `geo_altitude`. The wind is interpolated as east/north components (u/v), not as speed and direction, so a change of direction between levels is handled correctly. `wind_interpolated = 1` marks these rows; `wind_level_hpa`/`wind_level_height_m` name the nearer of the two levels. Below the lowest or above the highest level the edge level is used, `wind_interpolated = 0`, and the vertical distance is stored as `wind_level_gap_m` (0 when interpolated). Geoid/ellipsoid differences of ~50 m are ignored.

Derived columns, all in m/s: `tailwind_ms` (+ = wind pushes along the track), `crosswind_ms` (+ = pushes to the right), `airspeed_est_ms` (ground velocity minus wind vector). Missing `true_track` gives empty components.

The join is a row-preserving left join keyed by `(icao24, time_position)`: table `observation_wind`, view `observations_with_wind`, audit `weather_integration_audit` (match fraction, interpolated share, median level gap, share of gaps > 500 m). Without weather files every observation stays, with `wind_matched = 0`. The long weather table is stored as `weather_levels` for SQL queries.

## Limitations to state

- Model wind on a ~0.5° grid and hourly, not the wind the aircraft actually experienced.
- Linear interpolation between levels 1–1.5 km apart at cruise altitude smooths sharp jet-stream cores. Rows with `wind_interpolated = 0` (outside the level range) should be few; check the audit.
- `airspeed_est_ms` is an estimate (true airspeed approximation), not reported by OpenSky. It is computed **from the target** (ground speed) and must never be a model feature; `src/model_comparison.py` asserts this. Tailwind/crosswind use only wind and track and may be features.
- Do not use future weather information for a later-day prediction claim unless the same information would be available at prediction time; here wind is a descriptive covariate.

## First real check (22 October 2026, one snapshot, 124 observations)

All 124 observations matched. With nearest-level matching, 22 % had a vertical mismatch over 500 m (mostly above 6 km). With interpolation, 96 % are interpolated and only the observations above the then-highest level (200 hPa) remain unbracketed; adding 150 hPa covers them after a re-fetch. Median wind at 9–11 km was about 53 m/s from west-northwest, roughly a quarter of the observed ground speed.

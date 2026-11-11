"""Optional third source: modelled wind on pressure levels (Open-Meteo historical forecast API).

Fetch, with internet access, from the project folder (any clone that has the raw snapshots):
    python src/weather.py fetch                         # every complete UTC date found in data/raw/opensky
    python src/weather.py fetch --start 2026-11-12 --end 2026-11-25
Raw responses are saved unchanged under data/raw/weather/ and logged in data/raw/manifest.jsonl,
so export_data.py freezes them like the other sources. src/prepare.py then attaches the wind to every
observation with a row-preserving left join (table observation_wind, view observations_with_wind).

Matching per observation: nearest full UTC hour, nearest grid point, and the pressure level whose
geopotential height is closest to the aircraft's geometric altitude. Wind is modelled, not measured at
the aircraft; the level gap is stored so large vertical mismatches stay visible.
"""
import argparse
import hashlib
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import requests

# numpy/pandas are imported inside the analysis functions, so `fetch` also runs on the
# collector's minimal environment (requests only).

ROOT = Path(__file__).resolve().parents[1]
WEATHER_URL = "https://historical-forecast-api.open-meteo.com/v1/forecast"
DEFAULTS = {"grid_step_deg": 0.5,
            "pressure_levels": [1000, 925, 850, 700, 600, 500, 400, 300, 250, 200]}
WIND_COLUMNS = ["wind_time_utc", "wind_grid_lat", "wind_grid_lon", "wind_level_hpa", "wind_level_height_m",
                "wind_level_gap_m", "wind_speed_ms", "wind_dir_deg", "tailwind_ms", "crosswind_ms",
                "airspeed_est_ms", "wind_matched"]


def settings(config):
    return {**DEFAULTS, **config.get("weather", {})}


def grid_points(bbox, step):
    """Cell centres covering the collection rectangle."""
    def centres(low, high):
        values, value = [], low + step / 2
        while value < high - 1e-9:
            values.append(round(value, 4))
            value += step
        return values
    return [(a, o) for a in centres(bbox["lamin"], bbox["lamax"]) for o in centres(bbox["lomin"], bbox["lomax"])]


def hourly_variables(levels):
    return [f"{name}_{level}hPa" for level in levels
            for name in ("wind_speed", "wind_direction", "geopotential_height")]


def record_manifest(entry):
    entry["retrieved_at_utc"] = datetime.now(timezone.utc).isoformat()
    with (ROOT / "data/raw/manifest.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def manifest_entries():
    path = ROOT / "data/raw/manifest.jsonl"
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]


def snapshot_dates():
    """UTC dates present in the raw snapshot file names (YYYYMMDDT...Z.json)."""
    names = (p.name for p in (ROOT / "data/raw/opensky").glob("*.json"))
    return sorted({datetime.strptime(n[:8], "%Y%m%d").date() for n in names if n[:8].isdigit()})


def fetch_day(day, config):
    s = settings(config)
    points = grid_points(config["bbox"], s["grid_step_deg"])
    params = {"latitude": ",".join(str(p[0]) for p in points),
              "longitude": ",".join(str(p[1]) for p in points),
              "hourly": ",".join(hourly_variables(s["pressure_levels"])),
              "start_date": day.isoformat(), "end_date": day.isoformat(),
              "wind_speed_unit": "ms", "timezone": "GMT"}
    entry = {"source": "weather", "source_url": WEATHER_URL, "weather_date": day.isoformat(),
             "grid_step_deg": s["grid_step_deg"], "grid_points": len(points),
             "pressure_levels": s["pressure_levels"], "status": None,
             "attempted_at_utc": datetime.now(timezone.utc).isoformat()}
    try:
        response = requests.get(WEATHER_URL, params=params, timeout=120)
        entry["status"] = response.status_code
        response.raise_for_status()
        payload = response.json()
        items = payload if isinstance(payload, list) else [payload]
        if len(items) != len(points) or any("hourly" not in item for item in items):
            raise ValueError("Unexpected weather payload")
    except Exception as exc:
        record_manifest({**entry, "outcome": "failure", "error_type": type(exc).__name__})
        print(f"{day}: failed ({type(exc).__name__}, HTTP {entry['status']})")
        return False
    name = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + f"_{day:%Y%m%d}.json"
    destination = ROOT / "data/raw/weather" / name
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(response.content)
    record_manifest({**entry, "outcome": "success", "path": destination.relative_to(ROOT).as_posix(),
                     "sha256": hashlib.sha256(response.content).hexdigest(), "bytes": len(response.content)})
    print(f"{day}: saved {destination.relative_to(ROOT).as_posix()}")
    return True


def fetch(config, start=None, end=None):
    """Fetch complete UTC days that have no successful weather download yet."""
    today = datetime.now(timezone.utc).date()
    if start or end:
        first = start or end
        last = end or start
        days = [first + timedelta(d) for d in range((last - first).days + 1)]
    else:
        days = snapshot_dates()
    s = settings(config)
    done = {e["weather_date"] for e in manifest_entries()
            if e.get("source") == "weather" and e.get("outcome") == "success"
            and e.get("pressure_levels") == s["pressure_levels"] and e.get("grid_step_deg") == s["grid_step_deg"]}
    todo = [d for d in days if d < today and d.isoformat() not in done]
    skipped_today = [d for d in days if d >= today]
    if skipped_today:
        print("Skipped incomplete/future UTC days: " + ", ".join(map(str, skipped_today)))
    if not todo:
        print("No weather days to fetch.")
        return True
    return all([fetch_day(d, config) for d in todo])


def load_weather(paths):
    """Long table: one row per hour, grid point and pressure level. First download wins on duplicates."""
    import pandas as pd
    frames = []
    for path in paths:
        payload = json.loads(path.read_text())
        for item in payload if isinstance(payload, list) else [payload]:
            hourly = item["hourly"]
            times = pd.to_datetime(hourly["time"], utc=True)
            for key in hourly:
                if not key.startswith("wind_speed_") or not key.endswith("hPa"):
                    continue
                level = int(key[len("wind_speed_"):-3])
                frames.append(pd.DataFrame({
                    "time_utc": times, "grid_lat": float(item["latitude"]), "grid_lon": float(item["longitude"]),
                    "level_hpa": level,
                    "height_m": pd.to_numeric(hourly.get(f"geopotential_height_{level}hPa"), errors="coerce"),
                    "wind_speed_ms": pd.to_numeric(hourly[key], errors="coerce"),
                    "wind_dir_deg": pd.to_numeric(hourly.get(f"wind_direction_{level}hPa"), errors="coerce")}))
    columns = ["time_utc", "grid_lat", "grid_lon", "level_hpa", "height_m", "wind_speed_ms", "wind_dir_deg"]
    if not frames:
        return pd.DataFrame(columns=columns)
    weather = pd.concat(frames, ignore_index=True)
    weather = weather.drop_duplicates(["time_utc", "grid_lat", "grid_lon", "level_hpa"], keep="first")
    return weather.dropna(subset=["height_m", "wind_speed_ms", "wind_dir_deg"]).reset_index(drop=True)[columns]


def wind_components(velocity, track_deg, wind_speed, wind_from_deg):
    """Tailwind (+ pushes along the track), crosswind (+ pushes to the right) and estimated airspeed, m/s."""
    import numpy as np
    track = np.radians(track_deg)
    toward = np.radians(np.asarray(wind_from_deg, dtype=float) + 180.0)
    wx, wy = wind_speed * np.sin(toward), wind_speed * np.cos(toward)
    tail = wx * np.sin(track) + wy * np.cos(track)
    cross = wx * np.cos(track) - wy * np.sin(track)
    gx, gy = velocity * np.sin(track), velocity * np.cos(track)
    airspeed = np.hypot(gx - wx, gy - wy)
    return tail, cross, airspeed


def attach_wind(observations, weather):
    """Row-preserving left join of modelled wind onto observations, keyed by (icao24, time_position)."""
    import numpy as np
    import pandas as pd
    obs = observations[["icao24", "time_position", "latitude", "longitude", "geo_altitude",
                        "velocity", "true_track"]].reset_index(drop=True).copy()
    audit = {"source_available": not weather.empty, "weather_rows": len(weather), "observations": len(obs)}
    result = obs[["icao24", "time_position"]].copy()
    for column in WIND_COLUMNS:
        result[column] = np.nan
    result["wind_matched"] = 0
    if not weather.empty and not obs.empty:
        points = weather[["grid_lat", "grid_lon"]].drop_duplicates().reset_index(drop=True)
        scale = np.cos(np.radians(obs.latitude.to_numpy()))[:, None]
        d2 = (obs.latitude.to_numpy()[:, None] - points.grid_lat.to_numpy()[None, :]) ** 2 + \
             ((obs.longitude.to_numpy()[:, None] - points.grid_lon.to_numpy()[None, :]) * scale) ** 2
        nearest = points.iloc[d2.argmin(axis=1)].reset_index(drop=True)
        obs["row"] = np.arange(len(obs))
        obs["grid_lat"], obs["grid_lon"] = nearest.grid_lat, nearest.grid_lon
        obs["time_utc"] = pd.to_datetime(obs.time_position, unit="s", utc=True).dt.round("h")
        candidates = obs.merge(weather, on=["time_utc", "grid_lat", "grid_lon"], how="inner")
        if not candidates.empty:
            candidates["gap"] = (candidates.height_m - candidates.geo_altitude).abs()
            best = candidates.loc[candidates.groupby("row").gap.idxmin()].set_index("row")
            tail, cross, airspeed = wind_components(best.velocity.to_numpy(), best.true_track.to_numpy(),
                                                    best.wind_speed_ms.to_numpy(), best.wind_dir_deg.to_numpy())
            idx = best.index.to_numpy()
            values = {"wind_time_utc": best.time_utc.astype(str), "wind_grid_lat": best.grid_lat,
                      "wind_grid_lon": best.grid_lon, "wind_level_hpa": best.level_hpa,
                      "wind_level_height_m": best.height_m, "wind_level_gap_m": best.gap,
                      "wind_speed_ms": best.wind_speed_ms, "wind_dir_deg": best.wind_dir_deg,
                      "tailwind_ms": tail, "crosswind_ms": cross, "airspeed_est_ms": airspeed}
            result["wind_time_utc"] = result["wind_time_utc"].astype(object)
            for column, series in values.items():
                result.loc[idx, column] = np.asarray(series)
            result.loc[idx, "wind_matched"] = 1
    if len(result) != len(observations) or result[["icao24", "time_position"]].duplicated().any():
        raise AssertionError("Wind join changed the observation rows.")
    matched = result[result.wind_matched.eq(1)]
    audit.update({"matched_observations": len(matched),
                  "match_fraction": len(matched) / len(result) if len(result) else 0.0,
                  "median_level_gap_m": float(matched.wind_level_gap_m.median()) if len(matched) else None,
                  "share_level_gap_over_500m": float((matched.wind_level_gap_m > 500).mean()) if len(matched) else None,
                  "weather_time_min_utc": str(weather.time_utc.min()) if not weather.empty else None,
                  "weather_time_max_utc": str(weather.time_utc.max()) if not weather.empty else None})
    result["wind_matched"] = result.wind_matched.astype(int)
    return result, audit


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    f = sub.add_parser("fetch", help="Download modelled wind for complete UTC days.")
    f.add_argument("--start", type=date.fromisoformat)
    f.add_argument("--end", type=date.fromisoformat)
    args = parser.parse_args()
    config = json.loads((ROOT / "config.json").read_text())
    (ROOT / "data/raw").mkdir(parents=True, exist_ok=True)
    if not fetch(config, args.start, args.end):
        raise SystemExit("Some weather days failed; rerun later. Failures are logged in the manifest.")


if __name__ == "__main__":
    main()

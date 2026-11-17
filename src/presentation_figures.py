"""Numbers and figures for the concept presentation (presentation/KONZEPT_OFFENE_PUNKTE.md, part B).

    python src/presentation_figures.py

Reads data/processed/aircraft.sqlite (built by src/prepare.py), data/raw/manifest.jsonl and
data/raw/main_schedule.json, and writes
    outputs/tables/presentation_numbers.csv          one row per number: key, value, unit, source, placeholder
    outputs/figures/presentation/altitude_speed_kmh.png   slide 8 (replaces the pilot figure)
    outputs/figures/presentation/title_map.png            title slide
Only observations from snapshots with the final bounding box are used (prepare.py with
"require_current_bbox": true), like the main analysis. Samples use random_state=42, so reruns on the same
database give the same figures. Labels are German because the slides are German.
"""
import json
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

try:
    from .aircraft_metadata import UNKNOWN
    from .collection_coverage import summarize_coverage
    from .prepare import same_bbox
except ImportError:
    from aircraft_metadata import UNKNOWN
    from collection_coverage import summarize_coverage
    from prepare import same_bbox

ROOT = Path(__file__).resolve().parents[1]
RANDOM_STATE = 42
SCATTER_SAMPLE = 3000
MAP_SAMPLE = 1500
ZONES = ["near", "middle", "far"]
ZONE_LABELS = {"near": "nah", "middle": "mittel", "far": "fern"}
ZONE_COLORS = {"near": "#DD8452", "middle": "#55A868", "far": "#4C72B0"}  # as on slide 6
NAVY = "#13233A"  # title slide background
WIND_BAND_M = (9000, 11000)
EARTH_RADIUS_KM = 6371.0088
NUMBER_COLUMNS = ["key", "value", "unit", "source", "placeholder"]


def swiss(value, _position=None):
    """1234.5 -> 1'235 (Swiss thousands separator, as on the slides)."""
    return f"{value:,.0f}".replace(",", "'")


def read_table(db, sql):
    return pd.read_sql_query(sql, db)


def table_exists(db, name):
    return db.execute("SELECT COUNT(*) FROM sqlite_master WHERE name = ?", (name,)).fetchone()[0] > 0


def load_database(path):
    if not path.exists():
        raise SystemExit(f"{path} not found. Run src/prepare.py first.")
    with closing(sqlite3.connect(path)) as db:
        bbox_audit = read_table(db, "SELECT * FROM snapshot_bbox_audit")
        if not bool(bbox_audit.require_current_bbox.iloc[0]):
            raise SystemExit("The database was built with require_current_bbox = false. Presentation numbers use "
                             "the final bounding box only: set it to true in config.json and rerun src/prepare.py.")
        frames = {
            "bbox_audit": bbox_audit,
            "audit": read_table(db, "SELECT * FROM integration_audit"),
            "metadata_audit": read_table(db, "SELECT * FROM metadata_integration_audit"),
            "airports": read_table(db, "SELECT * FROM airports"),
            "observations": read_table(db, """SELECT icao24, time_position, latitude, longitude, altitude_m,
                                              velocity, zone, airport, date_utc FROM observations"""),
            "categories": read_table(db, "SELECT aircraft_category, COUNT(*) AS observations "
                                         "FROM observations_enriched GROUP BY 1"),
            "neighbours": (read_table(db, "SELECT ident FROM neighbour_airports")
                           if table_exists(db, "neighbour_airports") else pd.DataFrame(columns=["ident"])),
        }
        low, high = WIND_BAND_M
        frames["wind"] = (read_table(db, f"""SELECT wind_speed_ms, velocity FROM observations_with_wind
                                            WHERE wind_matched = 1 AND altitude_m BETWEEN {low} AND {high}""")
                          if table_exists(db, "observations_with_wind") else pd.DataFrame())
    return frames


def manifest_entries(root):
    path = root / "data/raw/manifest.jsonl"
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]


def coverage_gaps(entries, config, schedule, now=None):
    """Gaps in the 5-minute schedule from the first final-bbox snapshot to the end of the window.

    A gap is a run of consecutive scheduled slots without a successful response (failure, deferral or no
    request at all). While the collection is still running, the window ends with the newest local snapshot,
    because a local copy that is a few days old must not look like a collection gap.
    Returns (summary dict, window note) or (None, reason).
    """
    interval = int(config.get("interval_seconds", 300))
    final = [e for e in entries if e.get("source_url", "").endswith("/states/all") and e.get("outcome") == "success"
             and same_bbox(e.get("params") or {}, config["bbox"])]
    if not final:
        return None, "no successful snapshot with the final bbox in data/raw/manifest.jsonl"
    attempts = pd.to_datetime([e.get("attempted_at_utc") or e["retrieved_at_utc"] for e in final], utc=True,
                              format="ISO8601")
    step = pd.to_timedelta(interval, unit="s")
    start = attempts.min().floor(step)
    now = pd.Timestamp(now or datetime.now(timezone.utc))
    end_planned = pd.Timestamp(schedule["end_utc"]).tz_convert("UTC") if schedule else None
    if end_planned is not None and now >= end_planned:
        end, note = end_planned, "until the planned end of the collection"
    else:
        end, note = attempts.max().floor(step) + step, "until the newest local snapshot (collection still running)"
    _, slots, _, _ = summarize_coverage(entries, start, end, interval)
    missing = slots.outcome.ne("successful_response")
    runs = (missing & ~missing.shift(fill_value=False)).sum()
    summary = {"start": start, "end": end, "expected_slots": len(slots),
               "successful_slots": int((~missing).sum()), "gaps": int(runs),
               "missing_hours": missing.sum() * interval / 3600}
    return summary, note


def row(key, value, unit, source, placeholder):
    return {"key": key, "value": value, "unit": unit, "source": source, "placeholder": placeholder}


def presentation_numbers(frames, entries, config, schedule, scatter_n, map_n, now=None):
    obs, bbox, audit, meta = frames["observations"], frames["bbox_audit"], frames["audit"], frames["metadata_audit"]
    stage = audit.set_index("stage")
    rows = [
        row("successful_queries", int(bbox.snapshots_kept.iloc[0]), "snapshots",
            "snapshot_bbox_audit.snapshots_kept (successful snapshots with the final bbox)", "B2, B3"),
        row("raw_rows", int(bbox.rows_kept.iloc[0]), "state vectors",
            "snapshot_bbox_audit.rows_kept (raw rows with the final bbox)", "B2, B3"),
        row("clean_observations", len(obs), "observations", "observations (after all cleaning stages)",
            "B2, B3, B8"),
        row("distinct_aircraft", int(obs.icao24.nunique()), "aircraft", "COUNT(DISTINCT icao24) in observations",
            "B2, B3"),
        row("observed_utc_dates", int(obs.date_utc.nunique()), "dates", "distinct date_utc in observations", "B2"),
        row("type_join_match_pct", round(float(meta.observation_match_fraction.iloc[0]) * 100, 1), "%",
            "metadata_integration_audit.observation_match_fraction", "B4, B5, B15"),
        row("type_join_aircraft_match_pct", round(float(meta.aircraft_match_fraction.iloc[0]) * 100, 1), "%",
            "metadata_integration_audit.aircraft_match_fraction (distinct aircraft)", "B4 (Notiz)"),
    ]
    categories = frames["categories"]
    unknown = categories.loc[categories.aircraft_category.eq(UNKNOWN), "observations"].sum()
    rows.append(row("unknown_category_pct", round(100 * unknown / categories.observations.sum(), 1), "%",
                    "observations_enriched, share of observations with aircraft_category Unbekannt", "B13"))
    gaps, note = coverage_gaps(entries, config, schedule, now)
    if gaps:
        window = f"{gaps['start']:%Y-%m-%d %H:%M} to {gaps['end']:%Y-%m-%d %H:%M} UTC, {note}"
        rows += [row("coverage_gaps", gaps["gaps"], "gaps",
                     f"runs of 5-min slots without a successful snapshot (collection_coverage), {window}",
                     "B8, B10, B12, B15"),
                 row("coverage_missing_hours", round(gaps["missing_hours"], 1), "h",
                     f"missing slots x 5 min, {window}", "B12, B15"),
                 row("coverage_successful_slots", gaps["successful_slots"], "slots", window, "B8"),
                 row("coverage_expected_slots", gaps["expected_slots"], "slots", window, "B8")]
    else:
        rows += [row(key, "", unit, f"not available: {note}", ph) for key, unit, ph in
                 [("coverage_gaps", "gaps", "B8, B10, B12, B15"), ("coverage_missing_hours", "h", "B12, B15"),
                  ("coverage_successful_slots", "slots", "B8"), ("coverage_expected_slots", "slots", "B8")]]
    wind = frames["wind"]
    band = f"{WIND_BAND_M[0]}-{WIND_BAND_M[1]} m"
    if len(wind):
        median_wind, median_speed = wind.wind_speed_ms.median(), wind.velocity.median()
        rows += [row("wind_median_9_11km_kmh", int(round(median_wind * 3.6)), "km/h",
                     f"observations_with_wind, wind_matched = 1, altitude_m {band}: median wind_speed_ms x 3.6",
                     "B9"),
                 row("wind_share_of_ground_speed_pct", int(round(100 * median_wind / median_speed)), "%",
                     f"median wind speed / median ground speed (velocity), same rows ({band})", "B9"),
                 row("wind_observations_9_11km", len(wind), "observations", f"rows with wind, {band}", "B9")]
    else:
        hint = "no wind data: run src/weather.py fetch, then src/prepare.py"
        rows += [row(key, "", unit, hint, "B9") for key, unit in
                 [("wind_median_9_11km_kmh", "km/h"), ("wind_share_of_ground_speed_pct", "%"),
                  ("wind_observations_9_11km", "observations")]]
    buffer_lost = stage.lost.get("neighbour_airport_buffer", np.nan)
    rows += [row("scatter_sample_n", scatter_n, "observations",
                 f"random sample (random_state={RANDOM_STATE}) in altitude_speed_kmh.png", "B7"),
             row("title_map_sample_n", map_n, "observations",
                 f"random sample (random_state={RANDOM_STATE}) in title_map.png", "B1"),
             row("neighbour_buffer_airports", len(frames["neighbours"]), "airports",
                 f"config.json neighbour_airports.idents, radius {config['neighbour_airports']['radius_km']} km, "
                 f"mode {config['neighbour_airports']['mode']}", "B14"),
             row("neighbour_buffer_removed_rows", "" if pd.isna(buffer_lost) else int(buffer_lost), "observations",
                 "integration_audit, stage neighbour_airport_buffer", "B14")]
    # object dtype keeps counts as integers ("2", not "2.0") even when every value is numeric.
    return pd.DataFrame(rows, columns=NUMBER_COLUMNS, dtype=object)


def zone_sample(obs, n):
    data = obs.loc[obs.zone.isin(ZONES)]
    return data.sample(min(n, len(data)), random_state=RANDOM_STATE)


def zone_handles(size):
    from matplotlib.lines import Line2D
    # Legend points are opaque and larger than the translucent plot points.
    return [Line2D([], [], marker="o", linestyle="", markersize=size, markerfacecolor=ZONE_COLORS[z],
                   markeredgecolor="none", alpha=1.0, label=ZONE_LABELS[z]) for z in ZONES]


def altitude_speed_figure(sample, path):
    import matplotlib.pyplot as plt
    from matplotlib.ticker import FuncFormatter
    with plt.rc_context({"font.size": 16, "axes.titlesize": 18, "axes.labelsize": 17, "legend.fontsize": 15,
                         "legend.title_fontsize": 16}):
        fig, ax = plt.subplots(figsize=(10, 7.5), facecolor="white")
        ax.set_facecolor("white")
        # One scatter call in random sample order, so no zone is systematically drawn on top.
        ax.scatter(sample.altitude_m, sample.velocity * 3.6, c=sample.zone.map(ZONE_COLORS), s=16, alpha=0.4,
                   linewidths=0)
        ax.set_xlabel("Flughöhe (m)")
        ax.set_ylabel("Geschwindigkeit über Grund (km/h)")
        ax.xaxis.set_major_formatter(FuncFormatter(swiss))
        ax.yaxis.set_major_formatter(FuncFormatter(swiss))
        ax.grid(color="#E5E5E5", linewidth=0.8)
        ax.set_axisbelow(True)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        ax.legend(handles=zone_handles(12), title="Zone", loc="lower right", frameon=True)
        fig.tight_layout()
        fig.savefig(path, dpi=200, facecolor="white")
        plt.close(fig)


def circle(lat, lon, radius_km, points=181):
    """Latitude/longitude of the points at radius_km great-circle distance (same sphere as prepare.haversine).

    In degrees the circle is about 1/cos(latitude) wider east-west than north-south (one degree of longitude
    is only cos(latitude) x 111 km); the map axes undo this with the same cos(latitude) aspect correction.
    """
    bearing = np.linspace(0, 2 * np.pi, points)
    phi, lam, delta = np.radians(lat), np.radians(lon), radius_km / EARTH_RADIUS_KM
    phi2 = np.arcsin(np.sin(phi) * np.cos(delta) + np.cos(phi) * np.sin(delta) * np.cos(bearing))
    lam2 = lam + np.arctan2(np.sin(bearing) * np.sin(delta) * np.cos(phi), np.cos(delta) - np.sin(phi) * np.sin(phi2))
    return np.degrees(phi2), np.degrees(lam2)


def title_map_figure(sample, airports, config, path):
    import matplotlib.pyplot as plt
    bbox = config["bbox"]
    mid_lat = (bbox["lamin"] + bbox["lamax"]) / 2
    fig = plt.figure(figsize=(7, 5), facecolor=NAVY)  # 1.4 : 1
    ax = fig.add_axes([0, 0, 1, 1], facecolor=NAVY)
    ax.scatter(sample.longitude, sample.latitude, c=sample.zone.map(ZONE_COLORS), s=7, alpha=0.8, linewidths=0)
    for airport in airports.itertuples():
        for radius in (config["near_km"], config["far_km"]):
            lat, lon = circle(airport.latitude_deg, airport.longitude_deg, radius)
            ax.plot(lon, lat, linestyle=(0, (4, 3)), color="white", alpha=0.75, linewidth=1.1)
        ax.plot(airport.longitude_deg, airport.latitude_deg, marker="o", color="white", markersize=4)
        label = airport.iata_code if isinstance(airport.iata_code, str) and airport.iata_code else airport.ident
        ax.annotate(label, (airport.longitude_deg, airport.latitude_deg), xytext=(6, 6), textcoords="offset points",
                    color="white", fontsize=13, fontweight="bold")
    ax.set_xlim(bbox["lomin"], bbox["lomax"])
    ax.set_ylim(bbox["lamin"], bbox["lamax"])
    ax.set_aspect(1 / np.cos(np.radians(mid_lat)))  # 1 km east = 1 km north on the image
    ax.axis("off")
    fig.savefig(path, dpi=200, facecolor=NAVY)
    plt.close(fig)


def main(now=None):
    import matplotlib
    matplotlib.use("Agg")
    config = json.loads((ROOT / "config.json").read_text())
    frames = load_database(ROOT / "data/processed/aircraft.sqlite")
    schedule_path = ROOT / "data/raw/main_schedule.json"
    schedule = json.loads(schedule_path.read_text(encoding="utf-8-sig")) if schedule_path.exists() else None
    figures = ROOT / "outputs/figures/presentation"
    tables = ROOT / "outputs/tables"
    figures.mkdir(parents=True, exist_ok=True)
    tables.mkdir(parents=True, exist_ok=True)
    scatter = zone_sample(frames["observations"], SCATTER_SAMPLE)
    title = zone_sample(frames["observations"], MAP_SAMPLE)
    altitude_speed_figure(scatter, figures / "altitude_speed_kmh.png")
    title_map_figure(title, frames["airports"], config, figures / "title_map.png")
    numbers = presentation_numbers(frames, manifest_entries(ROOT), config, schedule, len(scatter), len(title), now)
    numbers.to_csv(tables / "presentation_numbers.csv", index=False)
    print(numbers.to_string(index=False))
    print(f"Saved {(tables / 'presentation_numbers.csv').relative_to(ROOT)} and 2 figures in "
          f"{figures.relative_to(ROOT)}")


if __name__ == "__main__":
    main()

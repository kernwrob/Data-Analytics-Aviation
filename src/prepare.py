"""Build an audited SQLite analysis database from snapshots your group collected."""
import hashlib
import json
import sqlite3
from contextlib import closing
from pathlib import Path

import numpy as np
import pandas as pd
try:
    from .aircraft_metadata import (normalize_icao24, prepare_metadata, enrich_observations, read_metadata_csv,
                                    load_typecode_categories, UNKNOWN)
    from .weather import load_weather, attach_wind, WIND_COLUMNS
except ImportError:
    from aircraft_metadata import (normalize_icao24, prepare_metadata, enrich_observations, read_metadata_csv,
                                   load_typecode_categories, UNKNOWN)
    from weather import load_weather, attach_wind, WIND_COLUMNS

ROOT = Path(__file__).resolve().parents[1]
FIELDS = ["icao24", "callsign", "origin_country", "time_position", "last_contact",
          "longitude", "latitude", "baro_altitude", "on_ground", "velocity",
          "true_track", "vertical_rate", "sensors", "geo_altitude", "squawk",
          "spi", "position_source", "category"]
BBOX_KEYS = ("lamin", "lamax", "lomin", "lomax")
# ADS-B emitter category (OpenSky state vector field 18); a cross-check only, never the aircraft category.
ADSB_LABELS = {0: "No information", 1: "No ADS-B emitter category", 2: "Light (< 15500 lbs)",
               3: "Small (15500-75000 lbs)", 4: "Large (75000-300000 lbs)", 5: "High vortex large",
               6: "Heavy (> 300000 lbs)", 7: "High performance", 8: "Rotorcraft", 9: "Glider/sailplane",
               10: "Lighter-than-air", 11: "Parachutist/skydiver", 12: "Ultralight/hang-glider/paraglider",
               13: "Reserved", 14: "Unmanned aerial vehicle", 15: "Space vehicle",
               16: "Surface vehicle - emergency", 17: "Surface vehicle - service", 18: "Point obstacle",
               19: "Cluster obstacle", 20: "Line obstacle"}


def haversine(lat, lon, airport_lat, airport_lon):
    lat, lon, airport_lat, airport_lon = map(np.radians, (lat, lon, airport_lat, airport_lon))
    a = np.sin((airport_lat-lat)/2)**2 + np.cos(lat)*np.cos(airport_lat)*np.sin((airport_lon-lon)/2)**2
    return 6371.0088 * 2 * np.arcsin(np.sqrt(np.clip(a, 0, 1)))


def manifest_bboxes(root):
    """Map snapshot path (POSIX, relative to the project) -> bbox in its manifest params."""
    manifest = root / "data/raw/manifest.jsonl"
    boxes = {}
    if manifest.exists():
        for line in manifest.read_text(encoding="utf-8-sig").splitlines():
            if not line.strip():
                continue
            entry = json.loads(line)
            if entry.get("source") == "snapshot" and entry.get("outcome") == "success" and entry.get("path"):
                # Windows collectors wrote backslash paths.
                boxes[entry["path"].replace("\\", "/")] = entry.get("params") or {}
    return boxes


def same_bbox(params, bbox):
    try:
        return all(abs(float(params[key]) - float(bbox[key])) < 1e-9 for key in BBOX_KEYS)
    except (KeyError, TypeError, ValueError):
        return False


def select_snapshots(paths, root, config):
    """Keep only snapshots taken with the current config.json bbox (unless require_current_bbox is false).

    Files without a successful manifest entry are counted and excluded, because their area is unknown.
    """
    require = config.get("require_current_bbox", True)
    boxes = manifest_bboxes(root) if require else {}
    status = {}
    for path in paths:
        key = path.relative_to(root).as_posix()
        if not require:
            status[path] = "kept"
        elif key not in boxes:
            status[path] = "missing_manifest"
        else:
            status[path] = "kept" if same_bbox(boxes[key], config["bbox"]) else "old_bbox"
    counts = {path: count_states(path) for path in paths}
    audit = {"require_current_bbox": bool(require), "snapshots_total": len(paths),
             "rows_total": sum(counts.values())}
    for name in ("kept", "old_bbox", "missing_manifest"):
        chosen = [p for p, s in status.items() if s == name]
        audit[f"snapshots_{name}"] = len(chosen)
        audit[f"rows_{name}"] = sum(counts[p] for p in chosen)
    return [p for p in paths if status[p] == "kept"], audit


def count_states(path):
    return len(json.loads(path.read_text()).get("states") or [])


def read_states(paths):
    rows = []
    for path in paths:
        payload = json.loads(path.read_text())
        for state in payload.get("states") or []:
            if len(state) not in (17, 18):
                raise ValueError(f"Unsupported state vector length in {path.name}: {len(state)}")
            row = dict(zip(FIELDS, state))
            row["snapshot_time"] = payload["time"]
            rows.append(row)
    if not rows:
        raise ValueError("No aircraft observations. Collect snapshots first.")
    # Fixed columns: 17-field (pre-extended) vectors keep an empty category column.
    frame = pd.DataFrame(rows, columns=[*FIELDS, "snapshot_time"])
    frame["category"] = frame["category"].astype("Int64")
    return frame


def clean_and_join(raw, airport_raw, config):
    audit = [{"stage": "raw", "rows": len(raw)}]
    required = ["icao24", "time_position", "last_contact", "latitude", "longitude", "velocity", "geo_altitude"]
    missing = raw.isna().sum().rename("missing").to_frame()
    data = raw.dropna(subset=required).copy()
    data["icao24"] = normalize_icao24(data.icao24)
    audit.append({"stage": "required_fields_present", "rows": len(data)})
    data = data.loc[data.on_ground.eq(False)].copy()
    audit.append({"stage": "airborne", "rows": len(data)})
    data["position_age_s"] = data.snapshot_time - data.time_position
    data["contact_age_s"] = data.snapshot_time - data.last_contact
    data = data.loc[data.position_age_s.between(0, config["max_age_seconds"]) &
                    data.contact_age_s.between(0, config["max_age_seconds"]) &
                    data.latitude.between(-90, 90) & data.longitude.between(-180, 180) &
                    data.velocity.ge(0)].copy()
    audit.append({"stage": "valid_and_fresh", "rows": len(data)})
    data = data.sort_values("snapshot_time").drop_duplicates(["icao24", "time_position"], keep="first").copy()
    audit.append({"stage": "unique_aircraft_position_timestamp", "rows": len(data)})
    airports = airport_raw.loc[airport_raw.ident.isin(config["airport_idents"]),
                               ["ident", "name", "latitude_deg", "longitude_deg", "elevation_ft"]].copy()
    if set(airports.ident) != set(config["airport_idents"]) or airports.ident.duplicated().any():
        raise ValueError("Missing or duplicate selected airport identifiers.")
    if airports[["latitude_deg", "longitude_deg"]].isna().any().any():
        raise ValueError("Selected airport coordinates are missing.")
    if data.empty:
        raise ValueError("All observations were excluded. Inspect coverage and filters.")
    distances = np.column_stack([haversine(data.latitude.to_numpy(), data.longitude.to_numpy(), a.latitude_deg, a.longitude_deg)
                                 for a in airports.itertuples()])
    nearest = distances.argmin(axis=1)
    data["airport_ident"] = airports.ident.to_numpy()[nearest]
    data["distance_km"] = distances[np.arange(len(data)), nearest]
    before = len(data)
    joined = data.merge(airports, left_on="airport_ident", right_on="ident", how="left",
                        validate="many_to_one", indicator=True)
    if len(joined) != before or not joined._merge.eq("both").all():
        raise AssertionError("Airport join changed row count or lost matches.")
    joined = joined.drop(columns=["_merge", "ident", "sensors"])
    joined["zone"] = np.select([joined.distance_km.le(config["near_km"]),
                                joined.distance_km.ge(config["far_km"])], ["near", "far"], default="middle")
    joined["observed_at_utc"] = pd.to_datetime(joined.time_position, unit="s", utc=True).astype(str)
    joined["date_utc"] = pd.to_datetime(joined.time_position, unit="s", utc=True).dt.strftime("%Y-%m-%d")
    local = pd.to_datetime(joined.time_position, unit="s", utc=True).dt.tz_convert("Europe/Zurich")
    joined["hour_local"] = local.dt.hour
    joined["weekday_local"] = local.dt.dayofweek
    joined["speed_kmh"] = joined.velocity * 3.6
    audit.append({"stage": "airport_join", "rows": len(joined), "unmatched": 0, "gained": 0, "lost": 0})
    return joined, airports, pd.DataFrame(audit), missing


def load_pinned_metadata(config):
    """Path of the pinned metadata CSV, or None when config.json leaves "metadata_file" empty."""
    name = (config.get("metadata_file") or "").strip()
    if not name:
        return None
    path = ROOT / name
    if not path.is_file():
        raise SystemExit(f"Pinned metadata file {name} (config.json \"metadata_file\") not found. Copy it from the "
                         "shared folder (docs/METADATA.md) or set \"metadata_file\" to \"\" to run without metadata.")
    expected = (config.get("metadata_sha256") or "").strip().lower()
    if not expected:
        raise SystemExit("config.json \"metadata_sha256\" is empty; the metadata file must be pinned by its SHA-256.")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != expected:
        raise SystemExit(f"{name} has SHA-256 {digest}, but config.json pins {expected}. Wrong or changed file.")
    return path


def main():
    config = json.loads((ROOT / "config.json").read_text())
    paths = sorted((ROOT / "data/raw/opensky").glob("*.json"))
    airport_paths = sorted((ROOT / "data/raw/airports").glob("*.csv"))
    if not paths or not airport_paths:
        raise SystemExit("Run the two collection commands before preparing data.")
    kept_paths, snapshot_audit = select_snapshots(paths, ROOT, config)
    if not kept_paths:
        raise SystemExit("No snapshot matches the current bbox in config.json (see snapshot_bbox_audit). "
                         "Set require_current_bbox to false only for exploratory pilot analysis.")
    # Pin the FIRST airport download for reproducibility; later downloads do not silently alter the join.
    raw = read_states(kept_paths)
    airport_raw = pd.read_csv(airport_paths[0])
    data, airports, audit, missing = clean_and_join(raw, airport_raw, config)
    bbox_stages = pd.DataFrame([
        {"stage": "raw_all_snapshots", "rows": snapshot_audit["rows_total"]},
        {"stage": "current_bbox", "rows": snapshot_audit["rows_kept"],
         "lost": snapshot_audit["rows_total"] - snapshot_audit["rows_kept"]}])
    audit = pd.concat([bbox_stages, audit], ignore_index=True)
    snapshot_audit = pd.DataFrame([snapshot_audit])
    typecodes = load_typecode_categories()  # data/reference/typecode_category.csv next to this code
    metadata_file = load_pinned_metadata(config)
    # Optional source: an empty "metadata_file" keeps all observations with category Unbekannt.
    metadata_raw = read_metadata_csv(metadata_file) if metadata_file else None
    metadata, source_audit, duplicate_audit = prepare_metadata(metadata_raw, typecodes)
    enriched, join_audit = enrich_observations(data, metadata)
    metadata_audit = pd.DataFrame([{**source_audit, **join_audit,
        "pinned_source": metadata_file.relative_to(ROOT).as_posix() if metadata_file else "unavailable",
        "pinned_sha256": config.get("metadata_sha256") or ""}])
    # Optional modelled wind (src/weather.py fetch); absence keeps every observation, wind columns empty.
    weather_paths = sorted((ROOT / "data/raw/weather").glob("*.json"))
    weather = load_weather(weather_paths)
    wind, wind_audit = attach_wind(data, weather)
    wind_audit = pd.DataFrame([{**wind_audit, "weather_files": len(weather_paths)}])
    folder = ROOT / "data/processed"
    folder.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(folder / "aircraft.sqlite")) as db, db:
        db.execute("DROP VIEW IF EXISTS observations_enriched")
        db.execute("DROP VIEW IF EXISTS observations_with_wind")
        airports.to_sql("airports", db, if_exists="replace", index=False)
        data.to_sql("observations", db, if_exists="replace", index=False)
        audit.to_sql("integration_audit", db, if_exists="replace", index=False)
        snapshot_audit.to_sql("snapshot_bbox_audit", db, if_exists="replace", index=False)
        db.execute("CREATE UNIQUE INDEX observation_key ON observations(icao24,time_position)")
        db.execute("CREATE UNIQUE INDEX airport_key ON airports(ident)")
        metadata.to_sql("aircraft_metadata", db, if_exists="replace", index=False)
        metadata_audit.to_sql("metadata_integration_audit", db, if_exists="replace", index=False)
        db.execute("CREATE UNIQUE INDEX aircraft_metadata_key ON aircraft_metadata(icao24)")
        typecodes.to_sql("typecode_categories", db, if_exists="replace", index=False)
        db.execute("CREATE UNIQUE INDEX typecode_categories_key ON typecode_categories(typecode)")
        weather.assign(time_utc=weather.time_utc.astype(str)).to_sql("weather_levels", db, if_exists="replace", index=False)
        wind.to_sql("observation_wind", db, if_exists="replace", index=False)
        wind_audit.to_sql("weather_integration_audit", db, if_exists="replace", index=False)
        db.execute("CREATE UNIQUE INDEX observation_wind_key ON observation_wind(icao24,time_position)")
        db.execute("CREATE VIEW observations_with_wind AS SELECT o.*, " +
                   ", ".join(f"w.{c}" for c in WIND_COLUMNS) +
                   " FROM observations o LEFT JOIN observation_wind w"
                   " ON o.icao24=w.icao24 AND o.time_position=w.time_position")
        # Category derived in SQL (join with the reference table, then the description fallback); it must
        # equal the Python result stored in aircraft_metadata, checked below.
        adsb = " ".join(f"WHEN {code} THEN '{label}'" for code, label in ADSB_LABELS.items())
        db.execute(f"""CREATE VIEW observations_enriched AS
            SELECT o.*, m.aircraft_manufacturer, m.aircraft_model, m.aircraft_typecode,
                   m.aircraft_icao_description,
                   CASE WHEN m.icao24 IS NULL OR m.category_conflict = 1 THEN '{UNKNOWN}'
                        WHEN t.category IS NOT NULL THEN t.category
                        WHEN m.aircraft_icao_description GLOB 'L[0-9]T' THEN 'Turboprop'
                        WHEN m.aircraft_icao_description GLOB 'L[0-9]P'
                          OR m.aircraft_icao_description GLOB 'H[0-9][A-Z]'
                          OR m.aircraft_icao_description GLOB 'G[0-9][A-Z]' THEN 'Sonstige'
                        ELSE '{UNKNOWN}' END AS aircraft_category,
                   CASE WHEN m.icao24 IS NULL OR m.category_conflict = 1 THEN 'none'
                        WHEN t.category IS NOT NULL THEN 'typecode'
                        WHEN m.aircraft_icao_description GLOB 'L[0-9][TP]'
                          OR m.aircraft_icao_description GLOB 'H[0-9][A-Z]'
                          OR m.aircraft_icao_description GLOB 'G[0-9][A-Z]' THEN 'icao_description'
                        ELSE 'none' END AS category_source,
                   CASE o.category {adsb} ELSE NULL END AS adsb_category_label,
                   m.metadata_conflict, CASE WHEN m.icao24 IS NULL THEN 0 ELSE 1 END AS metadata_matched
            FROM observations o
            LEFT JOIN aircraft_metadata m ON o.icao24 = m.icao24
            LEFT JOIN typecode_categories t ON t.typecode = m.aircraft_typecode""")
        mismatch = db.execute(f"""SELECT COUNT(*) FROM observations_enriched e
            LEFT JOIN aircraft_metadata m ON e.icao24 = m.icao24
            WHERE e.aircraft_category <> COALESCE(m.aircraft_category, '{UNKNOWN}')
               OR e.category_source <> COALESCE(m.category_source, 'none')""").fetchone()[0]
        if mismatch:
            raise AssertionError(f"SQL and Python aircraft categories differ for {mismatch} observations.")
        category_audit = pd.read_sql_query("""
            SELECT aircraft_category, category_source, COUNT(*) AS observations,
                   COUNT(DISTINCT icao24) AS aircraft, SUM(metadata_matched) AS metadata_matched_observations
            FROM observations_enriched GROUP BY 1, 2 ORDER BY observations DESC""", db)
        category_audit.to_sql("category_audit", db, if_exists="replace", index=False)
        unmapped = pd.read_sql_query("""
            SELECT e.aircraft_typecode AS typecode, MAX(e.aircraft_model) AS example_model,
                   MAX(e.aircraft_icao_description) AS icao_description, e.aircraft_category AS fallback_category,
                   COUNT(*) AS observations, COUNT(DISTINCT e.icao24) AS aircraft
            FROM observations_enriched e LEFT JOIN typecode_categories t ON t.typecode = e.aircraft_typecode
            WHERE e.metadata_matched = 1 AND COALESCE(e.aircraft_typecode, '') <> '' AND t.typecode IS NULL
            GROUP BY 1, 4 ORDER BY observations DESC, aircraft DESC""", db)
        # Explicit SQL join and aggregation from Python, part of the graded workflow.
        summary = pd.read_sql_query("""
            SELECT a.ident, a.name, o.zone, COUNT(*) AS observations,
                   COUNT(DISTINCT o.icao24) AS aircraft, AVG(o.velocity) AS mean_speed_m_s
            FROM observations o JOIN airports a ON o.airport_ident = a.ident
            GROUP BY a.ident, a.name, o.zone
        """, db)
        aircraft_types = pd.read_sql_query("""
            SELECT COALESCE(NULLIF(aircraft_typecode,''), 'Unbekannt') AS typecode,
                   COALESCE(NULLIF(aircraft_model,''), 'Unbekannt') AS model,
                   aircraft_category, COUNT(*) AS observations, COUNT(DISTINCT icao24) AS aircraft
            FROM observations_enriched GROUP BY 1,2,3 ORDER BY aircraft DESC, observations DESC
        """, db)
        category_summary = pd.read_sql_query("""
            SELECT aircraft_category, COUNT(*) AS observations, COUNT(DISTINCT icao24) AS aircraft,
                   SUM(metadata_matched) AS metadata_matched_observations
            FROM observations_enriched GROUP BY aircraft_category ORDER BY observations DESC
        """, db)
        type_counts = pd.read_sql_query("""
            SELECT COALESCE(NULLIF(aircraft_typecode,''), 'Unbekannt') AS typecode,
                   aircraft_category, COUNT(*) AS observations, COUNT(DISTINCT icao24) AS aircraft
            FROM observations_enriched GROUP BY 1,2 ORDER BY aircraft DESC, observations DESC
        """, db)
    audit.to_csv(folder / "integration_audit.csv", index=False)
    missing.to_csv(folder / "missing_raw.csv")
    summary.to_csv(folder / "sql_summary.csv", index=False)
    metadata_audit.to_csv(folder / "metadata_integration_audit.csv", index=False)
    duplicate_audit.to_csv(folder / "metadata_duplicate_candidates.csv", index=False)
    aircraft_types.to_csv(folder / "aircraft_types.csv", index=False)
    type_counts.to_csv(folder / "aircraft_type_counts.csv", index=False)
    category_summary.to_csv(folder / "aircraft_categories.csv", index=False)
    wind_audit.to_csv(folder / "weather_integration_audit.csv", index=False)
    snapshot_audit.to_csv(folder / "snapshot_bbox_audit.csv", index=False)
    category_audit.to_csv(folder / "category_audit.csv", index=False)
    tables = ROOT / "outputs/tables"
    tables.mkdir(parents=True, exist_ok=True)
    unmapped.to_csv(tables / "unmapped_typecodes.csv", index=False)
    print(snapshot_audit.to_string(index=False))
    print(audit.to_string(index=False))
    print(summary.to_string(index=False))
    print(metadata_audit.T.to_string(header=False))
    print(category_audit.to_string(index=False))
    print(wind_audit.to_string(index=False))


if __name__ == "__main__":
    main()

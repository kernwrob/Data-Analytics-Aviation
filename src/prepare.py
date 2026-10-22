"""Build an audited SQLite analysis database from snapshots your group collected."""
import json
import sqlite3
from contextlib import closing
from pathlib import Path

import numpy as np
import pandas as pd
try:
    from .aircraft_metadata import normalize_icao24, prepare_metadata, enrich_observations
except ImportError:
    from aircraft_metadata import normalize_icao24, prepare_metadata, enrich_observations

ROOT = Path(__file__).resolve().parents[1]
FIELDS = ["icao24", "callsign", "origin_country", "time_position", "last_contact",
          "longitude", "latitude", "baro_altitude", "on_ground", "velocity",
          "true_track", "vertical_rate", "sensors", "geo_altitude", "squawk",
          "spi", "position_source", "category"]


def haversine(lat, lon, airport_lat, airport_lon):
    lat, lon, airport_lat, airport_lon = map(np.radians, (lat, lon, airport_lat, airport_lon))
    a = np.sin((airport_lat-lat)/2)**2 + np.cos(lat)*np.cos(airport_lat)*np.sin((airport_lon-lon)/2)**2
    return 6371.0088 * 2 * np.arcsin(np.sqrt(np.clip(a, 0, 1)))


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


def main():
    config = json.loads((ROOT / "config.json").read_text())
    paths = sorted((ROOT / "data/raw/opensky").glob("*.json"))
    airport_paths = sorted((ROOT / "data/raw/airports").glob("*.csv"))
    if not paths or not airport_paths:
        raise SystemExit("Run the two collection commands before preparing data.")
    # Pin the FIRST airport download for reproducibility; later downloads do not silently alter the join.
    raw = read_states(paths)
    airport_raw = pd.read_csv(airport_paths[0])
    data, airports, audit, missing = clean_and_join(raw, airport_raw, config)
    metadata_paths = sorted((ROOT / "data/raw/aircraft_metadata").glob("*.csv"))
    # Optional source: absence preserves the original observations and analysis.
    metadata_raw = pd.read_csv(metadata_paths[0], dtype=str, keep_default_na=False) if metadata_paths else None
    metadata, source_audit, duplicate_audit = prepare_metadata(metadata_raw)
    enriched, join_audit = enrich_observations(data, metadata)
    metadata_audit = pd.DataFrame([{**source_audit, **join_audit,
        "pinned_source": metadata_paths[0].relative_to(ROOT).as_posix() if metadata_paths else "unavailable"}])
    folder = ROOT / "data/processed"
    folder.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(folder / "aircraft.sqlite")) as db, db:
        db.execute("DROP VIEW IF EXISTS observations_enriched")
        airports.to_sql("airports", db, if_exists="replace", index=False)
        data.to_sql("observations", db, if_exists="replace", index=False)
        audit.to_sql("integration_audit", db, if_exists="replace", index=False)
        db.execute("CREATE UNIQUE INDEX observation_key ON observations(icao24,time_position)")
        db.execute("CREATE UNIQUE INDEX airport_key ON airports(ident)")
        metadata.to_sql("aircraft_metadata", db, if_exists="replace", index=False)
        metadata_audit.to_sql("metadata_integration_audit", db, if_exists="replace", index=False)
        db.execute("CREATE UNIQUE INDEX aircraft_metadata_key ON aircraft_metadata(icao24)")
        db.execute("""CREATE VIEW observations_enriched AS
            SELECT o.*, m.aircraft_manufacturer, m.aircraft_model, m.aircraft_typecode,
                   m.aircraft_icao_description, COALESCE(m.aircraft_category, 'unknown/other') AS aircraft_category,
                   m.metadata_conflict, CASE WHEN m.icao24 IS NULL THEN 0 ELSE 1 END AS metadata_matched
            FROM observations o LEFT JOIN aircraft_metadata m ON o.icao24=m.icao24""")
        # Explicit SQL join and aggregation from Python, part of the graded workflow.
        summary = pd.read_sql_query("""
            SELECT a.ident, a.name, o.zone, COUNT(*) AS observations,
                   COUNT(DISTINCT o.icao24) AS aircraft, AVG(o.velocity) AS mean_speed_m_s
            FROM observations o JOIN airports a ON o.airport_ident = a.ident
            GROUP BY a.ident, a.name, o.zone
        """, db)
        aircraft_types = pd.read_sql_query("""
            SELECT COALESCE(NULLIF(aircraft_typecode,''), 'unknown/other') AS typecode,
                   COALESCE(NULLIF(aircraft_model,''), 'unknown/other') AS model,
                   aircraft_category, COUNT(*) AS observations, COUNT(DISTINCT icao24) AS aircraft
            FROM observations_enriched GROUP BY 1,2,3 ORDER BY aircraft DESC, observations DESC
        """, db)
        category_summary = pd.read_sql_query("""
            SELECT aircraft_category, COUNT(*) AS observations, COUNT(DISTINCT icao24) AS aircraft,
                   SUM(metadata_matched) AS metadata_matched_observations
            FROM observations_enriched GROUP BY aircraft_category ORDER BY observations DESC
        """, db)
        type_counts = pd.read_sql_query("""
            SELECT COALESCE(NULLIF(aircraft_typecode,''), 'unknown/other') AS typecode,
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
    print(audit.to_string(index=False))
    print(summary.to_string(index=False))
    print(metadata_audit.to_string(index=False))


if __name__ == "__main__":
    main()

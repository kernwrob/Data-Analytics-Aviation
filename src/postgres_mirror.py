"""Bonus: mirror the SQLite project database into PostgreSQL with explicit types and keys.

SQLite (data/processed/aircraft.sqlite, built by src/prepare.py) stays the primary database. This script copies
its tables into a PostgreSQL database with explicit column types, primary keys and foreign keys, so the same
data can be queried with joins, aggregations and window functions in PostgreSQL (notebooks/04_postgresql.ipynb).

    python src/postgres_mirror.py                 # rebuild every mirrored table from SQLite
    python src/postgres_mirror.py --sqlite other.sqlite

The connection comes from the environment variable DATABASE_URL or, if unset, from a DATABASE_URL line in the
project's .env file (gitignored), e.g. DATABASE_URL=postgresql+psycopg://localhost/aviation. Never put passwords
in code or notebooks. The rebuild runs in one transaction: if a key is violated or a row count differs from
SQLite, nothing in PostgreSQL changes. See docs/POSTGRESQL.md.
"""
import argparse
import math
import os
import sqlite3
from contextlib import closing
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

# pandas is imported inside the functions; psycopg and sqlalchemy only when connecting, so the schema and
# conversion logic can be tested offline without a server.

ROOT = Path(__file__).resolve().parents[1]
SQLITE_PATH = ROOT / "data/processed/aircraft.sqlite"
ENV_FILE = ROOT / ".env"

TEXT, BIGINT, INTEGER, SMALLINT = "TEXT", "BIGINT", "INTEGER", "SMALLINT"
DOUBLE, TIMESTAMPTZ, DATE = "DOUBLE PRECISION", "TIMESTAMPTZ", "DATE"
INTEGER_TYPES = {BIGINT, INTEGER, SMALLINT}

# Load order: referenced tables before the tables that point to them.
TABLES = {
    "airports": {
        "columns": {"ident": TEXT, "name": TEXT, "latitude_deg": DOUBLE, "longitude_deg": DOUBLE,
                    "elevation_ft": DOUBLE},
        "primary_key": ["ident"], "foreign_keys": [], "required": True},
    "observations": {
        "columns": {"icao24": TEXT, "callsign": TEXT, "origin_country": TEXT, "time_position": BIGINT,
                    "last_contact": BIGINT, "longitude": DOUBLE, "latitude": DOUBLE, "baro_altitude": DOUBLE,
                    "on_ground": SMALLINT, "velocity": DOUBLE, "true_track": DOUBLE, "vertical_rate": DOUBLE,
                    "geo_altitude": DOUBLE, "squawk": TEXT, "spi": SMALLINT, "position_source": SMALLINT,
                    "category": SMALLINT, "snapshot_time": BIGINT, "position_age_s": INTEGER,
                    "contact_age_s": INTEGER, "airport_ident": TEXT, "distance_km": DOUBLE, "name": TEXT,
                    "latitude_deg": DOUBLE, "longitude_deg": DOUBLE, "elevation_ft": DOUBLE, "zone": TEXT,
                    "observed_at_utc": TIMESTAMPTZ, "date_utc": DATE, "hour_local": SMALLINT,
                    "weekday_local": SMALLINT, "speed_kmh": DOUBLE},
        "primary_key": ["icao24", "time_position"],
        "foreign_keys": [(["airport_ident"], "airports", ["ident"])], "required": True},
    "aircraft_metadata": {
        "columns": {"icao24": TEXT, "aircraft_manufacturer": TEXT, "aircraft_model": TEXT,
                    "aircraft_typecode": TEXT, "aircraft_icao_description": TEXT, "aircraft_category": TEXT,
                    "metadata_source_record": TEXT, "metadata_conflict": TEXT},
        "primary_key": ["icao24"], "foreign_keys": [], "required": False},
    "weather_levels": {
        "columns": {"time_utc": TIMESTAMPTZ, "grid_lat": DOUBLE, "grid_lon": DOUBLE, "level_hpa": SMALLINT,
                    "height_m": DOUBLE, "wind_speed_ms": DOUBLE, "wind_dir_deg": DOUBLE},
        "primary_key": ["time_utc", "grid_lat", "grid_lon", "level_hpa"], "foreign_keys": [], "required": False},
    "observation_wind": {
        "columns": {"icao24": TEXT, "time_position": BIGINT, "wind_time_utc": TIMESTAMPTZ,
                    "wind_grid_lat": DOUBLE, "wind_grid_lon": DOUBLE, "wind_level_hpa": DOUBLE,
                    "wind_level_height_m": DOUBLE, "wind_level_gap_m": DOUBLE, "wind_interpolated": SMALLINT,
                    "wind_speed_ms": DOUBLE, "wind_dir_deg": DOUBLE, "tailwind_ms": DOUBLE, "crosswind_ms": DOUBLE,
                    "airspeed_est_ms": DOUBLE, "wind_matched": SMALLINT},
        "primary_key": ["icao24", "time_position"],
        "foreign_keys": [(["icao24", "time_position"], "observations", ["icao24", "time_position"])],
        "required": False},
    "integration_audit": {
        "columns": {"stage": TEXT, "rows": INTEGER, "unmatched": DOUBLE, "gained": DOUBLE, "lost": DOUBLE},
        "primary_key": [], "foreign_keys": [], "required": False},
    "metadata_integration_audit": {
        "columns": {"source_available": SMALLINT, "raw_metadata_rows": INTEGER, "invalid_metadata_keys": INTEGER,
                    "duplicate_keys": INTEGER, "duplicate_rows_removed": INTEGER, "conflicting_keys": INTEGER,
                    "unique_metadata_keys": INTEGER, "observations_before": INTEGER,
                    "observations_after": INTEGER, "matched_observations": INTEGER,
                    "unmatched_observations": INTEGER, "observation_match_fraction": DOUBLE,
                    "distinct_aircraft": INTEGER, "matched_distinct_aircraft": INTEGER,
                    "aircraft_match_fraction": DOUBLE, "gained": INTEGER, "lost": INTEGER, "pinned_source": TEXT},
        "primary_key": [], "foreign_keys": [], "required": False},
    "weather_integration_audit": {
        "columns": {"source_available": SMALLINT, "weather_rows": INTEGER, "observations": INTEGER,
                    "matched_observations": INTEGER, "match_fraction": DOUBLE, "interpolated_share": DOUBLE,
                    "median_level_gap_m": DOUBLE, "share_level_gap_over_500m": DOUBLE,
                    "weather_time_min_utc": TIMESTAMPTZ, "weather_time_max_utc": TIMESTAMPTZ,
                    "weather_files": INTEGER},
        "primary_key": [], "foreign_keys": [], "required": False},
}


class MirrorError(RuntimeError):
    """Configuration or data problem; the message never contains the database password."""


# --- connection settings -----------------------------------------------------------------------------------

def load_database_url(environ=None, env_file=ENV_FILE):
    """DATABASE_URL from the environment, else from a DATABASE_URL=... line in the project's .env file."""
    environ = os.environ if environ is None else environ
    if environ.get("DATABASE_URL", "").strip():
        return environ["DATABASE_URL"].strip()
    env_file = Path(env_file)
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("export "):
                line = line[len("export "):].strip()
            key, sep, value = line.partition("=")
            if line.startswith("#") or not sep or key.strip() != "DATABASE_URL":
                continue
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
                value = value[1:-1]
            if value:
                return value
    raise MirrorError("DATABASE_URL is not set. Set it in the environment or add a line "
                      "DATABASE_URL=postgresql+psycopg://localhost/aviation to the project's .env file "
                      "(see docs/POSTGRESQL.md).")


def redact(url):
    """URL with the password replaced, safe to print."""
    parts = urlsplit(url)
    if parts.password is None:
        return url
    host = parts.hostname or ""
    if parts.port:
        host += f":{parts.port}"
    return urlunsplit(parts._replace(netloc=f"{parts.username or ''}:***@{host}"))


def psycopg_url(url):
    """psycopg expects postgresql://; SQLAlchemy URLs name the driver (postgresql+psycopg://)."""
    scheme, sep, rest = url.partition("://")
    if not sep or scheme.split("+")[0] not in {"postgresql", "postgres"}:
        raise MirrorError("DATABASE_URL must start with postgresql:// or postgresql+psycopg://.")
    return "postgresql://" + rest


def sqlalchemy_url(url):
    """Pin the psycopg (v3) driver; plain postgresql:// would make SQLAlchemy look for psycopg2."""
    return "postgresql+psycopg://" + psycopg_url(url).partition("://")[2]


def engine(url=None):
    """SQLAlchemy engine for notebooks: notebooks/04_postgresql.ipynb uses this, never a literal URL."""
    from sqlalchemy import create_engine
    return create_engine(sqlalchemy_url(url or load_database_url()))


# --- schema -----------------------------------------------------------------------------------------------

def create_table_sql(table):
    spec = TABLES[table]
    lines = [f"    {column} {pg_type}" + (" NOT NULL" if column in spec["primary_key"] else "")
             for column, pg_type in spec["columns"].items()]
    if spec["primary_key"]:
        lines.append(f"    PRIMARY KEY ({', '.join(spec['primary_key'])})")
    for columns, parent, parent_columns in spec["foreign_keys"]:
        lines.append(f"    FOREIGN KEY ({', '.join(columns)}) REFERENCES {parent} ({', '.join(parent_columns)})")
    return f"CREATE TABLE {table} (\n" + ",\n".join(lines) + "\n)"


def check_schema():
    """Every key column exists and every foreign key points to an earlier table's primary key."""
    order = list(TABLES)
    for table, spec in TABLES.items():
        missing = [c for c in spec["primary_key"] if c not in spec["columns"]]
        if missing:
            raise MirrorError(f"{table}: primary key columns {missing} are not defined.")
        for columns, parent, parent_columns in spec["foreign_keys"]:
            if order.index(parent) >= order.index(table):
                raise MirrorError(f"{table}: {parent} must be loaded first.")
            if parent_columns != TABLES[parent]["primary_key"] or any(c not in spec["columns"] for c in columns):
                raise MirrorError(f"{table}: foreign key {columns} -> {parent}{parent_columns} is invalid.")
            if [spec["columns"][c] for c in columns] != [TABLES[parent]["columns"][c] for c in parent_columns]:
                raise MirrorError(f"{table}: foreign key column types differ from {parent}.")


# --- data -------------------------------------------------------------------------------------------------

def read_sqlite(path=SQLITE_PATH):
    """Read every mirrored table that exists; the columns must match the explicit schema exactly."""
    import pandas as pd
    path = Path(path)
    if not path.exists():
        raise MirrorError(f"{path} not found. Run src/prepare.py first.")
    frames = {}
    with closing(sqlite3.connect(path)) as db:
        present = {name for (name,) in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        for table, spec in TABLES.items():
            if table not in present:
                if spec["required"]:
                    raise MirrorError(f"Required table {table} is missing in {path.name}. Run src/prepare.py.")
                continue
            frame = pd.read_sql_query(f'SELECT * FROM "{table}"', db)
            unknown = [c for c in frame.columns if c not in spec["columns"]]
            absent = [c for c in spec["columns"] if c not in frame.columns]
            if unknown or absent:
                raise MirrorError(f"{table}: SQLite columns differ from the PostgreSQL schema "
                                  f"(not in schema: {unknown}, not in SQLite: {absent}). Update TABLES.")
            frames[table] = frame[list(spec["columns"])]
    return frames


def _convert(value, pg_type, column):
    import pandas as pd
    if value is None or (isinstance(value, float) and math.isnan(value)) or value is pd.NaT:
        return None
    if pg_type in INTEGER_TYPES:
        number = float(value)
        if not number.is_integer():
            raise MirrorError(f"{column}: {value!r} is not an integer.")
        return int(number)
    if pg_type == DOUBLE:
        return float(value)
    if pg_type == TIMESTAMPTZ:
        stamp = pd.Timestamp(value)
        return (stamp.tz_localize("UTC") if stamp.tzinfo is None else stamp.tz_convert("UTC")).to_pydatetime()
    if pg_type == DATE:
        return pd.Timestamp(value).date()
    return str(value)


def to_copy_rows(table, frame):
    """Python values per row in schema order: NaN -> NULL, whole floats -> int, text times -> datetime/date."""
    columns = TABLES[table]["columns"]
    converted = []
    for record in frame[list(columns)].itertuples(index=False, name=None):
        converted.append(tuple(_convert(value, pg_type, column)
                               for value, (column, pg_type) in zip(record, columns.items())))
    return converted


def mirror(sqlite_path=SQLITE_PATH, url=None):
    """Rebuild the mirrored tables in PostgreSQL in one transaction; returns rows per table in both databases."""
    import psycopg
    check_schema()
    url = url or load_database_url()
    frames = read_sqlite(sqlite_path)
    rows = {table: to_copy_rows(table, frame) for table, frame in frames.items()}
    counts = []
    try:
        with psycopg.connect(psycopg_url(url)) as connection:   # commits on success, rolls back on error
            with connection.cursor() as cursor:
                for table in reversed(TABLES):  # also drops tables that SQLite no longer has, so nothing stale stays
                    cursor.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
                for table, values in rows.items():
                    cursor.execute(create_table_sql(table))
                    columns = ", ".join(TABLES[table]["columns"])
                    with cursor.copy(f"COPY {table} ({columns}) FROM STDIN") as copy:
                        for row in values:
                            copy.write_row(row)
                    postgres_rows = cursor.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                    counts.append({"table": table, "sqlite_rows": len(frames[table]), "postgres_rows": postgres_rows})
                    if postgres_rows != len(frames[table]):
                        raise MirrorError(f"{table}: {postgres_rows} rows in PostgreSQL, {len(frames[table])} in SQLite.")
                cursor.execute("ANALYZE")
    except psycopg.Error as error:
        # psycopg messages name the server and the failed constraint, never the password.
        raise MirrorError(f"PostgreSQL rejected the mirror, nothing was changed: {error}") from None
    return counts


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--sqlite", type=Path, default=SQLITE_PATH, help="SQLite file (default: project database)")
    args = parser.parse_args()
    try:
        url = load_database_url()
        print(f"Mirroring {args.sqlite} into {redact(url)}")
        counts = mirror(args.sqlite, url)
    except MirrorError as error:
        raise SystemExit(str(error))
    width = max(len(c["table"]) for c in counts)
    print(f"{'table':<{width}}  sqlite_rows  postgres_rows")
    for c in counts:
        print(f"{c['table']:<{width}}  {c['sqlite_rows']:>11}  {c['postgres_rows']:>13}")
    print("Row counts match.")


if __name__ == "__main__":
    main()

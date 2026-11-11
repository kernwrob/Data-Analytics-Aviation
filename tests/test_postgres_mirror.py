"""Offline checks for the PostgreSQL mirror: type/key mapping, conversion and settings. No server needed."""
import contextlib
import copy
import io
import json
import re
import sqlite3
import tempfile
import unittest
from contextlib import closing
from datetime import date, datetime, timezone
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd
from src import postgres_mirror as mirror
from src import prepare

ROOT = Path(__file__).resolve().parents[1]
T0 = 1793527200  # 2026-11-01T10:00:00Z


def build_project_database(root, with_weather):
    """Run the real prepare.main on a two-aircraft fixture; optionally with one wind file."""
    for folder in ("opensky", "airports", "weather"):
        (root / "data/raw" / folder).mkdir(parents=True)
    (root / "config.json").write_text(json.dumps(
        {"airport_idents": ["TEST"], "max_age_seconds": 60, "near_km": 30, "far_km": 60}))
    pd.DataFrame({"ident": ["TEST"], "name": ["Test"], "latitude_deg": [47.], "longitude_deg": [8.],
                  "elevation_ft": [100.]}).to_csv(root / "data/raw/airports/a.csv", index=False)
    states = [["abcdef", "T1", "X", T0, T0, 8.0, 47.0, 1400., False, 100., 180., 0., None, 1500., None, False, 0, 3],
              ["123456", "T2", "X", T0, T0, 8.0, 47.0, 10300., False, 230., 90., 0., None, 10400., None, False, 0, 6]]
    (root / "data/raw/opensky/20261101T100000000000Z.json").write_text(json.dumps({"time": T0, "states": states}))
    if with_weather:
        hourly = {"time": ["2026-11-01T10:00"], "wind_speed_850hPa": [10.0], "wind_direction_850hPa": [0.0],
                  "geopotential_height_850hPa": [1500.0], "wind_speed_250hPa": [40.0],
                  "wind_direction_250hPa": [270.0], "geopotential_height_250hPa": [10400.0]}
        (root / "data/raw/weather/x.json").write_text(json.dumps([{"latitude": 47.0, "longitude": 8.0,
                                                                   "hourly": hourly}]))
    with patch.object(prepare, "ROOT", root), contextlib.redirect_stdout(io.StringIO()):
        prepare.main()
    return root / "data/processed/aircraft.sqlite"


class SchemaTests(unittest.TestCase):
    def test_types_and_keys_in_create_statements(self):
        observations = mirror.create_table_sql("observations")
        for fragment in ("icao24 TEXT NOT NULL", "time_position BIGINT NOT NULL", "velocity DOUBLE PRECISION",
                         "observed_at_utc TIMESTAMPTZ", "date_utc DATE", "on_ground SMALLINT",
                         "PRIMARY KEY (icao24, time_position)",
                         "FOREIGN KEY (airport_ident) REFERENCES airports (ident)"):
            self.assertIn(fragment, observations)
        wind = mirror.create_table_sql("observation_wind")
        self.assertIn("FOREIGN KEY (icao24, time_position) REFERENCES observations (icao24, time_position)", wind)
        self.assertIn("wind_time_utc TIMESTAMPTZ", wind)
        self.assertIn("PRIMARY KEY (ident)", mirror.create_table_sql("airports"))
        self.assertIn("PRIMARY KEY (icao24)", mirror.create_table_sql("aircraft_metadata"))
        self.assertIn("PRIMARY KEY (time_utc, grid_lat, grid_lon, level_hpa)", mirror.create_table_sql("weather_levels"))
        self.assertNotIn("PRIMARY KEY", mirror.create_table_sql("integration_audit"))

    def test_schema_is_consistent_and_parents_load_first(self):
        mirror.check_schema()
        order = list(mirror.TABLES)
        for table, spec in mirror.TABLES.items():
            for _, parent, _ in spec["foreign_keys"]:
                self.assertLess(order.index(parent), order.index(table))
        reordered = {"observations": mirror.TABLES["observations"], "airports": mirror.TABLES["airports"]}
        with patch.object(mirror, "TABLES", reordered), self.assertRaises(mirror.MirrorError):
            mirror.check_schema()
        wrong_target = copy.deepcopy(mirror.TABLES)
        wrong_target["observation_wind"]["foreign_keys"] = [(["icao24"], "observations", ["icao24"])]
        with patch.object(mirror, "TABLES", wrong_target), self.assertRaises(mirror.MirrorError):
            mirror.check_schema()

    def test_schema_matches_every_table_prepare_writes(self):
        for with_weather in (True, False):
            with self.subTest(with_weather=with_weather), tempfile.TemporaryDirectory() as tmp:
                path = build_project_database(Path(tmp), with_weather)
                frames = mirror.read_sqlite(path)
                self.assertEqual(list(frames), list(mirror.TABLES))
                for table, frame in frames.items():
                    rows = mirror.to_copy_rows(table, frame)
                    self.assertEqual(len(rows), len(frame))
                wind = dict(zip(mirror.TABLES["observation_wind"]["columns"],
                                mirror.to_copy_rows("observation_wind", frames["observation_wind"])[0]))
                if with_weather:
                    self.assertEqual(wind["wind_time_utc"], datetime(2026, 11, 1, 10, tzinfo=timezone.utc))
                    self.assertEqual(wind["wind_matched"], 1)
                else:
                    self.assertIsNone(wind["wind_time_utc"])
                    self.assertEqual(wind["wind_matched"], 0)
                obs = dict(zip(mirror.TABLES["observations"]["columns"],
                               mirror.to_copy_rows("observations", frames["observations"])[0]))
                self.assertEqual(obs["date_utc"], date(2026, 11, 1))
                self.assertIsInstance(obs["time_position"], int)

    def test_unknown_or_missing_columns_and_required_tables_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "x.sqlite"
            with closing(sqlite3.connect(path)) as db, db:
                db.execute("CREATE TABLE airports (ident TEXT, name TEXT, latitude_deg REAL, longitude_deg REAL, "
                           "elevation_ft REAL, extra TEXT)")
            with self.assertRaisesRegex(mirror.MirrorError, "extra"):
                mirror.read_sqlite(path)
            with closing(sqlite3.connect(path)) as db, db:
                db.execute("DROP TABLE airports")
                db.execute("CREATE TABLE airports (ident TEXT, name TEXT, latitude_deg REAL, longitude_deg REAL, "
                           "elevation_ft REAL)")
            with self.assertRaisesRegex(mirror.MirrorError, "observations"):
                mirror.read_sqlite(path)


class ConversionTests(unittest.TestCase):
    def test_missing_values_integers_times_and_dates(self):
        frame = pd.DataFrame({
            "time_utc": ["2026-10-22 13:00:00+00:00", None], "grid_lat": [46.5, np.nan], "grid_lon": [8.0, 8.5],
            "level_hpa": [250.0, np.nan], "height_m": [10400.0, 1.0], "wind_speed_ms": [40, 3],
            "wind_dir_deg": [270, 90]})
        first, second = mirror.to_copy_rows("weather_levels", frame)
        self.assertEqual(first[0], datetime(2026, 10, 22, 13, tzinfo=timezone.utc))
        self.assertEqual(first[3], 250)
        self.assertIsInstance(first[3], int)
        self.assertIsInstance(first[5], float)
        self.assertEqual((second[0], second[1], second[3]), (None, None, None))
        self.assertEqual(mirror._convert("2026-11-01", mirror.DATE, "date_utc"), date(2026, 11, 1))
        self.assertEqual(mirror._convert(" A ", mirror.TEXT, "callsign"), " A ")
        with self.assertRaises(mirror.MirrorError):
            mirror._convert(2.5, mirror.BIGINT, "time_position")


class SettingsTests(unittest.TestCase):
    def test_environment_wins_then_dotenv_then_clear_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            env_file = Path(tmp) / ".env"
            env_file.write_text("# local settings\nOTHER=1\nexport DATABASE_URL='postgresql+psycopg://u:secret@db/x'\n")
            self.assertEqual(mirror.load_database_url({"DATABASE_URL": "postgresql://h/y"}, env_file),
                             "postgresql://h/y")
            self.assertEqual(mirror.load_database_url({}, env_file), "postgresql+psycopg://u:secret@db/x")
            env_file.write_text("#DATABASE_URL=postgresql://commented/out\n")
            with self.assertRaises(mirror.MirrorError) as raised:
                mirror.load_database_url({}, env_file)
            self.assertIn("DATABASE_URL", str(raised.exception))
            with self.assertRaises(mirror.MirrorError):
                mirror.load_database_url({"DATABASE_URL": "  "}, Path(tmp) / "missing.env")

    def test_urls_are_normalized_and_never_printed_with_password(self):
        url = "postgresql+psycopg://postgres:p%40ss@localhost:5432/aviation"
        self.assertEqual(mirror.redact(url), "postgresql+psycopg://postgres:***@localhost:5432/aviation")
        self.assertEqual(mirror.redact("postgresql://localhost/aviation"), "postgresql://localhost/aviation")
        self.assertEqual(mirror.psycopg_url(url), "postgresql://postgres:p%40ss@localhost:5432/aviation")
        self.assertEqual(mirror.sqlalchemy_url("postgresql://localhost/aviation"),
                         "postgresql+psycopg://localhost/aviation")
        with self.assertRaises(mirror.MirrorError):
            mirror.psycopg_url("mysql://localhost/aviation")

    def test_no_credentials_in_code_or_notebook(self):
        credential = re.compile(r"postgres(?:ql)?(?:\+\w+)?://[^/\s:@]+:[^/\s@]+@")
        for path in (ROOT / "src/postgres_mirror.py", ROOT / "notebooks/04_postgresql.ipynb"):
            self.assertIsNone(credential.search(path.read_text(encoding="utf-8")), path.name)


if __name__ == "__main__":
    unittest.main()

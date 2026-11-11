"""Offline checks for the optional wind source; no network, fixtures never touch project data."""
import contextlib
import io
import json
import sqlite3
import tempfile
import unittest
from contextlib import closing
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import Mock, patch

import numpy as np
import pandas as pd
from src import prepare, weather

T0 = 1793527200  # 2026-11-01T10:00:00Z


def payload(lat, lon, hours=("2026-11-01T10:00", "2026-11-01T11:00")):
    """Open-Meteo style item: 850 hPa at ~1500 m (wind from north), 250 hPa at ~10400 m (wind from west)."""
    n = len(hours)
    return {"latitude": lat, "longitude": lon, "hourly": {
        "time": list(hours),
        "wind_speed_850hPa": [10.0] * n, "wind_direction_850hPa": [0.0] * n,
        "geopotential_height_850hPa": [1500.0] * n,
        "wind_speed_250hPa": [40.0] * n, "wind_direction_250hPa": [270.0] * n,
        "geopotential_height_250hPa": [10400.0] * n}}


class WindMathTests(unittest.TestCase):
    def test_components(self):
        # Wind from north (0 deg), aircraft flying south (180 deg): full tailwind.
        tail, cross, air = weather.wind_components(np.array([200.0]), np.array([180.0]),
                                                   np.array([10.0]), np.array([0.0]))
        self.assertAlmostEqual(tail[0], 10.0)
        self.assertAlmostEqual(cross[0], 0.0, places=6)
        self.assertAlmostEqual(air[0], 190.0)
        # Wind from west (270 deg), aircraft flying north: wind pushes to the right (east).
        tail, cross, _ = weather.wind_components(np.array([200.0]), np.array([0.0]),
                                                 np.array([10.0]), np.array([270.0]))
        self.assertAlmostEqual(tail[0], 0.0, places=6)
        self.assertAlmostEqual(cross[0], 10.0)

    def test_grid_covers_bbox(self):
        points = weather.grid_points({"lamin": 45.7, "lamax": 48.0, "lomin": 5.8, "lomax": 10.6}, 0.5)
        self.assertEqual(len(points), 50)
        self.assertEqual(points[0], (45.95, 6.05))


class WindJoinTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "w.json"
        self.path.write_text(json.dumps([payload(47.0, 8.0), payload(46.0, 6.5)]))

    def test_level_hour_point_and_rows_preserved(self):
        w = weather.load_weather([self.path])
        self.assertEqual(len(w), 2 * 2 * 2)
        obs = pd.DataFrame({
            "icao24": ["a", "b", "c", "d"],
            "time_position": [T0 + 600, T0 + 2400, T0, T0 + 86400],  # 10:10->10h, 10:40->11h, 10h, next day
            "latitude": [47.1, 47.0, 46.1, 47.0], "longitude": [8.1, 8.0, 6.4, 8.0],
            "geo_altitude": [1200.0, 11000.0, 1600.0, 1500.0],
            "velocity": [100.0, 230.0, 120.0, 100.0], "true_track": [180.0, 90.0, np.nan, 0.0]}, index=[7, 3, 9, 1])
        result, audit = weather.attach_wind(obs, w)
        self.assertEqual(result.icao24.tolist(), ["a", "b", "c", "d"])
        self.assertEqual(result.wind_matched.tolist(), [1, 1, 1, 0])
        self.assertEqual(result.wind_level_hpa.tolist()[:3], [850, 250, 850])
        self.assertEqual(result.wind_grid_lat.tolist()[:3], [47.0, 47.0, 46.0])
        self.assertTrue(result.wind_time_utc.iloc[1].startswith("2026-11-01 11:00"))
        self.assertAlmostEqual(result.tailwind_ms.iloc[0], 10.0)   # from north, flying south
        self.assertAlmostEqual(result.tailwind_ms.iloc[1], 40.0)   # from west, flying east
        self.assertTrue(np.isnan(result.tailwind_ms.iloc[2]))      # no track, no component
        self.assertAlmostEqual(result.wind_level_gap_m.iloc[0], 300.0)   # below the lowest level: edge
        self.assertEqual(result.wind_interpolated.tolist(), [0, 0, 1, 0])
        self.assertEqual(audit["matched_observations"], 3)
        self.assertAlmostEqual(audit["match_fraction"], 0.75)

    def test_vertical_interpolation_uses_components(self):
        # Halfway between 850 hPa (1500 m, 10 m/s from N) and 250 hPa (10400 m, 40 m/s from W).
        obs = pd.DataFrame({"icao24": ["m"], "time_position": [T0], "latitude": [47.0], "longitude": [8.0],
                            "geo_altitude": [5950.0], "velocity": [200.0], "true_track": [90.0]})
        result, audit = weather.attach_wind(obs, weather.load_weather([self.path]))
        row = result.iloc[0]
        self.assertEqual(row.wind_interpolated, 1)
        self.assertEqual(row.wind_level_gap_m, 0.0)
        self.assertAlmostEqual(row.wind_speed_ms, np.hypot(20.0, 5.0))
        self.assertAlmostEqual(row.wind_dir_deg, (np.degrees(np.arctan2(-20.0, 5.0))) % 360)
        self.assertAlmostEqual(row.tailwind_ms, 20.0)
        self.assertEqual(audit["interpolated_share"], 1.0)

    def test_no_weather_keeps_rows(self):
        obs = pd.DataFrame({"icao24": ["a"], "time_position": [T0], "latitude": [47.0], "longitude": [8.0],
                            "geo_altitude": [1000.0], "velocity": [100.0], "true_track": [0.0]})
        result, audit = weather.attach_wind(obs, weather.load_weather([]))
        self.assertEqual(len(result), 1)
        self.assertEqual(result.wind_matched.tolist(), [0])
        self.assertFalse(audit["source_available"])


class FetchTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        (self.root / "data/raw/opensky").mkdir(parents=True)
        today = datetime.now(timezone.utc).date()
        self.yesterday = today - timedelta(days=1)
        for day in (self.yesterday, today):
            (self.root / f"data/raw/opensky/{day:%Y%m%d}T120000000000Z.json").write_text("{}")
        self.config = {"bbox": {"lamin": 46.0, "lamax": 47.0, "lomin": 7.0, "lomax": 8.0},
                       "weather": {"grid_step_deg": 0.5, "pressure_levels": [850, 250]}}
        patcher = patch.object(weather, "ROOT", self.root)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_fetch_saves_raw_logs_and_skips_done_and_today(self):
        items = [payload(46.25, 7.25), payload(46.25, 7.75), payload(46.75, 7.25), payload(46.75, 7.75)]
        response = Mock(status_code=200, content=json.dumps(items).encode())
        response.json.return_value = items
        response.raise_for_status.return_value = None
        with patch.object(weather.requests, "get", return_value=response) as get, \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertTrue(weather.fetch(self.config))
            self.assertTrue(weather.fetch(self.config))   # second run: nothing left to do
        self.assertEqual(get.call_count, 1)
        params = get.call_args.kwargs["params"]
        self.assertEqual(params["start_date"], self.yesterday.isoformat())
        self.assertIn("geopotential_height_250hPa", params["hourly"])
        self.assertEqual(len(params["latitude"].split(",")), 4)
        entries = [json.loads(l) for l in (self.root / "data/raw/manifest.jsonl").read_text().splitlines()]
        self.assertEqual([e["outcome"] for e in entries], ["success"])
        self.assertTrue((self.root / entries[0]["path"]).exists())

    def test_failure_is_logged_not_saved(self):
        response = Mock(status_code=429)
        response.raise_for_status.side_effect = Exception("too many")
        with patch.object(weather.requests, "get", return_value=response), \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertFalse(weather.fetch(self.config))
        entries = [json.loads(l) for l in (self.root / "data/raw/manifest.jsonl").read_text().splitlines()]
        self.assertEqual(entries[0]["outcome"], "failure")
        self.assertFalse((self.root / "data/raw/weather").exists())


class PrepareIntegrationTests(unittest.TestCase):
    def test_prepare_builds_wind_table_and_view(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for folder in ("opensky", "airports", "weather"):
                (root / "data/raw" / folder).mkdir(parents=True)
            (root / "config.json").write_text(json.dumps(
                {"airport_idents": ["TEST"], "max_age_seconds": 60, "near_km": 30, "far_km": 60}))
            pd.DataFrame({"ident": ["TEST"], "name": ["Test"], "latitude_deg": [47.], "longitude_deg": [8.],
                          "elevation_ft": [100.]}).to_csv(root / "data/raw/airports/a.csv", index=False)
            states = [["abcdef", "T1", "X", T0, T0, 8.0, 47.0, 1400., False, 100., 180., 0., None, 1500., None, False, 0, 3],
                      ["123456", "T2", "X", T0, T0, 8.0, 47.0, 10300., False, 230., 90., 0., None, 10400., None, False, 0, 6]]
            (root / "data/raw/opensky/20261101T100000000000Z.json").write_text(json.dumps({"time": T0, "states": states}))
            (root / "data/raw/weather/x.json").write_text(json.dumps([payload(47.0, 8.0)]))
            with patch.object(prepare, "ROOT", root), contextlib.redirect_stdout(io.StringIO()):
                prepare.main()
            with closing(sqlite3.connect(root / "data/processed/aircraft.sqlite")) as db:
                rows = db.execute("""SELECT icao24, wind_level_hpa, ROUND(tailwind_ms, 3), wind_matched
                                     FROM observations_with_wind ORDER BY icao24""").fetchall()
                n_obs = db.execute("SELECT COUNT(*) FROM observations").fetchone()[0]
                audit = db.execute("SELECT matched_observations FROM weather_integration_audit").fetchone()[0]
            self.assertEqual(n_obs, 2)
            self.assertEqual(rows, [("123456", 250, 40.0, 1), ("abcdef", 850, 10.0, 1)])
            self.assertEqual(audit, 2)


if __name__ == "__main__":
    unittest.main()

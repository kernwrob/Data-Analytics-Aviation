"""Offline check of src/presentation_figures.py on a tiny fixture project (prepare.main + manifest + schedule)."""
import contextlib
import io
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pandas as pd
from tests.cleaning_config import with_cleaning
from src import prepare
from src import presentation_figures as figures

BBOX = {"lamin": 45.6, "lamax": 48.2, "lomin": 5.2, "lomax": 10.6}
T0 = 1794000000  # 2026-11-06T21:20:00Z, a 5-minute slot
EXPECTED_KEYS = ["successful_queries", "raw_rows", "clean_observations", "distinct_aircraft", "observed_utc_dates",
                 "type_join_match_pct", "type_join_aircraft_match_pct", "unknown_category_pct", "coverage_gaps",
                 "coverage_missing_hours", "coverage_successful_slots", "coverage_expected_slots",
                 "wind_median_9_11km_kmh", "wind_share_of_ground_speed_pct", "wind_observations_9_11km",
                 "scatter_sample_n", "title_map_sample_n", "neighbour_buffer_airports",
                 "neighbour_buffer_removed_rows"]


def state(icao24, t, lon, altitude, velocity):
    return [icao24, "T", "X", t, t, lon, 47.0, altitude, False, velocity, 90., 0., None, altitude, None, False, 0, 3]


def iso(seconds):
    return datetime.fromtimestamp(seconds, timezone.utc).isoformat()


class PresentationFiguresTests(unittest.TestCase):
    def build(self, root, with_weather):
        for folder in ("opensky", "airports", "weather"):
            (root / "data/raw" / folder).mkdir(parents=True)
        (root / "config.json").write_text(json.dumps(with_cleaning(
            {"bbox": BBOX, "airport_idents": ["TEST"], "max_age_seconds": 60, "near_km": 30, "far_km": 60,
             "interval_seconds": 300, "require_current_bbox": True, "metadata_file": "", "metadata_sha256": ""})))
        pd.DataFrame({"ident": ["TEST"], "name": ["Test"], "iata_code": ["TST"], "latitude_deg": [47.],
                      "longitude_deg": [8.], "elevation_ft": [100.]}).to_csv(root / "data/raw/airports/a.csv",
                                                                             index=False)
        # Slots T0, T0+300 (missed: no request), T0+600 (failed), T0+900. Near, middle and far aircraft.
        entries = []
        for t in (T0, T0 + 900):
            path = f"data/raw/opensky/{t}.json"
            states = [state(f"a{t % 100000:05d}", t, 8.1, 1000., 80.), state(f"b{t % 100000:05d}", t, 8.6, 5000., 180.),
                      state(f"c{t % 100000:05d}", t, 9.2, 10300., 230.)]
            (root / path).write_text(json.dumps({"time": t, "states": states}))
            entries.append({"source": "snapshot", "source_url": "https://opensky-network.org/api/states/all",
                            "params": {**BBOX, "extended": 1}, "attempted_at_utc": iso(t), "retrieved_at_utc": iso(t),
                            "status": 200, "outcome": "success", "path": path, "state_count": 3})
        entries.insert(1, {"source": "snapshot", "source_url": "https://opensky-network.org/api/states/all",
                           "params": {**BBOX, "extended": 1}, "attempted_at_utc": iso(T0 + 600),
                           "retrieved_at_utc": iso(T0 + 600), "status": 503, "outcome": "failure"})
        (root / "data/raw/manifest.jsonl").write_text("".join(json.dumps(e) + "\n" for e in entries))
        (root / "data/raw/main_schedule.json").write_text(json.dumps(
            {"start_utc": iso(T0), "end_utc": iso(T0 + 1200), "interval_seconds": 300, "days": 1}))
        if with_weather:
            first = pd.Timestamp(T0, unit="s").floor("h")
            hours = [f"{first + pd.to_timedelta(h, unit="h"):%Y-%m-%dT%H:%M}" for h in (0, 1)]
            hourly = {"time": hours, "wind_speed_850hPa": [10.0] * 2, "wind_direction_850hPa": [270.0] * 2,
                      "geopotential_height_850hPa": [1500.0] * 2, "wind_speed_250hPa": [40.0] * 2,
                      "wind_direction_250hPa": [270.0] * 2, "geopotential_height_250hPa": [10300.0] * 2}
            (root / "data/raw/weather/w.json").write_text(json.dumps(
                [{"latitude": 47.0, "longitude": lon, "hourly": hourly} for lon in (8.0, 8.5, 9.0)]))
        with patch.object(prepare, "ROOT", root), contextlib.redirect_stdout(io.StringIO()):
            prepare.main()

    def run_script(self, root):
        with patch.object(figures, "ROOT", root), contextlib.redirect_stdout(io.StringIO()):
            figures.main(now=datetime(2026, 12, 1, tzinfo=timezone.utc))
        return pd.read_csv(root / "outputs/tables/presentation_numbers.csv", dtype=str, keep_default_na=False).set_index("key")

    def test_all_numbers_and_both_figures_are_written(self):
        for with_weather in (True, False):
            with self.subTest(with_weather=with_weather), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                self.build(root, with_weather)
                numbers = self.run_script(root)
                self.assertEqual(numbers.index.tolist(), EXPECTED_KEYS)
                self.assertEqual(list(numbers.reset_index().columns), figures.NUMBER_COLUMNS)
                self.assertTrue(numbers.placeholder.str.startswith("B").all())
                value = numbers.value
                self.assertEqual((value["successful_queries"], value["raw_rows"], value["clean_observations"],
                                  value["distinct_aircraft"]), ("2", "6", "6", "6"))
                # Window T0 .. planned end T0+1200: slots T0+300 and T0+600 form one gap of 10 minutes.
                self.assertEqual((value["coverage_gaps"], value["coverage_expected_slots"],
                                  value["coverage_successful_slots"]), ("1", "4", "2"))
                self.assertAlmostEqual(float(value["coverage_missing_hours"]), 0.2)
                self.assertEqual(value["unknown_category_pct"], "100.0")
                self.assertEqual((value["scatter_sample_n"], value["title_map_sample_n"]), ("6", "6"))
                if with_weather:
                    # Both 10300 m aircraft sit exactly on the 250 hPa level: 40 m/s = 144 km/h, 40/230 = 17 %.
                    self.assertEqual((value["wind_median_9_11km_kmh"], value["wind_share_of_ground_speed_pct"],
                                      value["wind_observations_9_11km"]), ("144", "17", "2"))
                else:
                    self.assertEqual(value["wind_median_9_11km_kmh"], "")
                    self.assertIn("weather.py fetch", numbers.source["wind_median_9_11km_kmh"])
                for name in ("altitude_speed_kmh.png", "title_map.png"):
                    path = root / "outputs/figures/presentation" / name
                    self.assertGreater(path.stat().st_size, 1000, name)

    def test_running_collection_ends_window_at_newest_local_snapshot(self):
        entries = [{"source_url": "https://opensky-network.org/api/states/all", "params": BBOX,
                    "attempted_at_utc": iso(t), "retrieved_at_utc": iso(t), "status": 200, "outcome": "success",
                    "path": "x", "state_count": 1} for t in (T0, T0 + 300)]
        schedule = {"end_utc": iso(T0 + 86400)}
        summary, note = figures.coverage_gaps(entries, {"bbox": BBOX, "interval_seconds": 300}, schedule,
                                              now=pd.Timestamp(T0 + 7200, unit="s", tz="UTC"))
        self.assertEqual((summary["expected_slots"], summary["gaps"]), (2, 0))
        self.assertIn("still running", note)
        old_box = [{**entries[0], "params": {**BBOX, "lomin": 5.8}}]
        self.assertIsNone(figures.coverage_gaps(old_box, {"bbox": BBOX}, schedule)[0])

    def test_circle_radius_is_in_kilometres(self):
        for radius in (30, 60):
            lat, lon = figures.circle(47.0, 8.0, radius)
            distances = prepare.haversine(lat, lon, 47.0, 8.0)
            self.assertLess(abs(distances - radius).max(), 0.001)
        lat, lon = figures.circle(47.0, 8.0, 30)
        # In degrees the circle is wider east-west than north-south, by about 1/cos(47 deg).
        self.assertAlmostEqual((lon.max() - lon.min()) / (lat.max() - lat.min()), 1 / 0.6820, places=2)

    def test_database_without_final_bbox_rule_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.build(root, with_weather=False)
            config = json.loads((root / "config.json").read_text())
            (root / "config.json").write_text(json.dumps({**config, "require_current_bbox": False}))
            with patch.object(prepare, "ROOT", root), contextlib.redirect_stdout(io.StringIO()):
                prepare.main()
            with self.assertRaisesRegex(SystemExit, "require_current_bbox"):
                self.run_script(root)


if __name__ == "__main__":
    unittest.main()

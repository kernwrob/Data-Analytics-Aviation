"""Offline failure-path checks; fixtures are never written to project data."""
import contextlib
import io
import json
import sqlite3
import tempfile
import unittest
import sys
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import Mock, patch

import pandas as pd
import requests
from src import collect, prepare

# 17-field vector as before extended=1; the 18-field variant appends ADS-B category 6 (heavy).
STATE_17 = ["abcdef", "TEST1", "Example", 100, 100, 8., 47., 950., False, 50., 90., -3.5, None, 1000., None, False, 0]
STATE_18 = ["123456", "TEST2", "Example", 100, 100, 8.1, 47.1, 2950., False, 120., 90., 7.25, None, 3000., None, False, 0, 6]


class CollectionAuditTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        (self.root / "data/raw").mkdir(parents=True)
        self.config = {"bbox": {"lamin": 45.7, "lamax": 48, "lomin": 5.8, "lomax": 10.6}, "interval_seconds": 300}
        (self.root / "config.json").write_text(json.dumps(self.config))
        self.root_patch = patch.object(collect, "ROOT", self.root)
        self.root_patch.start()
        self.addCleanup(self.root_patch.stop)
        self.env_patch = patch.dict(collect.os.environ, {}, clear=True)
        self.env_patch.start()
        self.addCleanup(self.env_patch.stop)

    def entries(self):
        return [json.loads(line) for line in (self.root / "data/raw/manifest.jsonl").read_text().splitlines()]

    def response(self, status=200, payload=None):
        response = Mock(status_code=status, headers={}, url=collect.STATE_URL)
        response.content = json.dumps(payload).encode()
        response.json.return_value = payload
        return response

    def test_empty_snapshot_is_success_with_original_bytes(self):
        response = self.response(payload={"time": 100, "states": None})
        with patch.object(collect.requests, "get", return_value=response), contextlib.redirect_stdout(io.StringIO()):
            collect.retrieve("snapshot", self.config)
        entry, = self.entries()
        self.assertEqual(entry["state_count"], 0)
        self.assertEqual(entry["outcome"], "success")
        self.assertEqual((self.root / entry["path"]).read_bytes(), response.content)

    def test_rate_limit_is_recorded_without_retry(self):
        response = self.response(status=429)
        response.headers = {"X-Rate-Limit-Retry-After-Seconds": "3600"}
        with patch.object(collect.requests, "get", return_value=response) as request:
            with self.assertRaises(RuntimeError):
                collect.retrieve("snapshot", self.config)
        request.assert_called_once()
        entry, = self.entries()
        self.assertEqual(entry["status"], 429)
        self.assertEqual(entry["retry_after"], "3600")
        self.assertNotIn("path", entry)

    def test_airport_network_error_is_logged_without_details(self):
        with patch.object(collect.requests, "get", side_effect=requests.Timeout("private-details")):
            with self.assertRaises(RuntimeError) as raised:
                collect.retrieve("airports", self.config)
        entry, = self.entries()
        self.assertEqual(entry["error_type"], "Timeout")
        self.assertEqual(entry["outcome"], "failure")
        self.assertNotIn("private-details", json.dumps(entry) + str(raised.exception))

    def test_invalid_success_response_is_a_failure(self):
        with patch.object(collect.requests, "get", return_value=self.response(payload={"time": 100})):
            with self.assertRaises(RuntimeError):
                collect.retrieve("snapshot", self.config)
        entry, = self.entries()
        self.assertEqual(entry["status"], 200)
        self.assertEqual(entry["outcome"], "failure")
        self.assertEqual(entry["failure_stage"], "validation")

    def test_oauth_failure_never_logs_credentials_or_body(self):
        with patch.dict(collect.os.environ, {"OPENSKY_CLIENT_ID": "private-id", "OPENSKY_CLIENT_SECRET": "private-secret"}), \
                patch.object(collect.requests, "post", return_value=self.response(status=401)):
            with self.assertRaises(RuntimeError):
                collect.retrieve("snapshot", self.config)
        entry, = self.entries()
        self.assertEqual(entry["oauth_status"], 401)
        self.assertEqual(entry["failure_stage"], "oauth")
        self.assertNotIn("private-", json.dumps(entry))

    def test_rate_limit_deadline_survives_a_deferred_invocation(self):
        now = datetime.now(timezone.utc)
        collect.record_manifest({"source_url": collect.STATE_URL, "status": 429, "retry_after": "3600"})
        collect.record_manifest({"source_url": collect.STATE_URL, "status": None, "outcome": "deferred"})
        self.assertGreater(collect.rate_limit_wait_seconds(now + timedelta(seconds=300)), 3290)
        self.assertEqual(collect.rate_limit_wait_seconds(now + timedelta(seconds=3601)), 0)

    def test_missing_rate_limit_deadline_pauses_a_day(self):
        now = datetime.now(timezone.utc)
        collect.record_manifest({"source_url": collect.STATE_URL, "status": 429, "retry_after": None})
        self.assertGreater(collect.rate_limit_wait_seconds(now), 86390)

    def test_expired_window_cannot_make_a_request(self):
        with patch.object(sys, "argv", ["collect.py", "snapshot", "--scheduled", "--until-utc", "2000-01-01T00:00:00+00:00"]), \
                patch.object(collect.requests, "get") as request, contextlib.redirect_stdout(io.StringIO()):
            collect.main()
        request.assert_not_called()

    def test_scheduled_catchup_does_not_burst_requests(self):
        collect.record_manifest({"source_url": collect.STATE_URL, "status": 200, "outcome": "success"})
        with patch.object(sys, "argv", ["collect.py", "snapshot", "--scheduled"]), \
                patch.object(collect.requests, "get") as request, contextlib.redirect_stdout(io.StringIO()):
            collect.main()
        request.assert_not_called()
        self.assertEqual(self.entries()[-1]["reason"], "sampling_interval")

    def test_snapshot_requests_extended_category_and_logs_its_share(self):
        response = self.response(payload={"time": 100, "states": [STATE_17, STATE_18]})
        with patch.object(collect.requests, "get", return_value=response) as request, \
                contextlib.redirect_stdout(io.StringIO()):
            collect.retrieve("snapshot", self.config)
        self.assertEqual(request.call_args.kwargs["params"], {**self.config["bbox"], "extended": 1})
        entry, = self.entries()
        self.assertEqual(entry["params"]["extended"], 1)
        self.assertEqual(entry["category_present"], .5)

    def test_empty_snapshot_has_no_category_share(self):
        with patch.object(collect.requests, "get", return_value=self.response(payload={"time": 100, "states": []})), \
                contextlib.redirect_stdout(io.StringIO()):
            collect.retrieve("snapshot", self.config)
        self.assertIsNone(self.entries()[0]["category_present"])


class StateFieldTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        for folder in ("data/raw/opensky", "data/raw/airports"):
            (self.root / folder).mkdir(parents=True)
        # One pilot-style 17-field file and one extended 18-field file side by side.
        (self.root / "data/raw/opensky/old.json").write_text(json.dumps({"time": 100, "states": [STATE_17]}))
        (self.root / "data/raw/opensky/new.json").write_text(json.dumps({"time": 100, "states": [STATE_18]}))

    def test_category_is_read_and_old_vectors_stay_readable(self):
        raw = prepare.read_states(sorted((self.root / "data/raw/opensky").glob("*.json")))
        category = raw.set_index("icao24").category
        self.assertEqual(category["123456"], 6)
        self.assertTrue(pd.isna(category["abcdef"]))

    def test_only_old_vectors_still_produce_an_empty_category_column(self):
        raw = prepare.read_states([self.root / "data/raw/opensky/old.json"])
        self.assertTrue(raw.category.isna().all())

    def test_raw_altitude_vertical_rate_and_category_reach_observations(self):
        config = {"airport_idents": ["TEST"], "max_age_seconds": 60, "near_km": 30, "far_km": 60}
        (self.root / "config.json").write_text(json.dumps(config))
        pd.DataFrame({"ident": ["TEST"], "name": ["Test airport"], "latitude_deg": [47.],
                      "longitude_deg": [8.], "elevation_ft": [100.]}).to_csv(self.root / "data/raw/airports/fixture.csv", index=False)
        with patch.object(prepare, "ROOT", self.root), contextlib.redirect_stdout(io.StringIO()):
            prepare.main()
        with closing(sqlite3.connect(self.root / "data/processed/aircraft.sqlite")) as db:
            rows = db.execute("""SELECT icao24, baro_altitude, vertical_rate, category
                                 FROM observations ORDER BY icao24""").fetchall()
        self.assertEqual(rows, [("123456", 2950., 7.25, 6), ("abcdef", 950., -3.5, None)])


if __name__ == "__main__":
    unittest.main()

"""Offline failure-path checks; fixtures are never written to project data."""
import contextlib
import io
import json
import tempfile
import unittest
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import Mock, patch

import requests
from src import collect


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


if __name__ == "__main__":
    unittest.main()

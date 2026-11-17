import unittest
from src.collection_coverage import summarize_coverage


class CoverageTests(unittest.TestCase):
    def test_failure_empty_and_no_collection_are_different(self):
        def entry(time, outcome, status, count=None):
            return {"source_url": "https://opensky-network.org/api/states/all", "attempted_at_utc": time,
                    "retrieved_at_utc": time, "outcome": outcome, "status": status, "state_count": count}
        entries = [entry("2026-10-01T10:00:01Z", "success", 200, 0),
                   entry("2026-10-01T10:05:01Z", "failure", 503)]
        _, slots, _, summary = summarize_coverage(entries, "2026-10-01T12:00:00+02:00", "2026-10-01T10:15:00Z")
        self.assertEqual(slots.outcome.tolist(), ["successful_response", "failed_request", "no_collection"])
        self.assertTrue(slots.empty_response.iloc[0])
        self.assertEqual(summary["empty_responses"], 1)


if __name__ == "__main__":
    unittest.main()

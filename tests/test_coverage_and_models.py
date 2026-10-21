import unittest
import numpy as np
import pandas as pd
from src.collection_coverage import summarize_coverage
from src.model_comparison import make_comparison_models, compare_models, SPATIAL


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


class ComparisonTests(unittest.TestCase):
    def test_unseen_category_works_and_encoding_uses_training_only(self):
        train = pd.DataFrame({feature: [1., 2., 3., 4.] for feature in SPATIAL})
        train["aircraft_category"] = ["Jet landplane"] * 4
        test = train.iloc[[0]].copy()
        test["aircraft_category"] = "Previously unseen"
        features, model = make_comparison_models()["C: spatial and aircraft category"]
        model.fit(train[features], [10., 20., 30., 40.])
        self.assertTrue(np.isfinite(model.predict(test[features])).all())
        encoder = model[0].named_transformers_["category"][-1]
        self.assertEqual(encoder.categories_[0].tolist(), ["Jet landplane"])

    def test_comparison_refuses_pilot_data(self):
        with self.assertRaisesRegex(RuntimeError, "seven observed"):
            compare_models(pd.DataFrame({"date_utc": ["2026-10-01"]}),
                           pd.DataFrame({"date_utc": ["2026-10-01"]}), "pilot")


if __name__ == "__main__":
    unittest.main()

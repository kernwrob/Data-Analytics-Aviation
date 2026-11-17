"""Offline checks for the unified models 0, A-D, RF (src/model_comparison.py, CC-9). Synthetic data only."""
import json
import re
import tempfile
import unittest
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd
from tests.synthetic import CONFIG, SLOPES_FLAT, SLOPES_INTERACTION, make_observations
from src import model_comparison as mc
from src.features import interaction_columns

matplotlib.use("Agg")
ROOT = Path(__file__).resolve().parents[1]


def evaluate(split, seed=1, slopes=SLOPES_INTERACTION, **kwargs):
    data = mc.model_frame(make_observations(slopes, seed=seed, **kwargs), CONFIG)
    train, test = split(data)
    return mc.evaluate_models(train, test, "test", CONFIG), train


class FeatureListTests(unittest.TestCase):
    def test_no_leakage_and_lat_lon_only_in_the_forest(self):
        for include_wind in (False, True):
            specs = mc.model_specs(CONFIG, include_wind=include_wind)
            self.assertEqual("D: C + wind" in specs, include_wind)
            for name, spec in specs.items():
                self.assertFalse(mc.TARGET_DERIVED.intersection(spec.features), name)
                uses_position = bool({"latitude", "longitude"} & set(spec.features))
                self.assertEqual(uses_position, spec.kind == "forest", name)
                self.assertNotIn("near_indicator", spec.features)
                self.assertNotIn("altitude_x_near", spec.features)
        specs = mc.model_specs(CONFIG, include_wind=True)
        self.assertEqual(specs["A: altitude knot"].features, ["alt_low_km", "alt_high_km"])
        model_b = specs["B: + zone, airport, distance, flight phase"]
        self.assertTrue(set(interaction_columns(CONFIG)) <= set(model_b.numeric))
        self.assertEqual(model_b.categorical, ["airport", "flight_phase"])
        self.assertEqual(specs["C: B + aircraft category"].categorical[-1], "aircraft_category")
        self.assertTrue({"tailwind_ms", "crosswind_ms"} <= set(specs["D: C + wind"].numeric))

    def test_notebook_02_has_no_model_definitions_of_its_own(self):
        notebook = json.loads((ROOT / "notebooks/02_models.ipynb").read_text(encoding="utf-8"))
        code = "\n".join(c["source"] if isinstance(c["source"], str) else "".join(c["source"])
                         for c in notebook["cells"] if c["cell_type"] == "code")
        for definition in ("LinearRegression(", "RandomForestRegressor(", "DummyRegressor(", "GroupShuffleSplit(",
                           "train_test_split(", "make_pipeline(", "spatial =", "altitude_x_near"):
            self.assertNotIn(definition, code)
        self.assertIn("from src import model_comparison as mc", code)
        for function in ("model_frame", "model_specs", "split_by_date", "split_by_aircraft", "split_random_demo",
                         "evaluate_models", "coefficient_table", "rmse_bootstrap", "rmse_figure"):
            self.assertRegex(code, rf"mc\.{function}\(")


class EvaluationTests(unittest.TestCase):
    def test_metrics_per_zone_in_both_units_and_unseen_category(self):
        data = mc.model_frame(make_observations(SLOPES_INTERACTION, seed=2), CONFIG)
        train, test = mc.split_by_date(data)
        test = test.copy()
        test.loc[test.index[:5], "aircraft_category"] = "Previously unseen"
        metrics, predictions, fitted = mc.evaluate_models(train, test, "later_days", CONFIG)
        self.assertEqual(set(metrics.group), {"all", "near", "middle", "far"})
        self.assertTrue(np.allclose(metrics.RMSE_ms, metrics.RMSE_kmh / 3.6))
        self.assertTrue(np.isfinite(predictions["C: B + aircraft category"]).all())
        encoder = fitted["C: B + aircraft category"][0].named_transformers_["categorical"][-1]
        self.assertNotIn("Previously unseen", encoder.categories_[-1])
        # The models with context beat the baseline and the altitude-only model on these data.
        rmse = metrics.loc[metrics.group.eq("all")].set_index("model").RMSE_kmh
        self.assertLess(rmse["A: altitude knot"], rmse["0: mean baseline"])
        self.assertLess(rmse["B: + zone, airport, distance, flight phase"], rmse["A: altitude knot"])

    def test_coefficients_in_original_units_recover_the_slope(self):
        (_, _, fitted), train = evaluate(mc.split_by_date, slopes=SLOPES_FLAT, seed=3)
        table = mc.coefficient_table(fitted, train, CONFIG)
        model_a = table.loc[table.model.eq("A: altitude knot")].set_index("feature")
        self.assertAlmostEqual(model_a.loc["alt_low_km", "per_unit_kmh"], 60, delta=10)
        self.assertAlmostEqual(model_a.loc["alt_high_km", "per_unit_kmh"], 15, delta=3)
        sd = train.alt_low_km.std(ddof=0)
        self.assertAlmostEqual(model_a.loc["alt_low_km", "per_sd_kmh"], model_a.loc["alt_low_km", "per_unit_kmh"] * sd)
        model_c = table.loc[table.model.eq("C: B + aircraft category")]
        references = model_c.loc[model_c.feature.str.startswith("aircraft_category_"), "reference"]
        self.assertEqual(set(references), {"Kurzstrecke"})  # first category alphabetically in the fixture
        self.assertNotIn("RF: random forest (B + lat/lon)", set(table.model))

    def test_leakage_demo_random_split_looks_better_than_group_split(self):
        # Long tracks with strong persistent aircraft offsets: the forest recognises the flight from its lat/lon
        # track when neighbouring positions are in training (measured ratio 0.68-0.75 for seeds 4-6). A linear
        # model cannot memorise flights, so for it the demo shows little (ratio about 0.9-1.2).
        frame = make_observations(SLOPES_INTERACTION, seed=4, aircraft=120, per_aircraft=40, aircraft_sd=80.0,
                                  noise_sd=5.0)
        data = mc.model_frame(frame, CONFIG)
        forest = "RF: random forest (B + lat/lon)"
        results = {}
        for name, split in (("random", mc.split_random_demo), ("aircraft", mc.split_by_aircraft)):
            train, test = split(data)
            metrics, _, _ = mc.evaluate_models(train, test, name, CONFIG)
            results[name] = metrics.loc[metrics.group.eq("all")].set_index("model").RMSE_kmh[forest]
        self.assertLess(results["random"], 0.85 * results["aircraft"])

    def test_splits_keep_their_rules(self):
        data = mc.model_frame(make_observations(seed=5), CONFIG)
        train, test = mc.split_by_date(data)
        self.assertLess(max(train.date_utc), min(test.date_utc))
        train, test = mc.split_by_aircraft(data)
        self.assertTrue(set(train.icao24).isdisjoint(test.icao24))
        train, test = mc.split_random_demo(data)
        self.assertTrue(set(train.icao24) & set(test.icao24))  # that is exactly the leakage

    def test_guard_refuses_fewer_than_seven_dates(self):
        with self.assertRaisesRegex(RuntimeError, "seven observed"):
            mc.model_frame(make_observations(dates=6), CONFIG)
        data = mc.model_frame(make_observations(seed=6), CONFIG)
        short = data.loc[data.date_utc.isin(sorted(data.date_utc.unique())[:6])]
        with self.assertRaisesRegex(RuntimeError, "seven observed"):
            mc.evaluate_models(short.iloc[:600], short.iloc[600:], "x", CONFIG)

    def test_bootstrap_interval_and_figure(self):
        (metrics, predictions, fitted), _ = evaluate(mc.split_by_aircraft, seed=7)
        intervals = mc.rmse_bootstrap(predictions, list(fitted), "test", n_boot=100)
        merged = metrics.merge(intervals, on=["split", "model", "group"])
        self.assertEqual(len(merged), len(metrics))
        self.assertTrue((merged.RMSE_kmh_ci_low <= merged.RMSE_kmh * 1.0001).all())
        self.assertTrue((merged.RMSE_kmh_ci_high >= merged.RMSE_kmh * 0.9999).all())
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "rmse.png"
            mc.rmse_figure(metrics.assign(split="random_rows_demo"), path, intervals.assign(split="random_rows_demo"))
            self.assertGreater(path.stat().st_size, 1000)


if __name__ == "__main__":
    unittest.main()

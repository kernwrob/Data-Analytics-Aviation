"""Offline checks for the knot features (src/features.py) and the OLS interaction test (src/inference.py, CC-8)."""
import tempfile
import unittest
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd
from tests.synthetic import CONFIG, SLOPES_FLAT, SLOPES_INTERACTION, make_observations
from src import features, inference

matplotlib.use("Agg")  # figures are written to files only


class KnotFeatureTests(unittest.TestCase):
    def test_values_at_the_edges_and_below_zero(self):
        result = features.knot_features([-200., 0., 3000., 12000.], 3000)
        self.assertEqual(result.alt_low_km.tolist(), [-0.2, 0.0, 3.0, 3.0])
        self.assertEqual(result.alt_high_km.tolist(), [0.0, 0.0, 0.0, 9.0])
        # The two pieces always add up to the altitude in km.
        self.assertTrue(np.allclose(result.sum(axis=1), [-0.2, 0.0, 3.0, 12.0]))

    def test_optional_second_knot(self):
        result = features.knot_features([2000., 6000., 12000.], 3000, 10000)
        self.assertEqual(result.columns.tolist(), ["alt_low_km", "alt_high_km", "alt_top_km"])
        self.assertTrue(np.allclose(result.to_numpy(), [[2, 0, 0], [3, 3, 0], [3, 7, 2]]))
        self.assertEqual(features.altitude_terms({**CONFIG, "altitude_knot2_m": 10000})[-1], "alt_top_km")
        with self.assertRaisesRegex(ValueError, "above"):
            features.knot_settings({"altitude_knot_m": 3000, "altitude_knot2_m": 2000})
        with self.assertRaisesRegex(ValueError, "altitude_knot_m"):
            features.knot_settings({})

    def test_zone_dummies_and_interactions_use_far_as_reference(self):
        frame = pd.DataFrame({"zone": ["near", "middle", "far", "neighbour"], "altitude_m": [5000.] * 4,
                              "velocity": [100.] * 4})
        data = features.add_model_features(frame, CONFIG)
        self.assertEqual(data.zone.tolist(), ["near", "middle", "far"])  # other zones are not modelled
        self.assertEqual(data.alt_high_km_x_near.tolist(), [2.0, 0.0, 0.0])
        self.assertEqual(data.alt_low_km_x_middle.tolist(), [0.0, 3.0, 0.0])
        self.assertEqual(data.speed_kmh.tolist(), [360.0] * 3)
        self.assertEqual(features.interaction_columns(CONFIG),
                         ["zone_near", "zone_middle", "alt_low_km_x_near", "alt_high_km_x_near",
                          "alt_low_km_x_middle", "alt_high_km_x_middle"])


class InteractionTestTests(unittest.TestCase):
    def test_known_interaction_is_found_with_the_right_sign(self):
        tables = inference.run_inference(make_observations(SLOPES_INTERACTION, seed=1), CONFIG)
        coefficients = tables["main_coefficients"].set_index("term")
        near_low = coefficients.loc["alt_low_km:C(zone, Treatment('far'))[T.near]"]
        self.assertLess(near_low.p_value, 0.05)
        self.assertGreater(near_low.estimate_kmh, 0)
        self.assertTrue(near_low.ci_low_kmh < 35 < near_low.ci_high_kmh)  # true difference 95 - 60
        tests = tables["interaction_tests"].set_index("test")
        self.assertLess(tests.loc["altitude x zone: near vs far", "p_value"], 0.05)
        slopes = tables["zone_slopes"].set_index(["zone", "term"])
        for zone, (low, high) in SLOPES_INTERACTION.items():
            self.assertTrue(slopes.loc[(zone, "alt_low_km"), "ci_low_kmh"] < low <
                            slopes.loc[(zone, "alt_low_km"), "ci_high_kmh"], zone)
        # Both units and counts are reported.
        self.assertAlmostEqual(near_low.estimate_ms, near_low.estimate_kmh / 3.6)
        self.assertEqual(near_low.n_aircraft, 240)

    def test_no_interaction_gives_no_systematically_small_p_values(self):
        p_values = []
        for seed in range(20):
            tables = inference.run_inference(make_observations(SLOPES_FLAT, aircraft=120, seed=seed), CONFIG)
            tests = tables["interaction_tests"].set_index("test")
            p_values.append(tests.loc["altitude x zone: near vs far", "p_value"])
        self.assertLessEqual(np.mean(np.array(p_values) < 0.05), 0.2)

    def test_slope_per_zone_is_base_plus_interaction(self):
        tables = inference.run_inference(make_observations(SLOPES_INTERACTION, seed=2), CONFIG)
        coefficients = tables["main_coefficients"].set_index("term").estimate_kmh
        slopes = tables["zone_slopes"].set_index(["zone", "term"]).slope_kmh_per_1000m
        self.assertAlmostEqual(slopes[("far", "alt_high_km")], coefficients["alt_high_km"])
        self.assertAlmostEqual(slopes[("near", "alt_high_km")], coefficients["alt_high_km"] +
                               coefficients["alt_high_km:C(zone, Treatment('far'))[T.near]"])
        self.assertEqual(set(tables["zone_slopes"].segment), {"unter 3'000 m", "über 3'000 m"})

    def test_variants_and_small_levels_are_counted_not_modelled(self):
        data = make_observations(SLOPES_INTERACTION, seed=3)
        data.loc[data.icao24.isin(data.icao24.unique()[:5]), "aircraft_category"] = "Turboprop"
        tables = inference.run_inference(data, CONFIG)
        levels = tables["category_levels"].set_index("aircraft_category")
        self.assertFalse(levels.loc["Turboprop", "included"])
        self.assertNotIn("Turboprop", set(tables["category_slopes"].aircraft_category))
        self.assertEqual(set(tables["airport_slopes"].airport), {"ZRH", "GVA", "BSL"})
        self.assertIn("altitude x airport (near zone, reference ZRH)", set(tables["interaction_tests"].test))

    def test_guard_refuses_fewer_than_seven_dates(self):
        with self.assertRaisesRegex(RuntimeError, "seven observed"):
            inference.run_inference(make_observations(dates=6), CONFIG)

    def test_figures_are_written(self):
        tables = inference.run_inference(make_observations(SLOPES_INTERACTION, seed=4), CONFIG)
        with tempfile.TemporaryDirectory() as tmp:
            for name, draw, table in [("slopes.png", inference.slope_figure, tables["zone_slopes"]),
                                      ("residuals.png", inference.residual_figure, tables["residual_profile"])]:
                path = Path(tmp) / name
                if draw is inference.slope_figure:
                    draw(table, path, CONFIG)
                else:
                    draw(table, path)
                self.assertGreater(path.stat().st_size, 1000)


if __name__ == "__main__":
    unittest.main()

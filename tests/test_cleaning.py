"""Offline checks for the CC-10 cleaning stages (#13): order, altitude fallback, plausibility, neighbour buffer,
flight phase and the audit arithmetic. Small hand-made fixtures only."""
import copy
import unittest

import pandas as pd
from tests.cleaning_config import with_cleaning
from tests.test_category_and_bbox import NEW_BBOX, PrepareFixture
from src import prepare

T0 = 1794000000
# Main airport TEST at (47, 8). NEAR is 22.8 km east of it (inside its 30 km zone), FARN 76 km east (far zone).
AIRPORTS = pd.DataFrame({"ident": ["TEST", "NEAR", "FARN"], "name": ["Test", "Near neighbour", "Far neighbour"],
                         "iata_code": ["TST", None, None], "latitude_deg": [47., 47., 47.],
                         "longitude_deg": [8., 8.3, 9.0], "elevation_ft": [100., 100., 100.]})
CONFIG = with_cleaning({"airport_idents": ["TEST"], "max_age_seconds": 60, "near_km": 30, "far_km": 60})


def state(icao24, lat=47.0, lon=8.0, baro=1000., on_ground=False, velocity=100., vertical_rate=0., geo=1000.):
    return [icao24, "T", "X", T0, T0, lon, lat, baro, on_ground, velocity, 90., vertical_rate, None, geo,
            None, False, 0, 0]


def raw_frame(states):
    frame = pd.DataFrame(states, columns=prepare.FIELDS)
    frame["snapshot_time"] = T0
    return frame


def clean(states, airports=AIRPORTS, **overrides):
    """clean_and_join on the fixture; keys of neighbour_airports go there, every other key to the top level."""
    config = copy.deepcopy(CONFIG)
    for key, value in overrides.items():
        if key in prepare.NEIGHBOUR_KEYS:
            config["neighbour_airports"][key] = value
        else:
            config[key] = value
    return prepare.clean_and_join(raw_frame(states), airports, config)


def stages(audit):
    return audit.set_index("stage")


class OrderAndAltitudeTests(unittest.TestCase):
    def test_ground_rows_are_removed_before_the_required_field_check(self):
        # Two aircraft on the ground without any altitude, one airborne without position.
        data, _, audit, missing = clean([state("aaaaaa"), state("bbbbbb", on_ground=True, geo=None, baro=None),
                                         state("cccccc", on_ground=True, geo=None, baro=None),
                                         state("dddddd", lat=None)])
        audit = stages(audit)
        self.assertEqual(audit.loc["airborne", "lost"], 2)
        self.assertEqual(audit.loc["required_fields_present", "lost"], 1)
        self.assertEqual(data.icao24.tolist(), ["aaaaaa"])
        missing = missing.set_index("column_name")
        self.assertEqual(missing.loc["geo_altitude", "missing_all_rows"], 2)
        self.assertEqual(missing.loc["geo_altitude", "missing_airborne_rows"], 0)
        self.assertEqual(missing.loc["latitude", "missing_airborne_rows"], 1)
        self.assertEqual((missing.rows_all.iloc[0], missing.rows_airborne.iloc[0]), (4, 2))

    def test_altitude_from_geo_else_baro_and_rows_without_both_are_dropped(self):
        data, _, audit, _ = clean([state("aaaaaa", geo=1100., baro=1000.), state("bbbbbb", geo=None, baro=900.),
                                   state("cccccc", geo=None, baro=None)])
        rows = data.set_index("icao24")
        self.assertEqual((rows.loc["aaaaaa", "altitude_m"], rows.loc["aaaaaa", "altitude_source"]), (1100., "geo"))
        self.assertEqual((rows.loc["bbbbbb", "altitude_m"], rows.loc["bbbbbb", "altitude_source"]), (900., "baro"))
        self.assertTrue(pd.isna(rows.loc["bbbbbb", "geo_altitude"]))  # geo_altitude is kept unchanged
        self.assertNotIn("cccccc", rows.index)
        self.assertEqual(stages(audit).loc["required_fields_present", "lost"], 1)


class PlausibilityTests(unittest.TestCase):
    def check(self, stage, kept, removed):
        states = [state(f"{i:06x}", **values) for i, values in enumerate(kept + removed)]
        data, _, audit, _ = clean(states)
        self.assertEqual(len(data), len(kept))
        self.assertEqual(stages(audit).loc[stage, "lost"], len(removed))
        other = [s for s in ("plausible_altitude", "plausible_speed", "plausible_vertical_rate") if s != stage]
        self.assertTrue(stages(audit).loc[other, "lost"].eq(0).all())

    def test_altitude_limits_are_inclusive(self):
        self.check("plausible_altitude", kept=[{"geo": -300.}, {"geo": 15500.}, {"geo": None, "baro": 15500.}],
                   removed=[{"geo": -300.1}, {"geo": 15500.1}, {"geo": None, "baro": 16000.}])

    def test_speed_limits_are_inclusive(self):
        self.check("plausible_speed", kept=[{"velocity": 0.}, {"velocity": 350.}],
                   removed=[{"velocity": -0.1}, {"velocity": 350.1}])

    def test_vertical_rate_limit_and_missing_rate_is_kept(self):
        self.check("plausible_vertical_rate",
                   kept=[{"vertical_rate": 40.}, {"vertical_rate": -40.}, {"vertical_rate": None}],
                   removed=[{"vertical_rate": 40.1}, {"vertical_rate": -40.1}])

    def test_thresholds_come_from_config(self):
        data, _, audit, _ = clean([state("aaaaaa", velocity=300.), state("bbbbbb", velocity=200.)],
                                  plausibility={**CONFIG["plausibility"], "velocity_max_ms": 250})
        self.assertEqual(data.icao24.tolist(), ["bbbbbb"])
        self.assertEqual(stages(audit).loc["plausible_speed", "lost"], 1)

    def test_missing_settings_or_unknown_mode_stop(self):
        config = copy.deepcopy(CONFIG)
        del config["plausibility"]["vertical_rate_abs_max_ms"]
        with self.assertRaisesRegex(ValueError, "plausibility.vertical_rate_abs_max_ms"):
            prepare.clean_and_join(raw_frame([state("aaaaaa")]), AIRPORTS, config)
        with self.assertRaisesRegex(ValueError, "mode"):
            clean([state("aaaaaa")], mode="drop")


class FlightPhaseAndAirportTests(unittest.TestCase):
    def test_phase_threshold_is_inclusive_for_level_and_missing_rate_is_unknown(self):
        rates = {"aaaaaa": 2.6, "bbbbbb": 2.5, "cccccc": -2.5, "dddddd": -2.6, "eeeeee": None}
        data, _, _, _ = clean([state(k, vertical_rate=v) for k, v in rates.items()])
        self.assertEqual(data.set_index("icao24").flight_phase.to_dict(),
                         {"aaaaaa": "climb", "bbbbbb": "level", "cccccc": "level", "dddddd": "descent",
                          "eeeeee": "unknown"})
        self.assertEqual(prepare.flight_phase(pd.Series([3., 3.]), 5.).tolist(), ["level", "level"])

    def test_airport_short_name_from_iata_code_else_ident(self):
        data, airports, _, _ = clean([state("aaaaaa")])
        self.assertEqual((data.airport.iloc[0], data.airport_ident.iloc[0]), ("TST", "TEST"))
        self.assertIn("iata_code", airports.columns)
        no_iata = AIRPORTS.assign(iata_code=None)
        data, _, _, _ = prepare.clean_and_join(raw_frame([state("aaaaaa")]), no_iata, CONFIG)
        self.assertEqual(data.airport.iloc[0], "TEST")


class NeighbourBufferTests(unittest.TestCase):
    # aaaaaa: 3.8 km from FARN, 80 km from TEST (far) -> buffered.
    # bbbbbb: 3.8 km from NEAR but 19 km from TEST (near zone) -> never buffered.
    # cccccc: 30 km from FARN (outside the 15 km radius).
    STATES = [state("aaaaaa", lon=9.05), state("bbbbbb", lon=8.25), state("cccccc", lon=8.6)]

    def test_exclude_mode_drops_buffer_rows_outside_the_main_near_zone(self):
        data, _, audit, _ = clean(self.STATES, idents=["NEAR", "FARN"], mode="exclude")
        self.assertEqual(sorted(data.icao24), ["bbbbbb", "cccccc"])
        self.assertEqual(stages(audit).loc["neighbour_airport_buffer", "lost"], 1)
        rows = data.set_index("icao24")
        self.assertEqual((rows.loc["bbbbbb", "zone"], rows.loc["bbbbbb", "neighbour_ident"]), ("near", "NEAR"))
        self.assertAlmostEqual(rows.loc["bbbbbb", "neighbour_distance_km"], 3.79, places=1)

    def test_own_zone_mode_keeps_rows_and_marks_them(self):
        data, _, audit, _ = clean(self.STATES, idents=["NEAR", "FARN"], mode="own_zone")
        rows = data.set_index("icao24")
        self.assertEqual(rows.zone.to_dict(), {"aaaaaa": "neighbour", "bbbbbb": "near", "cccccc": "middle"})
        self.assertEqual(rows.neighbour_buffer.to_dict(), {"aaaaaa": 1, "bbbbbb": 0, "cccccc": 0})
        # The assignment to the main airport and its distance never change.
        self.assertEqual(set(rows.airport_ident), {"TEST"})
        self.assertAlmostEqual(rows.loc["aaaaaa", "distance_km"], 79.6, places=0)
        self.assertEqual(stages(audit).loc["neighbour_airport_buffer", "lost"], 0)

    def test_radius_comes_from_config_and_empty_list_disables_the_buffer(self):
        data, _, _, _ = clean(self.STATES, idents=["NEAR", "FARN"], radius_km=35)
        self.assertEqual(sorted(data.icao24), ["bbbbbb"])
        data, _, audit, _ = clean(self.STATES, idents=[])
        self.assertEqual(len(data), 3)
        self.assertTrue(data.neighbour_ident.isna().all())
        with self.assertRaisesRegex(ValueError, "neighbour airport identifiers"):
            clean(self.STATES, idents=["XXXX"])


class BufferHeightTests(unittest.TestCase):
    """Only approaches and departures are buffered: at most max_height_above_airport_m above the neighbour."""
    SEA_LEVEL = AIRPORTS.assign(elevation_ft=[100., 100., 0.])  # FARN at 0 ft: height = altitude_m exactly

    def test_overflight_stays_and_approach_is_removed(self):
        states = [state("aaaaaa", lon=9.05, geo=11000.), state("bbbbbb", lon=9.05, geo=800.)]
        data, _, audit, _ = clean(states, idents=["FARN"])
        self.assertEqual(data.icao24.tolist(), ["aaaaaa"])
        self.assertEqual(stages(audit).loc["neighbour_airport_buffer", "lost"], 1)
        row = data.iloc[0]
        # Inside the radius, but too high: kept, and visible as such for the notebook-01 count.
        self.assertLess(row.neighbour_distance_km, 15)
        self.assertAlmostEqual(row.neighbour_height_m, 11000. - 100 * prepare.FEET_TO_M)
        self.assertEqual(row.neighbour_buffer, 0)

    def test_limit_is_inclusive_and_comes_from_config(self):
        states = [state("aaaaaa", lon=9.05, geo=3000.), state("bbbbbb", lon=9.05, geo=3000.1),
                  state("cccccc", lon=8.6, geo=3500.)]  # cccccc: outside the radius, always kept
        data, _, _, _ = clean(states, airports=self.SEA_LEVEL, idents=["FARN"])
        self.assertEqual(sorted(data.icao24), ["bbbbbb", "cccccc"])
        data, _, _, _ = clean(states, airports=self.SEA_LEVEL, idents=["FARN"], max_height_above_airport_m=4000)
        self.assertEqual(data.icao24.tolist(), ["cccccc"])

    def test_missing_elevation_or_setting_stops(self):
        no_elevation = AIRPORTS.assign(elevation_ft=[100., 100., None])
        with self.assertRaisesRegex(ValueError, "without elevation_ft.*FARN"):
            clean([state("aaaaaa")], airports=no_elevation, idents=["FARN"])
        config = copy.deepcopy(CONFIG)
        del config["neighbour_airports"]["max_height_above_airport_m"]
        with self.assertRaisesRegex(ValueError, "max_height_above_airport_m"):
            prepare.clean_and_join(raw_frame([state("aaaaaa")]), AIRPORTS, config)

    def test_own_zone_marks_only_low_rows(self):
        states = [state("aaaaaa", lon=9.05, geo=11000.), state("bbbbbb", lon=9.05, geo=800.),
                  state("cccccc", lon=8.25, geo=500.)]  # cccccc: near zone of TEST, never buffered
        data, _, audit, _ = clean(states, idents=["NEAR", "FARN"], mode="own_zone")
        self.assertEqual(data.set_index("icao24").zone.to_dict(),
                         {"aaaaaa": "far", "bbbbbb": "neighbour", "cccccc": "near"})
        self.assertEqual(stages(audit).loc["neighbour_airport_buffer", "lost"], 0)


class AuditArithmeticTests(unittest.TestCase):
    def test_lost_rows_add_up_from_raw_to_final(self):
        states = [state("aaaaaa"), state("bbbbbb", on_ground=True), state("cccccc", geo=None, baro=None),
                  state("dddddd", geo=20000.), state("eeeeee", velocity=400.), state("ffffff", vertical_rate=50.),
                  state("aaaaaa"),  # duplicate key
                  state("111111", lon=9.05), state("222222", lon=8.25)]
        data, _, audit, _ = clean(states, idents=["NEAR", "FARN"])
        self.assertEqual(audit.stage.tolist(), ["raw", "airborne", "required_fields_present", "valid_and_fresh",
                                                "plausible_altitude", "plausible_speed", "plausible_vertical_rate",
                                                "unique_aircraft_position_timestamp", "airport_join",
                                                "neighbour_airport_buffer"])
        self.assertTrue((audit.rows.shift(1) - audit.rows).iloc[1:].eq(audit.lost.iloc[1:]).all())
        self.assertEqual(audit.rows.iloc[0] - audit.lost.iloc[1:].sum(), len(data))
        self.assertEqual(audit.lost.iloc[1:].tolist(), [1, 1, 0, 1, 1, 1, 1, 0, 1])
        self.assertEqual(sorted(data.icao24), ["222222", "aaaaaa"])


class PrepareTablesTests(PrepareFixture):
    def test_database_has_new_columns_views_and_audit_tables(self):
        self.snapshot("new", [state("aaaaaa", vertical_rate=5.), state("bbbbbb", geo=None, baro=800.)], NEW_BBOX)
        with self.run_prepare():
            pass
        rows = self.query("""SELECT icao24, altitude_m, altitude_source, airport, flight_phase
                             FROM observations_enriched ORDER BY icao24""")
        self.assertEqual(rows, [("aaaaaa", 1000.0, "geo", "TEST", "climb"), ("bbbbbb", 800.0, "baro", "TEST", "level")])
        self.assertEqual(self.query("SELECT COUNT(altitude_m) FROM observations_with_wind"), [(2,)])
        self.assertEqual(self.query("SELECT rows_all FROM missing_fields_audit WHERE column_name = 'geo_altitude'"),
                         [(2,)])
        self.assertEqual(self.query("SELECT COUNT(*) FROM neighbour_airports"), [(0,)])


if __name__ == "__main__":
    unittest.main()

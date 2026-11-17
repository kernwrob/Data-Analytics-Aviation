"""CC-10 cleaning settings for test fixtures: the thresholds of config.json, but no neighbour airports
(the one-airport fixtures have none). Tests that need neighbours set them explicitly."""
import copy

CLEANING = {"plausibility": {"altitude_min_m": -300, "altitude_max_m": 15500, "velocity_min_ms": 0,
                             "velocity_max_ms": 350, "vertical_rate_abs_max_ms": 40},
            "flight_phase_threshold_ms": 2.5,
            "neighbour_airports": {"idents": [], "radius_km": 15, "max_height_above_airport_m": 3000,
                                   "mode": "exclude"}}


def with_cleaning(config):
    """config plus a fresh copy of the cleaning settings."""
    return {**config, **copy.deepcopy(CLEANING)}

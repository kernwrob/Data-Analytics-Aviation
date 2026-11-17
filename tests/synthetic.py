"""Synthetic observations with a known altitude-speed relation, for the CC-8/CC-9 tests (no real data).

Each aircraft gets one zone, airport, category, date and a persistent speed offset (so positions of the same
aircraft are correlated, like real flights), and a short straight track (latitude/longitude change along it).
Speed in km/h = base + slope_low[zone] * alt_low_km + slope_high[zone] * alt_high_km + offset + noise.
"""
import numpy as np
import pandas as pd

from tests.cleaning_config import with_cleaning

CONFIG = with_cleaning({"altitude_knot_m": 3000, "altitude_knot2_m": None,
                        "inference": {"min_aircraft_per_level": 20}})
SLOPES_FLAT = {"near": (60.0, 15.0), "middle": (60.0, 15.0), "far": (60.0, 15.0)}
SLOPES_INTERACTION = {"near": (95.0, 15.0), "middle": (70.0, 15.0), "far": (60.0, 15.0)}


def make_observations(slopes=SLOPES_FLAT, aircraft=240, per_aircraft=10, dates=8, aircraft_sd=40.0,
                      noise_sd=20.0, seed=0):
    rng = np.random.default_rng(seed)
    rows = []
    zones = np.array(["near", "middle", "far"])
    airports = np.array(["ZRH", "GVA", "BSL"])
    categories = np.array(["Kurzstrecke", "Regionaljet", "Langstrecke"])
    for index in range(aircraft):
        zone, airport = zones[index % 3], airports[(index // 3) % 3]
        category = categories[rng.integers(3)]
        offset = rng.normal(0, aircraft_sd)
        date = f"2026-11-{12 + index % dates:02d}"
        lat0, lon0, heading = rng.uniform(46, 48), rng.uniform(6, 10), rng.uniform(0, 2 * np.pi)
        altitudes = rng.uniform(0, 12000, per_aircraft)
        low, high = np.minimum(altitudes, 3000) / 1000, np.maximum(altitudes - 3000, 0) / 1000
        speed = (300 + slopes[zone][0] * low + slopes[zone][1] * high + offset
                 + rng.normal(0, noise_sd, per_aircraft))
        rate = rng.normal(0, 6, per_aircraft)
        for k in range(per_aircraft):
            rows.append({"icao24": f"{index:06x}", "time_position": 1794000000 + index * 1000 + k * 10,
                         "date_utc": date, "zone": zone, "airport": airport, "aircraft_category": category,
                         "flight_phase": "climb" if rate[k] > 2.5 else ("descent" if rate[k] < -2.5 else "level"),
                         "altitude_m": altitudes[k], "velocity": speed[k] / 3.6,
                         "distance_km": {"near": 15.0, "middle": 45.0, "far": 90.0}[zone] + rng.normal(0, 5),
                         "latitude": lat0 + 0.02 * k * np.cos(heading),
                         "longitude": lon0 + 0.03 * k * np.sin(heading),
                         "tailwind_ms": rng.normal(0, 10), "crosswind_ms": rng.normal(0, 10)})
    return pd.DataFrame(rows)

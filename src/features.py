"""Model features shared by src/inference.py (CC-8) and src/model_comparison.py (CC-9).

Altitude enters every model as a piecewise-linear term with a knot at "altitude_knot_m" (config.json, 3000 m,
the 250 kt speed limit below FL100; docs/DECISIONS.md). In km, so each coefficient reads directly as
«speed change per 1,000 m below / above the knot»:
    alt_low_km  = min(altitude_m, knot) / 1000
    alt_high_km = max(altitude_m - knot, 0) / 1000
An optional second knot ("altitude_knot2_m", null = off) splits alt_high_km at that height and adds
alt_top_km = max(altitude_m - knot2, 0) / 1000.

Zone enters as dummies with far (en route) as reference, and as zone x altitude-term interactions. All of these
are computed row by row from the row's own values: nothing is fitted, so nothing leaks from test data.
"""
import numpy as np
import pandas as pd

ZONES = ["near", "middle", "far"]
REFERENCE_ZONE = "far"
ZONE_DUMMIES = [z for z in ZONES if z != REFERENCE_ZONE]
KMH_PER_MS = 3.6
MIN_OBSERVED_DATES = 7
TARGET = "speed_kmh"


def knot_settings(config):
    """(knot_m, knot2_m or None) from config.json; both keys must be present (knot2 may be null)."""
    missing = [key for key in ("altitude_knot_m", "altitude_knot2_m") if key not in config]
    if missing:
        raise ValueError(f"config.json lacks {missing} (see docs/DECISIONS.md, CC-8/CC-9).")
    knot = float(config["altitude_knot_m"])
    knot2 = config["altitude_knot2_m"]
    if knot2 is not None and float(knot2) <= knot:
        raise ValueError("altitude_knot2_m must be above altitude_knot_m.")
    return knot, (None if knot2 is None else float(knot2))


def altitude_terms(config):
    """Names of the altitude features for the configured knots."""
    _, knot2 = knot_settings(config)
    return ["alt_low_km", "alt_high_km"] + ([] if knot2 is None else ["alt_top_km"])


def knot_features(altitude_m, knot_m, knot2_m=None):
    """Piecewise-linear altitude features in km. Negative altitudes give a negative alt_low_km."""
    altitude = pd.Series(altitude_m, dtype=float)
    features = pd.DataFrame(index=altitude.index)
    features["alt_low_km"] = np.minimum(altitude, knot_m) / 1000
    if knot2_m is None:
        features["alt_high_km"] = np.maximum(altitude - knot_m, 0) / 1000
    else:
        features["alt_high_km"] = np.clip(altitude - knot_m, 0, knot2_m - knot_m) / 1000
        features["alt_top_km"] = np.maximum(altitude - knot2_m, 0) / 1000
    return features


def interaction_columns(config):
    """Names of the zone dummies and zone x altitude-term interactions (reference zone: far)."""
    terms = altitude_terms(config)
    return ([f"zone_{zone}" for zone in ZONE_DUMMIES] +
            [f"{term}_x_{zone}" for zone in ZONE_DUMMIES for term in terms])


def add_model_features(frame, config):
    """Copy of `frame` restricted to near/middle/far with knot features, zone dummies, interactions and speed_kmh."""
    data = frame.loc[frame.zone.isin(ZONES)].copy()
    knot, knot2 = knot_settings(config)
    for name, values in knot_features(data.altitude_m, knot, knot2).items():
        data[name] = values
    for zone in ZONE_DUMMIES:
        data[f"zone_{zone}"] = data.zone.eq(zone).astype(int)
        for term in altitude_terms(config):
            data[f"{term}_x_{zone}"] = data[term] * data[f"zone_{zone}"]
    if TARGET not in data:
        data[TARGET] = data.velocity * KMH_PER_MS
    return data


def check_observed_dates(*frames):
    """The 7-day guard of the models and the inference (docs/DECISIONS.md); never removed."""
    dates = set()
    for frame in frames:
        dates |= set(frame.date_utc)
    if len(dates) < MIN_OBSERVED_DATES:
        raise RuntimeError(f"At least seven observed UTC dates required ({len(dates)} found); "
                           "prefer 14 complete collection days.")
    return len(dates)


def residual_profile(frame, residual, band_m=1000, by="zone"):
    """Median residual per altitude band (and zone): checks the knot model's form, e.g. a plateau near cruise."""
    data = frame.assign(residual=residual, band_low_m=(np.floor(frame.altitude_m / band_m) * band_m).astype(int))
    keys = ["band_low_m"] + ([by] if by else [])
    profile = data.groupby(keys).agg(observations=("residual", "size"), aircraft=("icao24", "nunique"),
                                     median_residual_kmh=("residual", "median"),
                                     mean_residual_kmh=("residual", "mean")).reset_index()
    profile["median_residual_ms"] = profile.median_residual_kmh / KMH_PER_MS
    return profile

"""Optional A/B/C(/D) linear comparison with the SAME existing evaluation frames.

D adds modelled wind along/across the track (src/weather.py). `airspeed_est_ms` is derived from the
target (ground speed) and must never be a feature.
"""
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

ALTITUDE = ["geo_altitude"]
SPATIAL = ["geo_altitude", "distance_km", "latitude", "longitude", "near_indicator", "altitude_x_near"]
WIND = ["tailwind_ms", "crosswind_ms"]
TARGET_DERIVED = {"velocity", "speed_kmh", "airspeed_est_ms", "icao24"}
assert not TARGET_DERIVED.intersection(SPATIAL + WIND)


def make_comparison_models(include_wind=False):
    def numeric():
        return make_pipeline(SimpleImputer(strategy="median"), StandardScaler())
    category = make_pipeline(SimpleImputer(strategy="constant", fill_value="unknown/other"),
                             OneHotEncoder(handle_unknown="ignore", drop=None))
    models = {
        "A: altitude only": (ALTITUDE, make_pipeline(numeric(), LinearRegression())),
        "B: altitude and spatial": (SPATIAL, make_pipeline(numeric(), LinearRegression())),
        "C: spatial and aircraft category": (SPATIAL + ["aircraft_category"], make_pipeline(
            ColumnTransformer([("numeric", numeric(), SPATIAL),
                               ("category", category, ["aircraft_category"])]), LinearRegression())),
    }
    if include_wind:
        models["D: spatial, category and wind"] = (SPATIAL + WIND + ["aircraft_category"], make_pipeline(
            ColumnTransformer([("numeric", numeric(), SPATIAL + WIND),
                               ("category", category, ["aircraft_category"])]), LinearRegression()))
    return models


def compare_models(train, test, split_name):
    if len(set(train.date_utc) | set(test.date_utc)) < 7:
        raise RuntimeError("At least seven observed UTC dates required for the optional A/B/C comparison.")
    if train.empty or test.empty or train.zone.nunique() < 2 or test.zone.nunique() < 2:
        raise RuntimeError("Insufficient near/far evaluation coverage.")
    # Retain unmatched metadata in all models, with an explicit unknown category.
    train, test = train.copy(), test.copy()
    for frame in (train, test):
        if frame[["icao24", "time_position"]].duplicated().any():
            raise ValueError("Duplicate observation keys in comparison frames.")
        frame["aircraft_category"] = frame.get("aircraft_category", pd.Series(index=frame.index, dtype=str)).fillna("unknown/other")
    # D only when wind was joined and at least some training rows have it (missing values are imputed).
    include_wind = all(c in train and c in test for c in WIND) and train[WIND].notna().any().all()
    rows = []
    for name, (features, model) in make_comparison_models(include_wind).items():
        assert not TARGET_DERIVED.intersection(features)
        model.fit(train[features], train.velocity)
        predicted = model.predict(test[features])
        for zone in ("all", "near", "far"):
            mask = np.ones(len(test), dtype=bool) if zone == "all" else test.zone.eq(zone).to_numpy()
            if mask.sum() < 2:
                continue
            actual, pred = test.velocity.to_numpy()[mask], predicted[mask]
            rows.append({"split": split_name, "model": name, "group": zone,
                         "n": int(mask.sum()), "aircraft": test.loc[mask, "icao24"].nunique(),
                         "MAE_m_s": mean_absolute_error(actual, pred),
                         "RMSE_m_s": np.sqrt(mean_squared_error(actual, pred)), "R_squared": r2_score(actual, pred)})
    return pd.DataFrame(rows)

"""CC-9: the single definition of the prediction models 0, A-D and RF, their splits and their evaluation (#18).

Notebook 02 imports everything from here; there are no parallel model specs. Target: ground speed in km/h
(speed_kmh = velocity x 3.6); every table also shows m/s. Altitude enters as the knot features of
src/features.py (km below/above altitude_knot_m), zone as dummies plus zone x altitude interactions.

    0   mean baseline
    A   altitude knot only
    B   A + zone, zone x altitude, airport, distance_km, flight phase (control)
    C   B + aircraft category
    D   C + modelled tail- and crosswind (only when wind was joined)
    RF  random forest on B's inputs plus latitude/longitude (comparison only)

Latitude/longitude are no linear features any more. Every encoder, imputer and scaler is fitted on the
training rows only (inside the sklearn pipeline). `velocity`, `speed_kmh`, `airspeed_est_ms` (computed from the
target) and `icao24` are never features. Splits: later days (main), other aircraft (transfer) and a random row
split that only DEMONSTRATES leakage (same aircraft and flights on both sides) and is never a result.
Everything refuses to run on fewer than seven observed UTC dates.
"""
import warnings
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import GroupShuffleSplit, train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

try:
    from .aircraft_metadata import UNKNOWN
    from .features import (KMH_PER_MS, TARGET, ZONES, add_model_features, altitude_terms, check_observed_dates,
                           interaction_columns)
except ImportError:
    from aircraft_metadata import UNKNOWN
    from features import (KMH_PER_MS, TARGET, ZONES, add_model_features, altitude_terms, check_observed_dates,
                          interaction_columns)

RANDOM_STATE = 42
WIND = ["tailwind_ms", "crosswind_ms"]
CONTEXT = ["airport", "flight_phase"]
CATEGORY = ["aircraft_category"]
TARGET_DERIVED = {"velocity", "speed_kmh", "airspeed_est_ms", "icao24"}
SPLIT_LABELS = {"later_days": "Spätere Tage (Hauptergebnis)", "other_aircraft": "Andere Flugzeuge",
                "random_rows_demo": "Zufälliger Split: Demonstration, nicht Ergebnis"}
GROUPS = ["all", *ZONES]


@dataclass
class ModelSpec:
    """Inputs and estimator of one model; `linear` models get a coefficient table."""
    numeric: list
    categorical: list = field(default_factory=list)
    kind: str = "linear"  # linear, baseline or forest

    @property
    def features(self):
        return self.numeric + self.categorical


def model_specs(config, include_wind=False):
    """Feature lists of every model for the configured knots."""
    altitude = altitude_terms(config)
    spatial = altitude + interaction_columns(config) + ["distance_km"]
    specs = {"0: mean baseline": ModelSpec(altitude, kind="baseline"),
             "A: altitude knot": ModelSpec(altitude),
             "B: + zone, airport, distance, flight phase": ModelSpec(spatial, CONTEXT),
             "C: B + aircraft category": ModelSpec(spatial, CONTEXT + CATEGORY)}
    if include_wind:
        specs["D: C + wind"] = ModelSpec(spatial + WIND, CONTEXT + CATEGORY)
    specs["RF: random forest (B + lat/lon)"] = ModelSpec(spatial + ["latitude", "longitude"], CONTEXT, kind="forest")
    for name, spec in specs.items():
        leaked = TARGET_DERIVED.intersection(spec.features)
        assert not leaked, f"{name} uses target-derived columns {leaked}"
        if spec.kind == "linear":
            assert not {"latitude", "longitude"}.intersection(spec.features), f"{name}: lat/lon not linear"
    return specs


def make_pipeline_for(spec):
    """Unfitted pipeline: imputers, scaler and one-hot encoder are fitted on the training rows only."""
    if spec.kind == "baseline":
        return DummyRegressor(strategy="mean")
    numeric = make_pipeline(SimpleImputer(strategy="median"), StandardScaler())
    # drop="first": each dummy coefficient is the difference to the first (alphabetical) training category;
    # a category not seen in training is encoded like that reference.
    drop = None if spec.kind == "forest" else "first"
    categorical = make_pipeline(SimpleImputer(strategy="constant", fill_value=UNKNOWN),
                                OneHotEncoder(handle_unknown="ignore", drop=drop, sparse_output=False))
    parts = [("numeric", numeric, spec.numeric)]
    if spec.categorical:
        parts.append(("categorical", categorical, spec.categorical))
    estimator = (RandomForestRegressor(n_estimators=150, max_depth=10, min_samples_leaf=10,
                                       random_state=RANDOM_STATE, n_jobs=-1)
                 if spec.kind == "forest" else LinearRegression())
    return make_pipeline(ColumnTransformer(parts), estimator)


def model_frame(frame, config):
    """near/middle/far rows with model features; category Unbekannt when metadata is missing; 7-day guard."""
    data = add_model_features(frame, config)
    if "aircraft_category" not in data:
        data["aircraft_category"] = UNKNOWN
    data["aircraft_category"] = data.aircraft_category.fillna(UNKNOWN)
    if data[["icao24", "time_position"]].duplicated().any():
        raise ValueError("Duplicate observation keys in the model frame.")
    check_observed_dates(data)
    return data.reset_index(drop=True)


def check_split(train, test, name, min_train=100, min_test=30):
    if len(train) < min_train or len(test) < min_test:
        raise RuntimeError(f"{name}: too few observations (train {len(train)}, test {len(test)}).")
    if train.zone.nunique() < 2 or test.zone.nunique() < 2:
        raise RuntimeError(f"{name}: train and test both need at least two zones.")
    return train, test


def split_by_date(data, train_share=0.7):
    """Main split: the first 70 % of observed UTC dates train, the later dates test."""
    dates = sorted(data.date_utc.unique())
    cut = max(1, int(len(dates) * train_share))
    train, test = data.loc[data.date_utc.isin(dates[:cut])], data.loc[data.date_utc.isin(dates[cut:])]
    return check_split(train, test, "later_days")


def split_by_aircraft(data, test_size=0.3, min_aircraft=30):
    """Transfer split: 30 % of the aircraft (all their rows) are held out, same period."""
    if data.icao24.nunique() < min_aircraft:
        raise RuntimeError("Too few distinct aircraft for the held-out-aircraft evaluation.")
    splitter = GroupShuffleSplit(n_splits=1, test_size=test_size, random_state=RANDOM_STATE)
    train_index, test_index = next(splitter.split(data, groups=data.icao24))
    train, test = data.iloc[train_index], data.iloc[test_index]
    assert set(train.icao24).isdisjoint(test.icao24)
    return check_split(train, test, "other_aircraft")


def split_random_demo(data, test_size=0.3):
    """LEAKAGE DEMONSTRATION ONLY: random rows, so the same aircraft and flights are in train and test."""
    train, test = train_test_split(data, test_size=test_size, random_state=RANDOM_STATE)
    return check_split(train, test, "random_rows_demo")


def has_wind(train):
    return all(c in train for c in WIND) and bool(train[WIND].notna().any().all())


def evaluate_models(train, test, split_name, config):
    """Fit every model on train, predict test; metrics per zone in km/h and m/s, plus test predictions."""
    check_observed_dates(train, test)
    specs = model_specs(config, include_wind=has_wind(train))
    rows, predictions, fitted = [], test.copy(), {}
    for name, spec in specs.items():
        model = make_pipeline_for(spec)
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message="Found unknown categories")
            model.fit(train[spec.features], train[TARGET])
            predicted = model.predict(test[spec.features])
        predictions[name], fitted[name] = predicted, model
        for group in GROUPS:
            mask = np.ones(len(test), dtype=bool) if group == "all" else test.zone.eq(group).to_numpy()
            if mask.sum() < 2:
                continue
            actual = test[TARGET].to_numpy()[mask]
            rmse = float(np.sqrt(mean_squared_error(actual, predicted[mask])))
            mae = float(mean_absolute_error(actual, predicted[mask]))
            rows.append({"split": split_name, "model": name, "group": group, "n": int(mask.sum()),
                         "aircraft": test.loc[mask, "icao24"].nunique(), "RMSE_kmh": rmse, "MAE_kmh": mae,
                         "RMSE_ms": rmse / KMH_PER_MS, "MAE_ms": mae / KMH_PER_MS,
                         "R_squared": float(r2_score(actual, predicted[mask]))})
    return pd.DataFrame(rows), predictions, fitted


def coefficient_table(fitted, train, config):
    """Coefficients of the linear models: per training SD (standardized) and in original units."""
    specs = model_specs(config, include_wind=has_wind(train))
    rows = []
    for name, spec in specs.items():
        if spec.kind != "linear" or name not in fitted:
            continue
        transformer, regression = fitted[name][0], fitted[name][-1]
        names = transformer.get_feature_names_out()
        design = pd.DataFrame(transformer.transform(train[spec.features]), columns=names)
        scaler = transformer.named_transformers_["numeric"][-1]
        scale = dict(zip(spec.numeric, scaler.scale_))
        references = {}
        if "categorical" in transformer.named_transformers_:
            encoder = transformer.named_transformers_["categorical"][-1]
            references = {column: categories[index] for column, categories, index in
                          zip(spec.categorical, encoder.categories_, encoder.drop_idx_)}
        for feature_name, coefficient in zip(names, regression.coef_):
            part, raw = feature_name.split("__", 1)
            if part == "numeric":
                per_sd, per_unit = coefficient, coefficient / scale[raw]
                unit = ("km/h per 1,000 m" if raw.startswith("alt_") else
                        "km/h per km" if raw == "distance_km" else
                        "km/h per m/s" if raw in WIND else "km/h (dummy, reference zone far)")
                reference = ""
            else:
                column = next(c for c in spec.categorical if raw.startswith(c + "_"))
                per_unit, per_sd = coefficient, coefficient * design[feature_name].std(ddof=0)
                unit, reference = "km/h vs. reference category", references[column]
            rows.append({"model": name, "feature": raw, "per_unit_kmh": per_unit, "per_unit_ms": per_unit / KMH_PER_MS,
                         "per_sd_kmh": per_sd, "unit": unit, "reference": reference})
        rows.append({"model": name, "feature": "intercept", "per_unit_kmh": regression.intercept_,
                     "per_unit_ms": regression.intercept_ / KMH_PER_MS, "per_sd_kmh": np.nan,
                     "unit": "km/h at the training mean of every numeric input", "reference": ""})
    return pd.DataFrame(rows)


def rmse_bootstrap(predictions, models, split_name, n_boot=200):
    """95 % interval of the RMSE per model and zone, resampling whole test aircraft (random_state 42)."""
    rng = np.random.default_rng(RANDOM_STATE)
    rows = []
    for group in GROUPS:
        part = predictions if group == "all" else predictions.loc[predictions.zone.eq(group)]
        if part.icao24.nunique() < 2:
            continue
        codes, aircraft = pd.factorize(part.icao24)
        counts = np.bincount(codes, minlength=len(aircraft))
        draws = rng.integers(0, len(aircraft), size=(n_boot, len(aircraft)))
        weights = np.stack([np.bincount(d, minlength=len(aircraft)) for d in draws])
        for model in models:
            sse = np.bincount(codes, weights=(part[TARGET] - part[model]).to_numpy() ** 2, minlength=len(aircraft))
            rmse = np.sqrt((weights @ sse) / (weights @ counts))
            rows.append({"split": split_name, "model": model, "group": group,
                         "RMSE_kmh_ci_low": float(np.percentile(rmse, 2.5)),
                         "RMSE_kmh_ci_high": float(np.percentile(rmse, 97.5)), "bootstrap_samples": n_boot})
    return pd.DataFrame(rows)


def rmse_figure(metrics, path, intervals=None):
    """RMSE (km/h) per model x zone x split; the random split is labelled as a demonstration."""
    import matplotlib.pyplot as plt
    colors = {"all": "#8C8C8C", "near": "#DD8452", "middle": "#55A868", "far": "#4C72B0"}
    labels = {"all": "alle", "near": "nah", "middle": "mittel", "far": "fern"}
    splits = [s for s in SPLIT_LABELS if s in set(metrics.split)]
    models = list(dict.fromkeys(metrics.model))
    fig, axes = plt.subplots(1, len(splits), figsize=(6 * len(splits), 5), sharey=True, squeeze=False)
    width = 0.8 / len(GROUPS)
    for ax, split in zip(axes[0], splits):
        part = metrics.loc[metrics.split.eq(split)]
        for offset, group in enumerate(GROUPS):
            values = part.loc[part.group.eq(group)].set_index("model").RMSE_kmh.reindex(models)
            x = np.arange(len(models)) + (offset - (len(GROUPS) - 1) / 2) * width
            error = None
            if intervals is not None:
                ci = intervals.loc[intervals.split.eq(split) & intervals.group.eq(group)].set_index("model").reindex(models)
                error = np.vstack([values - ci.RMSE_kmh_ci_low, ci.RMSE_kmh_ci_high - values])
            ax.bar(x, values, width, color=colors[group], label=labels[group], yerr=error, capsize=2)
        ax.set_xticks(np.arange(len(models)), [m.split(":")[0] for m in models])
        ax.set_title(SPLIT_LABELS[split], fontsize=11, color="#B03030" if split == "random_rows_demo" else "black")
        ax.set_xlabel("Modell")
    axes[0][0].set_ylabel("RMSE (km/h)")
    axes[0][-1].legend(title="Zone")
    fig.suptitle("Vorhersagefehler pro Modell, Zone und Split (tiefer = besser)")
    fig.tight_layout()
    fig.savefig(path, dpi=160, facecolor="white")
    plt.close(fig)

"""CC-8: test the research question directly with OLS and cluster-robust standard errors (#19).

Main model (all observations, descriptive inference, speed in km/h, altitude terms in km; src/features.py):
    speed_kmh ~ (alt_low_km + alt_high_km) * C(zone, Treatment('far')) + C(airport) + C(flight_phase)
Standard errors are clustered by aircraft (icao24), because the positions of one aircraft are not independent;
p-values and intervals use t with (number of aircraft - 1) degrees of freedom.

- The coefficients alt_low_km:C(zone, ...)[T.near] and alt_high_km:C(zone, ...)[T.near] say how much steeper
  (km/h per 1,000 m) speed rises with altitude near the airports than en route (hypothesis 1, slide 11).
- Wald tests: near-zone interaction = 0 (2 coefficients) and every zone interaction = 0.
- Slopes per zone with 95 % CI are linear combinations of coefficients (contrasts with the full covariance).
Variants: (a) near zone only, airport x altitude (ZRH vs GVA vs BSL); (b) aircraft category x altitude with the
main model's controls; levels with fewer aircraft than inference.min_aircraft_per_level are left out and counted.
Refuses to run on fewer than seven observed UTC dates, like the models.
"""
import numpy as np
import pandas as pd

try:
    from .features import (KMH_PER_MS, REFERENCE_ZONE, ZONES, add_model_features, altitude_terms,
                           check_observed_dates, knot_settings, residual_profile)
except ImportError:
    from features import (KMH_PER_MS, REFERENCE_ZONE, ZONES, add_model_features, altitude_terms,
                          check_observed_dates, knot_settings, residual_profile)

ZONE_FACTOR = "C(zone, Treatment('far'))"
ZONE_LABELS = {"near": "nah", "middle": "mittel", "far": "fern"}
ZONE_COLORS = {"near": "#DD8452", "middle": "#55A868", "far": "#4C72B0"}
REQUIRED = ["icao24", "date_utc", "altitude_m", "velocity", "zone", "airport", "flight_phase"]


def factor(column, reference):
    return f"C({column}, Treatment('{reference}'))"


def formulas(config):
    """The three model formulas for the configured knots (one place, also printed in the notebook)."""
    altitude = " + ".join(altitude_terms(config))
    return {"main": f"speed_kmh ~ ({altitude}) * {ZONE_FACTOR} + C(airport) + C(flight_phase)",
            "airport_near": f"speed_kmh ~ {{airport_factor}} * ({altitude}) + C(flight_phase)",
            "category": (f"speed_kmh ~ {{category_factor}} * ({altitude}) + {ZONE_FACTOR} + C(airport) "
                         "+ C(flight_phase)")}


def fit_clustered(formula, data):
    """OLS with standard errors clustered by aircraft; t-based inference with G - 1 degrees of freedom."""
    import statsmodels.formula.api as smf
    groups = pd.factorize(data.icao24)[0]
    return smf.ols(formula, data=data).fit(cov_type="cluster", cov_kwds={"groups": groups}, use_t=True)


def coefficient_table(result, data, model):
    """Estimate, SE, 95 % CI and p per coefficient, in km/h and m/s, with n observations and aircraft."""
    ci = result.conf_int(0.05)
    table = pd.DataFrame({"model": model, "term": result.params.index,
                          "estimate_kmh": result.params.to_numpy(), "se_kmh": result.bse.to_numpy(),
                          "ci_low_kmh": ci[0].to_numpy(), "ci_high_kmh": ci[1].to_numpy(),
                          "p_value": result.pvalues.to_numpy()})
    for column in ("estimate", "se", "ci_low", "ci_high"):
        table[f"{column}_ms"] = table[f"{column}_kmh"] / KMH_PER_MS
    table["n_observations"], table["n_aircraft"] = int(result.nobs), data.icao24.nunique()
    table["unit"] = np.where(table.term.str.contains("alt_"), "km/h per 1,000 m (m/s per 1,000 m)",
                             "km/h (m/s) vs. reference")
    return table


def interaction_name(names, term, factor_text, level):
    """Parameter name of term x factor level, whatever order patsy wrote it in."""
    wanted = {term, f"{factor_text}[T.{level}]"}
    for name in names:
        if set(name.split(":")) == wanted:
            return name
    raise KeyError(f"No interaction {term} x {factor_text}[T.{level}] in the model.")


def wald_interaction(result, terms, factor_text, levels, label):
    """Joint Wald (F) test that all term x level interactions are zero."""
    names = list(result.params.index)
    chosen = [interaction_name(names, t, factor_text, level) for level in levels for t in terms]
    restriction = np.zeros((len(chosen), len(names)))
    for row, name in enumerate(chosen):
        restriction[row, names.index(name)] = 1
    test = result.wald_test(restriction, scalar=True, use_f=True)
    return {"test": label, "coefficients": len(chosen), "terms": "; ".join(chosen),
            "F": float(np.squeeze(test.statistic)), "df_num": float(test.df_num),
            "df_denom": float(test.df_denom), "p_value": float(test.pvalue)}


def group_slopes(result, data, terms, column, factor_text, levels, reference, segment_labels):
    """Slope (km/h per 1,000 m) per level and altitude segment = base term + interaction, with 95 % CI."""
    names = list(result.params.index)
    rows = []
    for level in levels:
        subset = data.loc[data[column].eq(level)]
        for term in terms:
            contrast = np.zeros(len(names))
            contrast[names.index(term)] = 1
            if level != reference:
                contrast[names.index(interaction_name(names, term, factor_text, level))] = 1
            test = result.t_test(contrast)
            low, high = np.asarray(test.conf_int(alpha=0.05)).ravel()
            rows.append({column: level, "segment": segment_labels[term], "term": term,
                         "slope_kmh_per_1000m": float(np.squeeze(test.effect)),
                         "se_kmh": float(np.squeeze(test.sd)), "ci_low_kmh": float(low), "ci_high_kmh": float(high),
                         "p_value_slope_zero": float(np.squeeze(test.pvalue)),
                         "n_observations": len(subset), "n_aircraft": subset.icao24.nunique()})
    table = pd.DataFrame(rows)
    for column_name in ("slope", "se", "ci_low", "ci_high"):
        source = "slope_kmh_per_1000m" if column_name == "slope" else f"{column_name}_kmh"
        target = "slope_ms_per_1000m" if column_name == "slope" else f"{column_name}_ms"
        table[target] = table[source] / KMH_PER_MS
    return table


def segment_labels(config):
    """German labels of the altitude segments, e.g. «unter 3'000 m» / «über 3'000 m»."""
    knot, knot2 = knot_settings(config)

    def metres(value):
        return f"{value:,.0f}".replace(",", "'") + " m"
    if knot2 is None:
        return {"alt_low_km": f"unter {metres(knot)}", "alt_high_km": f"über {metres(knot)}"}
    return {"alt_low_km": f"unter {metres(knot)}", "alt_high_km": f"{metres(knot)} bis {metres(knot2)}",
            "alt_top_km": f"über {metres(knot2)}"}


def inference_frame(frame, config):
    """Rows usable for inference (near/middle/far, no missing model input) with model features; 7-day guard."""
    missing = [c for c in REQUIRED if c not in frame]
    if missing:
        raise ValueError(f"Inference needs the columns {missing}.")
    data = add_model_features(frame.dropna(subset=REQUIRED), config)
    check_observed_dates(data)
    if data.zone.nunique() < len(ZONES):
        raise RuntimeError("Inference needs observations in all three zones.")
    return data.reset_index(drop=True)


def frequent_levels(data, column, min_aircraft):
    """Levels with at least min_aircraft distinct aircraft, and a table of all levels with their counts."""
    counts = data.groupby(column).agg(observations=("icao24", "size"), aircraft=("icao24", "nunique")).reset_index()
    counts["included"] = counts.aircraft.ge(min_aircraft)
    return sorted(counts.loc[counts.included, column]), counts


def reference_level(levels, preferred, data, column):
    if preferred in levels:
        return preferred
    return data.loc[data[column].isin(levels), column].value_counts().index[0]


def run_inference(frame, config):
    """Fit the main model and both variants; returns a dict of result tables (see module docstring)."""
    data = inference_frame(frame, config)
    terms = altitude_terms(config)
    labels = segment_labels(config)
    forms = formulas(config)
    tables = {}
    main = fit_clustered(forms["main"], data)
    tables["main_coefficients"] = coefficient_table(main, data, "main")
    others = [z for z in ZONES if z != REFERENCE_ZONE]
    tables["interaction_tests"] = pd.DataFrame([
        wald_interaction(main, terms, ZONE_FACTOR, ["near"], "altitude x zone: near vs far"),
        wald_interaction(main, terms, ZONE_FACTOR, others, "altitude x zone: all zones")])
    tables["zone_slopes"] = group_slopes(main, data, terms, "zone", ZONE_FACTOR, ZONES, REFERENCE_ZONE, labels)
    tables["residual_profile"] = residual_profile(data, main.resid.to_numpy())
    min_aircraft = int(config["inference"]["min_aircraft_per_level"])
    # (a) ZRH vs GVA vs BSL near the airports only.
    near = data.loc[data.zone.eq("near")].reset_index(drop=True)
    airports, airport_counts = frequent_levels(near, "airport", min_aircraft)
    tables["airport_levels"] = airport_counts
    if len(airports) >= 2:
        near = near.loc[near.airport.isin(airports)].reset_index(drop=True)
        reference = reference_level(airports, "ZRH", near, "airport")
        airport_factor = factor("airport", reference)
        result = fit_clustered(forms["airport_near"].format(airport_factor=airport_factor), near)
        tables["airport_coefficients"] = coefficient_table(result, near, "airport_near")
        tables["airport_slopes"] = group_slopes(result, near, terms, "airport", airport_factor, airports,
                                                reference, labels)
        tables["interaction_tests"] = pd.concat([tables["interaction_tests"], pd.DataFrame([wald_interaction(
            result, terms, airport_factor, [a for a in airports if a != reference],
            f"altitude x airport (near zone, reference {reference})")])], ignore_index=True)
    # (b) aircraft category x altitude with the main model's controls.
    if "aircraft_category" in data:
        categories, category_counts = frequent_levels(data.dropna(subset=["aircraft_category"]),
                                                      "aircraft_category", min_aircraft)
        tables["category_levels"] = category_counts
        if len(categories) >= 2:
            subset = data.loc[data.aircraft_category.isin(categories)].reset_index(drop=True)
            reference = reference_level(categories, "Kurzstrecke", subset, "aircraft_category")
            category_factor = factor("aircraft_category", reference)
            result = fit_clustered(forms["category"].format(category_factor=category_factor), subset)
            tables["category_coefficients"] = coefficient_table(result, subset, "category")
            tables["category_slopes"] = group_slopes(result, subset, terms, "aircraft_category", category_factor,
                                                     categories, reference, labels)
            tables["interaction_tests"] = pd.concat([tables["interaction_tests"], pd.DataFrame([wald_interaction(
                result, terms, category_factor, [c for c in categories if c != reference],
                f"altitude x aircraft category (reference {reference})")])], ignore_index=True)
    return tables


def slope_figure(slopes, path, config):
    """«Steigung pro Zone mit 95-%-KI»: one panel per altitude segment, zones in their slide colours."""
    import matplotlib.pyplot as plt
    labels = segment_labels(config)
    segments = [labels[t] for t in altitude_terms(config)]
    with plt.rc_context({"font.size": 13}):
        fig, axes = plt.subplots(1, len(segments), figsize=(5 * len(segments), 4.5), sharey=False)
        for ax, segment in zip(np.atleast_1d(axes), segments):
            part = slopes.loc[slopes.segment.eq(segment)].set_index("zone").reindex(ZONES)
            for x, zone in enumerate(ZONES):
                row = part.loc[zone]
                ax.errorbar(x, row.slope_kmh_per_1000m,
                            yerr=[[row.slope_kmh_per_1000m - row.ci_low_kmh], [row.ci_high_kmh - row.slope_kmh_per_1000m]],
                            fmt="o", color=ZONE_COLORS[zone], markersize=9, capsize=6, linewidth=2)
            ax.axhline(0, color="#999999", linewidth=0.8)
            ax.set_xticks(range(len(ZONES)), [ZONE_LABELS[z] for z in ZONES])
            ax.set_xlim(-0.5, len(ZONES) - 0.5)
            ax.set_title(f"Höhe {segment}")
            ax.set_xlabel("Zone")
            ax.set_ylabel("Steigung (km/h pro 1'000 m)")
        fig.suptitle("Steigung der Geschwindigkeit über Grund pro Zone, mit 95-%-Konfidenzintervall")
        fig.tight_layout()
        fig.savefig(path, dpi=200, facecolor="white")
        plt.close(fig)


def residual_figure(profile, path):
    """Median residual of the main model per 1,000 m band and zone: a systematic arc means a missing knot."""
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(10, 4.5))
    for zone in ZONES:
        part = profile.loc[profile.zone.eq(zone)]
        ax.plot(part.band_low_m + 500, part.median_residual_kmh, marker="o", color=ZONE_COLORS[zone],
                label=ZONE_LABELS[zone])
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_xlabel("Flughöhe (m), Bandmitte")
    ax.set_ylabel("Median-Residuum (km/h)")
    ax.set_title("Formprüfung des Knick-Modells: Residuen pro 1'000-m-Band")
    ax.legend(title="Zone")
    fig.tight_layout()
    fig.savefig(path, dpi=160, facecolor="white")
    plt.close(fig)

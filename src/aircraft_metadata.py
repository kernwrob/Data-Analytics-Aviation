"""Optional, pinned aircraft metadata; descriptive attributes, never flight identity."""
import pandas as pd

UNKNOWN = "unknown/other"
# Conservative finite mapping of ICAO Doc 8643 description codes, not weight or flight phase.
CATEGORY_MAP = {
    **{code: "Jet landplane" for code in ("L1J", "L2J", "L3J", "L4J")},
    **{code: "Turboprop landplane" for code in ("L1T", "L2T", "L4T")},
    **{code: "Piston landplane" for code in ("L1P", "L2P", "L4P")},
    **{code: "Helicopter" for code in ("H1T", "H2T", "H3T", "H1P", "H2P")},
}
SOURCE_FIELDS = {"manufacturername": "aircraft_manufacturer", "model": "aircraft_model",
                 "typecode": "aircraft_typecode", "icaoaircrafttype": "aircraft_icao_description"}
ATTRIBUTES = list(SOURCE_FIELDS.values())
COLUMNS = ["icao24", *ATTRIBUTES, "aircraft_category", "metadata_source_record", "metadata_conflict"]


def normalize_icao24(series):
    return series.astype("string").str.strip().str.lower()


def prepare_metadata(raw=None):
    """Prefer most complete record, breaking ties by original CSV record order.

    Never merge fields from different source records. All duplicate candidates and
    chosen records are audited; conflicting description codes map to unknown/other.
    """
    if raw is None:
        return pd.DataFrame({name: pd.Series(dtype="object") for name in COLUMNS}), {
            "source_available": False, "raw_metadata_rows": 0, "invalid_metadata_keys": 0,
            "duplicate_keys": 0, "duplicate_rows_removed": 0, "conflicting_keys": 0,
            "unique_metadata_keys": 0}, pd.DataFrame()
    if "icao24" not in raw:
        raise ValueError("Aircraft metadata must have an icao24 field.")
    data = raw.reindex(columns=["icao24", *SOURCE_FIELDS], fill_value="").copy()
    data["icao24"] = normalize_icao24(data.icao24)
    data["metadata_source_record"] = range(1, len(data) + 1)
    valid = data.icao24.str.fullmatch("[0-9a-f]{6}", na=False)
    invalid_count = int((~valid).sum())
    data = data.loc[valid].rename(columns=SOURCE_FIELDS).copy()
    for column in ATTRIBUTES:
        data[column] = data[column].fillna("").astype(str).str.strip()
    for column in ("aircraft_typecode", "aircraft_icao_description"):
        data[column] = data[column].str.upper()
    data["completeness"] = data[ATTRIBUTES].ne("").sum(axis=1)
    duplicates = data.loc[data.icao24.duplicated(keep=False)].copy()
    conflicts, description_conflicts = set(), set()
    for key, group in duplicates.groupby("icao24"):
        for column in ATTRIBUTES:
            if group.loc[group[column].ne(""), column].nunique() > 1:
                conflicts.add(key)
                if column == "aircraft_icao_description":
                    description_conflicts.add(key)
    chosen = data.sort_values(["completeness", "metadata_source_record"], ascending=[False, True])
    chosen = chosen.drop_duplicates("icao24", keep="first").sort_values("icao24")
    chosen["metadata_conflict"] = chosen.icao24.isin(conflicts).astype(int)
    chosen["aircraft_category"] = chosen.aircraft_icao_description.map(CATEGORY_MAP).fillna(UNKNOWN)
    chosen.loc[chosen.icao24.isin(description_conflicts), "aircraft_category"] = UNKNOWN
    if not duplicates.empty:
        selected = set(chosen.metadata_source_record)
        duplicates["selected"] = duplicates.metadata_source_record.isin(selected)
        duplicates["conflicting_key"] = duplicates.icao24.isin(conflicts)
    audit = {"source_available": True, "raw_metadata_rows": len(raw),
             "invalid_metadata_keys": invalid_count, "duplicate_keys": duplicates.icao24.nunique(),
             "duplicate_rows_removed": len(data) - len(chosen), "conflicting_keys": len(conflicts),
             "unique_metadata_keys": len(chosen)}
    return chosen[COLUMNS].reset_index(drop=True), audit, duplicates


def enrich_observations(observations, metadata):
    before_keys = observations[["icao24", "time_position"]].reset_index(drop=True)
    if before_keys.duplicated().any():
        raise ValueError("Observation keys are not unique before metadata integration.")
    enriched = observations.merge(metadata, on="icao24", how="left", validate="many_to_one", indicator=True)
    if len(enriched) != len(observations) or not enriched[["icao24", "time_position"]].equals(before_keys):
        raise AssertionError("Metadata integration changed observations or their unique keys.")
    matched = enriched._merge.eq("both")
    aircraft = observations.icao24.nunique()
    matched_aircraft = enriched.loc[matched, "icao24"].nunique()
    audit = {"observations_before": len(observations), "observations_after": len(enriched),
             "matched_observations": int(matched.sum()), "unmatched_observations": int((~matched).sum()),
             "observation_match_fraction": float(matched.mean()) if len(matched) else 0.0,
             "distinct_aircraft": aircraft, "matched_distinct_aircraft": matched_aircraft,
             "aircraft_match_fraction": matched_aircraft / aircraft if aircraft else 0.0,
             "gained": 0, "lost": 0}
    enriched["metadata_matched"] = matched.astype(int)
    enriched["aircraft_category"] = enriched.aircraft_category.fillna(UNKNOWN)
    return enriched.drop(columns="_merge"), audit

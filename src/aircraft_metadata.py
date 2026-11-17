"""Optional, pinned aircraft metadata; descriptive attributes, never flight identity.

Aircraft category (frozen 2026-11-12, docs/DECISIONS.md «Aircraft category by typecode»):
1. typecode found in data/reference/typecode_category.csv,
2. otherwise a conservative fallback on the ICAO Doc 8643 description (L?T -> Turboprop;
   L?P, H??, G?? -> Sonstige; jets and everything else are not guessed),
3. otherwise, or without a metadata match, Unbekannt. Unbekannt is never merged with Sonstige.
Duplicate records that disagree on typecode or description also give Unbekannt.
"""
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
TYPECODE_REFERENCE = ROOT / "data/reference/typecode_category.csv"
UNKNOWN = "Unbekannt"
OTHER = "Sonstige"
CATEGORIES = ["Kurzstrecke", "Regionaljet", "Langstrecke", "Turboprop", "Business-Jet", OTHER, UNKNOWN]
CATEGORY_SOURCES = ["typecode", "icao_description", "none"]
REFERENCE_COLUMNS = ["typecode", "category", "example_model", "source_note"]
# Fallback on ICAO Doc 8643 description codes (e.g. L2T = landplane, two turboprop engines).
DESCRIPTION_RULES = [(re.compile(r"L\dT"), "Turboprop"),
                     (re.compile(r"L\dP|H\d[A-Z]|G\d[A-Z]"), OTHER)]
SOURCE_FIELDS = {"manufacturername": "aircraft_manufacturer", "model": "aircraft_model",
                 "typecode": "aircraft_typecode", "icaoaircrafttype": "aircraft_icao_description"}
# The monthly «complete» dumps use camelCase names and call the description icaoAircraftClass.
COLUMN_ALIASES = {"icaoaircraftclass": "icaoaircrafttype"}
ATTRIBUTES = list(SOURCE_FIELDS.values())
COLUMNS = ["icao24", *ATTRIBUTES, "aircraft_category", "category_source", "category_conflict",
           "metadata_source_record", "metadata_conflict"]


def normalize_icao24(series):
    return series.astype("string").str.strip().str.lower()


def normalize_metadata_columns(raw):
    """Lower-case, unquoted column names; icaoAircraftClass becomes icaoaircrafttype."""
    names = [COLUMN_ALIASES.get(n, n) for n in
             (str(c).strip().strip("'\"").strip().lower() for c in raw.columns)]
    if len(set(names)) != len(names):
        raise ValueError(f"Ambiguous metadata columns after normalization: {names}")
    return raw.set_axis(names, axis=1)


def read_metadata_csv(path):
    """Read either dump format as strings; the quote character is taken from the first byte."""
    with open(path, "rb") as f:
        first = f.read(1)
    quote = "'" if first == b"'" else '"'
    raw = pd.read_csv(path, dtype=str, keep_default_na=False, quotechar=quote)
    return normalize_metadata_columns(raw)


def load_typecode_categories(path=TYPECODE_REFERENCE):
    """Versioned typecode -> category table; refuses unknown categories and duplicate typecodes."""
    table = pd.read_csv(path, dtype=str, keep_default_na=False)
    if list(table.columns) != REFERENCE_COLUMNS:
        raise ValueError(f"{path}: columns must be {REFERENCE_COLUMNS}.")
    table["typecode"] = table.typecode.str.strip().str.upper()
    table["category"] = table.category.str.strip()
    if table.typecode.eq("").any() or table.typecode.duplicated().any():
        raise ValueError(f"{path}: typecodes must be non-empty and unique.")
    invalid = sorted(set(table.category) - set(CATEGORIES[:-1]))
    if invalid:
        raise ValueError(f"{path}: categories {invalid} are not in the frozen schema (Unbekannt is not mappable).")
    return table


def description_category(code):
    for pattern, category in DESCRIPTION_RULES:
        if pattern.fullmatch(code or ""):
            return category
    return None


def assign_categories(metadata, typecodes):
    """Category and its source per metadata row; conflicting rows are Unbekannt with source none."""
    lookup = dict(zip(typecodes.typecode, typecodes.category))
    by_typecode = metadata.aircraft_typecode.map(lookup)
    by_description = metadata.aircraft_icao_description.map(description_category)
    conflict = metadata.category_conflict.eq(1)
    category = by_typecode.fillna(by_description).fillna(UNKNOWN)
    source = pd.Series("none", index=metadata.index)
    source[by_description.notna()] = "icao_description"
    source[by_typecode.notna()] = "typecode"
    category[conflict], source[conflict] = UNKNOWN, "none"
    return category, source


def prepare_metadata(raw=None, typecodes=None):
    """Prefer most complete record, breaking ties by original CSV record order.

    Never merge fields from different source records. All duplicate candidates and
    chosen records are audited; conflicting typecodes or description codes map to Unbekannt.
    """
    empty_audit = {"source_available": False, "raw_metadata_rows": 0, "invalid_metadata_keys": 0,
                   "duplicate_keys": 0, "duplicate_rows_removed": 0, "conflicting_keys": 0,
                   "typecode_conflicting_keys": 0, "description_conflicting_keys": 0, "unique_metadata_keys": 0}
    if raw is None:
        return pd.DataFrame({name: pd.Series(dtype="object") for name in COLUMNS}), empty_audit, pd.DataFrame()
    typecodes = load_typecode_categories() if typecodes is None else typecodes
    raw = normalize_metadata_columns(raw)
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
    conflicts = {column: set() for column in ATTRIBUTES}
    for key, group in duplicates.groupby("icao24"):
        for column in ATTRIBUTES:
            if group.loc[group[column].ne(""), column].nunique() > 1:
                conflicts[column].add(key)
    any_conflict = set().union(*conflicts.values())
    category_conflicts = conflicts["aircraft_typecode"] | conflicts["aircraft_icao_description"]
    chosen = data.sort_values(["completeness", "metadata_source_record"], ascending=[False, True])
    chosen = chosen.drop_duplicates("icao24", keep="first").sort_values("icao24")
    chosen["metadata_conflict"] = chosen.icao24.isin(any_conflict).astype(int)
    chosen["category_conflict"] = chosen.icao24.isin(category_conflicts).astype(int)
    chosen["aircraft_category"], chosen["category_source"] = assign_categories(chosen, typecodes)
    if not duplicates.empty:
        selected = set(chosen.metadata_source_record)
        duplicates["selected"] = duplicates.metadata_source_record.isin(selected)
        duplicates["conflicting_key"] = duplicates.icao24.isin(any_conflict)
        duplicates["typecode_conflict"] = duplicates.icao24.isin(conflicts["aircraft_typecode"])
    audit = {"source_available": True, "raw_metadata_rows": len(raw),
             "invalid_metadata_keys": invalid_count, "duplicate_keys": duplicates.icao24.nunique(),
             "duplicate_rows_removed": len(data) - len(chosen), "conflicting_keys": len(any_conflict),
             "typecode_conflicting_keys": len(conflicts["aircraft_typecode"]),
             "description_conflicting_keys": len(conflicts["aircraft_icao_description"]),
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
    enriched["aircraft_category"] = enriched.aircraft_category.fillna(UNKNOWN)
    enriched["category_source"] = enriched.category_source.fillna("none")
    by_typecode = int((matched & enriched.category_source.eq("typecode")).sum())
    audit = {"observations_before": len(observations), "observations_after": len(enriched),
             "matched_observations": int(matched.sum()), "unmatched_observations": int((~matched).sum()),
             "observation_match_fraction": float(matched.mean()) if len(matched) else 0.0,
             "distinct_aircraft": aircraft, "matched_distinct_aircraft": matched_aircraft,
             "aircraft_match_fraction": matched_aircraft / aircraft if aircraft else 0.0,
             # Share of metadata-matched observations whose typecode is in the reference table (target >= 0.9).
             "typecode_mapped_fraction": by_typecode / int(matched.sum()) if matched.any() else 0.0,
             "gained": 0, "lost": 0}
    enriched["metadata_matched"] = matched.astype(int)
    return enriched.drop(columns="_merge"), audit

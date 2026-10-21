"""Audit collected files and report coverage; never fit models from a pilot."""
import hashlib
import json
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from prepare import ROOT, clean_and_join, read_states
from collection_coverage import summarize_coverage


def main():
    config = json.loads((ROOT / "config.json").read_text())
    manifest_path = ROOT / "data/raw/manifest.jsonl"
    if not manifest_path.exists():
        raise SystemExit("No collection manifest yet. Run src/collect.py first.")
    entries = [json.loads(line) for line in manifest_path.read_text().splitlines() if line.strip()]
    files = []
    for entry in entries:
        if "path" in entry:
            path = ROOT / entry["path"]
            valid = path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == entry["sha256"]
            files.append({"path": entry["path"], "sha256_matches": valid})
    if any(not item["sha256_matches"] for item in files):
        raise SystemExit("A raw file is missing or its checksum changed. Resolve before analysis.")
    folder = ROOT / "outputs/pilot"
    folder.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(files).to_csv(folder / "file_integrity.csv", index=False)
    snapshots = pd.DataFrame([e for e in entries if e["source_url"].endswith("/states/all")])
    lines = ["# Collection pilot report", "",
             f"Generated UTC: {datetime.now(timezone.utc).isoformat()}", "",
             "This report summarizes all local collection attempts, not a completed analysis.",
             f"Raw files checked against manifest SHA-256: {len(files)}; all match.", ""]
    if not snapshots.empty:
        snapshots["success"] = snapshots.apply(lambda row: row.get("outcome") == "success" or
                                                (pd.isna(row.get("outcome")) and pd.notna(row.get("path"))), axis=1)
        snapshots["deferred"] = snapshots.get("outcome", pd.Series(index=snapshots.index, dtype=str)).eq("deferred")
        snapshots["attempted"] = ~snapshots.deferred
        snapshots["failure"] = ~snapshots.success & ~snapshots.deferred
        snapshots["empty"] = snapshots.success & snapshots.get("state_count", pd.Series(index=snapshots.index, dtype=float)).eq(0)
        snapshots["hour_utc"] = pd.to_datetime(snapshots.retrieved_at_utc, utc=True).dt.floor("h")
        coverage = snapshots.groupby("hour_utc").agg(invocations=("success", "size"), attempts=("attempted", "sum"),
                    successful=("success", "sum"), failed=("failure", "sum"),
                    deferred=("deferred", "sum"), empty=("empty", "sum"))
        hours = pd.date_range(coverage.index.min(), coverage.index.max(), freq="h")
        coverage = coverage.reindex(hours, fill_value=0).rename_axis("hour_utc")
        coverage.to_csv(folder / "hourly_coverage.csv")
        lines += [f"Snapshot invocations: {len(snapshots)}; request attempts: {int(snapshots.attempted.sum())}; "
                  f"successful: {int(snapshots.success.sum())}; "
                  f"failed: {int(snapshots.failure.sum())}; deferred without request: {int(snapshots.deferred.sum())}; "
                  f"empty: {int(snapshots['empty'].sum())}.",
                  "Attempted hourly coverage (UTC; zeros between first and last attempted hours are retained):",
                  "", "```text", coverage.to_string(), "```", ""]
    schedule_path = folder / "schedule.json"
    if schedule_path.exists():
        schedule = json.loads(schedule_path.read_text(encoding="utf-8-sig"))
        stop_path = folder / "stop.json"
        stop = json.loads(stop_path.read_text(encoding="utf-8-sig")) if stop_path.exists() else {}
        end = min(pd.Timestamp(stop.get("stopped_at_utc", datetime.now(timezone.utc).isoformat())),
                  pd.Timestamp(schedule["repetition_ends_local"]))
        attempts, slots, intervals, scheduled_summary = summarize_coverage(
            entries, schedule["first_scheduled_local"], end, config["interval_seconds"])
        slots.to_csv(folder / "scheduled_coverage.csv", index=False)
        intervals.to_csv(folder / "sampling_intervals.csv", index=False)
        (folder / "coverage_summary.json").write_text(json.dumps(scheduled_summary, indent=2) + "\n", encoding="utf-8")
        lines += ["## Scheduled pilot coverage", "",
                  f"First successful retrieval UTC: {scheduled_summary['first_success_utc']}",
                  f"Latest successful retrieval UTC: {scheduled_summary['latest_success_utc']}",
                  f"Task state: {stop.get('state', 'not captured')}; stopped UTC: {stop.get('stopped_at_utc', 'not stopped')}",
                  f"Expected scheduled slots: {len(slots)}; outcomes: {scheduled_summary['scheduled_outcomes']}",
                  "Legacy runs are matched to the schedule by request-start alignment within 90 seconds. Windows event history was disabled; aligned responses are inferred scheduled runs, not independently logged task events.",
                  "No-collection slots are missing observations. Failed requests differ from successful empty responses; neither proves zero air traffic.", ""]
        regular = intervals.loc[intervals.scheduled_slot_utc.notna()].attempt_utc.diff().dt.total_seconds().dropna()
        if len(regular):
            lines += [f"Scheduled request intervals: minimum {regular.min():.2f}, median {regular.median():.2f}, maximum {regular.max():.2f} seconds.", ""]
        if not slots.empty:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            import matplotlib.dates as mdates
            colors = {"successful_response": "#16803a", "failed_request": "#dc2626",
                      "no_collection": "#64748b", "deferred": "#d97706"}
            fig, ax = plt.subplots(figsize=(10, 3))
            for label, color in colors.items():
                selected = slots.loc[slots.outcome.eq(label)]
                ax.scatter(selected.scheduled_utc, [0] * len(selected), color=color, label=label.replace("_", " "), s=35)
            ax.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d %H:%M", tz=timezone.utc))
            ax.set_xlabel("Scheduled time (UTC)")
            ax.set_yticks([])
            ax.set_title("Technical pilot: acquisition coverage at five-minute slots")
            ax.legend(loc="upper center", bbox_to_anchor=(.5, -.3), ncol=4, fontsize=8)
            fig.tight_layout()
            fig.savefig(folder / "coverage.png", dpi=150, bbox_inches="tight")
            plt.close(fig)
    paths = sorted((ROOT / "data/raw/opensky").glob("*.json"))
    airport_paths = sorted((ROOT / "data/raw/airports").glob("*.csv"))
    if paths and airport_paths:
        raw = read_states(paths) if any(json.loads(p.read_text()).get("states") for p in paths) else None
        if raw is not None:
            try:
                data, airports, audit, missing = clean_and_join(raw, pd.read_csv(airport_paths[0]), config)
            except ValueError as exc:
                lines += [f"Preparation could not retain observations: {exc}", ""]
            else:
                summary = data.groupby("zone").agg(observations=("icao24", "size"), aircraft=("icao24", "nunique"),
                    altitude_min_m=("geo_altitude", "min"), altitude_median_m=("geo_altitude", "median"),
                    altitude_max_m=("geo_altitude", "max"), speed_median_m_s=("velocity", "median"))
                summary = summary.reindex(["near", "middle", "far"])
                summary[["observations", "aircraft"]] = summary[["observations", "aircraft"]].fillna(0).astype(int)
                summary.to_csv(folder / "zone_summary.csv")
                # Fixed 1000 m descriptive bins show how much overlap is actually sampled.
                data["altitude_band_lower_m"] = np.floor(data.geo_altitude / 1000) * 1000
                bands = data.groupby(["altitude_band_lower_m", "zone"]).agg(
                    observations=("icao24", "size"), aircraft=("icao24", "nunique"))
                bands.to_csv(folder / "altitude_band_coverage.csv")
                dates = sorted(data.date_utc.unique())
                lines += [f"Pinned airport reference: {airport_paths[0].relative_to(ROOT).as_posix()}",
                          f"Successful snapshot files: {len(paths)}; clean observed UTC dates: {len(dates)} ({', '.join(dates)}).",
                          f"Clean observations: {len(data)}; distinct aircraft: {data.icao24.nunique()}.", "",
                          "Sequential cleaning and join audit:", "", "```text", audit.to_string(index=False), "```", "",
                          "Proximity groups (aircraft can appear in multiple groups):", "", "```text",
                          summary.to_string(), "```", "",
                          "Common altitude support: inspect altitude_band_coverage.csv; shared bins alone do not establish adequate sample sizes.",
                          "", "Selected airports:", "", "```text", airports.to_string(index=False), "```", ""]
                lines += ["Missingness before deletion:", "", "```text", missing.to_string(), "```", ""]
        else:
            lines += ["All successful snapshots were empty; no observations available for preparation.", ""]
    else:
        lines += ["Both source files are required before cleaning and airport integration can be checked.", ""]
    metadata_audit_path = ROOT / "data/processed/metadata_integration_audit.csv"
    if metadata_audit_path.exists():
        lines += ["## Optional aircraft metadata", "", "Audit from the latest preparation build:", "", "```text",
                  pd.read_csv(metadata_audit_path).to_string(index=False), "```", ""]
    lines += ["## What remains to establish", "",
              "The approximately two-hour technical pilot checks the pipeline; main collection dates and duration remain a group decision.",
              "Then decide whether near/far distinct-aircraft counts and overlapping altitude bands support the question.",
              "At least seven observed UTC dates are required by the modeling notebook; 14 complete collection days are preferred.",
              "A short pilot cannot establish service reliability, daily traffic patterns, model performance or causal effects.",
              "The collection rectangle includes foreign airspace. Nearest airport means nearest of LSZH, LSGG and LFSB, not a verified route."]
    report = folder / "report.md"
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Saved {report.relative_to(ROOT)}")
    print("\n".join(lines[:15]))


if __name__ == "__main__":
    main()

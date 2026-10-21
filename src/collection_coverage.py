"""Coverage of scheduled slots: missing acquisition is never zero air traffic."""
import pandas as pd


def summarize_coverage(entries, start, end, interval_seconds=300):
    records = [e for e in entries if e.get("source_url", "").endswith("/states/all")]
    attempts = pd.DataFrame(records)
    start, end = pd.Timestamp(start).tz_convert("UTC"), pd.Timestamp(end).tz_convert("UTC")
    slots = pd.date_range(start, end, freq=f"{interval_seconds}s", inclusive="left")
    rows = []
    if not attempts.empty:
        attempts["attempt_utc"] = pd.to_datetime(attempts.get("attempted_at_utc", attempts.retrieved_at_utc), utc=True)
        attempts["retrieval_utc"] = pd.to_datetime(attempts.retrieved_at_utc, utc=True)
        attempts["success"] = [e.get("outcome") == "success" or
                               (e.get("status") == 200 and "path" in e) for e in records]
        attempts["empty"] = [bool(success and e.get("state_count") == 0)
                             for e, success in zip(records, attempts.success)]
        attempts["scheduled_slot_utc"] = pd.Series(pd.NaT, index=attempts.index, dtype="datetime64[ns, UTC]")
        attempt_seconds = attempts.attempt_utc.astype("int64") / 1e9
    for slot in slots:
        # Match by request START, with a 90 s startup tolerance, rather than by response time.
        # Legacy logs have no explicit task tag: alignment is evidence, not task-event history.
        candidates = attempts.loc[(attempt_seconds >= slot.value / 1e9 - 5) &
                                  (attempt_seconds < slot.value / 1e9 + 90)] if not attempts.empty else pd.DataFrame()
        if candidates.empty:
            outcome, empty, status = "no_collection", False, None
        else:
            index = candidates.index[candidates.success][0] if candidates.success.any() else candidates.index[0]
            attempts.loc[index, "scheduled_slot_utc"] = slot
            chosen = attempts.loc[index]
            outcome = "successful_response" if chosen.success else (
                "deferred" if chosen.get("outcome") == "deferred" else "failed_request")
            empty, status = bool(attempts.loc[index, "empty"]), chosen.get("status")
        rows.append({"scheduled_utc": slot, "outcome": outcome, "empty_response": empty, "http_status": status})
    coverage = pd.DataFrame(rows, columns=["scheduled_utc", "outcome", "empty_response", "http_status"])
    successes = attempts.loc[attempts.success].sort_values("attempt_utc") if not attempts.empty else pd.DataFrame()
    intervals = pd.DataFrame()
    if not successes.empty:
        intervals = successes[["attempt_utc", "retrieval_utc", "scheduled_slot_utc"]].copy()
        intervals["seconds_since_previous_success"] = intervals.attempt_utc.diff().dt.total_seconds()
        intervals["gap_over_330_seconds"] = intervals.seconds_since_previous_success.gt(interval_seconds + 30)
    counts = coverage.outcome.value_counts().to_dict()
    summary = {"first_success_utc": successes.retrieval_utc.iloc[0].isoformat() if len(successes) else None,
               "latest_success_utc": successes.retrieval_utc.iloc[-1].isoformat() if len(successes) else None,
               "successful_responses": int(attempts.success.sum()) if len(attempts) else 0,
               "failed_requests": sum(not s and e.get("outcome") != "deferred" for s, e in zip(attempts.success, records)) if len(attempts) else 0,
               "empty_responses": int(attempts["empty"].sum()) if len(attempts) else 0,
               "expected_scheduled_slots": len(slots), "scheduled_outcomes": counts,
               "scheduled_start_utc": pd.Timestamp(start).isoformat(), "coverage_end_utc": pd.Timestamp(end).isoformat(),
               "alignment_tolerance_seconds": 90}
    return attempts, coverage, intervals, summary

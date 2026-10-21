"""One research snapshot per invocation. Schedule externally; no background daemon.

From project root: python src/collect.py airports | snapshot
Optional environment variables: OPENSKY_CLIENT_ID and OPENSKY_CLIENT_SECRET.
Never reuse credentials from the reference notebook.
"""
import argparse
import hashlib
import json
import os
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
STATE_URL = "https://opensky-network.org/api/states/all"
TOKEN_URL = "https://auth.opensky-network.org/auth/realms/opensky-network/protocol/openid-connect/token"
AIRPORT_URL = "https://davidmegginson.github.io/ourairports-data/airports.csv"
METADATA_URL = "https://opensky-network.org/datasets/metadata/aircraftDatabase.csv"


def record_manifest(entry):
    entry["retrieved_at_utc"] = datetime.now(timezone.utc).isoformat()
    with (ROOT / "data/raw/manifest.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def save_response(response, folder, suffix, entry):
    name = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + suffix
    destination = ROOT / folder / name
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(response.content)
    record_manifest({**entry,
                     "path": str(destination.relative_to(ROOT)),
                     "sha256": hashlib.sha256(response.content).hexdigest(),
                     "bytes": len(response.content), "status": response.status_code})
    print(f"Saved {destination.relative_to(ROOT)}")


def retrieve(source, config, collection_mode="manual"):
    """Log one outcome per attempt, without response bodies or credentials."""
    url = {"airports": AIRPORT_URL, "snapshot": STATE_URL, "metadata": METADATA_URL}[source]
    params = config["bbox"] if source == "snapshot" else None
    entry = {"source": source, "source_url": url, "params": params,
             "attempted_at_utc": datetime.now(timezone.utc).isoformat(),
             "status": None, "auth_mode": "anonymous", "collection_mode": collection_mode}
    try:
        headers = {}
        if source == "snapshot":
            client_id = os.environ.get("OPENSKY_CLIENT_ID")
            secret = os.environ.get("OPENSKY_CLIENT_SECRET")
            if bool(client_id) != bool(secret):
                raise ValueError("Set both OAuth environment variables, or neither.")
            if client_id:
                entry["auth_mode"] = "oauth"
                entry["failure_stage"] = "oauth"
                token = requests.post(TOKEN_URL, data={"grant_type": "client_credentials",
                    "client_id": client_id, "client_secret": secret}, timeout=30)
                entry["oauth_status"] = token.status_code
                if token.status_code != 200:
                    raise RuntimeError(f"OAuth failed: HTTP {token.status_code}")
                headers["Authorization"] = "Bearer " + token.json()["access_token"]
        entry["failure_stage"] = "download"
        response = requests.get(url, params=params, headers=headers, timeout=60)
        entry.update(status=response.status_code,
                     resolved_url=response.url, last_modified=response.headers.get("Last-Modified"),
                     retry_after=response.headers.get("X-Rate-Limit-Retry-After-Seconds")
                                 or response.headers.get("Retry-After"),
                     credits_remaining=response.headers.get("X-Rate-Limit-Remaining"))
        if response.status_code != 200:
            raise RuntimeError(f"Download failed: HTTP {response.status_code}")
        entry["failure_stage"] = "validation"
        if source == "airports":
            if not response.content.startswith((b'"id"', b'id,')):
                raise ValueError("Expected airport CSV.")
            folder, suffix = "data/raw/airports", ".csv"
        elif source == "metadata":
            if not response.content.startswith((b'"icao24"', b'icao24,')):
                raise ValueError("Expected official aircraft metadata CSV.")
            folder, suffix = "data/raw/aircraft_metadata", ".csv"
        else:
            payload = response.json()
            if (not isinstance(payload, dict) or type(payload.get("time")) is not int
                    or "states" not in payload
                    or (payload["states"] is not None and not isinstance(payload["states"], list))):
                raise ValueError("Unexpected state-vector response schema.")
            if any(not isinstance(s, list) or len(s) not in (17, 18)
                   for s in payload["states"] or []):
                raise ValueError("Unsupported state vector.")
            entry.update(snapshot_time=payload["time"], state_count=len(payload["states"] or []))
            folder, suffix = "data/raw/opensky", ".json"
    except (requests.RequestException, ValueError, KeyError, RuntimeError) as exc:
        # Exception messages can contain request details; log only their class.
        record_manifest({**entry, "outcome": "failure", "error_type": type(exc).__name__})
        raise RuntimeError(f"{source} collection failed at {entry.get('failure_stage', 'configuration')}; "
                           f"HTTP {entry['status']}; inspect data/raw/manifest.jsonl.") from None
    entry.pop("failure_stage", None)
    save_response(response, folder, suffix, {**entry, "outcome": "success"})


def rate_limit_wait_seconds(now):
    """Respect the last HTTP 429 deadline across externally scheduled invocations."""
    manifest = ROOT / "data/raw/manifest.jsonl"
    if not manifest.exists():
        return 0
    for line in reversed(manifest.read_text(encoding="utf-8").splitlines()):
        entry = json.loads(line)
        if entry.get("source_url") != STATE_URL or entry.get("outcome") == "deferred":
            continue
        if entry.get("status") != 429:
            return 0
        retry = entry.get("retry_after")
        if retry is None:
            # No deadline supplied: pause for a day rather than retrying every five minutes.
            delay = 86400
        else:
            try:
                delay = max(0, float(retry))
            except (ValueError, TypeError):
                try:
                    deadline = parsedate_to_datetime(retry)
                    return max(0, (deadline - now).total_seconds())
                except (ValueError, TypeError):
                    delay = 86400
        retrieved = datetime.fromisoformat(entry["retrieved_at_utc"])
        return max(0, delay - (now - retrieved).total_seconds())
    return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source", choices=["airports", "snapshot", "metadata"])
    parser.add_argument("--scheduled", action="store_true")
    parser.add_argument("--until-utc", help="Optional explicit end timestamp with timezone; stops late queued runs.")
    args = parser.parse_args()
    (ROOT / "data/raw").mkdir(parents=True, exist_ok=True)
    config = json.loads((ROOT / "config.json").read_text())
    now = datetime.now(timezone.utc)
    if args.until_utc:
        end = datetime.fromisoformat(args.until_utc)
        if end.tzinfo is None:
            raise ValueError("--until-utc must include a timezone offset.")
        if now >= end:
            print("Collection window expired; no request made.")
            return
    if args.source == "snapshot":
        wait = rate_limit_wait_seconds(now)
        if wait > 0:
            record_manifest({"source": "snapshot", "source_url": STATE_URL,
                             "params": config["bbox"], "outcome": "deferred", "status": None,
                             "wait_seconds": wait})
            print(f"Rate-limit cooldown: skipped request; {wait:.0f} seconds remaining.")
            return
        if args.scheduled:
            manifest = ROOT / "data/raw/manifest.jsonl"
            if manifest.exists():
                for line in reversed(manifest.read_text(encoding="utf-8").splitlines()):
                    entry = json.loads(line)
                    if entry.get("source_url") == STATE_URL and entry.get("outcome") != "deferred":
                        previous = datetime.fromisoformat(entry.get("attempted_at_utc", entry["retrieved_at_utc"]))
                        # Allow ten seconds of scheduling jitter, while suppressing catch-up bursts.
                        if (now - previous).total_seconds() < config["interval_seconds"] - 10:
                            record_manifest({"source": "snapshot", "source_url": STATE_URL,
                                "params": config["bbox"], "status": None, "outcome": "deferred",
                                "reason": "sampling_interval", "collection_mode": "scheduled"})
                            print("Recent snapshot attempt; no extra request between five-minute ticks.")
                            return
                        break
    retrieve(args.source, config, "scheduled" if args.scheduled else "manual")


if __name__ == "__main__":
    main()

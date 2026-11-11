#!/bin/bash
# macOS counterpart of scripts/collection.ps1 (Start / Pause / Resume / Status).
# Registers a per-user launchd LaunchAgent that runs one OpenSky snapshot every
# five minutes (aligned to :00, :05, ...) inside a bounded window.
#
#   scripts/collection_mac.sh status
#   scripts/collection_mac.sh start --start-at 2026-11-12T09:00:00+01:00 --days 14
#   scripts/collection_mac.sh pause
#   scripts/collection_mac.sh resume
#
# Shares data/raw/main_schedule.json and data/raw/collection_control.jsonl with the
# Windows script, so a window paused on Windows can be resumed on the Mac (and back)
# after copying data/raw. Never run two collectors at the same time.
# Like on Windows: the Mac is NOT woken from sleep; sleep = missing observations.
# Written for the macOS default bash 3.2; dates are handled with the project Python.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LABEL="ch.zhaw.aircraftproject.maincollection"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
RAW="$ROOT/data/raw"
SCHEDULE="$RAW/main_schedule.json"
CONTROL="$RAW/collection_control.jsonl"
HISTORY="$RAW/schedules"
LOG_DIR="$RAW/logs"
PY="$ROOT/.venv/bin/python"
DOMAIN="gui/$(id -u)"

die() { echo "Error: $*" >&2; exit 1; }

[ "$(uname)" = "Darwin" ] || die "This script is for macOS. On Windows use scripts/collection.ps1."
[ -x "$PY" ] || die "Install .venv first (python3 -m venv .venv && .venv/bin/pip install -r requirements.txt)."

# Small Python helper for ISO timestamps (BSD date differs from GNU date).
pyrun() { "$PY" - "$@"; }

is_loaded() { launchctl print "$DOMAIN/$LABEL" >/dev/null 2>&1; }

record_control() {  # $1 = action, $2 = JSON details
    mkdir -p "$RAW"
    pyrun "$1" "$2" "$LABEL" "$CONTROL" <<'EOF'
import json, socket, sys
from datetime import datetime, timezone
action, details, label, path = sys.argv[1:5]
entry = {"action": action, "task_name": label, "platform": "macos",
         "host": socket.gethostname(),
         "event_utc": datetime.now(timezone.utc).isoformat(),
         "details": json.loads(details)}
with open(path, "a", encoding="utf-8") as f:
    f.write(json.dumps(entry) + "\n")
EOF
}

preserve_plist() {
    if [ -f "$PLIST" ]; then
        mkdir -p "$HISTORY"
        cp "$PLIST" "$HISTORY/$(date +%Y%m%dT%H%M%S)-main-mac.plist"
    fi
}

write_plist() {  # $1 = begin epoch, $2 = end ISO (UTC)
    local begin_epoch="$1" end_iso="$2" minutes="" m
    for m in 0 5 10 15 20 25 30 35 40 45 50 55; do
        minutes="$minutes        <dict><key>Minute</key><integer>$m</integer></dict>
"
    done
    mkdir -p "$(dirname "$PLIST")" "$LOG_DIR"
    # The start guard skips ticks before the chosen start; --until-utc in collect.py
    # stops after the deadline; its recency guard suppresses catch-up bursts after wake.
    cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key><string>$LABEL</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/sh</string>
        <string>-c</string>
        <string>[ "\$(date -u +%s)" -ge $begin_epoch ] || exit 0; exec "$PY" "$ROOT/src/collect.py" snapshot --scheduled --until-utc "$end_iso"</string>
    </array>
    <key>WorkingDirectory</key><string>$ROOT</string>
    <key>StartCalendarInterval</key>
    <array>
$minutes    </array>
    <key>RunAtLoad</key><false/>
    <key>ProcessType</key><string>Background</string>
    <key>StandardOutPath</key><string>$LOG_DIR/collector_mac.log</string>
    <key>StandardErrorPath</key><string>$LOG_DIR/collector_mac.log</string>
</dict>
</plist>
EOF
    plutil -lint "$PLIST" >/dev/null || die "Generated plist is invalid: $PLIST"
}

load_agent() {
    is_loaded && launchctl bootout "$DOMAIN/$LABEL" 2>/dev/null || true
    launchctl bootstrap "$DOMAIN" "$PLIST"
}

ACTION="${1:-status}"; shift || true
START_AT=""; DAYS=0
while [ $# -gt 0 ]; do
    case "$1" in
        --start-at) START_AT="${2:-}"; shift 2 ;;
        --days) DAYS="${2:-0}"; shift 2 ;;
        *) die "Unknown argument: $1" ;;
    esac
done

case "$ACTION" in
status)
    if is_loaded; then echo "$LABEL: ENABLED (loaded in launchd)"; else echo "$LABEL: not running"; fi
    [ -f "$SCHEDULE" ] && { echo "Schedule:"; cat "$SCHEDULE"; echo; }
    if [ -f "$RAW/manifest.jsonl" ]; then
        echo "Last manifest entry:"
        pyrun "$(tail -n 1 "$RAW/manifest.jsonl")" <<'EOF'
import json, sys
e = json.loads(sys.argv[1])
print(f"  {e.get('retrieved_at_utc')}  {e.get('source')}  {e.get('outcome')}  states={e.get('state_count')}")
EOF
    fi
    [ -f "$LOG_DIR/collector_mac.log" ] && { echo "Log tail:"; tail -n 3 "$LOG_DIR/collector_mac.log"; }
    pmset -g | grep -E "^ *sleep " | sed 's/^/Power: /' || true
    ;;
start)
    [ -n "$START_AT" ] && [ "$DAYS" -ge 1 ] && [ "$DAYS" -le 60 ] \
        || die "Provide --start-at with timezone offset and --days from 1 to 60."
    is_loaded && die "Main collection is already enabled. Pause or resume it instead of adding a second collector."
    # Parse and validate; prints: begin_epoch begin_utc end_utc
    read -r BEGIN_EPOCH BEGIN_UTC END_UTC <<<"$(pyrun "$START_AT" "$DAYS" "$SCHEDULE" <<'EOF'
import json, os, sys
from datetime import datetime, timedelta, timezone
start, days, schedule = sys.argv[1], int(sys.argv[2]), sys.argv[3]
begin = datetime.fromisoformat(start.replace("Z", "+00:00"))
if begin.tzinfo is None:
    sys.exit("StartAt must include a timezone offset, e.g. +01:00.")
now = datetime.now(timezone.utc)
if begin <= now:
    sys.exit("Choose a future --start-at.")
if os.path.exists(schedule):
    prev = json.load(open(schedule, encoding="utf-8-sig"))
    if datetime.fromisoformat(prev["end_utc"].replace("Z", "+00:00")) > now:
        sys.exit("A collection window is still valid (maybe started on the other computer). Use resume to keep its deadline.")
end = begin + timedelta(days=days)
print(int(begin.timestamp()), begin.astimezone(timezone.utc).isoformat(), end.astimezone(timezone.utc).isoformat())
EOF
)" || exit 1
    [ -n "${END_UTC:-}" ] || exit 1
    preserve_plist
    write_plist "$BEGIN_EPOCH" "$END_UTC"
    load_agent
    DETAILS="{\"start_utc\": \"$BEGIN_UTC\", \"end_utc\": \"$END_UTC\", \"interval_seconds\": 300, \"days\": $DAYS}"
    pyrun "$SCHEDULE" "$DETAILS" <<'EOF'
import json, sys
json.dump(json.loads(sys.argv[2]), open(sys.argv[1], "w", encoding="utf-8"), indent=2)
EOF
    record_control start "$DETAILS"
    echo "Main collection enabled. First tick at/after $BEGIN_UTC (UTC), end $END_UTC (UTC)."
    ;;
pause)
    is_loaded || die "Main collection is not running on this Mac."
    preserve_plist
    launchctl bootout "$DOMAIN/$LABEL"
    record_control pause '{}'
    echo "Main collection paused. Data and schedule deadline are preserved."
    ;;
resume)
    [ -f "$SCHEDULE" ] || die "Start a chosen collection window first (no data/raw/main_schedule.json)."
    is_loaded && { echo "Main collection is already enabled; no second collector started."; exit 0; }
    read -r BEGIN_EPOCH END_UTC <<<"$(pyrun "$SCHEDULE" <<'EOF'
import json, sys
from datetime import datetime, timezone
s = json.load(open(sys.argv[1], encoding="utf-8-sig"))
start = datetime.fromisoformat(s["start_utc"].replace("Z", "+00:00"))
end = datetime.fromisoformat(s["end_utc"].replace("Z", "+00:00"))
now = datetime.now(timezone.utc)
if (end - now).total_seconds() < 300:
    sys.exit("This window has expired or has fewer than five minutes remaining. Choose a new start and duration.")
print(int(max(start, now).timestamp()), end.astimezone(timezone.utc).isoformat())
EOF
)" || exit 1
    [ -n "${END_UTC:-}" ] || exit 1
    preserve_plist
    write_plist "$BEGIN_EPOCH" "$END_UTC"
    load_agent
    record_control resume "{\"end_utc\": \"$END_UTC\"}"
    echo "Main collection resumed on this Mac. End $END_UTC (UTC)."
    echo "Make sure the Windows collector is paused - never run both."
    ;;
*)
    die "Usage: $0 status | start --start-at ISO --days N | pause | resume"
    ;;
esac

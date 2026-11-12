#!/bin/bash
# Einrichtung des Sammel-Macs für das Data-Analytics-Projekt (OpenSky-Sammlung).
# Ausführen im Terminal des NEUEN Benutzers:   bash setup_sammler.sh
# Das Skript kann gefahrlos mehrmals laufen. Es startet die Sammlung NICHT,
# es zeigt am Schluss nur den Start-Befehl an.
set -euo pipefail

REPO_URL="https://github.com/kernwrob/Data-Analytics-Aviation.git"
TARGET="$HOME/Developer/Data-Analytics-Aviation"
FALLBACK_BRANCH="matteo/Data-Analytics-Aviation"

ok()   { printf '  \033[32m✔\033[0m %s\n' "$*"; }
info() { printf '\n\033[1m%s\033[0m\n' "$*"; }
die()  { printf '\n\033[31m✘ %s\033[0m\n' "$*" >&2; exit 1; }

info "1/7  System prüfen"
[ "$(uname)" = "Darwin" ] || die "Dieses Skript ist nur für macOS."
OS_VERSION="$(sw_vers -productVersion)"
ok "macOS $OS_VERSION"
case "$OS_VERSION" in 10.[0-9].*|10.1[0-2].*) die "macOS ist zu alt für Python 3.13 (mindestens 10.13 nötig)." ;; esac

info "2/7  Git (Command Line Tools)"
if ! xcode-select -p >/dev/null 2>&1; then
    xcode-select --install || true
    die "Bitte die Installation der Command Line Tools im Fenster abschliessen und das Skript danach nochmals starten."
fi
ok "$(git --version)"

info "3/7  Python 3.13"
PYTHON=""
for candidate in python3.13 /usr/local/bin/python3.13 /Library/Frameworks/Python.framework/Versions/3.13/bin/python3.13; do
    if command -v "$candidate" >/dev/null 2>&1; then PYTHON="$(command -v "$candidate")"; break; fi
done
[ -n "$PYTHON" ] || die "Python 3.13 nicht gefunden. Installer von https://www.python.org/downloads/macos/ installieren (Schritt 3 der Anleitung) und Skript neu starten."
ok "$("$PYTHON" --version) ($PYTHON)"

info "4/7  Repository holen"
mkdir -p "$(dirname "$TARGET")"
if [ -d "$TARGET/.git" ]; then
    git -C "$TARGET" fetch origin
    ok "Repository existiert bereits: $TARGET"
else
    echo "  GitHub fragt gleich nach Benutzername und Passwort."
    echo "  Als Passwort den GitHub-Token einfügen (nicht das GitHub-Passwort)."
    git clone "$REPO_URL" "$TARGET"
    ok "Geklont nach $TARGET"
fi
cd "$TARGET"
# Sobald der Mac-Sammler in main gemergt ist, wird main verwendet.
if git cat-file -e origin/main:scripts/collection_mac.sh 2>/dev/null; then BRANCH="main"; else BRANCH="$FALLBACK_BRANCH"; fi
if [ -n "$(git status --porcelain --untracked-files=no)" ]; then
    die "Im Repository gibt es lokale Änderungen. Bitte zuerst klären (git status)."
fi
git switch "$BRANCH" >/dev/null 2>&1 || git switch -c "$BRANCH" --track "origin/$BRANCH" >/dev/null
git pull --ff-only origin "$BRANCH" >/dev/null
ok "Branch: $BRANCH ($(git log --oneline -1))"
grep -q '"extended": 1' src/collect.py || die "collect.py sendet kein extended=1. Falscher Stand des Repos?"
ok "collect.py fragt die Flugzeugkategorie ab (extended=1)"

info "5/7  Python-Umgebung (.venv, nur was der Sammler braucht)"
[ -x .venv/bin/python ] || "$PYTHON" -m venv .venv
.venv/bin/python -m pip install --quiet --upgrade pip
.venv/bin/python -m pip install --quiet \
    requests==2.34.2 urllib3==2.8.0 certifi==2026.7.22 idna==3.20 charset-normalizer==3.5.2
.venv/bin/python -c "import requests; print('  requests', requests.__version__)"
chmod +x scripts/collection_mac.sh
ok "Umgebung bereit"

info "6/7  Testabruf bei OpenSky"
mkdir -p data/raw
.venv/bin/python src/collect.py snapshot || die "Testabruf fehlgeschlagen. Internetverbindung prüfen, dann nochmals versuchen."
if ls data/raw/airports/*.csv >/dev/null 2>&1; then
    ok "Flughafen-Referenzdatei ist schon vorhanden"
else
    .venv/bin/python src/collect.py airports || die "Download der Flughafen-Datei fehlgeschlagen."
fi
tail -n 1 data/raw/manifest.jsonl | .venv/bin/python -c "import json,sys; e=json.loads(sys.stdin.read()); print('  Letzter Eintrag:', e.get('source'), e.get('outcome'))"

info "7/7  Energie-Einstellungen (braucht Admin-Passwort, optional)"
read -r -p "  Ruhezustand am Netzteil deaktivieren und Neustart nach Stromausfall aktivieren? [j/N] " answer
if [ "${answer:-n}" = "j" ] || [ "${answer:-n}" = "J" ]; then
    if sudo pmset -c sleep 0 disksleep 0 displaysleep 10 autorestart 1; then
        ok "Gesetzt: kein Ruhezustand am Netzteil, Bildschirm aus nach 10 Min, Neustart nach Stromausfall"
    else
        echo "  Nicht gesetzt (kein Admin?). Bitte von Hand einstellen, siehe Anleitung Schritt 5."
    fi
else
    echo "  Übersprungen. Bitte von Hand einstellen, siehe Anleitung Schritt 5."
fi
pmset -g | grep -E "^ *(sleep|autorestart) " | sed 's/^/  Aktuell: /' || true

info "Fertig ✔"
cat <<EOF
  Die Sammlung läuft noch NICHT. Start mit dem abgemachten Zeitpunkt, z. B.:

    cd "$TARGET"
    scripts/collection_mac.sh start --start-at 2026-11-12T09:00:00+01:00 --days 14

  Danach prüfen:   scripts/collection_mac.sh status
EOF

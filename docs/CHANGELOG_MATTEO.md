# Änderungsprotokoll Matteo

Ein Eintrag pro Änderung, als Vorlage für Notion. Punkt-Nummern beziehen sich auf den Auftrag «Sammler-Fix, Analyse-Ausbau, Doku» (Punkte 1–8).

---

## Phase 0 – Lokale Umgebung auf dem Mac

**Datum · Branch · PR-Link:** 2026-10-22 · – (nur lokal, kein Commit) · –

**Punkt:** 8

**Was wurde geändert:** Auf dem Mac eine virtuelle Umgebung (`.venv`) mit Python 3.13.17 angelegt und alle Pakete aus `requirements-lock.txt` installiert. `pywinpty` gibt es nur für Windows. Deshalb wurde es über eine temporäre Kopie des Lockfiles mit dem Marker `sys_platform == "win32"` ausgelassen.

**Warum:** Damit auf dem Mac mit genau denselben Paketversionen analysiert werden kann wie auf dem Windows-Sammelgerät.

**Geänderte Dateien und Funktionen:** keine im Repo. Lokal nur `.venv/`, das von Git ignoriert wird.

**Wie getestet:** 17/17 Unit-Tests grün, `pip check` ohne Konflikte, alle Imports der drei Notebooks funktionieren.

**Auswirkung auf Daten/Ergebnisse:** keine.

**Offene Fragen an die Gruppe:**
- Sollen `appnope`, `pexpect` und `ptyprocess` (nur Mac/Linux) in Phase 3 mit Markern ins Lockfile? Heute installiert pip sie ohne feste Version.
- Wer stellt einen aktuellen Datenexport für Phase 2a bereit?

---

## Phase 1 – Sammler-Fix

### Punkt 1 – `extended=1` und ADS-B-Kategorie

**Datum · Branch · PR-Link:** 2026-10-22 · `fix/sammler-extended` · https://github.com/kernwrob/Data-Analytics-Aviation/pull/1

**Punkt:** 1

**Was wurde geändert:** Der Sammler schickt bei jedem Snapshot zusätzlich `extended=1` an OpenSky. Dadurch kommt pro Flugzeug ein 18. Feld mit, die ADS-B-Kategorie (`category`). Im Manifest steht neu `category_present`, also der Anteil der Vektoren mit 18 Feldern. In `prepare.py` ist die Spalte `category` jetzt immer vorhanden: Alte Pilot-Dateien mit 17 Feldern bekommen eine leere Spalte statt gar keine.

**Warum:** Der Dozent will, dass die Flugzeugkategorie zentral in der Analyse steht. Die ADS-B-Kategorie liefert OpenSky nur mit `extended=1`. Wird das nicht vor der Hauptsammlung eingebaut, fehlt sie für die ganze Sammlung.

**Geänderte Dateien und Funktionen:**
- `src/collect.py`: `retrieve()` (Request-Parameter und `category_present` im Manifest)
- `src/prepare.py`: `read_states()` (feste Spalten, `category` als ganze Zahl mit Lücken)
- `tests/test_collect.py`: 4 neue Tests (`test_snapshot_requests_extended_category_and_logs_its_share`, `test_empty_snapshot_has_no_category_share`, `test_category_is_read_and_old_vectors_stay_readable`, `test_only_old_vectors_still_produce_an_empty_category_column`)

**Wie getestet:** 22/22 Tests grün. Gegenprobe: Mit dem alten Code schlagen 3 der neuen Tests fehl. Dazu ein manueller Live-Snapshot (22.10.2026, 14:48 Uhr Zürich): Manifest zeigt `extended: 1` und `category_present: 1.0`, und `category` kommt als Integer in der SQLite-Tabelle `observations` und im View `observations_enriched` an.

**Auswirkung auf Daten/Ergebnisse:** Keine Zeilen mehr oder weniger, nur eine zusätzliche Spalte. Live-Snapshot: 167 Vektoren, alle mit 18 Feldern. Aber 162 haben Kategorie 0 («keine Information»), je 1× Light, Heavy und Rotorcraft, 2× Kategorie 1. Nach den bestehenden Filtern bleiben 124 Zeilen, davon 119 mit Kategorie 0.

**Offene Fragen an die Gruppe:**
- Fast alle Flugzeuge melden Kategorie 0. Die ADS-B-Kategorie taugt deshalb vermutlich nur als Kreuzcheck. Die eigentliche Kategorie muss aus den Metadaten kommen (Typecode-Mapping, Phase 2a). Einverstanden?
- Das ist erst ein Snapshot. Mit der Hauptsammlung prüfen, ob der Anteil Kategorie 0 so hoch bleibt.

### Punkt 2 – Rohdaten vollständig

**Datum · Branch · PR-Link:** 2026-10-22 · `fix/sammler-extended` · https://github.com/kernwrob/Data-Analytics-Aviation/pull/1

**Punkt:** 2

**Was wurde geändert:** Geprüft, dass `save_response()` die komplette JSON-Antwort unverändert speichert: Die SHA-256-Prüfsumme der Datei stimmt mit dem Manifest überein, und beim Sammeln wird nichts gefiltert. Neu ist ein Test, der sicherstellt, dass `baro_altitude`, `vertical_rate` und `category` bis in die SQLite-Tabelle `observations` kommen. An den Filtern in `prepare.py` wurde nichts geändert.

**Warum:** Für den Höhen-Fallback (Phase 2a) und das Modell D mit `vertical_rate` müssen diese Felder in der Datenbank vorhanden sein.

**Geänderte Dateien und Funktionen:** `tests/test_collect.py`: neuer Test `test_raw_altitude_vertical_rate_and_category_reach_observations`. Er baut mit `prepare.main()` eine Test-Datenbank aus einer alten (17 Felder) und einer neuen (18 Felder) Fixture-Datei.

**Wie getestet:** Neuer Offline-Test grün. Live-Snapshot zusätzlich von Hand geprüft.

**Auswirkung auf Daten/Ergebnisse:** Keine Änderung. Info für Phase 2a: Im Live-Snapshot fallen 33 von 167 Zeilen wegen fehlender `geo_altitude` heraus. 29 davon stehen aber am Boden und würden sowieso entfernt. Von den 4 Flugzeugen in der Luft haben 2 eine `baro_altitude`, der Fallback würde hier also 2 Zeilen zurückholen.

**Offene Fragen an die Gruppe:** Die Spalte `sensors` wird in `prepare.py` absichtlich entfernt. Sie ist ohne Sensor-Filter bei OpenSky immer leer (167/167). Kein Handlungsbedarf, nur zur Info.

### Punkt 3 – Doku und PR

**Datum · Branch · PR-Link:** 2026-10-22 · `fix/sammler-extended` · https://github.com/kernwrob/Data-Analytics-Aviation/pull/1

**Punkt:** 3

**Was wurde geändert:** In `docs/COLLECTION.md` steht ein kurzer Absatz zur Änderung. Darin steht auch, dass der Sammel-Laptop vor Start oder Resume `git switch main` und `git pull origin main` ausführen muss. In `docs/DECISIONS.md` gibt es einen neuen Abschnitt «Collector fix», und `docs/AI_USAGE_LOG.csv` hat neue Zeilen für Phase 0 und Phase 1.

**Warum:** Der Sammel-Laptop ruft `src/collect.py` direkt aus dem Repo-Ordner auf. Nur mit dem aktuellen Stand wird `extended=1` wirklich gesendet.

**Geänderte Dateien und Funktionen:** `docs/COLLECTION.md`, `docs/DECISIONS.md`, `docs/AI_USAGE_LOG.csv`, `docs/CHANGELOG_MATTEO.md` (neu).

**Wie getestet:** CSV-Struktur des KI-Logs geprüft (alle Zeilen 10 Spalten), Tests 22/22 grün.

**Auswirkung auf Daten/Ergebnisse:** keine.

**Offene Fragen an die Gruppe:** Wer macht den `git pull` auf dem Sammel-Laptop (Robin?), und wann startet die Hauptsammlung?

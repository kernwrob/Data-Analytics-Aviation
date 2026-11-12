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

---

## Mac-Sammler und Wechsel Windows ↔ Mac

**Datum · Branch · PR-Link:** 2026-11-11 · `matteo/Data-Analytics-Aviation` · –

**Was wurde geändert:** Neues Skript `scripts/collection_mac.sh` als Mac-Gegenstück zu `collection.ps1` (Aktionen `start`, `pause`, `resume`, `status`). Es registriert einen launchd-Agent, der alle 5 Minuten `src/collect.py snapshot --scheduled --until-utc …` aufruft. `collection.ps1` wurde minimal angepasst: `Start` verweigert einen neuen Zeitraum auch dann, wenn das Zeitfenster auf dem Mac gestartet wurde, und `Resume` funktioniert auch ohne lokalen Task (Übergabe Mac → Windows). In `docs/COLLECTION.md` gibt es neue Abschnitte zum Mac und zur Übergabe, im README einen Satz.

**Warum:** Die Hauptsammlung soll wahlweise auf Matteos Mac oder auf einem Windows-Laptop laufen können. Der Ordner `data/raw` wandert mit dem Sammler, deshalb müssen nie zwei Datenstände zusammengeführt werden.

**Geänderte Dateien und Funktionen:** `scripts/collection_mac.sh` (neu), `scripts/collection.ps1`, `docs/COLLECTION.md`, `README.md`, `docs/AI_USAGE_LOG.csv`, `docs/CHANGELOG_MATTEO.md`.

**Wie getestet:** Syntaxcheck (`bash -n`) und Simulation unter Linux mit nachgebautem `launchctl`: Start, doppelter Start wird verweigert, Pause, neuer Start bei gültigem Fenster wird verweigert, Resume, Resume mit einer von Windows geschriebenen Zeitplan-Datei. Ein echter Lauf auf macOS steht noch aus. Die Windows-Änderung ist nicht auf Windows getestet.

**Auswirkung auf Daten/Ergebnisse:** keine, `collect.py` ist unverändert.

**Offene Fragen an die Gruppe:** Auf welchem Gerät startet die Hauptsammlung, und ab wann?

---

## Setup-Skript für den Sammel-Mac

**Datum · Branch · PR-Link:** 2026-11-11 · `matteo/Data-Analytics-Aviation` · –

**Was wurde geändert:** `scripts/setup_sammler_mac.sh` richtet einen frischen Mac als Sammelgerät ein (Git, Repo klonen, `.venv` nur mit `requests`, Testabruf, Energie-Einstellungen). `docs/SETUP_MACBOOK.md` ist die Schritt-für-Schritt-Anleitung dazu (MacBook Pro A1502).

**Wie getestet:** Syntaxcheck (`bash -n`). Echter Lauf auf dem MacBook steht noch aus.

**Auswirkung auf Daten/Ergebnisse:** keine.

---

## Winddaten als dritte Quelle (Issue #36)

**Datum · Branch · PR-Link:** 2026-11-11 · `matteo/Data-Analytics-Aviation` · –

**Was wurde geändert:** Neues Modul `src/weather.py`. `fetch` holt pro UTC-Tag modellierten Wind (Open-Meteo Historical Forecast API, 10 Druckniveaus, 0.5°-Raster über dem Sammelgebiet) und speichert die Rohantworten mit Manifest-Eintrag. `src/prepare.py` hängt jeder Beobachtung den Wind an (nächste Stunde, nächster Rasterpunkt, Niveau mit der nächsten geopotentiellen Höhe) und berechnet Rückenwind, Seitenwind und geschätzte Fluggeschwindigkeit. Neue Tabellen `weather_levels`, `observation_wind`, `weather_integration_audit` und View `observations_with_wind`. Einstellungen in `config.json` unter `weather`. Doku in `docs/WEATHER.md`.

**Warum:** Ein Teil der Unterschiede in der Grundgeschwindigkeit ist Wind, nicht Flugzeugverhalten. Der Dozent wollte zusätzliche Komplexität. Winddaten lassen sich nachträglich holen, deshalb blockiert das die Sammlung nicht.

**Geänderte Dateien und Funktionen:** `src/weather.py` (neu), `src/prepare.py` (`main`), `config.json`, `tests/test_weather.py` (neu), `docs/WEATHER.md` (neu), `README.md`.

**Wie getestet:** 7 neue Offline-Tests (Windkomponenten, Raster, Stunden-/Punkt-/Niveau-Zuordnung, zeilenerhaltender Join, Fetch mit gemocktem Server inkl. Fehlerfall, `prepare.main` mit View). Bestehende Tests in `test_collect` und `test_metadata` weiterhin grün. Ein echter Abruf bei Open-Meteo steht noch aus (aus der Testumgebung nicht erreichbar).

**Auswirkung auf Daten/Ergebnisse:** Tabelle `observations` unverändert. Wind nur in den neuen Tabellen bzw. der View.

**Offene Fragen an die Gruppe:** Entscheid in #22: Wind als Feature in den Modellen (z. B. Rückenwind als zusätzliche Variable) oder nur beschreibend?

---

## Wind: vertikale Interpolation, 150 hPa, Modell D

**Datum · Branch · PR-Link:** 2026-11-11 · `matteo/Data-Analytics-Aviation` · –

**Was wurde geändert:** `src/weather.py` interpoliert den Wind jetzt linear zwischen den zwei Druckniveaus über und unter dem Flugzeug, und zwar als Ost-/Nord-Komponenten (neue Funktion `vertical_wind`, neue Spalte `wind_interpolated`, Audit `interpolated_share`). Zusätzliches Niveau 150 hPa (ca. 13,5 km) in `config.json`. `src/model_comparison.py` hat ein optionales Modell D (Raum + Kategorie + Rücken-/Seitenwind) und eine Prüfung, dass keine vom Ziel abgeleitete Spalte (z. B. `airspeed_est_ms`) als Feature verwendet wird.

**Warum:** Beim ersten echten Abruf lagen 22 % der Beobachtungen mehr als 500 m neben der nächsten Windstufe. Nach der Interpolation sind 96 % interpoliert; der Rest liegt über 200 hPa und wird mit 150 hPa abgedeckt.

**Geänderte Dateien und Funktionen:** `src/weather.py` (`vertical_wind`, `attach_wind`), `src/model_comparison.py`, `config.json`, `tests/test_weather.py`, `tests/test_coverage_and_models.py`, `docs/WEATHER.md`.

**Wie getestet:** 31/31 Tests grün (2 neue: Interpolation mit Richtungswechsel, Modell D ohne Ziel-Leakage). `prepare.py` auf dem Snapshot vom 22.10. neu gebaut: 124/124 gematcht, 96 % interpoliert.

**Auswirkung auf Daten/Ergebnisse:** `observations` unverändert. Wegen der neuen Druckstufe lädt `python src/weather.py fetch` den 22.10. einmal neu.

---

## EDA: Wind und Flugzeugtyp in Notebook 01 (Roadmap CC-2, #16, #17)

**Datum · Branch · PR-Link:** 2026-11-11 · `matteo/Data-Analytics-Aviation` · –

**Was wurde geändert:** `notebooks/01_data_and_eda.ipynb` hat einen neuen Abschnitt «Wind and aircraft type» mit fünf Blöcken. Alle lesen per SQL aus `observations_with_wind`, `observations_enriched` und `weather_levels`:
1. Tabelle Höhenband × Zone mit mittlerem Wind, Rückenwind und Gegenwind-Anteil. Es zählen nur Zeilen mit `wind_matched = 1`. Der Anteil `wind_interpolated` wird pro Höhenband und Zone und zusätzlich pro Höhenband allein ausgewiesen.
2. Grafik: Grundgeschwindigkeit und geschätzte Fluggeschwindigkeit (`airspeed_est_ms`) über der Höhe, nur beschreibend.
3. Rückenwind nach Flugrichtung in Sektoren: Ost = `true_track` 45–135°, West = 225–315°, Rest = Nord/Süd. Dazu ein Histogramm, ein Boxplot pro Höhenband und eine Tabelle.
4. Anteil der Beobachtungen und der Flugzeuge pro Kategorie und Zone, inkl. `unknown/other`. Die Anteile rechnet SQL mit einer Fensterfunktion.
5. Folium-Karte: Windpfeile des Rasters für eine wählbare Stunde und Druckstufe (Standard: die Stunde mit den meisten Beobachtungen, 250 hPa). Die Pfeile zeigen nach `wind_dir_deg + 180°`, also dorthin, wohin der Wind weht. Die Beobachtungen dieser Stunde sind nach Rückenwind eingefärbt.

Nach jedem Block steht ein Interpretations-Platzhalter mit Leitfragen für die Gruppe. Das Wind-Audit (`weather_integration_audit`) steht neu im Datenqualitätsteil. Ohne Winddaten überspringt das Notebook die Wind-Blöcke mit einem Hinweis.

**Warum:** Die Roadmap verlangt Wind und Kategorie in der EDA (Pflicht 4 «reiche EDA», Bonus Kreativität und Karte). Die Zerlegung «Grundgeschwindigkeit = Flugzeug + Wind» soll schon in der EDA sichtbar sein.

**Geänderte Dateien und Funktionen:** `notebooks/01_data_and_eda.ipynb` (Datenqualitäts-Zelle, neuer Abschnitt mit `flight_direction` und `wind_arrow`). Neue Ausgaben: `outputs/figures/ground_vs_airspeed_altitude.png`, `tailwind_by_direction.png`, `category_share_by_zone.png`, `wind_map.html` und `outputs/tables/weather_integration_audit.csv`, `wind_by_altitude_zone.csv`, `wind_interpolation_by_altitude.csv`, `tailwind_by_direction.csv`, `category_share_by_zone.csv`.

**Wie getestet:**
- Ganzes Notebook mit `jupyter nbconvert --execute` auf dem Pilot-Snapshot vom 22.10. (124 Beobachtungen, alle mit Wind) ausgeführt, ohne Fehler.
- Zusätzlich in Kopien der Datenbank: (a) ohne Wind-Tabellen, dabei wurden die Hinweise ausgegeben und die Wind-Blöcke übersprungen; (b) mit Test-Kategorien, um Legende und Farben in Block 4 zu prüfen.
- Grafiken und Karte angeschaut. Die Pfeile zeigen bei Wind aus ~300° nach Ost-Südost. Ostflüge haben auf 9–11 km im Median +44 m/s Rückenwind, Westflüge −48 m/s, was zur Vorzeichen-Konvention passt.
- Unit-Tests: 31/31 grün (`python -m unittest discover -s tests`).
- Kein neuer Unit-Test, die Hilfsfunktionen bleiben im Notebook (so entschieden).

**Auswirkung auf Daten/Ergebnisse:** Keine Änderung an `src/`, Datenbank oder Modellen. Das Notebook ist ohne Ausgaben gespeichert. Auf dem Mac fehlen die Metadaten, deshalb ist dort alles `unknown/other`. Die Zahlen aus dem Pilot (ein Snapshot) sind kein Ergebnis.

**Offene Fragen an die Gruppe:** Welche Stunde und Druckstufe soll die Karte für die Präsentation zeigen? Die Interpretationen in den Platzhaltern schreibt die Gruppe nach der Hauptsammlung.

---

## PostgreSQL-Bonus: Mirror und Notebook 04 (Roadmap CC-3, #22)

**Datum · Branch · PR-Link:** 2026-11-11 · `matteo/Data-Analytics-Aviation` · –

**Was wurde geändert:**
- Neues Skript `src/postgres_mirror.py`. Es kopiert die SQLite-Tabellen in eine PostgreSQL-Datenbank `aviation` mit expliziten Typen (`TIMESTAMPTZ`, `DATE`, `BIGINT`, `DOUBLE PRECISION`, …), Primärschlüsseln und Fremdschlüsseln (`observations.airport_ident → airports`, `observation_wind → observations`). Gespiegelt werden `airports`, `observations`, `aircraft_metadata`, `weather_levels`, `observation_wind` und die drei Audit-Tabellen.
- Alles läuft in einer einzigen Transaktion: Tabellen neu anlegen, Daten per `COPY` laden, Zeilenzahlen mit SQLite vergleichen. Bei einem Fehler bleibt PostgreSQL unverändert.
- Die Verbindung kommt aus der Umgebungsvariable `DATABASE_URL` oder aus der Datei `.env` im Projektordner (gitignored). Vorlage ist `.env.example`. Im Code steht kein Passwort, und die URL wird immer mit `***` statt Passwort ausgegeben.
- Neues Notebook `notebooks/04_postgresql.ipynb` mit vier Teilen:
  1. Abgleich mit SQLite: Zeilenzahlen aller Tabellen und dieselbe SQL-Aggregation in beiden Datenbanken.
  2. Join Beobachtungen – Flughäfen – Wind.
  3. Aggregation nach Zone und Höhenband mit echtem Median (`percentile_cont`), dazu eine Grafik.
  4. Fensterfunktionen `ROW_NUMBER`/`RANK`: die schnellsten Flugzeuge pro Flughafen, jedes Flugzeug nur einmal.
- Doku `docs/POSTGRESQL.md` mit Installation, `.env`, Laden der Variablen in VS Code-Notebooks, je einem Abschnitt für macOS und Windows (für Kevin und Robin) und einer Fehlertabelle.
- `psycopg[binary]` und `sqlalchemy` in `requirements.txt`, die Versionen fest in `requirements-lock.txt`. README angepasst.

**Warum:** Das ist ein Bonuspunkt («PostgreSQL mit Joins/Aggregationen aus Python»), und ohne ihn liegt das Maximum bei 21/22. SQLite bleibt die Hauptdatenbank, PostgreSQL ist nur eine Kopie.

**Geänderte Dateien und Funktionen:**
- Neu: `src/postgres_mirror.py` (`TABLES`, `load_database_url`, `redact`, `create_table_sql`, `check_schema`, `read_sqlite`, `to_copy_rows`, `mirror`, `engine`), `notebooks/04_postgresql.ipynb`, `docs/POSTGRESQL.md`, `tests/test_postgres_mirror.py`, `.env.example`.
- Geändert: `requirements.txt`, `requirements-lock.txt`, `README.md`.

**Wie getestet:**
- 8 neue Offline-Tests ohne Server: Typen und Schlüssel im `CREATE TABLE`, Lade-Reihenfolge der Fremdschlüssel, Schema passt zu allen Tabellen, die `prepare.py` schreibt (mit und ohne Wind), Umwandlung von leeren Werten, Ganzzahlen und Zeiten, `.env`-Logik, kein Passwort in Ausgabe und Code. Gesamt 39/39 grün.
- Lokal mit PostgreSQL 16 (Homebrew): Mirror auf dem Pilot-Snapshot, alle Zeilenzahlen gleich. Ein zweiter Lauf liefert dasselbe Ergebnis.
- Absichtlich kaputte SQLite-Kopie (Flughafen existiert nicht): Der Fremdschlüssel greift, und PostgreSQL bleibt unverändert (geprüft an `weather_levels`).
- Notebook 04 mit `nbconvert` ausgeführt, ohne Fehler. Die Grafik habe ich angeschaut und so angepasst, dass Linien bei Bändern mit zu wenigen Flugzeugen unterbrochen sind statt gerade durchgezogen.
- Der Windows-Abschnitt ist nicht auf Windows getestet.

**Auswirkung auf Daten/Ergebnisse:** Keine. SQLite, `prepare.py` und die anderen Notebooks bleiben unverändert. Die PostgreSQL-Kopie muss nach jedem `prepare.py` neu gebaut werden.

**Offene Fragen an die Gruppe:** Antwort des Dozenten zu #22 abwarten: zählt die Kopie aus SQLite als «PostgreSQL statt SQLite»? Kevin oder Robin sollten den Windows-Weg einmal durchspielen.

---

## Fix: Notebook 01, Block 2 (Linien über dünne Höhenbänder)

**Datum · Branch · PR-Link:** 2026-11-11 · `matteo/Data-Analytics-Aviation` · –

**Was wurde geändert:** Die Median-Linien in der Grafik «Ground speed vs. estimated airspeed» werden jetzt unterbrochen, wenn ein Höhenband zu wenige Flugzeuge hat. Vorher wurden solche Bänder weggelassen, und die Linie lief gerade darüber hinweg. Die Schwelle zählt neu einzelne Flugzeuge statt Beobachtungen (mindestens 5, gleiche Regel wie in Notebook 04). Die Tabelle unter der Grafik zeigt pro Band zusätzlich die Anzahl Flugzeuge.

**Warum:** Eine gerade Linie über ein fehlendes Band täuscht einen Verlauf vor, den die Daten nicht zeigen. Das ist mir bei Notebook 04 (CC-3) aufgefallen.

**Geänderte Dateien und Funktionen:** `notebooks/01_data_and_eda.ipynb` (Zelle Block 2).

**Wie getestet:** Notebook auf dem Pilot-Snapshot ausgeführt, die Grafik ist unverändert, weil alle Bänder genug Flugzeuge haben. Zusätzlich auf einer Kopie, in der das Band 3000–5000 m nur noch 4 Flugzeuge hat: Die Linie bricht dort ab. Unit-Tests 39/39 grün.

**Auswirkung auf Daten/Ergebnisse:** Nur die Darstellung, keine Daten.

---

## Hauptsammlung gestartet und Kartenausschnitt vergrössert

**Datum · Branch · PR-Link:** 2026-11-12 · `matteo/Data-Analytics-Aviation` · –

**Was wurde geändert:**
- Hauptsammlung auf dem alten MacBook gestartet: 12.11. 19:30 bis 26.11. 19:30, alle 5 Minuten (Issue #47, #32).
- Kartenausschnitt in `config.json` von 45.7–48.0 °N / 5.8–10.6 °E auf **45.6–48.2 °N / 5.2–10.6 °E** vergrössert.
- Doku nachgeführt: `DECISIONS.md` (Sammlung und Ausschnitt, Zeile «Collection owner and dates» nicht mehr *Pending*), `COLLECTION.md` (aktueller Stand, Fernzugriff, Ablauf bei Änderungen), `SETUP_MACBOOK.md` (Stand, Fernzugriff, Bildschirm aus).

**Warum:** Genf lag nur 24 km vom Westrand entfernt, Basel 46 km vom Nordrand. Vom Ring 30–60 km um Genf lagen nur 68 % im Ausschnitt, bei Basel 91 %. An- und Abflüge über Frankreich fehlten, der Flughafenvergleich wäre schief gewesen. Jetzt liegen alle drei Flughäfen mindestens 68 km vom Rand entfernt. Der Ausschnitt bleibt unter 25 Quadratgrad und kostet weiterhin 1 Credit pro Abruf.

**Geänderte Dateien und Funktionen:** `config.json` (`bbox`), `docs/DECISIONS.md`, `docs/COLLECTION.md`, `docs/SETUP_MACBOOK.md`, `docs/AI_USAGE_LOG.csv`, dieses Protokoll. Kein Code geändert.

**Wie getestet:** Abstände und Anteile pro Zone mit Haversine-Distanz und Stichprobe berechnet (alter und neuer Ausschnitt). Credit-Regel in der OpenSky-REST-Doku nachgelesen. Unit-Tests verwenden eigene Test-Konfigurationen und sind nicht betroffen. Nach dem Wechsel auf dem Sammel-Mac: erster Snapshot mit `"lomin": 5.2` im Manifest und `success` prüfen.

**Auswirkung auf Daten/Ergebnisse:** Ab dem Wechsel mehr Beobachtungen, vor allem westlich von Genf und nördlich von Basel. Die Snapshots mit altem Ausschnitt (ca. 1–2 h am 12.11.) werden in der Hauptanalyse ausgeschlossen, damit alle denselben Raum abdecken. Der Filter in `prepare.py` ist noch offen (eigenes Issue). Das Wind-Raster wird automatisch grösser.

**Offene Fragen an die Gruppe:** Entscheid zur Kenntnis nehmen. Einverstanden, dass die ersten 1–2 Stunden mit altem Ausschnitt nicht in die Hauptanalyse kommen?


---

## CC-7: Flugzeugkategorie über Typecode und Filter alter Kartenausschnitt

**Datum · Branch · PR-Link:** 2026-11-12 · `matteo/Data-Analytics-Aviation` · – (Issues #12, #52)

**Was wurde geändert:**
- **Neue Metadaten-Datei:** Statt `aircraftDatabase.csv` (4.11.2024) nehmen wir neu die vollständige Monatsdatei `aircraft-database-complete-2025-08.csv` von OpenSky (616'675 Einträge, 0 Duplikate). `config.json` legt die Datei mit Pfad **und SHA-256** fest (`metadata_file`, `metadata_sha256`). `collect.py` liest die Download-URL neu aus `config.json` (`metadata_url`).
- **Robustes Einlesen:** Die neue Datei hat ein anderes Format (einfache Anführungszeichen, camelCase, `icaoAircraftClass`). `read_metadata_csv()` erkennt beide Formate.
- **Neue Kategorien über den Typecode:** Kurzstrecke, Regionaljet, Langstrecke, Turboprop, Business-Jet, Sonstige, Unbekannt.
  - Zuordnung: Typecode-Tabelle → ICAO-Beschreibung (`L?T` → Turboprop, `L?P`/`H??`/`G??` → Sonstige) → Unbekannt.
  - Jets ohne bekannten Typecode werden nicht geraten. Widersprüchliche Duplikate (Typecode oder Beschreibung) werden Unbekannt.
  - Neue Spalte `category_source` (`typecode` / `icao_description` / `none`).
- **Referenztabelle** `data/reference/typecode_category.csv` mit 140 Typecodes: alle Beispiele aus dem Schema plus jeder Typecode, der in den ersten 13 Snapshots vorkommt. Bei unsicheren Typen steht eine Begründung in `source_note`.
- **SQLite:**
  - Tabelle `typecode_categories`. Der View `observations_enriched` berechnet die Kategorie per SQL-Join, und `prepare.py` prüft, dass SQL und Python dasselbe ergeben.
  - Neu im View: `adsb_category_label` (ADS-B-Kategorie als lesbarer Text, nur Kreuzcheck).
  - Neue Audit-Tabelle `category_audit`, Liste `outputs/tables/unmapped_typecodes.csv`.
- **Alter Kartenausschnitt:** `prepare.py` nimmt nur Snapshots, deren Ausschnitt laut Manifest dem aktuellen `config.json` entspricht (`require_current_bbox: true`). Snapshots ohne Manifest-Eintrag fallen auch raus.
  - Neue Audit-Stufen `raw_all_snapshots` → `current_bbox`.
  - Neue Tabelle `snapshot_bbox_audit`.
- `unknown/other` heisst überall `Unbekannt` (Code, Notebooks 01/02/04, Tests).
- Notebook 01, Block 4: neue Tabelle «Abdeckung pro Flughafen × Zone» (Anteil mit Metadaten, mit bekannter Kategorie, über Typecode). Notebook 01 zeigt neu auch das Snapshot- und das Kategorie-Audit.
- PostgreSQL-Mirror: neue Spalten und Tabellen im Schema. `export_data.py` kopiert `data/reference/` und die gepinnte Metadaten-Datei ins Paket.
- `.gitignore`: `data/raw_backup*/` (lokale Sicherung von `data/raw`).
- Doku: `METADATA.md` (neue Version, Kategorien, alte Beschreibung als Historie), `DECISIONS.md` (Schema eingefroren, Metadaten-Version, Umsetzung Ausschnitt-Filter), `COLLECTION.md` (Daten nur lesend vom Sammler kopieren).

**Warum:** Die alte Kategorie über die ICAO-Beschreibung hat A320, B777 und Citation in dieselbe Klasse gesteckt («Jet landplane»). Der Dozent will die Kategorie aber zentral in der Analyse. Die alte Metadaten-Datei ist laut OpenSky unvollständig und lag nur auf einem Windows-Gerät. Die Snapshots mit altem Ausschnitt decken weniger Fläche ab und würden den Flughafenvergleich verzerren.

**Geänderte Dateien und Funktionen:**
- `src/aircraft_metadata.py`: `read_metadata_csv`, `normalize_metadata_columns`, `load_typecode_categories`, `description_category`, `assign_categories` (neu); `prepare_metadata`, `enrich_observations` (angepasst); `UNKNOWN = "Unbekannt"`, `CATEGORIES`.
- `src/prepare.py`: `manifest_bboxes`, `same_bbox`, `select_snapshots`, `count_states`, `load_pinned_metadata` (neu); `main` (Filter, Pinning, neue Tabellen, View, Audits).
- `src/collect.py` (`retrieve`), `src/model_comparison.py`, `src/postgres_mirror.py` (`TABLES`), `src/export_data.py` (`main`).
- `config.json`, `data/reference/typecode_category.csv` (neu), `.gitignore`.
- Notebooks 01, 02, 04.
- Tests: `tests/test_category_and_bbox.py` (neu, 12 Tests), Anpassungen in `test_collect.py` (+2 Tests), `test_metadata.py`, `test_weather.py`, `test_postgres_mirror.py`, `test_coverage_and_models.py`.
- Doku: `docs/METADATA.md`, `docs/DECISIONS.md`, `docs/COLLECTION.md`.

**Wie getestet:**
- 53/53 Unit-Tests grün (vorher 39), alle offline mit kleinen Fixtures. Abgedeckt sind:
  - Reihenfolge der Zuordnung, Typecode schlägt falsche Beschreibung, Jets werden nicht geraten
  - Typecode-Konflikt → Unbekannt und gezählt
  - beide CSV-Formate
  - falsche Prüfsumme oder fehlende Datei → Abbruch, leerer Eintrag → alles Unbekannt
  - Ausschnitt-Filter (alter raus, neuer drin, Flag aus → alles drin, fehlender Manifest-Eintrag raus, Windows-Pfad)
  - View, ADS-B-Label und Liste der nicht gemappten Typecodes
- Echte Daten: 13 Snapshots vom Sammel-Mac (nur lesend per `rsync` kopiert), `prepare.py` gelaufen, SQL = Python bei allen Zeilen.
- Notebook 01 und Notebook 04 (mit neu gebautem PostgreSQL-Mirror) ohne Fehler ausgeführt, Outputs nur im Scratchpad. Die Notebooks im Repo sind ohne Outputs.
- Notebook 02 nicht ausgeführt: Die 7-Tage-Sperre greift und bleibt.

**Auswirkung auf Daten/Ergebnisse:**
- Hauptanalyse heute: 13 Snapshots, davon 11 mit altem Ausschnitt ausgeschlossen (777 Zeilen). Es bleiben 2 Snapshots → 122 Beobachtungen, 77 Flugzeuge.
- Metadaten-Treffer: 88,5 % der Beobachtungen (Pilot mit alter Datei: 67,3 %). Davon haben 99,1 % einen Typecode aus der Tabelle.
- Kategorien (Hauptanalyse, Beobachtungen / Flugzeuge): Kurzstrecke 79 / 50, Unbekannt 15 / 10, Regionaljet 10 / 5, Business-Jet 8 / 5, Langstrecke 5 / 4, Turboprop 5 / 3.
- Modell C (Raum + Kategorie) bekommt jetzt echte Klassen statt fast nur «Jet landplane». Ergebnisse gibt es erst ab 7 Sammeltagen.

**Offene Fragen an die Gruppe:**
1. Kategorie-Schema und Referenztabelle zur Kenntnis nehmen (`DECISIONS.md`, Status «to be acknowledged by the group»). Passen die Grenzfälle: A220 als Kurzstrecke, A306 als Langstrecke, CRJ2 inkl. Challenger 850 als Regionaljet, PC-6 als Sonstige?
2. Die Metadaten-Datei (108 MB, SHA-256 `41309cab…`) geht über die gemeinsame Ablage (#14) an Kevin und Robin. Ohne sie bricht `prepare.py` mit einer klaren Meldung ab. Wer ohne Metadaten arbeiten will, setzt `"metadata_file": ""`.
3. Die neue Datei hat eine Spalte `timestamp`. Damit könnte man bei Duplikaten den neusten Eintrag wählen. Wir behalten die bisherige Regel (vollständigster Eintrag, dann Reihenfolge). In dieser Datei gibt es **0 Duplikate** und **0 Duplikate mit unterschiedlichem Typecode**, die Frage ist also aktuell ohne Wirkung.
4. Die Liste der nicht gemappten Typecodes ist heute leer, weil alle beobachteten Typecodes eingetragen sind. Wer prüft sie während der Sammlung (z. B. nach 7 Tagen) und ergänzt neue Typecodes?
5. Aufgefallen, nicht Teil dieses Auftrags: 75 von 203 Zeilen fallen in der Stufe `required_fields_present` weg, alle wegen fehlender `geo_altitude`. 74 davon sind Flugzeuge am Boden (`on_ground`), die in der Stufe `airborne` ohnehin wegfielen. Die Audit-Tabelle schreibt sie also der falschen Stufe zu. Für CC-10 (Höhe aus `baro_altitude`, Reihenfolge der Filter) vormerken.
6. Aufgefallen: Der PostgreSQL-Mirror enthält jetzt alle 616'648 Metadaten-Zeilen (vorher 0 auf dem Mac). Er läuft trotzdem in Sekunden, sollte aber nur die Flugzeuge aus den Beobachtungen spiegeln, falls er auf Windows zu langsam wird.

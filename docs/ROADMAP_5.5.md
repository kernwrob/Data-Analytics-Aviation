# Roadmap zur Note 5.5–6

Stand: 11. November 2026, **aktualisiert am 12. November 2026** nach dem Projekt-Review (`docs/REVIEW_2026-11-12.md`) und dem Start der Hauptsammlung. Branch `matteo/Data-Analytics-Aviation`. Erstellt nach einer Durchsicht von Code, Notebooks, Tests und Doku gegen das Bewertungsraster in `docs/COURSE_EVALUATION.md`. Eine Note lässt sich nicht garantieren; diese Liste zeigt, wo die Punkte liegen und was dafür noch fehlt.

## 1. Wo die Punkte liegen

Schlussprojekt: **max. 22 Punkte** = 9 Pflicht + 6 Bonus + 7 Video. Wie Punkte in Noten umgerechnet werden, steht im Auszug nicht. Für eine 5.5–6 sollte das Ziel sein: **alle 9 Pflichtpunkte, mindestens 5 der 6 Bonuspunkte und 6–7 Punkte beim Video.** Jeder fehlende Pflichtpunkt kostet mehr als ein Bonuspunkt bringt.

Die Konzeptpräsentation (19.11., 10 Min., 8 Kriterien) ist separat bewertet. Ob und wie stark sie in die Note eingeht, ist im Auszug nicht angegeben.

## 2. Stand pro Kriterium

Legende: ✅ steht · 🟡 Code steht, Ergebnis fehlt · ❌ fehlt

### Pflicht (9 Punkte)

| # | Kriterium | Stand | Beleg im Repo | Was noch fehlt |
|---|---|---|---|---|
| 1 | Eigene Datensammlung per API | 🟡 | `src/collect.py`, Pilot 1.10., Mac-/Windows-Skripte. **Hauptsammlung läuft seit 12.11. 19:30** auf dem alten MacBook bis 26.11. 19:30, Ausschnitt am ersten Abend vergrössert (#47, #52) | Täglich überwachen, Lücken mit Grund notieren (#4), Daten einfrieren und Abdeckung dokumentieren (#15) |
| 2 | Integration ≥ 2 Quellen, dokumentiert | ✅/🟡 | OpenSky + OurAirports (räumlich), Flugzeug-Metadaten (Key-Join `icao24`), Wind (Zeit/Ort/Höhe); Audits mit Zeilen vor/nach | Kategorie über Typecode statt ICAO-Beschreibung (→ CC-7, #12), Bereinigung mit Audit (→ CC-10, #13), Audits auf den finalen Daten |
| 3 | SQLite + SQL aus Python | ✅ | `prepare.py`, Views `observations_enriched`, `observations_with_wind`, SQL-Aggregationen in Notebook 01 | – |
| 4 | Reiche EDA (Tabellen + Grafiken) | 🟡 | Notebook 01: Qualität, Abdeckung, Verteilungen, Höhe×Speed, Höhenbänder, Karte, Wind und Kategorie (CC-2 ✅) | Vergleich der drei Flughäfen, `vertical_rate`/Flugphase, Ausreisser (→ CC-10), EDA auf Hauptdaten (#16) |
| 5 | Regression mit Frage über Standard-Vorhersage hinaus | 🟡 | Near/far-Vergleich, spätere Tage vs. andere Flugzeuge, Modellkette A–D | Interaktionstest Höhe × Zone und Flughafenvergleich mit p-Wert (→ CC-8, #19), Modellform an die Daten anpassen (→ CC-9, #18), Wind-Modell D sichtbar machen (→ CC-1) |
| 6 | Evaluation mit Gütemassen | ✅ | MAE, RMSE, R² pro Gruppe, Baseline | Läuft erst ab 7 Sammeltagen (bewusste Sperre) |
| 7 | Korrekte Interpretation | ❌ | Platzhalter in den Notebooks | Koeffiziententabellen (→ CC-8, CC-9), Interpretation als feste Phase KW 48 (#23), Notebooks als Bericht (#48), Walkthrough (#49) |
| 8 | KI-Dokumentation inkl. Vor-/Nachteile | 🟡 | `docs/AI_USAGE_LOG.csv`, `docs/CHANGELOG_MATTEO.md` | Laufend nachführen; Einträge von Kevin und Robin; `docs/AI_REFLECTION.md` in eigenen Worten (#26) |
| 9 | Material auf Moodle | ❌ | `src/export_data.py` (datierter, geprüfter Export) | Notebooks mit Outputs + HTML, Probelauf durch Nicht-Autor, Nachweis-Matrix (#25, #29) |

### Bonus (6 Punkte)

| # | Kriterium | Stand | Was noch fehlt |
|---|---|---|---|
| 1 | Kreativität | 🟡 | Stark: Zerlegung der Grundgeschwindigkeit in **Flugzeug + Wind**, in der EDA sichtbar (CC-2 ✅), in den Modellen noch nicht (→ CC-1). Dazu eigene Typecode-Kategorien (→ CC-7), Leakage-Demo (→ CC-9), Sensitivität der Schwellen (→ CC-12, #50). |
| 2 | PostgreSQL o. ä. (kein SQLite) mit Joins/Aggregationen | ✅ (Vorbehalt) | Umgesetzt (CC-3 ✅: `src/postgres_mirror.py`, Notebook 04). Offen: zählt ein Mirror zusätzlich zu SQLite? Frage an Mario (#10, #22). |
| 3 | Geografische Daten visualisiert | ✅ | Folium-Karte und Windkarte (CC-2 ✅). Optional: Residuen-Karte (#17). |
| 4 | Chi², ANOVA oder Korrelation mit p-Wert | ✅ | Spearman steht. Kruskal-Wallis über Zonen innerhalb von Höhenbändern und Chi² Kategorie × Zone machen es robuster (→ CC-4). |
| 5 | k-Means zusätzlich | 🟡 | Läuft, aber nur auf 2 Merkmalen, Ergebnis trivial. Mehr Merkmale und Kreuztabelle mit Kategorie und Zone (→ CC-11, #21). |
| 6 | Öffentliches GitHub-Repo | 🟡 | Repo ist bereits **öffentlich**. Publishing-Check (→ CC-6), README, Lizenz, Datenquellen (#24, #51), URL auf die Folien. |

### Video (7 Punkte)

Länge = 3 Personen × 5 Min. = **15 Minuten**. Alle sprechen, KI-Reflexion ist ein eigenes Kriterium, Code nur zeigen, wenn er etwas erklärt. Das ist reine Vorbereitungsarbeit und kommt bei den Issues dran.

## 3. Bereits umgesetzt

**12. November 2026**

- **Hauptsammlung gestartet** auf dem alten MacBook (macOS Monterey 12.7.6): 12.11. 19:30 bis 26.11. 19:30, alle 5 Minuten, 14 Tage (#47). Erster Check: 9 Snapshots, 0 Fehler.
- **Kartenausschnitt vergrössert** auf 45.6–48.2 °N, 5.2–10.6 °E. Vorher lag Genf 24 km vom Westrand, vom Ring 30–60 km um Genf waren nur 68 % abgedeckt (#52, `DECISIONS.md`).
- **Projekt-Review** gegen das Bewertungsraster (`docs/REVIEW_2026-11-12.md`), alle Punkte als Issues bzw. Kommentare erfasst (#47–#52).
- CC-2 (EDA Wind und Typ) und CC-3 (PostgreSQL) am 11.11. erledigt.

**11. November 2026**


- **Winddaten als dritte Quelle** (`src/weather.py`, `docs/WEATHER.md`): stündlicher Modellwind auf 11 Druckstufen, Rohdaten mit Manifest, zeilenerhaltender Join, Rückenwind/Seitenwind/geschätzte Fluggeschwindigkeit. Erster echter Test: 124/124 Beobachtungen gematcht, Jetstream ~53 m/s auf 9–11 km.
- **Vertikale Interpolation** statt nächster Stufe: Anteil mit >500 m Höhenabstand von 22 % auf 3 % gesenkt; 150 hPa ergänzt den Rest nach einem erneuten `fetch`.
- **Modell D** in `src/model_comparison.py` (Raum + Kategorie + Wind) mit Prüfung gegen Ziel-Leakage (`airspeed_est_ms` ist aus der Zielvariable berechnet und darf nie Feature sein).
- **Mac-Sammler** und Setup für das MacBook.
- `.DS_Store` in `.gitignore` aufgenommen.
- Tests: 31/31 grün.

Was ich am bestehenden Code geprüft und **für gut befunden** habe: Leakage-Schutz in den Modellen, Mindestgrenze von 7 Tagen vor jeder Evaluation, getrennte Splits (spätere Tage / andere Flugzeuge), skaliertes k-Means mit Silhouette, Spearman mit einer Beobachtung pro Flugzeug, Audits bei jedem Join, Checksummen und Export. Das ist methodisch deutlich sauberer als die 5.5er-Referenzarbeit.

## 4. Grösste Risiken

1. **Ausfall des Sammel-Macs.** Jeder Tag ohne Snapshots fehlt für immer. Täglicher Status-Check, Lücken mit Grund notieren (#4).
2. **Flugzeugkategorie ist zu grob.** Die heutige Zuordnung über die ICAO-Beschreibung macht aus A320, B777 und Citation dieselbe Kategorie, die ADS-B-Kategorie ist fast immer 0. Mario hat die Kategorie ausdrücklich verlangt → CC-7 jetzt.
3. **Metadaten-Datei fehlt auf dem Mac** und ist vom November 2024; Abdeckung im Pilot nur ~67 %. → CC-7 lädt sie neu und dokumentiert die Version.
4. **Die Forschungsfrage wird noch nicht direkt getestet** (kein Interaktionstest near/far, kein Flughafenvergleich). → CC-8 vor dem 19.11.
5. **Interpretation unter Zeitdruck.** Sammlung bis 26.11., Analyse bis 30.11. Interpretation als feste Phase in KW 48 (#23), Notebooks parallel als Bericht schreiben (#48).
6. **PostgreSQL-Bonus unsicher**, bis Mario antwortet (#10).

## 5. Aufträge für Claude Code

So verwenden: in VS Code Claude Code öffnen, den Auftrag als Prompt einfügen. **Immer nur einer gleichzeitig, und nicht parallel zu einer Cowork-Session an denselben Dateien arbeiten.** **Reihenfolge ab 12.11.:** CC-7 jetzt → CC-10 → CC-8 und CC-9 bis 19.11. → CC-1, CC-4, CC-11 bis 26.11. → CC-12 → CC-5 und CC-6 im Dezember. Jeder Auftrag endet mit grünen Tests, Eintrag in `docs/CHANGELOG_MATTEO.md` und `docs/AI_USAGE_LOG.csv` und einem Commit auf `matteo/Data-Analytics-Aviation` (kein Push ohne dein OK).

Die Notebooks verweigern Modelle bei weniger als 7 Sammeltagen. Bis dahin Notebook-Änderungen nur so weit testen, wie es mit dem Pilot geht, und die Sperre **nicht** entfernen.

### CC-1 · Wind und Kategorie in die Modellkette (Notebook 02) — passt zu #18

> Lies `docs/ROADMAP_5.5.md` (Abschnitt CC-1), `docs/WEATHER.md` und `src/model_comparison.py`. Erweitere die letzte Code-Zelle von `notebooks/02_models.ipynb`: Lade zusätzlich `SELECT icao24, time_position, tailwind_ms, crosswind_ms FROM observation_wind` (nur wenn die Tabelle existiert) und hänge die Spalten mit einem `one_to_one`-Merge auf `(icao24, time_position)` an dieselben Train/Test-Frames wie die Kategorie, mit denselben Zeilen-Asserts. `compare_models` erkennt die Windspalten selbst und rechnet dann Modell D. Ergänze eine Markdown-Zelle, die A→B→C→D als Frage formuliert: «Wie viel erklären Raum, Flugzeugtyp und Wind jeweils zusätzlich?» Füge eine Grafik hinzu: RMSE pro Modell und Zone (near/far) für beide Splits. Verwende **nie** `airspeed_est_ms` als Feature. Teste die Zelle mit einem kleinen synthetischen Datensatz über 8 Tage in einem neuen Unit-Test, nicht mit echten Daten.

### CC-2 · EDA um Wind und Kategorie erweitern (Notebook 01) — passt zu #16, #17 · ✅ erledigt 11.11.

> Erweitere `notebooks/01_data_and_eda.ipynb` um einen Abschnitt «Wind und Flugzeugtyp», der `observations_with_wind` und `observations_enriched` per SQL liest: (1) Tabelle Windgeschwindigkeit und Rückenwind nach Höhenband und Zone; (2) Grafik Grundgeschwindigkeit vs. geschätzte Fluggeschwindigkeit (`airspeed_est_ms`) über der Höhe, nur beschreibend; (3) Verteilung des Rückenwinds nach Flugrichtung (Ost vs. West, aus `true_track`); (4) Anteil Beobachtungen pro Flugzeugkategorie und Zone inkl. `unknown/other`; (5) Folium-Karte: Windpfeile des Rasters für eine gewählte Stunde über die Beobachtungen gelegt. Jede Grafik mit Achsen in Einheiten, Titel und Legende, gespeichert unter `outputs/figures/`. Füge nach jedem Block eine Markdown-Zelle mit Interpretations-Platzhalter für die Gruppe ein. Die Wind-Audit-Tabelle (`weather_integration_audit`) gehört in den Datenqualitätsteil.

### CC-3 · PostgreSQL-Bonus — passt zu #22 · ✅ erledigt 11.11.

> Ziel: Bonuskriterium «PostgreSQL mit Joins und Aggregationen aus Python», zusätzlich zu SQLite (SQLite bleibt Pflicht). Installiere lokal PostgreSQL (`brew install postgresql@16`, `brew services start postgresql@16`). Erstelle `src/postgres_mirror.py`: liest die Tabellen aus `data/processed/aircraft.sqlite` und schreibt sie mit expliziten Typen, Primärschlüsseln (`observations(icao24,time_position)`, `airports(ident)`, `aircraft_metadata(icao24)`, `observation_wind(icao24,time_position)`) und Fremdschlüsseln (`observations.airport_ident → airports.ident`, `observation_wind → observations`) in eine Datenbank `aviation`. Verbindung über die Umgebungsvariable `DATABASE_URL`, nie Passwörter im Code. Füge `psycopg[binary]` und `sqlalchemy` zu `requirements.txt` hinzu. Neues Notebook `notebooks/04_postgresql.ipynb` mit mindestens drei SQL-Abfragen aus Python: Join Beobachtungen–Flughäfen–Wind, Aggregation nach Zone und Höhenband, Fensterfunktion (z. B. Rang der schnellsten Flugzeuge pro Flughafen). Zeige, dass die Zeilenzahlen mit SQLite übereinstimmen. Dokumentiere Installation und Start in `docs/POSTGRESQL.md`. Tests: Typ- und Schlüssel-Mapping offline testen, ohne laufenden Server.

### CC-4 · Statistische Tests robuster machen (Notebook 03) — passt zu #20

> Ergänze `notebooks/03_statistics_and_clusters.ipynb` um (1) Kruskal-Wallis-Test der Grundgeschwindigkeit über near/middle/far **innerhalb** jedes Höhenbands mit genügend Daten (eine Beobachtung pro Flugzeug und Band, Mindestgrösse pro Gruppe 20), mit H-Statistik, p-Wert, n pro Gruppe und Effektgrösse (epsilon²); (2) Chi²-Unabhängigkeitstest Flugzeugkategorie × Zone (eine Zeile pro Flugzeug, Kategorien mit erwarteter Häufigkeit < 5 zusammenfassen), mit Cramér's V. Beide Tests mit Annahmen und Hinweis auf multiples Testen (Holm-Korrektur über die Höhenbänder). Keine Tests zwischen Variablen, die aus derselben Grösse abgeleitet sind (z. B. Speed-Bins vs. Speed-Cluster). Ergebnisse als CSV in `outputs/tables/`.

### CC-5 · Mac-Reproduzierbarkeit — passt zu #25

> Die README beschreibt nur Windows. Ergänze einen Abschnitt «Local setup (macOS)» mit `python3.13 -m venv .venv`, Installation aus `requirements-lock.txt` mit `pywinpty` ausgeschlossen (siehe Phase 0 in `docs/CHANGELOG_MATTEO.md`) und den Befehlen `src/weather.py fetch` und `src/prepare.py`. Kläre die offene Frage aus Phase 0: plattformabhängige Pakete (`pywinpty`, `appnope`, `pexpect`, `ptyprocess`) mit Umgebungsmarkern ins Lockfile aufnehmen, sodass dieselbe Datei auf Windows und macOS installiert. Prüfe mit einer frischen venv.

### CC-6 · Publishing-Check — passt zu #24, #51

> Das Repo ist bereits öffentlich. Prüfe es deshalb sofort: Suche in der gesamten Git-Historie nach Zugangsdaten, Tokens, E-Mail-Adressen und privaten Pfaden (`git log -p`, z. B. mit `gitleaks`, falls installiert) und liste Funde auf, ohne die Historie umzuschreiben. Prüfe, dass `data/`, `outputs/`, `exports/` und `.DS_Store` ignoriert werden und keine solche Datei in der Historie liegt. Schlage eine Lizenz und einen kurzen Abschnitt «Data sources and terms» für die README vor (OpenSky, OurAirports, Open-Meteo CC BY 4.0). Ergebnis als Bericht `docs/PUBLISHING_CHECK.md`.

### CC-7 · Flugzeugkategorie über Typecode + Filter alter Ausschnitt — passt zu #12, #52 · **als Nächstes**

> Ausführlicher Auftrag: `Prompt/Claude_Code_Prompt_CC-7_Kategorie.md` (ausserhalb des Repos). Kurz: aktuelle OpenSky-Metadaten laden und als neue gepinnte Version dokumentieren; eigene Tabelle `data/reference/typecode_category.csv` mit den Kategorien Kurzstrecke, Regionaljet, Langstrecke, Turboprop, Business-Jet, Sonstige, Unbekannt; Reihenfolge Typecode → ICAO-Beschreibung → Unbekannt; ADS-B-Kategorie nur als Kreuzcheck; nicht gemappte Typecodes mit Anzahl; in `prepare.py` Snapshots mit altem Kartenausschnitt ausschliessen und im Audit zählen. Schema vor dem Blick auf Resultate in `DECISIONS.md` einfrieren.

### CC-8 · Forschungsfrage direkt testen: OLS mit Interaktionen — passt zu #19

> In Notebook 03 (oder 02) eine OLS-Regression mit `statsmodels`: `velocity ~ altitude_km + I(altitude_km**2) + C(zone) * altitude_km + C(airport)` mit cluster-robusten Standardfehlern nach `icao24` (`cov_type="cluster"`). Der Koeffizient `altitude_km:C(zone)[T.near]` mit p-Wert beantwortet Teilfrage 1. Zweite Variante mit `C(airport) * altitude_km` für ZRH vs. GVA vs. BSL, dritte mit `C(aircraft_category) * altitude_km`. Koeffiziententabelle und Steigung pro Zone mit 95-%-Konfidenzintervall, in m/s und km/h. `statsmodels` in `requirements.txt` und Lockfile. Test auf synthetischen Daten mit bekannter Interaktion.

### CC-9 · Modellform, Koeffizienten, Leakage-Demo, Fehlergrafik — passt zu #18

> In `src/model_comparison.py` und Notebook 02: Modell A nicht-linear (Polynom 2. Grades oder `SplineTransformer`), `latitude`/`longitude` nicht als lineare Features (höchstens im Random Forest). Koeffiziententabelle der linearen Modelle (standardisiert und in Originaleinheiten). Leakage-Demo: dieselben Features einmal mit zufälligem Split (`random_state=42`), klar als «Demonstration, nicht Ergebnis» bezeichnet, gegen Split nach Tag und nach Flugzeug. Ergebnisgrafik: RMSE nach Modell (0, A–D) × Zone × Split, optional Bootstrap-Konfidenzintervall nach Flugzeug. R² nicht zwischen near und far vergleichen. Die 7-Tage-Sperre bleibt.

### CC-10 · Aufbereitung: Höhe, Plausibilität, weitere Flughäfen, Flugphase — passt zu #13

> In `src/prepare.py`, jede Stufe mit Zeile in `integration_audit`: `altitude_m` aus `geo_altitude`, sonst `baro_altitude`, plus `altitude_source`; Plausibilitätsfilter mit Schwellen in `config.json` (Höhe −300 bis 15'500 m, Speed 0–350 m/s, |vertical_rate| ≤ 40 m/s, fehlende Steigrate nicht filtern); Puffer um weitere Verkehrsflughäfen im Ausschnitt (mindestens LIMC, LIME, EDNY, LSZB, LSZA, LSGS, EDSB; Liste in `config.json`) mit Modus `exclude` oder `own_zone`, ohne die Zuordnung zu ZRH/GVA/BSL zu ändern; Spalte `airport` (ZRH/GVA/BSL); Spalte `flight_phase` (climb/level/descent, Schwelle ±2.5 m/s in `config.json`). EDA-Tabelle «ausgeschlossene Zeilen pro Grund». Tests für jede Stufe.

### CC-11 · k-Means aussagekräftiger — passt zu #21

> In Notebook 03: Merkmale `altitude_m`, `velocity`, `vertical_rate` (standardisiert, auf Punktebene) bzw. Profil pro Flugzeug und Tag (Median-Höhe, Median-Speed, Median |vertical_rate|, Anteil near, Median-Distanz). k = 2–6 mit Inertia und Silhouette (feste Stichprobe). Cluster mit Kategorie und Zone kreuztabellieren und vorsichtig als Flugphasen bzw. Flugzeugtypen beschreiben.

### CC-12 · Sensitivität der Zonenschwellen — passt zu #50

> Kern-Effekt near vs. far (Interaktionskoeffizient aus CC-8 oder Median-Differenz pro Höhenband) für 20/50, 30/60 und 40/80 km sowie mit und ohne Puffer um weitere Flughäfen (CC-10). Kleine Tabelle mit Effekt, Konfidenzintervall und n. Hauptschwellen 30/60 km bleiben, wie in `DECISIONS.md` eingefroren.

## 6. Später, mit den Issues

Nicht-Code-Arbeit, als Issues geplant: Sammlung überwachen und einfrieren (#4, #15), Daten teilen (#14), Wind für alle Sammeltage holen nach dem 26.11. (#22), Konzeptpräsentation am 19.11. (Kevin, #6–#9, #11), Fragen an Mario (#10), Interpretation (#23), Notebooks als Bericht (#48), Walkthrough (#49), KI-Reflexion (#26), Repo aufräumen (#51), Video und Moodle (#27–#29).

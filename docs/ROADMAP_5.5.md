# Roadmap zur Note 5.5–6

Stand: 11. November 2026, Branch `matteo/Data-Analytics-Aviation`. Erstellt nach einer Durchsicht von Code, Notebooks, Tests und Doku gegen das Bewertungsraster in `docs/COURSE_EVALUATION.md`. Eine Note lässt sich nicht garantieren; diese Liste zeigt, wo die Punkte liegen und was dafür noch fehlt.

## 1. Wo die Punkte liegen

Schlussprojekt: **max. 22 Punkte** = 9 Pflicht + 6 Bonus + 7 Video. Wie Punkte in Noten umgerechnet werden, steht im Auszug nicht. Für eine 5.5–6 sollte das Ziel sein: **alle 9 Pflichtpunkte, mindestens 5 der 6 Bonuspunkte und 6–7 Punkte beim Video.** Jeder fehlende Pflichtpunkt kostet mehr als ein Bonuspunkt bringt.

Die Konzeptpräsentation (19.11., 10 Min., 8 Kriterien) ist separat bewertet. Ob und wie stark sie in die Note eingeht, ist im Auszug nicht angegeben.

## 2. Stand pro Kriterium

Legende: ✅ steht · 🟡 Code steht, Ergebnis fehlt · ❌ fehlt

### Pflicht (9 Punkte)

| # | Kriterium | Stand | Beleg im Repo | Was noch fehlt |
|---|---|---|---|---|
| 1 | Eigene Datensammlung per API | 🟡 | `src/collect.py`, Pilot 1.10. (35 Snapshots, 968 Flugzeuge), Mac-/Windows-Skripte | **Hauptsammlung läuft noch nicht.** Grösstes Risiko des ganzen Projekts. |
| 2 | Integration ≥ 2 Quellen, dokumentiert | ✅/🟡 | OpenSky + OurAirports (räumlich), Flugzeug-Metadaten (Key-Join `icao24`), neu Wind (Zeit/Ort/Höhe); Audits mit Zeilen vor/nach | Audits auf den finalen Daten erzeugen und auf einer Folie zeigen |
| 3 | SQLite + SQL aus Python | ✅ | `prepare.py`, Views `observations_enriched`, `observations_with_wind`, SQL-Aggregationen in Notebook 01 | – |
| 4 | Reiche EDA (Tabellen + Grafiken) | 🟡 | Notebook 01: Qualität, Abdeckung, Verteilungen, Höhe×Speed, Höhenbänder, Karte | Wind und Kategorie fehlen in der EDA (→ CC-2) |
| 5 | Regression mit Frage über Standard-Vorhersage hinaus | ✅ | Near/far-Vergleich, spätere Tage vs. andere Flugzeuge, Modellkette A–C | Wind-Modell D einbinden (→ CC-1) |
| 6 | Evaluation mit Gütemassen | ✅ | MAE, RMSE, R² pro Gruppe, Baseline | Läuft erst ab 7 Sammeltagen (bewusste Sperre) |
| 7 | Korrekte Interpretation | ❌ | Platzhalter in den Notebooks | Nach den finalen Ergebnissen, gemeinsam |
| 8 | KI-Dokumentation inkl. Vor-/Nachteile | 🟡 | `docs/AI_USAGE_LOG.csv`, `docs/CHANGELOG_MATTEO.md` | Laufend nachführen, Reflexion für Video/Folien |
| 9 | Material auf Moodle | ❌ | `src/export_data.py` (datierter, geprüfter Export) | Am Schluss |

### Bonus (6 Punkte)

| # | Kriterium | Stand | Was noch fehlt |
|---|---|---|---|
| 1 | Kreativität | 🟡 | Stark: Zerlegung der Grundgeschwindigkeit in **Flugzeug + Wind** (neu). Muss in EDA und Modellen sichtbar werden (→ CC-1, CC-2). |
| 2 | PostgreSQL o. ä. (kein SQLite) mit Joins/Aggregationen | ❌ | Nicht implementiert. Frage an Dozenten offen (#22), technisch aber gut machbar (→ CC-3). **Sicherer Bonuspunkt, den ihr nicht liegen lassen solltet.** |
| 3 | Geografische Daten visualisiert | ✅ | Folium-Karte. Besser: Karte mit Modellfehlern oder Windfeld (→ CC-2). |
| 4 | Chi², ANOVA oder Korrelation mit p-Wert | ✅ | Spearman steht. Kruskal-Wallis über Zonen innerhalb von Höhenbändern und Chi² Kategorie × Zone machen es robuster (→ CC-4). |
| 5 | k-Means zusätzlich | ✅ | Flugzeugprofile, skaliert, Silhouette. Optional: Profil mit windbereinigter Geschwindigkeit. |
| 6 | Öffentliches GitHub-Repo | 🟡 | Repo existiert. Vor dem Veröffentlichen bereinigen (→ CC-6), URL auf die Folien. |

### Video (7 Punkte)

Länge = 3 Personen × 5 Min. = **15 Minuten**. Alle sprechen, KI-Reflexion ist ein eigenes Kriterium, Code nur zeigen, wenn er etwas erklärt. Das ist reine Vorbereitungsarbeit und kommt bei den Issues dran.

## 3. Heute verbessert (bereits committet)

- **Winddaten als dritte Quelle** (`src/weather.py`, `docs/WEATHER.md`): stündlicher Modellwind auf 11 Druckstufen, Rohdaten mit Manifest, zeilenerhaltender Join, Rückenwind/Seitenwind/geschätzte Fluggeschwindigkeit. Erster echter Test: 124/124 Beobachtungen gematcht, Jetstream ~53 m/s auf 9–11 km.
- **Vertikale Interpolation** statt nächster Stufe: Anteil mit >500 m Höhenabstand von 22 % auf 3 % gesenkt; 150 hPa ergänzt den Rest nach einem erneuten `fetch`.
- **Modell D** in `src/model_comparison.py` (Raum + Kategorie + Wind) mit Prüfung gegen Ziel-Leakage (`airspeed_est_ms` ist aus der Zielvariable berechnet und darf nie Feature sein).
- **Mac-Sammler** und Setup für das MacBook.
- `.DS_Store` in `.gitignore` aufgenommen.
- Tests: 31/31 grün.

Was ich am bestehenden Code geprüft und **für gut befunden** habe: Leakage-Schutz in den Modellen, Mindestgrenze von 7 Tagen vor jeder Evaluation, getrennte Splits (spätere Tage / andere Flugzeuge), skaliertes k-Means mit Silhouette, Spearman mit einer Beobachtung pro Flugzeug, Audits bei jedem Join, Checksummen und Export. Das ist methodisch deutlich sauberer als die 5.5er-Referenzarbeit.

## 4. Grösste Risiken

1. **Sammlung startet zu spät.** Ohne 7–14 Tage keine Modelle, keine Interpretation. Alles andere ist zweitrangig.
2. **Flugzeugkategorie ist dünn.** Metadaten decken im Pilot nur ~67 % der Beobachtungen ab, die ADS-B-Kategorie ist fast immer 0. Mario hat die Kategorie ausdrücklich verlangt → in der EDA offen zeigen, `unknown/other` als eigene Gruppe behalten.
3. **Metadaten-Datei fehlt auf dem Mac.** Die 94-MB-Datei liegt nur auf dem Windows-Gerät. Wer final auswertet, braucht sie (oder `collect.py metadata` neu laden und als neue gepinnte Datei dokumentieren).
4. **PostgreSQL-Bonus offen.** Ohne ihn ist das Maximum 21/22.
5. **Interpretation unter Zeitdruck.** Sammlung bis ~26.11., Analyse bis 30.11. ist eng; Interpretation und Folien deshalb parallel vorbereiten.

## 5. Aufträge für Claude Code

So verwenden: in VS Code Claude Code öffnen, den Auftrag als Prompt einfügen. **Immer nur einer gleichzeitig, und nicht parallel zu einer Cowork-Session an denselben Dateien arbeiten.** Jeder Auftrag endet mit grünen Tests, Eintrag in `docs/CHANGELOG_MATTEO.md` und `docs/AI_USAGE_LOG.csv` und einem Commit auf `matteo/Data-Analytics-Aviation` (kein Push ohne dein OK).

Die Notebooks verweigern Modelle bei weniger als 7 Sammeltagen. Bis dahin Notebook-Änderungen nur so weit testen, wie es mit dem Pilot geht, und die Sperre **nicht** entfernen.

### CC-1 · Wind und Kategorie in die Modellkette (Notebook 02) — passt zu #18

> Lies `docs/ROADMAP_5.5.md` (Abschnitt CC-1), `docs/WEATHER.md` und `src/model_comparison.py`. Erweitere die letzte Code-Zelle von `notebooks/02_models.ipynb`: Lade zusätzlich `SELECT icao24, time_position, tailwind_ms, crosswind_ms FROM observation_wind` (nur wenn die Tabelle existiert) und hänge die Spalten mit einem `one_to_one`-Merge auf `(icao24, time_position)` an dieselben Train/Test-Frames wie die Kategorie, mit denselben Zeilen-Asserts. `compare_models` erkennt die Windspalten selbst und rechnet dann Modell D. Ergänze eine Markdown-Zelle, die A→B→C→D als Frage formuliert: «Wie viel erklären Raum, Flugzeugtyp und Wind jeweils zusätzlich?» Füge eine Grafik hinzu: RMSE pro Modell und Zone (near/far) für beide Splits. Verwende **nie** `airspeed_est_ms` als Feature. Teste die Zelle mit einem kleinen synthetischen Datensatz über 8 Tage in einem neuen Unit-Test, nicht mit echten Daten.

### CC-2 · EDA um Wind und Kategorie erweitern (Notebook 01) — passt zu #16, #17

> Erweitere `notebooks/01_data_and_eda.ipynb` um einen Abschnitt «Wind und Flugzeugtyp», der `observations_with_wind` und `observations_enriched` per SQL liest: (1) Tabelle Windgeschwindigkeit und Rückenwind nach Höhenband und Zone; (2) Grafik Grundgeschwindigkeit vs. geschätzte Fluggeschwindigkeit (`airspeed_est_ms`) über der Höhe, nur beschreibend; (3) Verteilung des Rückenwinds nach Flugrichtung (Ost vs. West, aus `true_track`); (4) Anteil Beobachtungen pro Flugzeugkategorie und Zone inkl. `unknown/other`; (5) Folium-Karte: Windpfeile des Rasters für eine gewählte Stunde über die Beobachtungen gelegt. Jede Grafik mit Achsen in Einheiten, Titel und Legende, gespeichert unter `outputs/figures/`. Füge nach jedem Block eine Markdown-Zelle mit Interpretations-Platzhalter für die Gruppe ein. Die Wind-Audit-Tabelle (`weather_integration_audit`) gehört in den Datenqualitätsteil.

### CC-3 · PostgreSQL-Bonus — passt zu #22

> Ziel: Bonuskriterium «PostgreSQL mit Joins und Aggregationen aus Python», zusätzlich zu SQLite (SQLite bleibt Pflicht). Installiere lokal PostgreSQL (`brew install postgresql@16`, `brew services start postgresql@16`). Erstelle `src/postgres_mirror.py`: liest die Tabellen aus `data/processed/aircraft.sqlite` und schreibt sie mit expliziten Typen, Primärschlüsseln (`observations(icao24,time_position)`, `airports(ident)`, `aircraft_metadata(icao24)`, `observation_wind(icao24,time_position)`) und Fremdschlüsseln (`observations.airport_ident → airports.ident`, `observation_wind → observations`) in eine Datenbank `aviation`. Verbindung über die Umgebungsvariable `DATABASE_URL`, nie Passwörter im Code. Füge `psycopg[binary]` und `sqlalchemy` zu `requirements.txt` hinzu. Neues Notebook `notebooks/04_postgresql.ipynb` mit mindestens drei SQL-Abfragen aus Python: Join Beobachtungen–Flughäfen–Wind, Aggregation nach Zone und Höhenband, Fensterfunktion (z. B. Rang der schnellsten Flugzeuge pro Flughafen). Zeige, dass die Zeilenzahlen mit SQLite übereinstimmen. Dokumentiere Installation und Start in `docs/POSTGRESQL.md`. Tests: Typ- und Schlüssel-Mapping offline testen, ohne laufenden Server.

### CC-4 · Statistische Tests robuster machen (Notebook 03) — passt zu #20

> Ergänze `notebooks/03_statistics_and_clusters.ipynb` um (1) Kruskal-Wallis-Test der Grundgeschwindigkeit über near/middle/far **innerhalb** jedes Höhenbands mit genügend Daten (eine Beobachtung pro Flugzeug und Band, Mindestgrösse pro Gruppe 20), mit H-Statistik, p-Wert, n pro Gruppe und Effektgrösse (epsilon²); (2) Chi²-Unabhängigkeitstest Flugzeugkategorie × Zone (eine Zeile pro Flugzeug, Kategorien mit erwarteter Häufigkeit < 5 zusammenfassen), mit Cramér's V. Beide Tests mit Annahmen und Hinweis auf multiples Testen (Holm-Korrektur über die Höhenbänder). Keine Tests zwischen Variablen, die aus derselben Grösse abgeleitet sind (z. B. Speed-Bins vs. Speed-Cluster). Ergebnisse als CSV in `outputs/tables/`.

### CC-5 · Mac-Reproduzierbarkeit — passt zu #25

> Die README beschreibt nur Windows. Ergänze einen Abschnitt «Local setup (macOS)» mit `python3.13 -m venv .venv`, Installation aus `requirements-lock.txt` mit `pywinpty` ausgeschlossen (siehe Phase 0 in `docs/CHANGELOG_MATTEO.md`) und den Befehlen `src/weather.py fetch` und `src/prepare.py`. Kläre die offene Frage aus Phase 0: plattformabhängige Pakete (`pywinpty`, `appnope`, `pexpect`, `ptyprocess`) mit Umgebungsmarkern ins Lockfile aufnehmen, sodass dieselbe Datei auf Windows und macOS installiert. Prüfe mit einer frischen venv.

### CC-6 · Veröffentlichung vorbereiten (nicht veröffentlichen) — passt zu #24

> Bereite das Repo für eine spätere Veröffentlichung vor, ohne es öffentlich zu schalten: Suche in der gesamten Git-Historie nach Zugangsdaten, Tokens, E-Mail-Adressen und privaten Pfaden (`git log -p`, z. B. mit `gitleaks`, falls installiert) und liste Funde auf, ohne die Historie umzuschreiben. Prüfe, dass `data/`, `outputs/`, `exports/` und `.DS_Store` ignoriert werden und keine solche Datei in der Historie liegt. Schlage eine Lizenz und einen kurzen Abschnitt «Data sources and terms» für die README vor (OpenSky, OurAirports, Open-Meteo CC BY 4.0). Ergebnis als Bericht `docs/PUBLISHING_CHECK.md`.

## 6. Später, mit den Issues

Nicht-Code-Arbeit, die wir im nächsten Schritt als Issues planen: Sammlung starten und überwachen (#3, #4, #32), Wind für alle Sammeltage holen (#36), Konzeptpräsentation am 19.11. (#6–#9, #11), Fragen an die Dozenten (#10, #22), Interpretation (#23), Video und Moodle (#27–#29).

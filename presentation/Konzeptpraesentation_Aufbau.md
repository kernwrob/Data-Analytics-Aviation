# Konzeptpräsentation – Aufbau und Inhalte

**Data Analytics Leistungsnachweis · ZHAW SML · HS 26/27**
Gruppe: Kevin, Matteo, Robin · Dozierende: Mario, Alexander
Stand: 12.11.2026

> **Für Claude / KI-Assistenten:** Diese Datei ist die verbindliche Grundlage für die Folien. Thema, Forschungsfrage und Methoden sind festgelegt und von Mario akzeptiert. Keine neuen Themen vorschlagen. **Keine Resultate erfinden**: Es gibt nur Pilotdaten (1.10.2026, ca. 3 Stunden). Alle Grafiken aus dem Pilot als «Pilotdaten, keine Resultate» beschriften. Sprache der Folien: Deutsch. Ziel: in allen 8 Bewertungskriterien Note 6.

---

## 1. Rahmen

| Punkt | Vorgabe |
|---|---|
| Termin | **Do, 19.11.2026**, vor Ort in Winterthur, zu Beginn der Vorlesung |
| Abgabe Folien | **PDF auf Moodle bis Sa, 14.11.2026** |
| Dauer | **10 Minuten**, frei gesprochen, alle drei sprechen (je ca. 3 Min.) |
| Inhalt | Die Idee, **noch ohne Resultate**. Das Thema wird hier offiziell genehmigt. |
| Umfang | ca. 9–10 Folien (≈ 1 Min. pro Folie) |
| Bewertung | Note 1–6, Durchschnitt aus 8 Kriterien |

### Die 8 Bewertungskriterien und wo sie abgedeckt werden

| # | Kriterium | Was es für die 6 braucht | Folie(n) |
|---|---|---|---|
| 1 | Struktur | Klarer Titel, **alle vollen Namen**, Agenda, roter Faden, ausgewogene Gewichtung | 1, 2, Übergänge |
| 2 | Hintergrund & Problem | Kontext klar, Problem überzeugend motiviert (nicht nur «tief = langsam») | 3 |
| 3 | Ziel & Forschungsfrage | Eine klare Hauptfrage + 3 Teilfragen | 4 |
| 4 | Daten | **Quellen zeigen** (Name, Link/Logo), **Struktur erklären** (Beispielzeile, Spalten, Einheiten, Umfang) | 5, 6 |
| 5 | Methoden | Passend zur Frage, korrekt beschrieben, **begründet** («wir machen X, weil …») | 7, 8 |
| 6 | Erwartete Resultate | Plausible Hypothesen, **direkt mit den Teilfragen verknüpft** | 9 |
| 7 | Sprache | Frei sprechen, keine Textwüste ablesen, Fachbegriffe erklären | alle |
| 8 | Qualität | Grafiken mit Achsenbeschriftung, Einheiten, Legende, Quelle; Tabellen sauber; wenig Text | alle |

---

## 2. Roter Faden (in einem Satz)

**Beschreiben → Modellieren → ehrlich testen.**
Wir sammeln selbst Flugdaten über der Schweiz, vergleichen Höhe und Geschwindigkeit nahe den Flughäfen mit dem Streckenflug und prüfen, ob Ort, Flugzeugtyp und Wind die Vorhersage verbessern, auch für neue Tage und unbekannte Flugzeuge.

---

## 3. Folienaufbau

### Folie 1 – Titel
- **Titel (Vorschlag):** «Tief und langsam, hoch und schnell? Flughöhe und Geschwindigkeit über der Schweiz»
- Untertitel: Data Analytics Leistungsnachweis, Konzeptpräsentation
- **Volle Namen aller drei**, Gruppennummer, ZHAW SML, HS 26/27, Datum 19.11.2026
- Bild: Flugzeug im Anflug oder Karte der Schweiz mit Flugspuren (eigene Pilotkarte, Quelle angeben)

### Folie 2 – Agenda
Hintergrund · Forschungsfrage · Daten · Pipeline · Methoden · Erwartete Resultate · Zeitplan
(Optional: wer welchen Teil präsentiert)

### Folie 3 – Hintergrund & Problem
Kernaussagen:
- Flugzeuge sind beim Start und bei der Landung **tief und langsam**, im Reiseflug **hoch und schnell**.
- In Europa gilt unter 10'000 ft (≈ 3'000 m) meist ein Tempolimit von **250 Knoten (≈ 460 km/h)**. Nahe den Flughäfen sollte der Zusammenhang also anders aussehen als im Streckenflug.
- **Das eigentliche Problem:** Die API liefert die **Geschwindigkeit über Grund**. Diese hängt nicht nur von der Höhe ab, sondern auch vom **Ort** (Anflug vs. Reiseflug), vom **Flugzeugtyp** und vom **Wind** (in Reiseflughöhe oft 150–200 km/h). Wie viel davon erklärt was, ist nicht offensichtlich.
- **Warum relevant (Motivation):** Lärmprognose rund um Flughäfen, Luftraumplanung, Erkennen auffälliger Anflüge.
- Abgrenzung: Das Grundresultat «tief = langsam» ist erwartbar. Interessant ist, den Unterschied zu **quantifizieren**, die Faktoren zu **erklären** und **ehrlich zu testen**, ob ein Modell auf neue Situationen übertragbar ist.

Grafik: schematisches Flugprofil (Start → Steigflug → Reiseflug → Sinkflug → Landung) mit Zone «nah» markiert.

### Folie 4 – Ziel & Forschungsfrage
**Hauptfrage:**
> «Wie unterscheidet sich der Zusammenhang zwischen Flughöhe und Geschwindigkeit in Flughafennähe und im Streckenflug, und verbessert zusätzlicher Kontext (Ort, Flugzeugtyp, Wind) die Vorhersage für ungesehene Tage und Flugzeuge?»

**Drei Teilfragen:**
1. **Vergleich:** Wie unterscheidet sich der Zusammenhang Höhe ↔ Geschwindigkeit nahe den Flughäfen Zürich (ZRH), Genf (GVA), Basel (BSL) und im Streckenflug?
2. **Modell:** Sagt ein angereichertes Modell (Höhe + Ort + Flugzeugkategorie + Wind) die Geschwindigkeit besser voraus als ein Modell, das nur die Höhe kennt?
3. **Evaluation:** Gilt das auch für **spätere Tage** und für **unbekannte Flugzeuge**?

Hinweis fürs Sprechen: Die Frage geht bewusst über eine reine Vorhersage hinaus (Vergleich nah/fern + Generalisierung). Die Flugzeugkategorie ist auf Wunsch von Mario drin, um die Analyse zu vertiefen.

### Folie 5 – Datenquellen
| Quelle | Inhalt | Zugang | Rolle |
|---|---|---|---|
| **OpenSky Network API** | Position, Höhe, Geschwindigkeit über Grund, Steig-/Sinkrate, Kurs, `icao24` | REST-API, alle 5 Min. per Python-Skript, **selbst gesammelt** | Hauptquelle |
| **OurAirports** | Koordinaten ZRH, GVA, BSL | CSV-Download | Distanz zum Flughafen, Zone |
| **OpenSky Flugzeugdatenbank** | Flugzeugtyp pro `icao24` (ca. 520'000 Einträge) | CSV, Join auf `icao24` | Flugzeugkategorie |
| **Open-Meteo** | Wind auf 11 Druckstufen (≈ 0.1–13.5 km Höhe), stündlich | API | Rücken- und Seitenwind auf Flughöhe |

Logos/Links der Quellen auf die Folie. Unten: «Keine fertigen Datensätze, Hauptquelle selbst gesammelt.»

### Folie 6 – Datenstruktur
**Beispielzeile vorher (OpenSky, eine Zeile = ein Flugzeug zu einem Zeitpunkt):**

| icao24 | Zeit (UTC) | Breite | Länge | Höhe | Geschw. | Steigrate | Kurs |
|---|---|---|---|---|---|---|---|
| 4b1805 | 12:32 | 47.40 | 8.60 | 2'400 m | 410 km/h | −5 m/s | 140° |

**Nach dem Anreichern:**

| Höhe | Geschw. | Distanz | Zone | Flughafen | Kategorie | Rückenwind |
|---|---|---|---|---|---|---|
| 2'400 m | 410 km/h | 7 km | nah | ZRH | Jet | +14 km/h |

- **Zonen:** nah < 30 km, mittel 30–60 km, fern > 60 km vom nächsten der drei Flughäfen
- **Flugzeugkategorien:** Jet, Turboprop, Kolben, Helikopter, unbekannt/andere (aus ICAO-Typbeschreibung)
- **Rückenwind statt Windstärke:** Gegenwind bremst, Rückenwind schiebt, Seitenwind ändert die Geschwindigkeit über Grund kaum. Entscheidend ist der Wind **in Flugrichtung**, und zwar auf der **Flughöhe** des Flugzeugs.
- **Umfang aus dem Pilot (1.10.2026, ca. 3 h):** 35 Abfragen, 5'664 Rohzeilen → 4'115 bereinigte Beobachtungen, 968 verschiedene Flugzeuge. Hochgerechnet auf 14 Tage: grob mehrere 100'000 Beobachtungen.
- Speicherung: **SQLite** mit mehreren Tabellen (Beobachtungen, Flughäfen, Flugzeugtypen, Wind), Abfragen per SQL aus Python.

### Folie 7 – Datenpipeline
Schema-Grafik (Pfeile von links nach rechts):

**Sammeln** (OpenSky, alle 5 Min., 14 Tage) → **Bereinigen** (am Boden, fehlende/unrealistische Werte, veraltete Meldungen raus) → **Anreichern** (Distanz/Zone, Flugzeugtyp, Wind) → **Speichern** (SQLite, zusätzlich PostgreSQL) → **EDA** → **Modelle A–D** → **Evaluation** (3 Splits) → Zusatz (Statistik-Tests, k-Means, Karte)

Darunter in einer Zeile: «Jeder Join wird dokumentiert: Zeilen vorher/nachher, Trefferquote, nichts geht verloren (Left Join).»
Beispiel aus dem Pilot: Flugzeugtyp-Join trifft 67 % der Beobachtungen; die restlichen bleiben als «unbekannt» drin und werden offen gezeigt.

### Folie 8 – Erste Einblicke (Pilotdaten)
- **1 Grafik:** Streudiagramm Höhe gegen Geschwindigkeit, eingefärbt nach Zone (`outputs/figures/altitude_speed.png` bzw. `LN/altitude_speed.png`, dieselbe Grafik, die Mario überzeugt hat)
- Optional zweite Grafik: Karte mit Flugspuren oder Rückenwind nach Flugrichtung (`tailwind_by_direction.png`)
- Beschriftung gross: **«Pilotdaten vom 1.10.2026, ca. 3 h – keine Resultate»**
- Aussage: Der erwartete Zusammenhang ist sichtbar, die Pipeline funktioniert technisch. Erster Wind-Check: auf 9–11 km Höhe ca. 53 m/s (≈ 190 km/h) Wind, rund ein Viertel der Geschwindigkeit über Grund → Wind ist nicht vernachlässigbar.

### Folie 9 – Methoden
**EDA:** Kennzahlen pro Zone, Flughafen und Kategorie; Streudiagramm Höhe × Geschwindigkeit; Boxplots nach Kategorie und Gegen-/Rückenwind; Vergleich innerhalb gleicher Höhenbänder; Karte.

**Modelle (lineare Regression, schrittweise):**

| Modell | Kennt | Beantwortet |
|---|---|---|
| A | nur Höhe | Wie viel erklärt die Höhe allein? |
| B | + Distanz, Zone, Flughafen, **Höhe × Zone** | Hilft der Ort? Interaktion = Teilfrage 1 |
| C | + Flugzeugkategorie | Hilft der Flugzeugtyp? |
| D | + Rücken- und Seitenwind | Hilft der Wind? |

Begründung: Lineare Regression ist interpretierbar (Koeffizienten = «wie viel km/h pro 1'000 m»). Der Interaktionsterm Höhe × Zone zeigt direkt, ob die Geschwindigkeit nahe dem Flughafen anders mit der Höhe zunimmt.

**Evaluation (R², RMSE, MAE, gegen eine einfache Baseline):**

| Split | Frage | Erwartung |
|---|---|---|
| Zufällig | nur zum Vergleich | zu gut wegen Data Leakage |
| Nach Tag (früh → spät) | Funktioniert das Modell an späteren Tagen? | schlechter, hier sollte der Wind helfen |
| Nach Flugzeug (`icao24` gruppiert) | Funktioniert es bei unbekannten Flugzeugen? | hier sollte der Flugzeugtyp helfen |

**Data Leakage in einem Satz:** Messpunkte desselben Fluges sind fast identisch. Beim zufälligen Split landen Nachbarpunkte in Training und Test, das Modell «kennt» die Antwort schon. Deshalb teilen wir nach Tag bzw. nach Flugzeug.

**Zusatzanalysen:** ANOVA / Kruskal-Wallis (Geschwindigkeit nach Zone bzw. Kategorie, mit p-Wert), k-Means auf Höhe, Geschwindigkeit, Steigrate (Gruppen sollten Flugphasen ergeben: Steigflug, Reiseflug, Anflug), Karte mit Geodaten, PostgreSQL zusätzlich zu SQLite, öffentliches GitHub-Repo.

Tipp: Methoden auf **zwei Folien** aufteilen (9a Modelle, 9b Evaluation + Zusatz), falls zu voll.

### Folie 10 – Erwartete Resultate (Hypothesen)
Jede Hypothese mit der Teilfrage verknüpfen:

| Teilfrage | Hypothese |
|---|---|
| 1 Vergleich | Nahe den Flughäfen steigt die Geschwindigkeit stark mit der Höhe (Anflug/Steigflug, 250-Knoten-Limit). Im Streckenflug ist der Zusammenhang deutlich flacher (Reiseflug). |
| 2 Modell | R² steigt von A nach D. Den grössten Sprung erwarten wir durch den Ort (B), Wind und Kategorie bringen kleinere, aber messbare Verbesserungen. |
| 3 Evaluation | Der zufällige Split überschätzt die Güte. An **neuen Tagen** hilft vor allem der **Wind** (Wetter wechselt), bei **neuen Flugzeugen** vor allem der **Flugzeugtyp**. |

Formulierung immer als «Wir erwarten …», **keine Zahlen als Ergebnis** darstellen.

### Folie 11 – Zeitplan, Risiken & Stand
**Zeitplan (Zeitstrahl-Grafik):**
- 01.10. Pilot erfolgreich (Sammlung + Pipeline getestet)
- ab ca. 13.11. Hauptsammlung 24/7, 14 Tage, auf einem Gerät
- bis ca. 26.11. Sammlung abgeschlossen, Daten einfrieren
- bis 30.11. EDA, Modelle, Evaluation
- Dezember: Interpretation, Folien, Video (15 Min.)
- **10.01.2027 Schlussabgabe** (Video, PDF, ZIP)

**Risiken und Gegenmassnahmen (kurz):**
- Sammelausfall (Schlaf, Internet) → ein festes Gerät 24/7, tägliche Statuskontrolle, Lücken werden dokumentiert, nicht aufgefüllt
- Flugzeugtyp nur zu ca. 67 % bekannt → «unbekannt» als eigene Gruppe behalten, offen zeigen
- Nachbarflughäfen (z. B. Mailand-Malpensa) liegen im Gebiet → als Einschränkung nennen, Sensitivitätscheck
- Wind ist Modellwind (0.5°-Raster, stündlich), keine Messung am Flugzeug

**Repo:** GitHub-URL `github.com/kernwrob/Data-Analytics-Aviation` auf die Folie. KI-Nutzung wird laufend in einem Logbuch dokumentiert.

### Folie 12 (optional) – Fragen / Danke
Kurz, mit Repo-URL und Namen. Nicht nötig, wenn die Zeit knapp ist.

---

## 4. Zeitbudget und Aufteilung (10 Min.)

| Teil | Folien | Zeit | Wer |
|---|---|---|---|
| Einstieg, Hintergrund, Forschungsfrage | 1–4 | ca. 3 Min. | Person 1 |
| Daten, Struktur, Pipeline, Pilot | 5–8 | ca. 3.5 Min. | Person 2 |
| Methoden, erwartete Resultate, Zeitplan | 9–11 | ca. 3.5 Min. | Person 3 |

Übergänge bewusst sprechen («Damit haben wir die Frage, jetzt: woher kommen die Daten?») → zählt für den roten Faden.

---

## 5. Checkliste für die Note 6

**Inhalt**
- [ ] Alle **vollen Namen** auf der Titelfolie
- [ ] Problem motiviert mit Anwendungsbezug (Lärm, Luftraum, auffällige Anflüge), nicht nur «tief = langsam»
- [ ] Forschungsfrage wörtlich auf einer eigenen Folie, 3 Teilfragen
- [ ] Jede Datenquelle mit Namen und Link; Beispielzeile mit Spalten und Einheiten
- [ ] Jede Methode mit **Begründung** («weil …»)
- [ ] Data Leakage und die drei Splits erklärt
- [ ] Hypothesen eindeutig den Teilfragen zugeordnet
- [ ] Pilotgrafiken klar als Pilot beschriftet, keine erfundenen Resultate

**Form (wissenschaftlicher Standard)**
- [ ] Jede Grafik: Titel, Achsen mit Einheiten (m, km/h), Legende, Quelle unten rechts («Quelle: OpenSky Network, eigene Sammlung, 1.10.2026»)
- [ ] Einheitliche Farben: Zone nah/mittel/fern auf allen Folien gleich
- [ ] Max. ca. 5 Stichpunkte pro Folie, keine ganzen Sätze zum Ablesen
- [ ] Foliennummern, einheitliche Schrift, Quellenangaben
- [ ] Englische Fachbegriffe kurz erklären (Ground Speed, Data Leakage, R², RMSE)

**Vortrag**
- [ ] Frei sprechen, Stichworte nur in den Notizen
- [ ] Probe-Durchlauf mit Stoppuhr (Di 17.11. oder Mi 18.11.), Ziel 9:30 Min.
- [ ] PDF bis **Sa 14.11.** auf Moodle

---

## 6. Mögliche Fragen der Dozierenden (vorbereiten)

| Frage | Antwort-Kern |
|---|---|
| Warum ist das mehr als «tief = langsam»? | Wir quantifizieren den Unterschied nah/fern, zerlegen ihn in Ort, Typ und Wind und testen ehrlich auf neue Tage und Flugzeuge. |
| Warum kein zufälliger Train/Test-Split? | Data Leakage: Nachbarpunkte desselben Fluges sind fast identisch, R² wäre künstlich hoch. Wir zeigen den zufälligen Split nur zum Vergleich. |
| Was ist die zweite Datenquelle? | Flugzeugdatenbank (Join auf `icao24`) und Open-Meteo-Wind (Join über Zeit, Ort, Höhe); Flughafenkoordinaten für die Distanz. |
| Wie viele Daten habt ihr? | Pilot: 4'115 Beobachtungen von 968 Flugzeugen in ca. 3 h. Hauptsammlung: 14 Tage, alle 5 Min. |
| Was, wenn der Flugzeugtyp fehlt? | Bleibt als «unbekannt» drin, wird offen ausgewiesen; nicht weglassen, um Metriken zu schönen. |
| Warum Rückenwind statt Windstärke? | Geschwindigkeit über Grund = Fluggeschwindigkeit + Wind in Flugrichtung. Seitenwind spielt kaum eine Rolle. |
| Warum 30 km als «nah»? | Typischer Bereich für Anflug/Abflug unter 10'000 ft; wird vor der Auswertung fixiert und mit 60 km als Grenze zu «fern» ergänzt. |
| Ist «nah» gleich «im Anflug»? | Nein, auch Überflüge liegen nahe. Darum die Höhe im Modell und k-Means für Flugphasen. |

---

## 7. Hinweis zum Arbeiten mit Claude und dem Repo

Nur das Repo durchschauen zu lassen reicht **nicht** zuverlässig, weil:
- `main` noch auf dem Anfangsstand ist; Wind, Modell D, PostgreSQL usw. liegen auf dem Branch `matteo/Data-Analytics-Aviation`,
- die Bewertungskriterien der Konzeptpräsentation nicht vollständig im Repo stehen,
- viele Repo-Dokumente technisch, englisch und teils veraltet sind (z. B. alter Pilot-Stand, offene Entscheide),
- Claude sonst leicht «Resultate» formuliert, die es noch nicht gibt.

**Empfohlener Prompt:**
> «Erstelle mir eine PowerPoint-Konzeptpräsentation (10 Min., ca. 10–11 Folien, Deutsch) genau nach der Struktur in `Konzeptpraesentation_Aufbau.md`. Halte dich an die Bewertungskriterien in Abschnitt 1 und die Checkliste in Abschnitt 5. Erfinde keine Resultate, beschrifte Pilotgrafiken als Pilotdaten. Verwende wenig Text pro Folie und schreibe die ausführlichen Erklärungen in die Sprechernotizen. Grafiken aus `outputs/figures/` (Branch `matteo/Data-Analytics-Aviation`) einbauen.»

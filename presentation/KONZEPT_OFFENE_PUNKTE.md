# Konzeptpräsentation – Änderungen und offene Punkte

**Stand:** 17.11.2026 · **Präsentation:** Di, 15.12.2026, 10 Min., vor Ort in Winterthur
**Datei:** `Konzeptpraesentation_Flugdaten_Schweiz_v2.pptx` (iCloud → ZHAW/HS26:27/Data Analytics/Leistungsnachweise/PP, nicht im Repo)
**Nächster Schritt:** nach Sammelende am **26.11.2026** die Platzhalter in Teil B füllen.

> **Platzhalter finden:** In PowerPoint nach `[DATEN` und `[OFFEN` suchen. Alle Platzhalter sind **pink und fett**, auf den Folien und in den Sprechnotizen.
> **Achtung:** Die Datei in PowerPoint schliessen, bevor Claude sie bearbeitet. Sonst überschreibt das Speichern in PowerPoint die Änderungen (so passiert am 17.11.).

---

## Teil A – Schon erledigt (17.11.2026)

| Folie | Vorher → Nachher | Begründung |
|---|---|---|
| 1 | Datum 19.11.2026 → **15.12.2026** | Termin verschoben |
| 3 (Notiz) | Antwort auf Rückfrage zum 250-kt-Limit ergänzt | Limit hängt von der Luftraumklasse ab, deshalb «meist» |
| 4 (Notiz) | Forschungsfrage nicht mehr wörtlich vorlesen, sondern in einem Satz frei zusammenfassen | Kriterium 7: frei gesprochen |
| 5 (+ Notiz) | Flugzeugdatenbank 520'000 → **617'000 Einträge, Stand 08/2025** | Seit 12.11. gepinnte Version: 616'675 Einträge (`docs/METADATA.md`) |
| 6 | Beispielzeile: Steigrate −5 → **+8 m/s** | Punkt liegt südöstlich von ZRH, Kurs 140° = weg vom Flughafen; Sinken war unplausibel, Steigen passt zu einem Start auf Piste 16 |
| 6 (+ Notiz) | Kategorie «Jet» → **«Kurzstrecke»**, Notiz nennt die 7 Typecode-Kategorien | Seit 12.11. gilt das Typecode-Schema (`data/reference/typecode_category.csv`) |
| 6 | Zonen < 30 / > 60 km → **≤ 30 / ≥ 60 km** | So ist es im Code definiert |
| 6 | Titel des Umfang-Kastens → **«Umfang Hauptsammlung (12.–26.11.2026, 14 Tage)»** | Pilotzahlen sind am 15.12. überholt |
| 7 (+ Notiz) | Typ-Join «67 %» → **«ca. 88 %»** | 67.3 % galt mit der alten Datenbank, neu 88.5 % (`metadata_integration_audit.csv`, Stand 12.11.) |
| 8 | Titel → **«Erster Blick auf die Sammlung»**, Pilot-Text ersetzt | neuer Termin |
| 8 | Wind-Check richtig datiert (**22.10.**) und in **km/h** statt m/s | Die 53 m/s stammen vom 22.10., nicht vom Pilot (`docs/WEATHER.md`) |
| 9 (+ Notiz) | Lineare Regression **mit Knick bei 3'000 m** (250-kt-Grenze), **Flugphase aus der Steigrate** als Kontrollvariable | Die Kurve flacht oben ab, eine Gerade wäre falsch spezifiziert (Kriterium 5). **Gruppe muss das bestätigen.** |
| 10 (+ Notiz) | **Chi²-Test (Kategorie × Zone)** ergänzt | Zusatzpunkt 4 doppelt abgesichert |
| 10 | Fliesstext «Zusätzlich: …» → Überschrift **«Zusätzlich geplant»** und **5 graue Kacheln** (Statistik, k-Means, Karte, PostgreSQL, GitHub) im Stil der Modell-Bausteine auf Folie 9 | Passt besser ins Design und ist schneller erfassbar (Kriterium 8) |
| 11 | Hypothese 1 prüfbar: **«Messbar: Interaktion Höhe × Zone, p < 0.05»**; Hypothese 2: **«R² im Tag-Split»** | Kriterium 6: Erwartung an die Forschungsfrage gekoppelt |
| 11 (Notiz) | «Zahlen erst nach der Hauptsammlung» → «Sammlung abgeschlossen, Auswertung prüft die Hypothesen» | neuer Termin |
| 12 | Zeitstrahl: **12.11.** Start (statt «ab ca. 13.11.»), **26.11.** abgeschlossen und **gelb als erledigt** markiert, Dezember «Interpretation, Video» | falsches Startdatum, Stand am 15.12. |
| 12 (+ Notiz) | Risiko «Flugzeugtyp nur zu ca. 67 % bekannt» → **«ca. 12 % unbekannt»**; Notiz in der Vergangenheit («lief vom 12. bis 26.11.») | siehe Folie 7, neuer Termin |

---

## Teil B – Platzhalter nach Sammelende (ab 26.11.2026)

**Voraussetzungen**
- [ ] Rohdaten vom Sammler auf den Analyse-Mac spiegeln (rsync gemäss `docs/COLLECTION.md`)
- [ ] `src/prepare.py` laufen lassen (SQLite und Audits neu)
- [ ] Wind für alle Sammeltage holen: `python src/weather.py fetch --start 2026-11-12 --end 2026-11-26`
- [ ] Notebook 01 auf allen 14 Tagen ausführen
- [ ] Zahlen und Grafiken: `python src/presentation_figures.py` → `outputs/tables/presentation_numbers.csv` und `outputs/figures/presentation/`

| # | Folie | Platzhalter | Was eintragen / tun | Quelle |
|---|---|---|---|---|
| B1 | 1 | `[DATEN: Karte aus Hauptsammlung neu …]` | Titelkarte aus den 14 Tagen neu erzeugen (1'500 zufällige Beobachtungen, finaler Ausschnitt). Bildunterschrift: «Hauptsammlung 12.–26.11.2026: 1'500 zufällig gezogene Beobachtungen, …». Marker löschen | Notebook 01 |
| B2 | 6 | `[DATEN: n]` ×4 im Umfang-Kasten | Abfragen, Rohzeilen, bereinigte Beobachtungen, Flugzeuge. Danach die Textfarbe wieder normal setzen | `data/raw/manifest.jsonl`, `data/processed/integration_audit.csv` bzw. `src/pilot_report.py` |
| B3 | 6 (Notiz) | `[DATEN: n]` ×3 | gleiche Zahlen wie B2 | wie B2 |
| B4 | 7 | `[DATEN: Wert aus 14 Tagen]` | Trefferquote des Typ-Joins (jetzt «ca. 88 %») | `data/processed/metadata_integration_audit.csv` → `observation_match_fraction` |
| B5 | 7 (Notiz) | `[DATEN: 88]` | wie B4 | wie B4 |
| B6 | 8 | **Grafik** + `[DATEN: Grafik neu …]` | Scatterplot aus 14 Tagen: y-Achse «Geschwindigkeit über Grund (km/h)», x-Achse «Flughöhe (m)», Legende «Zone: nah / mittel / fern» (orange / grün / blau wie Folie 6), deckende, grössere Legendenpunkte | Notebook 01 |
| B7 | 8 | `[DATEN: n]` in der Bildunterschrift | Grösse der Stichprobe in der Grafik | Notebook 01 |
| B8 | 8 | `[DATEN: n] Beobachtungen …, [DATEN: x] Lücken` | Anzahl Beobachtungen und dokumentierte Lücken. Danach Textfarbe normal | wie B2, `docs/COLLECTION_LOG.md` |
| B9 | 8 | `[DATEN: Median 14 Tage]` | Wind-Median auf 9–11 km aus allen Tagen (ersetzt den Check vom 22.10.); Anteil an der Geschwindigkeit über Grund prüfen | View `observations_with_wind` |
| B10 | 8 (Notiz) | `[DATEN: x]` | Lücken, wie B8 | wie B8 |
| B11 | 12 | `[DATEN: Stand?]` beim 30.11. | erledigt → Kreis und Datum gelb wie die anderen Meilensteine; sonst den Stand angeben | Stand Notebooks 01–03 |
| B12 | 12 | `[DATEN: Ergebnis x Lücken, y h]` | Ergebnis beim Risiko «Sammelausfall» | `docs/COLLECTION_LOG.md` |
| B13 | 12 | `[DATEN]` bei «ca. 12 % unbekannt» | Anteil «Unbekannt» aus 14 Tagen | `data/processed/category_audit.csv` |
| B14 | 12 | `[OFFEN: Puffer umgesetzt?]` (Folie + Notiz) | Ist der Puffer um Nachbarflughäfen (LIMC, LIME, EDNY, LSZB, LSZA, LSGS, LFLB, LFLP) umgesetzt, Text auf «Puffer um n Flughäfen ausgeschlossen, Sensitivitätscheck» ändern | Roadmap H4 / CC-10 |
| B15 | 12 (Notiz) | `[DATEN: Stand EDA, Modelle, Evaluation]`, `[DATEN: 88]`, `[DATEN: x Lücken, total y Stunden]` | Stand, Trefferquote (wie B4), Lücken (wie B12) | wie oben |

**Am Schluss:** In PowerPoint nach `[DATEN` und `[OFFEN` suchen, es darf nichts mehr gefunden werden. Danach als PDF exportieren.

---

## Teil C – Entscheide der Gruppe (unabhängig von den Daten)

- [ ] **Wer präsentiert welchen Teil?** Folie 2: «[ERGÄNZEN: Person 1/2/3]» und in allen Sprechnotizen «[Person 1/2/3, ca. … Sekunden]» bzw. «zeigt [Person 2]», «erklärt jetzt [Person 3]» durch Namen ersetzen
- [ ] **Name auf Folie 1:** Schreibweise «Hou Yün Chiu» mit Kevin klären; Folie und Vorstellung («Wir sind Kevin, …») sollen zueinander passen
- [ ] **Gruppennummer 36** mit der Anmeldung auf Moodle abgleichen
- [ ] **Methode Folie 9 bestätigen:** Knick bei 3'000 m und Flugphase aus der Steigrate (sonst Spline/Polynom)
- [ ] **Moodle:** Gilt die PDF-Frist (ursprünglich 14.11.) auch verschoben? Finale Version als PDF hochladen
- [ ] **Fragen an Mario nach der Präsentation:** Zählt PostgreSQL zusätzlich zu SQLite für den Zusatzpunkt? Reichen die Typecode-Kategorien? Antwort in `docs/DECISIONS.md` eintragen
- [ ] **Proben:** Notizen auf Stichworte kürzen, jede Person probt ihren Teil mit Stoppuhr (Ziel unter 10 Min., Notizen ergeben heute ca. 9:20)

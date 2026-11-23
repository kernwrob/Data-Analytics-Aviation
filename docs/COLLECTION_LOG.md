# Collection Log – Hauptsammlung OpenSky

Protokoll der Kontrollen am Sammel-Mac (altes MacBook, Benutzer «Sammler»). Dient als Nachweis «Collection gaps explained» (Pflicht 1) und als Quelle für die Präsentations-Platzhalter B8 und B12 (`presentation/KONZEPT_OFFENE_PUNKTE.md`).

**Sammlung:** Start 2026-11-12 18:30 UTC (19:30 CH), Ende 2026-11-26 18:30 UTC, Intervall 300 s, 14 Tage, `launchd`-Job `ch.zhaw.aircraftproject.maincollection`, Abfrage anonym.

**Prüfbefehl:** per `ssh sammler@192.168.0.59` aus der Ferne: `scripts/collection_mac.sh status`, die letzten Manifest-Einträge, die Anzahl erfolgreicher Snapshots und Fehler sowie `uptime`, `df -h ~` und `pmset -g log` (Sleep/Wake).

Zeiten der Prüfung in Schweizer Zeit; Manifest-Zeiten sind UTC.

| Prüfung (CH) | Geprüft von | Status | Letzter Snapshot (UTC) | Snapshots ok | Erwartet | Fehler | Lücken (mit Grund) | Uptime | Freier Speicher | Bemerkungen |
|---|---|---|---|---|---|---|---|---|---|---|
| 2026-11-18 00:44 | Matteo | ENABLED | 2026-11-17 23:40, success | 1'504 | ca. 1'503 | 0 | keine | 6 Tage (kein Neustart seit Start) | 89 GiB | Kein Sleep/Wake seit Start (nur Display-Assertion 17.11.). OpenSky-Credits 116 um 23:40 UTC, reicht bei 288 Abfragen/Tag. 8–13 Flugzeuge pro Snapshot in der Nacht, plausibel. |
| 2026-11-23 22:02 | Matteo | ENABLED | 2026-11-23 21:00, success (Status 200) | 3'062 | 3'198 | 0 | 136 Snapshots fehlen (95.7 %), alle am 23.11. (CH): 08:55–18:51 nur vereinzelte Snapshots (ca. alle 2 h), 19:50–21:51 keine (23 Slots). Grund: Stromunterbruch im Haus (Sicherung aus), Mac lief auf Akku; `pmset -c sleep 0` galt nur am Netz, auf Akku schlief der Mac und wachte nur zur Wartung kurz auf | nicht geprüft | nicht geprüft | Keine Fehler im Manifest, Lücken also kein Netzwerkproblem. 21:55 CH als `deferred` (sampling_interval) übersprungen, weil der nachgeholte Snapshot um 21:51 lief; ab 22:00 CH wieder im 5-Minuten-Takt. Massnahme: `sudo pmset -b sleep 0` gesetzt (kein Schlaf auch auf Akku). Ausgleich nach dem 26.11. offen (ca. 11–12 h). |

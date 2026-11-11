# Sammel-MacBook einrichten – Schritt für Schritt

Gerät: MacBook Pro 13″ Retina (A1502, 2013–2015), i5, 8 GB RAM. Frisch zurückgesetzt.

Ziel: Das MacBook sammelt 14 Tage lang alle 5 Minuten einen OpenSky-Snapshot. Es muss dafür **am Strom, wach, online und eingeloggt** sein. Ein gesperrter Bildschirm ist in Ordnung.

Dauer: ca. 30–45 Minuten (das meiste ist Warten auf Downloads).

---

## Schritt 1 – Grundeinrichtung abschliessen

Der Einrichtungs-Assistent läuft nach der Neuinstallation von selbst.

1. Sprache, Land, **WLAN** (Heimnetz, «automatisch verbinden»).
2. Bei **Apple-ID**: **«Später einrichten»** / überspringen. Du brauchst keine.
3. **Benutzer anlegen**: Name z. B. `Sammler`, ein einfaches Passwort, das du dir merkst. Dieser Benutzer ist automatisch Administrator.
4. **FileVault**: falls angeboten, **ausschalten**. Nur dann funktioniert die automatische Anmeldung nach einem Neustart.

## Schritt 2 – GitHub-Token erstellen (auf deinem normalen Mac oder im Browser)

Das Repo ist privat, deshalb braucht das MacBook einen Token statt eines Passworts.

1. github.com → Profilbild → **Settings** → **Developer settings** → **Personal access tokens** → **Fine-grained tokens** → *Generate new token*.
2. Name: `Sammel-Mac`, Ablauf: **90 Tage**.
3. *Resource owner*: `kernwrob`, *Repository access*: nur `Data-Analytics-Aviation`.
   Falls `kernwrob` nicht wählbar ist: einen **Classic token** mit Häkchen bei `repo` erstellen.
4. Rechte: **Contents: Read-only** genügt. Das MacBook muss nur herunterladen.
5. Token kopieren und auf das MacBook bringen (AirDrop oder Notiz). Er wird nur einmal angezeigt.

## Schritt 3 – Python 3.13 installieren

1. Auf dem MacBook https://www.python.org/downloads/macos/ öffnen.
2. Neueste **Python 3.13.x** → *macOS 64-bit universal2 installer* herunterladen und installieren.
3. Am Schluss im Finder-Fenster **«Install Certificates.command»** doppelklicken.

## Schritt 4 – Setup-Skript ausführen

1. Die Datei `scripts/setup_sammler_mac.sh` aus dem Repo aufs MacBook kopieren (USB-Stick, AirDrop oder auf GitHub «Download raw file»), z. B. auf den Schreibtisch.
2. **Terminal** öffnen (Programme → Dienstprogramme) und eingeben:

   ```bash
   bash ~/Desktop/setup_sammler_mac.sh
   ```

3. Was passiert:
   - Fehlt Git, erscheint ein Fenster «Command Line Tools installieren». **Installieren**, warten, Skript **danach nochmals starten**.
   - Beim Klonen fragt Git nach **Username** (dein GitHub-Name) und **Password** → hier den **Token aus Schritt 2** einfügen. Beim Einfügen siehst du nichts, das ist normal.
   - Es folgen ein Testabruf bei OpenSky und der Download der Flughafen-Datei.
   - Zum Schluss fragt das Skript nach den Energie-Einstellungen → mit `j` bestätigen, Benutzer-Passwort eingeben.
4. Am Ende steht **«Fertig ✔»**. Bei einem roten ✘ steht dort, was zu tun ist. Danach Skript einfach nochmals starten.

## Schritt 5 – Systemeinstellungen kontrollieren

| Einstellung | Wo | Wert |
|---|---|---|
| Kein Ruhezustand am Netzteil | Batterie / Energie sparen → Optionen | «Ruhezustand verhindern, wenn Bildschirm aus»: **an** (setzt das Skript) |
| Neustart nach Stromausfall | Energie sparen | **an** (setzt das Skript) |
| Automatische Anmeldung | Benutzer & Gruppen → «Automatisch anmelden als» | **Sammler**. Nur möglich bei FileVault aus. |
| Automatische Updates | Softwareupdate → Automatische Updates | für die 14 Tage **aus**, sonst nächtlicher Neustart |
| WLAN | Netzwerk | Heimnetz, «automatisch verbinden» an. LAN-Kabel ist noch besser. |
| Optional: Fernzugriff | Allgemein → Teilen → **Bildschirmfreigabe** an | So prüfst du den Status von deinem Mac aus |

Warum automatische Anmeldung wichtig ist: Der Sammler läuft nur, solange der Benutzer eingeloggt ist. Nach einem Stromausfall startet das MacBook so von selbst neu und sammelt weiter.

## Schritt 6 – Sammlung starten (erst wenn die Gruppe den Zeitpunkt abgemacht hat)

```bash
cd ~/Developer/Data-Analytics-Aviation
scripts/collection_mac.sh start --start-at 2026-11-12T09:00:00+01:00 --days 14
```

- Datum und Zeit anpassen, `+01:00` bleibt (Winterzeit Schweiz). Die Startzeit muss **in der Zukunft** liegen.
- **Ca. 15 Minuten nach der Startzeit** prüfen:

  ```bash
  scripts/collection_mac.sh status
  ```

  Unter «Last manifest entry» sollte `snapshot  success` mit aktueller Uhrzeit (UTC, 1 h früher als in der Schweiz) stehen.

Danach MacBook aufgeklappt und am Strom stehen lassen. Bildschirm sperren geht mit Ctrl + Cmd + Q.

## Schritt 7 – Während der 14 Tage

- **Einmal am Tag** `scripts/collection_mac.sh status`. Die letzte Zeile sollte höchstens 5–10 Minuten alt sein und `success` zeigen.
- **Nicht** `setup_sammler_mac.sh` oder `collect.py snapshot` von Hand laufen lassen, solange gesammelt wird.
- **Nie** gleichzeitig auf einem anderen Computer sammeln.
- Zuklappen, abmelden oder ausschalten = fehlende Daten. Bei Bedarf vorher `pause`, danach `resume`.
- Bei Problemen (mehrere `failure` hintereinander): letzte Zeilen aus `data/raw/manifest.jsonl` und `data/raw/logs/collector_mac.log` an Claude schicken.

## Schritt 8 – Nach den 14 Tagen

Die Sammlung hört von selbst auf. Danach erstellst du den Daten-Export für die Gruppe (dafür braucht es die volle Python-Umgebung, das machen wir zusammen). Den GitHub-Token danach auf GitHub löschen.

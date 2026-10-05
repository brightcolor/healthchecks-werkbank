# healthchecks-werkbank: Entwurf

Stand 05.10.2026. Mathias hat den Entwurf in vier Abschnitten im Chat freigegeben; dieses Dokument fasst ihn zusammen.

## 1. Ziel

hc.bcsrv.de, das selbst betriebene Healthchecks auf docker-a1, bekommt die Werkbank-Ausprägung von bright color: Onyx-Leiste links, Papiergrund, gelbe Hauptknöpfe, hell und dunkel. Eine eigene Fassung des Images folgt jeder neuen Healthchecks-Version selbstständig. Die CI baut und prüft sie, docker-a1 übernimmt sie mit Sicherung und Rückweg. Ist eine Prüfung rot, läuft die bisherige Fassung weiter, und Mathias bekommt eine Meldung.

**Erfolgskriterien**

- hc.bcsrv.de zeigt die Werkbank hell und dunkel, mit Leiste links, auf Rechner und Handy. Jede Seite von Healthchecks bleibt bedienbar.
- Erscheint eine neue Healthchecks-Version, baut, prüft und veröffentlicht die CI das Image selbstständig. docker-a1 übernimmt es beim nächsten Timerlauf nach einer Sicherung der Datenbank.
- Eine rote Prüfung erzeugt ein Issue samt Mail. docker-a1 behält die laufende Fassung.
- Scheitert ein Update auf dem Server, nimmt das Skript es selbst zurück und meldet es über Healthchecks.

## 2. Entscheidungen

| Frage | Entscheidung |
|---|---|
| Navigation | Onyx-Leiste links mit Akkordeon, Werkbank-Rahmen wie im ISPConfig-Theme |
| Weg | Aufsatz-Repo: eigenes Image auf Basis des offiziellen; der Code von Healthchecks bleibt unverändert |
| Automatik | bei Grün bauen, prüfen und ausliefern; bei Rot Stopp mit Meldung, Anpassung in einer Sitzung |
| Sichtbarkeit | öffentliches Repo `brightcolor/healthchecks-werkbank`, Image `ghcr.io/brightcolor/healthchecks-werkbank` |
| Auslieferung | docker-a1 holt neue Images selbst über einen Timer; GitHub hat keinen Zugang zum Server |
| Texte | Die Oberfläche bleibt englisch wie Healthchecks. Leiste, Kopfzeile, Meldungen und Vorlesetexte des Themes nutzen dieselbe Sprache und dieselben Begriffe. Der Gruß „Moin.“ auf der Anmeldeseite bleibt. Skripte auf dem Server melden auf Deutsch. |
| Lizenz | BSD 2-Clause wie die übrigen Theme-Repos von bright color. Die Lizenz von Healthchecks (BSD 3-Clause) liegt als `UPSTREAM-LICENCE` bei, die Schriften mit ihrer OFL. Die Logos sind Marken von bright color und von der Repo-Lizenz ausgenommen. |

## 3. Ausgangslage

- docker-a1 (aarch64, Ubuntu 24.04): `/opt/healthchecks/compose.yaml`, Image `healthchecks/healthchecks:latest` in Version v4.3, SQLite im Volume `data`, veröffentlicht über Traefik am Netz `root_netbird` (Dienstport 8000).
- Healthchecks v4.4 liegt seit 31.08.2026 auf Docker Hub, gebaut für amd64, arm und arm64. GitHub-Releases und Docker-Hub-Tags heißen gleich, etwa `v4.4`.
- `templates/base.html` ist in v4.3 und v4.4 gleich. Alle Stylesheets stehen in einem `{% compress css %}`-Block. Das offizielle Image bündelt beim Bau (`COMPRESS_OFFLINE = True`; `collectstatic` und `compress` mit `DEBUG=False SECRET_KEY=build-key`) und liefert über WhiteNoise aus `static-collected` aus. Ein zusätzliches Stylesheet braucht deshalb einen eigenen Bau.
- Die Farben laufen über 78 CSS-Variablen in `static/css/variables.css`, je einmal hell auf `:root` und dunkel auf `body.dark`.
- Den Modus setzt Healthchecks serverseitig nach der Profileinstellung `theme`: leer (hell), `dark` oder `system`. Gespeichert wird per POST auf `/accounts/profile/appearance/` (URL-Name `hc-appearance`) mit dem Feld `theme`. Besuchern ohne Anmeldung zeigt Healthchecks die helle Fassung.
- Die Projektliste liefert `/projects/menu/` als HTML-Bruchstück, je Projekt mit Link und Gesamtzustand (`ic-up`, `ic-grace`, `ic-down`).
- Die Container-Prüfung des Images ist `./fetchstatus.py`; die Statusadresse lautet `/api/v3/status/`.
- Vorbilder im Bestand: `postal-arm64` (CI folgt fremden Versionen, prüft ghcr.io, baut nativ auf ARM), `dmarc-analyzer` (Image nach ghcr.io), `mailwizz-werkbank` und `postal-brightcolor` (Werkbank für Fremdsoftware), `ispconfig-brightcolor` (Leiste).

## 4. Repo und Bau

```
Dockerfile                  FROM healthchecks/healthchecks:${HC_VERSION}
VERSION                     Fassung des Themes, beginnend mit 1.0.0
werkbank/einbau.py          setzt die Zeilen in base.html und die Fassung in leiste.html
werkbank/static/bc/         werkbank.css, Schriften, Logos, leiste.js
werkbank/templates/bc/      leiste.html (Leiste, Kopfzeile, Markenfläche der Anmeldung)
deploy/                     hc-werkbank-update, systemd-Dienst und -Timer, logrotate, Beispiel der Einstellungsdatei
tests/                      Musterdaten, Browserprüfung, Kontrast, Variablen, Update-Probe
.github/workflows/build.yml
LICENSE, UPSTREAM-LICENCE, README.md, CHANGELOG.md
```

**Bau**

1. Das Dockerfile kopiert `werkbank/static/bc/` nach `/opt/healthchecks/static/bc/` und `werkbank/templates/bc/` nach `/opt/healthchecks/templates/bc/`.
2. `einbau.py` setzt in `templates/base.html` zwei Zeilen:
   - vor `</head>` den Link auf `{% static 'bc/werkbank.css' %}`, damit das Stylesheet hinter dem gebündelten CSS lädt,
   - vor `<nav class="navbar navbar-default">` die Zeile `{% include "bc/leiste.html" %}`.

   Jeder Anker muss genau einmal vorkommen. Fehlt einer oder steht er mehrfach da, bricht der Bau ab, und die Meldung nennt Anker, Datei und gefundene Anzahl. Außerdem schreibt `einbau.py` die Fassung aus `VERSION` in `leiste.html`.
3. Danach laufen `collectstatic` und `compress` wie im offiziellen Dockerfile.

**Tags**

- `<Healthchecks-Version>-wb<Theme-Fassung>`, etwa `4.4-wb1.0.0`. Dieser Tag bleibt unverändert und trägt den Rückweg.
- Dazu die beweglichen Tags `4.4` und `latest`.
- Eine Theme-Änderung ohne neue Healthchecks-Version erhöht die Fassung in `VERSION`.
- Labels: `org.opencontainers.image.version` mit dem vollen Tag, `org.opencontainers.image.source`, `org.opencontainers.image.base.name` (etwa `docker.io/healthchecks/healthchecks:v4.4`), `org.opencontainers.image.licenses`.

**Plattformen:** linux/arm64 für docker-a1 und linux/amd64 für die Prüfungen, jeweils nativ auf einem eigenen Runner.

**Einstellungen**

- Name und Logo von Healthchecks kommen über `SITE_NAME` und `SITE_LOGO_URL` aus dessen `.env`. Der Bereichsname in der Leiste ist `SITE_NAME`.
- Adressen, die `leiste.js` braucht (Projektliste, Darstellung, Projektübersicht), setzt `leiste.html` über `{% url %}` in `data-`-Attribute. Das Skript selbst enthält keine Pfade.
- Die CI-Werte stehen gesammelt im `env`-Block von `build.yml`: Upstream-Repo, Basis-Image, Ziel-Image. Der Zeitplan steht im `schedule` desselben Workflows.
- Die Werte für das Update auf docker-a1 stehen in `/etc/hc-werkbank.conf` (Abschnitt 7).

**README** beschreibt Bau, Tags, Auslieferung, Rückweg und die Ersteinrichtung einer frischen Instanz: Das erste Admin-Konto legt der Betreiber mit `docker compose exec healthchecks ./manage.py createsuperuser` an, so wie es Healthchecks vorsieht.

## 5. Theme und Leiste

### Leiste

Onyx, 256 px breit, fest links, scrollt in sich, in beiden Modi gleich. Healthchecks rendert sie aus `bc/leiste.html` mit den Werten, die `base.html` ohnehin kennt (`project`, `page`, `check`, `request.user`, `site_name`).

- Oben das helle Logo ohne Claim (`bc-logo-light-noclaim`, 170 px breit) als Link zur Projektübersicht, darunter `SITE_NAME` in kleinen Versalien.
- Je Projekt ein Modul im Akkordeon: Zustandssymbol in der Hausampel, Name, Winkel.
- Das aktuelle Projekt ist offen: gelbe Kante 4 px, gelbes Symbol, darunter Checks, Integrations, Badges und Settings. Der aktuelle Eintrag trägt den Cyan-Punkt und `aria-current="page"`. Integrations zeigt den Hinweis von Healthchecks bei gestörten Kanälen.
- Ein Modul ist offen, ein Klick auf das offene klappt es zu, `aria-expanded` folgt. Das Untermenü steht im DOM direkt hinter seinem Modul.
- Unter den Projekten: New Project, Docs, Account Settings, für Superuser Site Administration. New Project öffnet den Dialog von Healthchecks; auf Seiten ohne diesen Dialog führt der Eintrag zur Projektübersicht.
- Fußzeile für Superuser: Version von Healthchecks (`{% site_version %}`) und Fassung des Themes.
- `leiste.js` holt die Projektliste von `/projects/menu/` und baut daraus die Module. Die Adressen der Unterpunkte entstehen aus den Adressen des aktuellen Projekts mit dem Code des jeweiligen Projekts.
- Ohne JavaScript zeigt die Leiste das aktuelle Projekt. Scheitert der Abruf der Projektliste, bleibt das aktuelle Projekt stehen, und ein Hinweis in der Leiste sagt, dass die übrigen Projekte gerade fehlen und ein Neuladen der Seite hilft.
- Ohne Anmeldung zeigt die Leiste Logo, Docs und Log In.
- Die Navigation von Healthchecks bleibt im Markup und ist ausgeblendet. Ihre Skripte, etwa das Projektmenü und der Dialog für neue Projekte, laufen weiter.

### Kopfzeile

60 px hoch, klebt oben, weiß, im dunklen Modus in der Kartenfläche.

- Menüknopf unter 900 px.
- Brotkrumen „Projekt › Seite“, auf Check-Details und Log „Projekt › Checks › Name des Checks“.
- Umschalter Hell/Dunkel: schickt `theme=dark` oder `theme=` samt CSRF-Token per POST an die Darstellungs-Seite und setzt `body.dark` sofort. Scheitert das Speichern, springt der Modus zurück, und eine Meldung unter der Kopfzeile nennt Ursache und nächsten Schritt, etwa: „Your appearance setting wasn't saved because Healthchecks didn't respond. Reload the page and try again.“ Steht die Einstellung auf „System“, wechselt der Umschalter vom gerade angezeigten Modus in den anderen und speichert diesen fest. „System“ bleibt im Profil wählbar.
- Avatar (Onyx-Kreis mit gelbem Anfangsbuchstaben der E-Mail) und „Log Out“ als Textlink, der das Abmeldeformular von Healthchecks abschickt.
- Ohne Anmeldung trägt die Kopfzeile den Menüknopf für schmale Bildschirme; die Anmeldeseite hat keine Kopfzeile.

### Farben und Bausteine

`werkbank.css` lädt zuletzt und besteht aus drei Teilen:

1. Schriften (Anton, Atkinson Hyperlegible, IBM Plex Mono aus `bc-fonts.css`) und Tokens (`bc-tokens.css`) der Hausschrift,
2. den 78 Variablen von Healthchecks, hell auf `:root` und dunkel auf `body.dark`, jeweils auf Werkbank-Tokens gesetzt,
3. der Stilschicht: Leiste, Kopfzeile, Karten, Knöpfe, Felder, Tabellen, Zustände, Anmeldeseite, schmale Bildschirme.

- Papiergrund, weiße Karten mit 12 px Rundung, 1 px Linie und leisem Schatten. Felder und Knöpfe mit 8 px Rundung und 38 px Höhe.
- Hauptknopf (`btn-primary`) Gelb mit Tinte-Schrift, Löschen (`btn-danger`) Pink mit weißer Schrift, die übrigen Knöpfe mit Umriss.
- Anton in Versalien für Seiten- und Kartentitel, Text in Atkinson Hyperlegible, Cron-Ausdrücke, Ping-Adressen und Code in IBM Plex Mono.
- Textlinks hell `#b3146a`, dunkel Cyan. Fokus hell `#0a86ad`, dunkel Cyan.
- Vierfarbband 4 px fest am oberen Rand.
- Zustände in der Hausampel: up Limette, grace Gelb, down Pink, started Cyan, paused und new leise. Die Symbole behalten ihre Form, der Zustand bleibt so auch ohne Farbe erkennbar.

### Schmale Bildschirme

- Unter 900 px fährt die Leiste aus dem Bild. Der Menüknopf holt sie herein, der Fokus wandert hinein, und ein Schleier legt sich über den Inhalt. Escape oder ein Fingertipp auf den Schleier schließen sie und geben den Fokus an den Menüknopf zurück. Eingeklappt ist sie `visibility: hidden` und damit aus der Tab-Reihenfolge.
- Unter 640 px sind Listen zweizeilig: oben fett der Titel, darunter leise die übrigen Angaben, getrennt mit „ · “. Die Umstellung geschieht allein über CSS auf dem Markup von Healthchecks.
  - Checks: Titel ist der Name, darunter letzter Ping · Zeitplan · Tags.
  - Integrations: Titel ist der Name der Integration, darunter ihre übrigen Spalten.
  - Ping-Log: Titel ist das Ereignis mit Zeitpunkt, darunter die übrigen Spalten.

### Anmeldeseite

Auf der Anmeldeseite (`page == "login"`) gibt `leiste.html` die Markenfläche aus: Onyx mit Logo, „Moin.“ in Anton und `SITE_NAME`. Die Stilschicht stellt sie links neben die Anmeldekarte von Healthchecks; schmal stapeln sich beide. Das Logo hat einen Alternativtext, der Gruß ist für Vorleseprogramme ausgeblendet.

### Barrierefreiheit

- Sprunglink „Skip to content“ als erstes fokussierbares Element.
- Kontrast: Schrift ab 4,8:1, Bedienelemente und Fokusringe ab 3:1, in beiden Modi.
- Bei `prefers-reduced-motion` fährt die Leiste ohne Bewegung ein und aus.

## 6. Ablauf in der CI

Ein Workflow `build.yml` auf den Runnern von GitHub (`ubuntu-latest` für amd64, `ubuntu-24.04-arm` für arm64).

**Auslöser**

- Zeitplan viermal täglich, versetzt zur vollen Stunde.
- Push auf `main`.
- Pull Requests: bauen und prüfen, ohne Veröffentlichung.
- Handstart mit den Eingaben `hc_version` (leer: neuestes Release) und `force` (neu bauen, auch wenn der Tag existiert).

**1 · Entscheiden**

- Version: neuestes Release von `healthchecks/healthchecks` (Tag `v4.4` ergibt Version `4.4`), beim Handstart die Eingabe.
- Fehlt `healthchecks/healthchecks:v4.4` noch auf Docker Hub, endet der Lauf grün mit einem Hinweis in der Zusammenfassung.
- Ziel-Tag `4.4-wb<VERSION>`. Liegt er schon in ghcr.io, endet ein Lauf aus dem Zeitplan grün. Ein Push auf `main` baut und prüft dann wie ein Pull Request und veröffentlicht nichts; eine Theme-Änderung geht mit erhöhter Fassung in `VERSION` heraus. `force` baut, prüft und veröffentlicht den Tag neu.

**2 · Bauen**

- Je Plattform ein Job mit `docker buildx`. Das Ergebnis geht per Digest ohne Tag nach ghcr.io.
- Pull Requests bauen amd64 und laden das Image lokal.

**3 · Prüfen**

arm64: Der Container startet, wird gesund, und die Anmeldeseite lädt `werkbank.css`.

amd64 vollständig:

- **Variablen:** Die Namen in `variables.css` des Basis-Images werden mit den Namen in `werkbank.css` verglichen, getrennt nach hell und dunkel. Eine neue Variable macht den Lauf rot und wird genannt. Eine entfallene Variable steht als Hinweis in der Zusammenfassung.
- **Musterdaten** über `manage.py shell`: Superuser mit zufälligem Passwort aus dem Lauf, zwei Projekte, Checks in jedem Zustand (up, grace, down, started, paused, new), Integrationen, Pings.
- **Browser** mit Playwright (Chromium), Anmeldung über das Formular von Healthchecks. Seiten: Anmeldung, Projektübersicht, Checks, Check-Details, Log, Integrations, Badges, Projekt-Settings, Account Settings, Appearance, Docs. Jede Seite hell und dunkel, Seiten ohne Anmeldung hell. Je Seite: Antwort 200, Leiste vorhanden, `werkbank.css` geladen, Konsole ohne Fehler.
- **Kontrast** über jede sichtbare Schrift mit `check-contrast.js` aus der Hausschrift.
- **Breiten** 320, 390, 768, 1024, 1280 und 1440 ohne Querscrollen; bei 390 ist die Check-Liste zweizeilig.
- **Bedienung der Leiste:** Akkordeon, Escape, Fokusführung, Umschalter Hell/Dunkel samt Fehlerfall (scheitert der POST, springt der Modus zurück, und die Meldung erscheint).
- **Update-Probe:** `hc-werkbank-update` läuft gegen einen Compose-Aufbau im Runner. Mit dem neuen Image erwartet die Probe den Wechsel und eine geprüfte Sicherung. Mit einem absichtlich kaputten Image erwartet sie den Rückweg: alte Fassung läuft, Datenbank wie vorher. Ein weiterer Lauf nutzt Einstellungen abseits der Vorgaben.
- **Quelltext:** `shellcheck` für die Skripte, `bc_check.py lint --variant workbench` für das Stylesheet.
- Die Bilder aller Seiten hängen am Lauf.

`check-contrast.js` und `bc_check.py` liegen als Kopie aus der Hausschrift in `tests/`, mit Quellvermerk. Ändert sich die Hausschrift, werden die Kopien nachgezogen.

**4 · Veröffentlichen**

Nur bei Grün und außerhalb von Pull Requests: `docker buildx imagetools create` setzt aus beiden Digests die Tags `4.4-wb1.0.0`, `4.4` und `latest`.

**Bei Rot**

- Es wird nichts veröffentlicht.
- Ein Schritt legt ein Issue mit dem Label `theme-rot` an oder ergänzt das offene: Version, gescheiterte Prüfung, Auszug aus dem Log, Link zum Lauf. GitHub schickt dazu die Mail.
- Die Anpassung geschieht in einer Sitzung. Ein Push auf `main` startet den nächsten Lauf.
- Ist ein späterer Lauf für dieselbe Version grün, schließt die CI das Issue mit einem Verweis auf diesen Lauf.

## 7. Auslieferung auf docker-a1

### Skript `hc-werkbank-update`

`/usr/local/sbin/hc-werkbank-update` ist ein Bash-Skript (`set -euo pipefail`). Der systemd-Dienst `hc-werkbank-update.service` startet es über `hc-run hc-werkbank-update -- /usr/local/sbin/hc-werkbank-update`, der Timer `hc-werkbank-update.timer` stündlich zur Minute 37 (`OnCalendar=*-*-* *:37:00`). Den Takt ändert ein Drop-in (`systemctl edit hc-werkbank-update.timer`).

Ablauf eines Laufs:

1. Sperre per `flock`, damit immer nur ein Lauf arbeitet.
2. `docker pull <IMAGE>:<TRACK_TAG>`, Fassung aus dem Label `org.opencontainers.image.version`. Steht dieselbe Fassung schon in `<TAG_VARIABLE>` der `.env`, endet der Lauf mit 0.
3. Sicherung: SQLite-Sicherungsfunktion im laufenden Container, Kopie nach `<BACKUP_DIR>/healthchecks-<alter Tag>-<Zeitstempel UTC>.sqlite` mit Rechten 600. `PRAGMA integrity_check` muss `ok` liefern. Sicherungen über `BACKUP_KEEP` hinaus fallen weg, die älteste zuerst.
4. `<TAG_VARIABLE>` in `<COMPOSE_DIR>/.env` auf den neuen Tag setzen, dann `docker compose up -d --wait --wait-timeout <WAIT_SECONDS>`.
5. Prüfung im Container gegen `http://localhost:<APP_PORT>`: Der Container ist `healthy`, jeder Pfad aus `CHECK_PATHS` antwortet mit 200, die Anmeldeseite enthält `STYLE_MARKER`.
6. Scheitert Schritt 4 oder 5, folgt der Rückweg: Container stoppen, Datenbank aus der Sicherung zurück ins Volume, alter Tag in die `.env`, `up -d --wait`, Prüfung wiederholen. Pings, die zwischen Sicherung und Rückweg ankommen, gehen dabei verloren.
7. Jeder Schritt landet mit Zeitstempel in UTC in `LOG_FILE`; eine logrotate-Regel hält die Datei klein.

Rückgabewerte: 0 aktuell oder erfolgreich gewechselt, 1 Update gescheitert und zurückgenommen (oder ghcr.io nicht erreichbar), 2 ungültige Einstellung, 3 Rückweg gescheitert.

### Einstellungen

`/etc/hc-werkbank.conf` gehört root und ist nur für root schreibbar; das Skript prüft das vor dem Einlesen. Die Vorgaben stehen gesammelt am Anfang des Skripts. Jeder Wert wird gegen seine Grenzen geprüft. Bei einem ungültigen Wert endet das Skript mit 2, ohne etwas zu ändern, und meldet Einstellung, Wert und erlaubten Bereich, etwa: „BACKUP_KEEP ist 0. Erlaubt sind 1 bis 100. Trage einen gültigen Wert in /etc/hc-werkbank.conf ein.“

| Einstellung | Vorgabe | Bedeutung | Grenzen |
|---|---|---|---|
| `IMAGE` | `ghcr.io/brightcolor/healthchecks-werkbank` | verfolgtes Image | Image-Name ohne Tag |
| `TRACK_TAG` | `latest` | beweglicher Tag, auf den das Skript schaut | gültiger Tag |
| `COMPOSE_DIR` | `/opt/healthchecks` | Ordner mit `compose.yaml` und `.env` | vorhandener Ordner |
| `SERVICE` | `healthchecks` | Dienst in der Compose-Datei | Dienst muss existieren |
| `TAG_VARIABLE` | `HC_IMAGE_TAG` | Variable in der `.env`, die den Tag hält | Variablenname |
| `DB_PATH` | Wert von `DB_NAME` aus der `.env` | Pfad der SQLite-Datei im Container | absoluter Pfad; fehlt `DB_NAME` in der `.env`, muss `DB_PATH` gesetzt sein |
| `BACKUP_DIR` | `/root/backups/healthchecks` | Ablage der Sicherungen | absoluter Pfad |
| `BACKUP_KEEP` | `10` | Zahl der Sicherungen, die bleiben | 1 bis 100 |
| `WAIT_SECONDS` | `180` | Frist, bis der Container gesund sein muss | 30 bis 1800 |
| `APP_PORT` | `8000` | Port von Healthchecks im Container | 1 bis 65535 |
| `CHECK_PATHS` | `/api/v3/status/ /accounts/login/` | Pfade, die nach dem Start mit 200 antworten müssen | Pfade mit `/` am Anfang |
| `STYLE_MARKER` | `bc/werkbank` | Text, den die Anmeldeseite enthalten muss | mindestens ein Zeichen |
| `LOG_FILE` | `/var/log/hc-werkbank-update.log` | Protokoll der Läufe | absoluter Pfad |

### Meldungen

- `hc-run` kommt als Kopie des Skripts von den übrigen Hosts nach `/usr/local/sbin/`. Es meldet Start, Erfolg oder Fehlschlag mit den letzten Ausgabezeilen an den Check „docker-a1 · Werkbank-Update für Healthchecks“ im Projekt mit dem OpsKnight-Kanal (heute „Thor“). Von dort gehen Fehlschläge an OpsKnight und per Mail. Die Ping-Adresse geht per Pipe direkt nach `/etc/hc-run.d/hc-werkbank-update.url` (root, 600) und erscheint in keinem Chat und keinem Protokoll.
- Fällt Healthchecks ganz aus, kann es selbst nicht melden. Dafür bekommt Uptime Kuma (uptimekuma.bright-color.de) einen HTTP-Monitor auf `https://hc.bcsrv.de/api/v3/status/` mit dem Schlüsselwort `OK` und den dort vorhandenen Benachrichtigungen.

### Protokoll

Das Log auf docker-a1 hält jeden Lauf fest: alter und neuer Tag, Sicherung, Prüfungen, Ergebnis. Die nächste Sitzung an docker-a1 überträgt Läufe mit Wechsel oder Rückweg mit dem Vermerk „rekonstruiert“ ins Serverprotokoll `docker-a1.md`.

### Einmalige Umstellung

In einer Sitzung, mit Eintrag im Serverprotokoll:

1. Datenbank mit der SQLite-Sicherungsfunktion sichern, dazu `compose.yaml` und `.env`, alles nach `/root/backups/`.
2. In `compose.yaml` `image: ghcr.io/brightcolor/healthchecks-werkbank:${HC_IMAGE_TAG}` eintragen, in der `.env` `HC_IMAGE_TAG=4.4-wb1.0.0`. `SITE_NAME` prüfen.
3. `docker compose up -d --wait`, danach Prüfung von außen und im Browser: hell, dunkel, Handy.
4. `hc-run`, Skript, Einstellungsdatei, Dienst, Timer und logrotate-Regel einrichten, den Check anlegen und seine Ping-Adresse ablegen, den Timer starten.
5. Monitor in Uptime Kuma anlegen, mit eigenem Eintrag in `uptimekuma.bright-color.de.md`.

Die Umstellung bringt das Update von Healthchecks v4.3 auf v4.4 mit, samt Datenbankänderungen.

**Rückweg:** Timer stoppen, in `compose.yaml` `image: healthchecks/healthchecks:v4.3`, Datenbank aus der Sicherung zurück, `docker compose up -d`.

## 8. Fehlerfälle

| Fall | Verhalten | Meldung |
|---|---|---|
| Anker in `base.html` fehlt oder steht mehrfach da | Bau bricht ab, nichts wird veröffentlicht | Issue nennt Anker, Datei, Anzahl und Version |
| Neue Variable in `variables.css` | Prüfung rot | Issue nennt die Variablen |
| Seite mit Fehler, Kontrast unter der Grenze, Querscrollen oder einzeilige Liste auf dem Handy | Prüfung rot | Issue nennt Seite, Modus, Breite und Befund; Bilder hängen am Lauf |
| Update-Probe scheitert | Prüfung rot | Issue nennt den gescheiterten Schritt |
| Basis-Image fehlt noch auf Docker Hub | Lauf endet grün, der nächste Durchgang versucht es erneut | Hinweis in der Zusammenfassung |
| ghcr.io ist von docker-a1 aus unerreichbar | Lauf endet mit 1, die laufende Fassung bleibt | `hc-run` meldet den Fehlschlag mit Grund |
| Sicherung scheitert oder die Integritätsprüfung meldet einen Fehler | Update unterbleibt, Lauf endet mit 1 | Fehlschlag mit Grund |
| Neuer Container wird nicht gesund, oder eine Prüfung scheitert | Rückweg auf alten Tag und Sicherung, Lauf endet mit 1 | Fehlschlag mit Grund und den letzten Zeilen |
| Rückweg scheitert | Lauf endet mit 3; das Log nennt Sicherung und Befehle für die Handarbeit | Uptime Kuma meldet den Ausfall von hc.bcsrv.de |
| Ungültige Einstellung | Lauf endet mit 2, nichts wird geändert | Meldung nennt Einstellung, Wert und erlaubten Bereich |

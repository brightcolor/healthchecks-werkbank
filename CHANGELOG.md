# Änderungen

## 1.0.0 (unveröffentlicht)

- Werkbank für Healthchecks: Onyx-Leiste mit Projekten als Akkordeon, Kopfzeile mit Umschalter für Hell und Dunkel, Anmeldeseite mit Markenfläche.
- Farbableitung: Jede feste Farbe aus den Stylesheets von Healthchecks bekommt eine Werkbank-Rolle.
- CI folgt neuen Healthchecks-Versionen, prüft im Browser und veröffentlicht nach ghcr.io.
- Update-Skript für docker-a1 mit Sicherung der Datenbank und Rückweg.
- Einstellungen des Update-Skripts mit Grenzen und Prüfung (`--nur-pruefen`), darunter `CHECK_TIMEOUT`, `LOCK_FILE` und `FAILED_FILE`.
- Eine zurückgenommene Fassung lassen spätere Läufe aus; `--erneut` versucht sie noch einmal.
- Listen auf dem Handy zweizeilig, Kopfzeile dort mit der aktuellen Seite.

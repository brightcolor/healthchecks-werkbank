# Änderungen

## 1.1.0 (5. Oktober 2026)

- Oberfläche auf Deutsch: Seiten, Dialoge, Meldungen, Skripte, Integrationen und Alarme. Zustände heißen in Ordnung, verspätet und ausgefallen, Period heißt Intervall, Grace Time Kulanz. Die Doku bleibt englisch.
- Katalog in `werkbank/deutsch/` mit Einträgen für ganze Textstücke, Quelltext und ganze Vorlagen, Wörtertabellen für Zustände, Integrationsarten und Rollen sowie Korrekturen an Djangos Zeitangaben („vor 1 Tag, 5 Stunden“).
- Mails im Hausdesign: alle Mails im Layout mit Etikett, Titel und Vorschau, Hausampel, Knopf in Tinte; „Hallo,“ und „Viele Grüße“; Nur-Text-Fassungen mit Zeilen bis 78 Zeichen. Anschrift, Impressum und Datenschutz im Fuß über `WB_MAIL_ANSCHRIFT`, `WB_MAIL_IMPRESSUM_URL` und `WB_MAIL_DATENSCHUTZ_URL`.
- Neue Healthchecks-Versionen mit Texten, die der Katalog noch nicht kennt, gehen raus; ein Issue mit dem Label `uebersetzung` nennt die Stellen.
- CI: Vollständigkeit des Katalogs, jede Vorlage kompiliert, jede Mail im Browser, Abschnitt „Übersetzung“ im Bericht.
- Weitere Integrationen: Der Knopf wächst mit seiner Beschriftung.

## 1.0.0 (5. Oktober 2026)

- Werkbank für Healthchecks: Onyx-Leiste mit Projekten als Akkordeon, Kopfzeile mit Umschalter für Hell und Dunkel, Anmeldeseite mit Markenfläche.
- Farbableitung: Jede feste Farbe aus den Stylesheets von Healthchecks bekommt eine Werkbank-Rolle.
- CI folgt neuen Healthchecks-Versionen, prüft im Browser und veröffentlicht nach ghcr.io.
- Update-Skript für docker-a1 mit Sicherung der Datenbank und Rückweg.
- Einstellungen des Update-Skripts mit Grenzen und Prüfung (`--nur-pruefen`), darunter `CHECK_TIMEOUT`, `LOCK_FILE` und `FAILED_FILE`.
- Eine zurückgenommene Fassung lassen spätere Läufe aus; `--erneut` versucht sie noch einmal.
- Listen auf dem Handy zweizeilig, Kopfzeile dort mit der aktuellen Seite.

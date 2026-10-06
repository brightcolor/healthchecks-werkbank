# Änderungen

## 1.1.1 (6. Oktober 2026)

- Name der Instanz: Enthält `SITE_NAME` einen Namen aus `WB_MARKEN` (Vorgabe „bright color“), erscheint er in Leiste, Anmeldung und Doku so, wie er geschrieben ist. Das Tag `werkbank_name` setzt ihn dort in `<span class="bc-brand">`.
- Nur-Text-Mails lassen Platz für längere Namen und Adressen und bleiben bei 78 Zeichen je Zeile.
- Browserprüfung mit dem Namen „bright color | health“ wie auf hc.bcsrv.de; ein neuer Test meldet Markennamen in Versalien auf jeder Seite und in jeder Mail.
- CI: Actions mit Node 24 (checkout v7, setup-python v7, setup-node v7, upload-artifact v7, download-artifact v8, docker/login-action v4, docker/setup-buildx-action v4), alle Jobs auf `ubuntu-24.04`.
- Einheitstests sammeln auch ohne Django: Die Django-Tests prüfen auf `django.core`.

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

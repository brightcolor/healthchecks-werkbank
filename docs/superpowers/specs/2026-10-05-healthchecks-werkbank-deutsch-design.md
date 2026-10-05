# healthchecks-werkbank 1.1: Deutsch und Mails im Hausdesign

Stand 05.10.2026. Mathias hat den Entwurf in fünf Abschnitten im Chat freigegeben; dieses Dokument fasst ihn zusammen. Grundlage bleibt die Spec von 1.0 (`2026-10-05-healthchecks-werkbank-design.md`); was dort steht und hier nicht geändert wird, gilt weiter.

## 1. Ziel

Healthchecks spricht auf hc.bcsrv.de Deutsch: Oberfläche, Einrichtung und Nachrichten der Integrationen, Mails und die Meldungen aus Python und Skripten. Die Doku bleibt englisch. Die Mails erscheinen im Mail-Design von bright color. Beides bleibt updatesicher in derselben Art wie Einbau und Farbableitung: Ändert Healthchecks einen Text, bleibt dieser englisch, bis der Katalog nachzieht, und ein Issue nennt ihn.

**Erfolgskriterien**

- Unter Healthchecks v4.4 erscheint außerhalb der Doku kein englisches Textstück; ein Vollständigkeitstest prüft das.
- Datumsangaben, Dauern und Zustände stehen auf Deutsch. Zahlen, die Skripte lesen, behalten den Dezimalpunkt; die Live-Updates im Log laufen.
- Jede Mail erscheint im Hausdesign, mit deutscher Nur-Text-Fassung. Kontrast und Breiten sind geprüft.
- Bleiben nach einem Update Texte englisch, geht die Fassung trotzdem raus, und ein Issue mit dem Label `uebersetzung` nennt sie.
- Fassung 1.1.0 kommt über den Timer auf docker-a1, mit Sicherung und Rückweg.

## 2. Entscheidungen

| Frage | Entscheidung |
|---|---|
| Umfang | Oberfläche, Integrationen (Einrichtung und Nachrichten), Mails, Meldungen aus Python und Skripten. Die Doku bleibt englisch, Navigation und Inhalt. |
| Neue englische Texte nach einem Update | Hinweis: Die Fassung geht raus, ein Issue mit dem Label `uebersetzung` nennt die Texte. |
| Weg | Katalog beim Bau, geprüft je Eintrag wie die Anker in `base.html`. Djangos eigene Texte über `USE_I18N`. |
| Begriffe | Check, Ping, Badge, Tag und Slug bleiben. Period heißt Intervall, Grace Time heißt Kulanz. Zustände: in Ordnung, verspätet, ausgefallen, gestartet, pausiert, neu. |
| Ton | Du-Form und die Textregeln der Hausschrift (`references/texte.md`) |
| Mails | Hausdesign nach `samples/mail.html`; Inhalt und Daten liefert Healthchecks |
| Mail-Fuß | Grund der Mail, Link zur Instanz, Abmeldelink. Anschrift, Impressum und Datenschutz kommen aus Einstellungen und bleiben für hc.bcsrv.de leer. |
| Sprache | Einstellung `WB_SPRACHE` mit Vorgabe `de`; `en` überspringt den Katalog |
| Fassung | 1.1.0, Tag `4.4-wb1.1.0` |

## 3. Ausgangslage

Gemessen an Healthchecks v4.4:

- Healthchecks hat keine Übersetzung: `USE_I18N = False`, keine `trans`-Tags. Am Ende von `hc/settings.py` liest es `hc/local_settings.py`, falls vorhanden.
- Umfang der Texte:

| Bereich | Umfang |
|---|---|
| Oberfläche (`templates/` ohne `docs/` und `emails/`) | rund 1.070 Textstücke, 4.000 Wörter |
| Integrationen (`hc/integrations/*/templates/`, 68 Vorlagen in 31 Apps) | Einrichtung rund 650 Textstücke, Nachrichten rund 50 |
| Mails (`templates/emails/`, 43 Dateien) | rund 210 Textstücke, 1.200 Wörter |
| Python (Views, Formulare) | rund 54 Stellen mit Meldungen, Feldnamen und Hilfetexten |
| Skripte (`static/js/`) | rund 10 Sätze |
| Doku | rund 5.250 Textstücke, 30.000 Wörter |

- Dauern setzt `hc/lib/date.py` zusammen: Einheiten mit angehängtem „s“ (`format_duration`), Kurzformen h, min, sec (`format_hms`, `format_approx_duration`) und `pluralize` (`format_duration_for_sentence`).
- Datumsformate stehen in englischer Reihenfolge in den Vorlagen (`M j`, `F j`, `M j, Y`, `N Y`, `M j, H:i`, `D Y-m-d H:i:s T`); `c` und `r` sind Maschinenformate. Im Browser formatiert `static/js/dates.js` mit `Intl` in `en-US` und `en-GB`. `naturaltime` und `timesince` kommen in 20 Dateien vor.
- Zustände erscheinen über Variablen: `{{ status|upper }}` an 10 Stellen, `flip.new_status`, der Filter `uppercase_if_down` in Berichten, der Mail-Betreff `{{ flip.new_status|upper }} | {{ check.name_then_code }}`.
- Zahlenfalle: `front/log.html` gibt `last_event_timestamp` (Kommazahl aus `created.timestamp()`) in ein Skript, und `log.js` schickt ihn für Live-Updates zurück. Mit deutschem Zahlenformat stünde dort ein Komma.
- Mails: `emails/base.html` ist ein Tabellenlayout mit den Blöcken `title`, `content`, `content_more` und `unsub`, einem Knopf aus `button_url` und `button_text` und dem Logo aus `absolute_site_logo_url`. Elf Mails erben es. `alert-body-html.html` und `verify-email-body-html.html` sind schlichte eigene Seiten; die Alarm-Mail hat Healthchecks in v4.0, v4.2 und v4.3 geändert. Absolute Adressen liefert `{% site_root %}`.
- Release-Takt: In den letzten zwölf Monaten erschienen 8 Releases. In den letzten 7 Release-Schritten änderten sich Vorlagen 6-mal, Stylesheets 5-mal, `base.html` und die Farbvariablen je 2-mal.

## 4. Katalog und Bau

### Ablage

`werkbank/deutsch/` enthält TOML-Dateien nach Bereichen: `oberflaeche.toml`, `integrationen.toml`, `mails.toml`, `code.toml` und `werkbank.toml` für die eigenen Texte der Werkbank. TOML liest Python mit `tomllib` ohne Zusatzpaket, und mehrzeilige HTML-Stücke bleiben lesbar.

### Einträge

- **Text** (`[[text]]` mit `datei`, `en`, `de`): wirkt in sichtbarem Text und in den Attributen `title`, `placeholder`, `aria-label`, `alt` sowie `value` bei Knöpfen (`input` vom Typ `submit`, `button`, `reset`). Ein Eintrag trifft ein ganzes Textstück, Leerraum zusammengefasst; Code, Klassen, Adressen und Variablen bleiben unberührt. `datei = "*"` gilt für alle Dateien im Geltungsbereich.
- **Quelltext** (`[[quelltext]]` mit `datei`, `en`, `de`, optional `anzahl`): ersetzt ein genaues Stück Quelle. Dafür sind Sätze mit Tags und Variablen da, Pluralformen, Datumsformate, Python und Skripte. Ohne `anzahl` muss der Eintrag mindestens einmal treffen, mit `anzahl` genau so oft.
- **Gleich bleibend**: Einträge mit gleichem `en` und `de` markieren geprüfte Wörter wie Slack, Cron oder API.
- Quelltext-Einträge wirken vor Text-Einträgen, jeweils in der Reihenfolge des Katalogs.

### Geltungsbereich

- Vorlagen unter `templates/` ohne die Doku (`templates/docs/` und `templates/front/docs_*.html`: Navigation, Suche, Einzelseite, Cron-Spickzettel),
- `hc/integrations/*/templates/`,
- eigene Skripte unter `static/js/` (ohne `.min.js`),
- Python-Dateien, die `code.toml` nennt,
- die Vorlagen und Skripte der Werkbank selbst (`templates/bc/`, `static/bc/leiste.js`).

### Bericht

Nach dem Anwenden sucht der Bau in Vorlagen und Skripten des Geltungsbereichs Textstücke mit mindestens zwei Buchstaben, die kein Eintrag erfasst hat. Ausgenommen sind `<script>`, `<style>`, `<pre>`, `<code>`, Template-Variablen und Kommentare. Der Bericht `werkbank-bericht.json` bekommt einen Abschnitt `uebersetzung` mit den Listen „englisch“ (Datei, Text) und „ohne Fundstelle“ (Datei, Eintrag) samt Zahlen.

### Ort im Bau

Reihenfolge im Dockerfile: Einbau, Farbableitung, Mail-Layout (Abschnitt 7), Katalog, `hc/local_settings.py` mit Formatmodul (Abschnitt 5), dann `collectstatic` und `compress`. Das Mail-Layout ist wie alle eigenen Vorlagen englisch geschrieben und wird über den Katalog deutsch; deshalb kommt es vor dem Katalog. Geänderte Vorlagen und Skripte gelangen so in die gesammelten Dateien und ins Offline-Manifest. Lokal machen `tools/dev.py einsetzen` und `tools/dev.py stil` dasselbe.

### Einstellungen

| Einstellung | Vorgabe | Bedeutung | Grenzen |
|---|---|---|---|
| `WB_SPRACHE` | `de` | Sprache des Images; `en` überspringt den Katalog sowie Sprache und Formatmodul in `local_settings.py`. Mail-Layout und Mail-Einstellungen gelten in beiden Sprachen. | `de` oder `en` |
| `WB_KATALOG` | `deutsch` | Ordner des Katalogs in `werkbank/` | vorhandener Ordner |

Ein ungültiger Katalog (Syntaxfehler, unbekannter Schlüssel, fehlendes oder leeres `en` oder `de`) bricht den Bau ab. Die Meldung nennt Datei, Eintrag und was zu ändern ist.

## 5. Django, Zahlen, Datum, Dauern und Zustände

1. **Djangos eigene Texte:** Der Bau schreibt `hc/local_settings.py` mit `USE_I18N = True` und `LANGUAGE_CODE = "de"`. Damit kommen „vor 3 Stunden“, Formularfehler sowie Monats- und Wochentagsnamen aus Djangos mitgelieferter Übersetzung.
2. **Zahlen mit Punkt:** `FORMAT_MODULE_PATH` zeigt auf ein eigenes Modul `werkbank_formate`. Darin setzt `de/formats.py` `DECIMAL_SEPARATOR = "."`, `THOUSAND_SEPARATOR = ""` und `NUMBER_GROUPING = 0`. Die Datumsformate fallen auf Djangos deutsche Vorgaben zurück.
3. **Datumsformate:** Quelltext-Einträge stellen die Reihenfolge in den Vorlagen auf Deutsch um, etwa `M j` zu `j. M` („5. Okt.“). `c` und `r` bleiben. In `dates.js` setzt der Katalog `de-DE`.
4. **Dauern:** Quelltext-Einträge in `hc/lib/date.py` ergeben Tag/Tage, Stunde/Stunden, Minute/Minuten, Woche/Wochen und Sekunde/Sekunden, kurz h, min und s.
5. **Zustände:** Ein Quelltext-Eintrag ergänzt `hc/front/templatetags/hc_extras.py` um den Filter `zustand` (up → in Ordnung, grace → verspätet, down → ausgefallen, started → gestartet, paused → pausiert, new → neu). Die Vorlagen geben ihre Zustandswörter darüber aus. Der Mail-Betreff lautet „backup-nacht ist ausgefallen“ oder „backup-nacht ist wieder in Ordnung“.
6. **Python und Skripte:** `code.toml` enthält Quelltext-Einträge für Meldungen, Feldnamen, Hilfetexte und `ValidationError` in Views und Formularen sowie für die Sätze in Skripten.
7. **Eigene `local_settings.py`:** Hängt ein Betreiber eine eigene Datei ein, ersetzt sie die aus dem Image. Die README nennt die Zeilen, die er übernehmen muss.

## 6. Texte und Begriffe

| Healthchecks | Deutsch |
|---|---|
| Check, Ping, Badge, Tag, Slug | bleiben; Plural Checks, Pings, Badges, Tags |
| Period · Grace Time | Intervall · Kulanz |
| up · grace · down · started · paused · new | in Ordnung · verspätet · ausgefallen · gestartet · pausiert · neu |
| Schedule · Cron Expression · Time Zone | Zeitplan · Cron-Ausdruck · Zeitzone |
| Last Ping · Ping URL · Ping Key · API Key | Letzter Ping · Ping-Adresse · Ping-Schlüssel · API-Schlüssel |
| Integrations · Projects · Team | Integrationen · Projekte · Team |
| Settings · Account Settings · Appearance | Einstellungen · Konto · Darstellung |
| Events · Downtime · Filtering Rules · Reminders | Ereignisse · Ausfallzeit · Filterregeln · Erinnerungen |
| Log In · Log Out · Sign Up | Anmelden · Abmelden · Registrieren |
| Email | E-Mail als Name und Feldbeschriftung; im Fließtext „Mail“, etwa Alarm-Mail, Mail-Bericht |

- Knöpfe sagen, was passiert: „Check anlegen“, „Integration hinzufügen“, „Speichern“, „Abbrechen“, „Pausieren“, „Entfernen“.
- Du-Form, kurze aktive Sätze, echte Umlaute, keine Negativabgrenzungen.
- Meldungen sagen zuerst, was passiert ist, dann die Ursache und den nächsten Schritt mit Ort in der Oberfläche. Vage Meldungen von Healthchecks werden dabei genauer, soweit der Code die Ursache klar zeigt; Erfundenes kommt nicht hinein.
- Anton-Titel bleiben in Versalien, etwa „BEI HEALTHCHECKS ANMELDEN“. Der Gruß „Moin.“ bleibt.
- Mails beginnen mit „Hallo,“; Healthchecks kennt nur die Mailadresse. Gruß „Viele Grüße“, darunter der Name der Instanz.
- Die eigenen Texte der Werkbank laufen über `werkbank.toml`: Leiste und Kopfzeile (Neues Projekt, Doku, Konto, Abmelden, Menü, Ereignisse), die Beschriftungen des Umschalters und die Meldung beim Speichern der Darstellung.
- Die Doku bleibt englisch; Leiste und Kopfzeile drumherum sind deutsch.

## 7. Mails im Hausdesign

1. **Grundlayout:** `werkbank/mails/base.html` folgt `samples/mail.html` der Hausschrift. Papier außen, Weiß innen, 600 px. Oben ein Kopfbalken in Tinte mit `bc-logo-light-noclaim.png` (170 × 28 px), darunter das Vierfarbband aus vier Zellen à 4 px. Darunter Etikett mit Quadrat und Anton-Titel, Inhalt, Knopf in Tinte mit VML für Outlook, Fuß in Papier tief. Der Bau kopiert die Datei an die Stelle von `templates/emails/base.html`.
2. **Blöcke und Variablen:** Das Layout stellt dieselben Blöcke bereit wie das Original (`title`, `content`, `content_more`, `unsub`) und nutzt `button_url` und `button_text`. Vor dem Kopieren vergleicht der Bau die Blöcke und Variablen des Originals mit denen des Layouts. Fehlt einer, bricht der Bau ab; sonst ginge Inhalt verloren. Die Prüfsumme des Originals steht in `werkbank/mails/original.sha256`. Weicht sie ab, ohne dass Blöcke oder Variablen fehlen, entsteht ein Hinweis.
3. **Alarm-Mail und Adressbestätigung:** Quelltext-Einträge setzen `alert-body-html.html` und `verify-email-body-html.html` in das Layout (`extends` und `block content`) und färben Zustände und Tabellen nach der Hausampel: ausgefallen Pink, wieder in Ordnung Limette, verspätet Gelb. Inhalt und Daten bleiben die von Healthchecks. Greift ein Eintrag nicht, bleibt die Mail schlicht wie bei Healthchecks und steht im Hinweis.
4. **Technik nach der Hausschrift (`references/medien.md`):** nur Tabellen mit `role="presentation"`, Stile inline, Geistertabelle für Outlook, `color-scheme: light`, versteckter Vorschautext mit dem Betreff. Logo als PNG mit absoluter Adresse über `{% site_root %}`. Anton und Atkinson als Webfonts in einem `@media screen`-Block für Apple Mail und iOS; Outlook bekommt Impact und Arial, alle anderen die Stapel der Hausschrift.
5. **Nur-Text-Fassungen** bleiben, deutsch, Zeilen bis 78 Zeichen, Signaturtrenner „-- “.
6. **Fuß:** Grund der Mail, Link zur Instanz und der Abmeldelink von Healthchecks. Anschrift, Impressum und Datenschutz erscheinen, sobald ihre Einstellungen gesetzt sind:

| Einstellung | Vorgabe | Bedeutung | Grenzen |
|---|---|---|---|
| `WB_MAIL_ANSCHRIFT` | leer | Anschrift im Mail-Fuß, eine Zeile | bis 200 Zeichen |
| `WB_MAIL_IMPRESSUM_URL` | leer | Link zum Impressum | Adresse mit `https://` |
| `WB_MAIL_DATENSCHUTZ_URL` | leer | Link zur Datenschutzerklärung | Adresse mit `https://` |

`hc/local_settings.py` liest die drei Werte aus der Umgebung und prüft sie beim Start. Ein ungültiger Wert hält Healthchecks mit einer Meldung an, die Einstellung, Wert und erwartete Form nennt. Ein Template-Tag in `hc_extras.py` gibt sie an das Layout.

7. **Logo:** `vendor/hausschrift/assets/logo/png/bc-logo-light-noclaim.png` kommt in die Kopie der Hausschrift und beim Bau nach `static/bc/logo/`.

## 8. Prüfung

1. **Einheitstests:** Katalog-Maschine (Text- und Quelltext-Einträge, ganze Textstücke, Attribute, Knöpfe, gleich bleibende Einträge, `anzahl`, Reihenfolge, Meldungen bei kaputtem Katalog), deutsche Dauern aus dem angepassten `date.py`, Filter `zustand`, Vergleich der Mail-Blöcke, Prüfung der Mail-Einstellungen, ein Lauf mit `WB_SPRACHE=en` ohne Änderung.
2. **Vollständigkeit:** `werkbank/deutsch/stand.toml` nennt die Healthchecks-Version, für die der Katalog vollständig ist (heute v4.4). Ein Test wendet den Katalog auf genau diese Version unter `.upstream/` an und erwartet null englische Textstücke und null Einträge ohne Fundstelle. Liegt dort nur eine andere Version, etwa in der CI für ein neues Release, überspringt er sich, und der Hinweis übernimmt.
3. **Browsertests:** Die vorhandenen Tests erwarten deutsche Texte. Neu: Der Zeitstempel im Log steht mit Punkt, und die Live-Updates antworten. Zustände, Dauern und Datumsangaben erscheinen deutsch. Breiten- und Überdeckungstests fangen zu lange Beschriftungen ab. Tests, die bestimmte deutsche Texte von Healthchecks erwarten, laufen nur gegen die Version aus `stand.toml` und überspringen sich sonst, damit ein umformulierter Text bei einem neuen Release nur einen Hinweis ergibt. Tests für die Texte der Werkbank, Djangos Datumsangaben, das Zahlenformat, Breiten, Kontrast und Überdeckung laufen immer.
4. **Mails:** `tests/mails/rendern.py` rendert in der Testinstanz jede Mail mit Musterdaten zu HTML und Text. Die CI macht davon Bilder bei 360, 390 und 760 px, prüft den Kontrast und hängt die Bilder an den Lauf. `bc_check.py lint` prüft das Mail-Layout. Lokal macht `tools/dev.py mails` dasselbe. Echte Mailprogramme zeigt nach dem Ausrollen ein Anmeldelink an Mathias.

## 9. CI und Hinweis

- Die Zusammenfassung des Laufs bekommt einen Abschnitt „Übersetzung“ mit den Zahlen und den Listen aus dem Bericht, dazu Hinweise zum Mail-Layout.
- Gibt es nach einem veröffentlichten Lauf Hinweise, öffnet oder ergänzt der Lauf ein Issue mit dem Label `uebersetzung` (Einstellung `WB_HINWEIS_LABEL`). Der Titel nennt Version und Zahl der offenen Punkte, etwa „Healthchecks v4.5: 12 Texte noch englisch“. Ein späterer Lauf ohne Hinweise schließt es.
- Hinweise halten keine Fassung auf. Rot bleibt, was etwas kaputt macht: ungültiger Katalog, fehlende Blöcke oder Variablen im Mail-Layout, Seiten mit Fehler, Kontrast, Querscrollen oder Überdeckung.

## 10. Auslieferung

- `VERSION` wird 1.1.0. Der Push auf `main` baut, prüft und veröffentlicht `4.4-wb1.1.0`, `4.4` und `latest`.
- docker-a1 übernimmt die Fassung zur nächsten Minute 37 mit Sicherung und Rückweg; es ist das erste echte automatische Update. Die Sitzung beobachtet den Lauf und hält ihn im Serverprotokoll `docker-a1.md` fest.
- README, CHANGELOG und die Spec von 1.0 ziehen nach: Sprache, Katalog, `WB_SPRACHE`, `WB_KATALOG`, `WB_HINWEIS_LABEL`, die drei Mail-Einstellungen und der Hinweis zu eigenen `local_settings.py`. In der Spec von 1.0 ersetzt dieser Entwurf die Zeile „Texte“ der Entscheidungen.

## 11. Fehlerfälle

| Fall | Verhalten | Meldung |
|---|---|---|
| Katalogeintrag ohne Fundstelle | Der Text bleibt englisch, die Fassung geht raus | Issue `uebersetzung` |
| Neues englisches Textstück | bleibt englisch, die Fassung geht raus | Issue `uebersetzung` |
| Katalog ungültig | Bau bricht ab | Issue `theme-rot` nennt Datei und Eintrag |
| Mail-Layout von Healthchecks mit neuem Block oder neuer Variable | Bau bricht ab | Issue `theme-rot` nennt Block oder Variable |
| Mail-Layout geändert, Blöcke und Variablen vollständig | Fassung geht raus | Hinweis im Issue `uebersetzung` |
| Eintrag an Alarm- oder Bestätigungsmail greift nicht | Mail bleibt schlicht wie bei Healthchecks | Hinweis im Issue `uebersetzung` |
| Zeitstempel im Log mit Komma | Browsertest rot | Issue `theme-rot` |
| Deutsche Beschriftung zu lang | Breiten- oder Überdeckungstest rot | Issue `theme-rot` |
| `WB_SPRACHE` oder `WB_KATALOG` ungültig | Bau bricht ab | Meldung nennt Einstellung, Wert und erlaubte Werte |
| `WB_MAIL_*` ungültig | Healthchecks startet nicht; das Update-Skript nimmt eine neue Fassung zurück | Meldung im Containerlog nennt Einstellung, Wert und erwartete Form |

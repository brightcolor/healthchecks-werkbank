# Werkbank 1.1: Deutsch und Mails im Hausdesign – Umsetzungsplan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Healthchecks erscheint auf Deutsch (ohne Doku), seine Mails im Mail-Design von bright color, beides updatesicher über einen Katalog beim Bau.

**Architecture:** Ein Katalog aus TOML-Dateien (`werkbank/deutsch/`) ersetzt beim Bau Texte in Vorlagen, Skripten und einzelnen Python-Dateien; `werkbank/sprache.py` prüft jeden Eintrag und meldet englische Reste. `werkbank/mails.py` setzt ein eigenes Mail-Layout an die Stelle von `emails/base.html`, nachdem es Blöcke und Variablen verglichen hat. Djangos eigene Texte kommen über `USE_I18N` aus einem Einstellungsmodul, das ein Formatmodul mit Dezimalpunkt einbindet.

**Tech Stack:** Python 3.13 (nur Standardbibliothek: `tomllib`, `re`, `hashlib`), Django-Vorlagen von Healthchecks v4.4, Bash, GitHub Actions, Playwright.

**Spec:** `docs/superpowers/specs/2026-10-05-healthchecks-werkbank-deutsch-design.md` (Grundlage weiter `2026-10-05-healthchecks-werkbank-design.md`)

## Global Constraints

- Bau-Skripte laufen im Image von Healthchecks: nur Standardbibliothek, Python 3.13.
- Begriffe: Check, Ping, Badge, Tag, Slug bleiben; Period → Intervall; Grace Time → Kulanz; up/grace/down/started/paused/new → in Ordnung/verspätet/ausgefallen/gestartet/pausiert/neu; weitere Begriffe nach Abschnitt 6 der Spec.
- Texte: Du-Form, kurze aktive Sätze, echte Umlaute, keine Negativabgrenzungen („X statt Y“, „nicht X, sondern Y“), keine Zeitangaben zur Dauer. Meldungen: was passiert ist, Ursache, nächster Schritt.
- Nichts fest im Code: Pfade, Dateinamen, Grenzen als Einstellungen mit Vorgabe an einer Stelle (`VORGABEN`), Prüfung mit verständlicher Meldung, Tests auch mit anderen Werten.
- Hinweis statt Stopp für englische Reste und Einträge ohne Fundstelle; Rot für ungültigen Katalog, fehlende Mail-Blöcke oder -Variablen, Seitenfehler, Kontrast, Querscrollen, Überdeckung.
- Keine Agenten (Vorgabe von Mathias); Umsetzung in dieser Sitzung.
- Arbeit an docker-a1 kommt ins Serverprotokoll `C:\Users\brigh\Claude Workingdir\Serverprotokolle\docker-a1.md` (frisch lesen, gezielt einfügen).
- Dateien, die Python unter Windows schreibt: als Bytes oder mit `newline="\n"` schreiben, damit LF bleibt.

## Dateien

| Datei | Aufgabe |
|---|---|
| `werkbank/sprache.py` | Katalog laden, prüfen, anwenden, Bericht, Inventur |
| `werkbank/deutsch/katalog.toml` | Stand, Geltungsbereich, Zustandswörter |
| `werkbank/deutsch/werkbank.toml`, `code.toml`, `oberflaeche.toml`, `integrationen.toml`, `mails.toml` | Einträge |
| `werkbank/erweiterungen.toml` | Filter `zustand` und Tag `werkbank_mail` in `hc_extras.py`, in jeder Sprache |
| `werkbank/django/werkbank_einstellungen.py` | Vorlage des Einstellungsmoduls (Sprache, Zustände, Mail-Einstellungen) |
| `werkbank/django/werkbank_formate/de/formats.py` | Formatmodul mit Dezimalpunkt |
| `werkbank/mails.py`, `werkbank/mails/base.html`, `werkbank/mails/original.sha256` | Mail-Layout |
| `vendor/hausschrift/assets/logo/png/bc-logo-light-noclaim.png` | Logo für Mails |
| `tests/test_sprache.py`, `tests/test_werkbank_einstellungen.py`, `tests/test_mails.py`, `tests/test_sprache_vollstaendig.py`, `tests/test_hinweis.py` | Einheitstests |
| `tests/mails/rendern.py`, `tests/e2e/mails.spec.mjs` | Mails rendern und prüfen |
| `tools/ci/hinweis.sh`, `tools/ci/bericht.py`, `tools/ci/testinstanz.sh`, `.github/workflows/build.yml` | CI |
| `Dockerfile`, `tools/dev.py` | Bau und lokale Entwicklung |

---

### Task 1: Katalog-Maschine

**Files:**
- Create: `werkbank/sprache.py`
- Test: `tests/test_sprache.py`

**Interfaces:**
- Produces: `sprache.bauen(wurzel: Path, werkbank: Path, bericht: Path | None = None) -> dict`, `sprache.inventur(wurzel, werkbank, muster="*", global_ab=0) -> str`, `sprache.SprachFehler`, `sprache.stuecke(quelle) -> list[Stueck]`, `sprache.einstellung(name) -> str`. Kommandozeile `python sprache.py bauen|inventur --wurzel … --werkbank … [--bericht …]`.

- [ ] **Step 1: Tests schreiben.** Fälle mit kleinen Vorlagen in `tmp_path`: ganzes Textstück ersetzt, Leerraum bleibt, „Log“ trifft „Login“ nicht; `title`, `placeholder`, `aria-label`, `alt` ersetzt, `value` nur an `input` vom Typ submit/button/reset, `class` und `href` unberührt; `<script>`, `<style>`, `<pre>`, `<code>`, `<textarea>` und Kommentare unberührt; Quelltext ersetzt alle Vorkommen, `anzahl` abweichend → unverändert und „ohne Fundstelle“ mit Zahl; globale Einträge wirken in allen Vorlagen, dateieigene gehen vor; Einträge mit gleichem `en` und `de` gelten als geprüft; Erkennung meldet unberührte englische Textstücke, aber keine deutschen Ersetzungen und keine Reste aus Quelltext-Ersetzungen; fehlende Datei → ohne Fundstelle; Ausnahmen des Geltungsbereichs bleiben unberührt und ungemeldet; `WB_SPRACHE=en` ändert keine Vorlage; Fehler mit Meldung: TOML-Syntax, unbekannter Abschnitt oder Schlüssel, leeres `de`, `anzahl` bei Text, Quelltext mit `datei = "*"`, doppelter Eintrag, `WB_SPRACHE=fr`, fehlender Katalog-Ordner, Erweiterung ohne Anker; CRLF-Dateien behalten CRLF; Inventur liefert gültiges TOML mit den englischen Resten; Bericht wird in eine vorhandene JSON-Datei unter `uebersetzung` eingefügt.

- [ ] **Step 2: Tests laufen lassen, sie scheitern** (`.venv/Scripts/python -m pytest tests/test_sprache.py -q`).

- [ ] **Step 3: `werkbank/sprache.py` schreiben.** Kern:

```python
VORGABEN = {
    "WB_SPRACHE": "de",
    "WB_KATALOG": "deutsch",
    "WB_KATALOG_KONFIG": "katalog.toml",
    "WB_ERWEITERUNGEN": "erweiterungen.toml",
    "WB_EINSTELLUNGSMODUL": "hc/werkbank_einstellungen.py",
    "WB_FORMATMODUL": "hc/werkbank_formate",
    "WB_LOCAL_SETTINGS": "hc/local_settings.py",
}
SPRACHEN = ("de", "en")
SICHTBARE_ATTRIBUTE = ("title", "placeholder", "aria-label", "alt")   # nach HTML sichtbar
KNOPF_TYPEN = ("submit", "button", "reset")                           # value ist dort Beschriftung
TOKEN = re.compile(
    r"\{#.*?#\}|\{%\s*comment\s*%\}.*?\{%\s*endcomment\s*%\}|\{%.*?%\}|\{\{.*?\}\}|<!--.*?-->"
    r"|<(?P<opak>script|style|pre|code|textarea)\b.*?</(?P=opak)\s*>|</?[A-Za-z][^<>]*>",
    re.S | re.I,
)
ATTRIBUT = re.compile(r"""(?P<name>[A-Za-z_:][-A-Za-z0-9_:.]*)\s*=\s*(?P<q>["'])(?P<wert>.*?)(?P=q)""", re.S)
```

`stuecke(quelle)` liefert Textlücken zwischen den Treffern von `TOKEN` und die sichtbaren Attributwerte der HTML-Tags mit Lage. `text_anwenden(quelle, woerter)` ersetzt Stücke, deren zusammengefasster Inhalt (`" ".join(s.split())`) ein Schlüssel ist, behält Leerraum davor und danach und bricht ab, wenn ein Ersatz das Anführungszeichen seines Attributs enthält. `quelltext_anwenden` zählt `en` und ersetzt nur, wenn die Zahl passt (ohne `anzahl` mindestens 1). Erkennung: Stücke des Ergebnisses, die als Stück im Original vorkamen, Buchstaben enthalten und keinem gleich bleibenden Eintrag entsprechen. `bauen()`: Einstellungen prüfen, Erweiterungen anwenden (Fehlschlag bricht ab), Einstellungsmodul, Formatmodul und `local_settings.py` schreiben, bei `de` den Katalog anwenden, Bericht schreiben. Dateien werden als Bytes gelesen; CRLF bleibt erhalten.

- [ ] **Step 4: Tests laufen lassen, sie bestehen.**
- [ ] **Step 5: Commit** „Katalog-Maschine für die Übersetzung beim Bau“.

### Task 2: Django-Teil und Erweiterungen

**Files:**
- Create: `werkbank/django/werkbank_einstellungen.py`, `werkbank/django/werkbank_formate/__init__.py`, `werkbank/django/werkbank_formate/de/__init__.py`, `werkbank/django/werkbank_formate/de/formats.py`, `werkbank/erweiterungen.toml`, `werkbank/deutsch/katalog.toml`
- Test: `tests/test_werkbank_einstellungen.py`

**Interfaces:**
- Consumes: `sprache.bauen` schreibt die Dateien nach `hc/` und ersetzt `@@WB_SPRACHE@@` und `@@WB_ZUSTAENDE@@`.
- Produces: Einstellungen `WERKBANK_SPRACHE`, `WERKBANK_ZUSTAENDE`, `WB_MAIL_ANSCHRIFT`, `WB_MAIL_IMPRESSUM_URL`, `WB_MAIL_DATENSCHUTZ_URL`; Filter `zustand`, Tag `werkbank_mail`.

- [ ] **Step 1: Tests schreiben** (mit `pytest.importorskip("django")`): Vorlage mit `de` und Zuständen ausführen → `USE_I18N`, `LANGUAGE_CODE == "de"`, `FORMAT_MODULE_PATH`; mit `en` ohne diese Namen; Mail-Einstellungen leer als Vorgabe, gültige Werte übernommen, `WB_MAIL_IMPRESSUM_URL=http://x` und eine Anschrift über 200 Zeichen werfen `ImproperlyConfigured` mit Name und Wert; Formatmodul hat Punkt und leere Tausendertrennung; die Erweiterung trifft `hc_extras.py` aus `.upstream/<stand>` genau einmal (übersprungen ohne Quelle).
- [ ] **Step 2: Tests scheitern.**
- [ ] **Step 3: Dateien schreiben.**

`werkbank/erweiterungen.toml` (Anker `register = template.Library()`, `anzahl = 1`) ergänzt:

```python
@register.filter
def zustand(status: str) -> str:
    """Zustand eines Checks in Worten der Werkbank (WERKBANK_ZUSTAENDE), sonst unverändert."""
    return getattr(settings, "WERKBANK_ZUSTAENDE", {}).get(status, status)


@register.simple_tag
def werkbank_mail(name: str) -> str:
    """Wert einer Mail-Einstellung der Werkbank, etwa WB_MAIL_IMPRESSUM_URL; leer, wenn nicht gesetzt."""
    return getattr(settings, name, "")
```

`werkbank/deutsch/katalog.toml`:

```toml
[katalog]
stand = "v4.4"

[bereich]
vorlagen = ["templates/**/*.html", "hc/integrations/*/templates/*.html"]
ausnahmen = ["templates/docs/**", "templates/front/docs_*.html"]

[zustaende]
up = "in Ordnung"
grace = "verspätet"
down = "ausgefallen"
started = "gestartet"
paused = "pausiert"
new = "neu"
```

- [ ] **Step 4: Tests bestehen.** **Step 5: Commit** „Einstellungsmodul, Formatmodul und Erweiterungen“.

### Task 3: Mail-Layout

**Files:**
- Create: `werkbank/mails.py`, `werkbank/mails/base.html`, `werkbank/mails/original.sha256`, `vendor/hausschrift/assets/logo/png/bc-logo-light-noclaim.png`
- Test: `tests/test_mails.py`

**Interfaces:**
- Produces: `mails.einsetzen(wurzel, werkbank, hausschrift) -> list[str]` (Hinweise), `mails.MailFehler`, Kommandozeile `python mails.py einsetzen --wurzel … --werkbank … --hausschrift … [--bericht …]`; Blöcke des Layouts `title`, `content`, `content_more`, `unsub` (wie Healthchecks) und zusätzlich `etikett`, `ueberschrift`, `vorschau`, `grund`.

- [ ] **Step 1: Tests schreiben:** fehlender Block oder fehlende Variable → `MailFehler` mit Namen; abweichende Prüfsumme → Hinweis; Prüfsumme über LF-normalisierten Text; Layout und Logo landen an ihrem Ziel; echtes Layout gegen `.upstream/<stand>/templates/emails/base.html`: vollständig und Prüfsumme gleich (übersprungen ohne Quelle); Einstellungen `WB_MAIL_LAYOUT` und `WB_MAIL_LOGO_ZIEL` mit anderen Werten.
- [ ] **Step 2: Tests scheitern.**
- [ ] **Step 3: Umsetzen.** `mails.py` mit `VORGABEN` (`WB_MAIL_LAYOUT=templates/emails/base.html`, `WB_MAIL_VORLAGE=mails/base.html`, `WB_MAIL_PRUEFSUMME=mails/original.sha256`, `WB_MAIL_LOGO=assets/logo/png/bc-logo-light-noclaim.png`, `WB_MAIL_LOGO_ZIEL=static/bc/logo/bc-logo-light-noclaim.png`). `werkbank/mails/base.html` übernimmt Aufbau und Technik aus `samples/mail.html` der Hausschrift: mso-Blöcke, drei `<style>`-Blöcke (Layout, Apple, Webfonts mit `{% site_root %}{% static 'bc/fonts/…' %}`), Vorschautext aus `{% block vorschau %}`, Tinte-Balken mit Logo (`{% site_root %}{% static 'bc/logo/bc-logo-light-noclaim.png' %}`, 170 × 28), Vierfarbband, Etikett mit Cyan-Quadrat aus `{% block etikett %}{% site_name %}{% endblock %}`, Anton-Titel aus `{% block ueberschrift %}{% site_name %}{% endblock %}`, Inhalt aus `content` in einer Zelle mit Atkinson 16/25 px Tinte, Knopf aus `button_text`/`button_url` in Tinte (VML und Link), `content_more`, Fuß in Papier tief mit `{% block grund %}This message comes from {% site_name %}.{% endblock %}`, Link zu `{% site_root %}`, Anschrift, Impressum und Datenschutz über `{% werkbank_mail "…" %}` wenn gesetzt, dann `unsub`. Texte des Layouts englisch; `werkbank.toml` übersetzt sie. Logo-PNG aus der Hausschrift in die Kopie unter `vendor/` übernehmen, `QUELLE.md` ergänzen. Prüfsumme des Originals v4.4 eintragen.
- [ ] **Step 4: Tests bestehen.** **Step 5: Commit** „Mail-Layout im Hausdesign“.

### Task 4: Bau und lokale Entwicklung

**Files:**
- Modify: `Dockerfile`, `tools/dev.py`, `tools/ci/testinstanz.sh`, `tests/e2e/hilfen.mjs`, `playwright.config.mjs`
- Create: `tests/mails/rendern.py`, `tests/e2e/mails.spec.mjs`
- Test: `tests/test_dev.py` (ergänzt)

- [ ] **Step 1: Dockerfile:** `ARG WB_SPRACHE=de`; nach `farben.py bauen`: `python /tmp/werkbank/mails.py einsetzen … --bericht /opt/healthchecks/werkbank-bericht.json` und `WB_SPRACHE="$WB_SPRACHE" python /tmp/werkbank/sprache.py bauen --wurzel /opt/healthchecks --werkbank /tmp/werkbank --bericht /opt/healthchecks/werkbank-bericht.json`; dann `collectstatic` und `compress`.
- [ ] **Step 2: `tools/dev.py`:** `einsetzen()` kopiert vor dem Einsetzen `templates/`, `static/` und `hc/` aus der sauberen Quelle über die Arbeitskopie (Katalog und Erweiterungen wirken nur auf unberührte Dateien), danach Einbau, Farben, Mails, Sprache; `lokale_einstellungen()` schreibt `from hc.werkbank_einstellungen import *` plus die Compress-Zeilen; `nur_stil()` wendet nach dem Kopieren von `leiste.js` die Einträge für `static/bc/leiste.js` an; neuer Befehl `mails` rendert über `manage.py shell -c` mit `tests/mails/rendern.py` nach `tests/e2e/ergebnisse/mails/`; `pruefen` ruft vorher `mails` auf und setzt `WB_HC_VERSION`. Test in `tests/test_dev.py`: `nur_einsetzen` holt Vorlagen, Skripte und Python-Dateien aus der Quelle zurück.
- [ ] **Step 3: `tests/mails/rendern.py`:** baut je Mailart den Kontext wie die Aufrufstelle und rendert mit `hc.lib.emails.make_message(name, "empfang@example.org", ctx)`; schreibt `<name>.html`, `<name>.txt`, `<name>-betreff.txt` nach `WB_MAILS_ZIEL`. Aufrufstellen: `login` (`hc/accounts/models.py:152`, mit und ohne Einladung), `transfer_request` (`:183`), `report` und `nag` (`:279`, `:289`), `alert` (`hc/integrations/email/transport.py:79`, ausgefallen und wieder in Ordnung), `verify_email` (`hc/api/models.py:1079`), `signal_rate_limited`, `call_limit`, `sms_limit` (`hc/api/models.py:1113–1135`), `sudo_code` (`hc/accounts/decorators.py:49`), `flapping_notice`, `deletion_notice`, `deletion_scheduled` (Kommandos unter `hc/accounts/management/commands/`). Daten aus den Musterdaten, Flips und Pings ungespeichert.
- [ ] **Step 4: `tests/e2e/mails.spec.mjs`:** jede gerenderte HTML-Datei bei 360, 390 und 760 px öffnen, Bild ablegen, Kontrastlauf ohne Befund, kein Querscrollen; Text- und Betreffdateien deutsch (nur wenn `WB_HC_VERSION` dem Stand entspricht).
- [ ] **Step 5: `tools/ci/testinstanz.sh`:** nach den Musterdaten `rendern.py` im Container ausführen und `docker cp` nach `tests/e2e/ergebnisse/mails/`.
- [ ] **Step 6: Prüfen und Commit** „Übersetzung und Mail-Layout im Bau und lokal“.

### Task 5: Katalog Werkbank und Code

**Files:** Create `werkbank/deutsch/werkbank.toml`, `werkbank/deutsch/code.toml`

- [ ] **Step 1:** `werkbank.toml`: Texte aus `templates/bc/leiste.html` (Leiste, Kopfzeile, Markenfläche, Vorlesetexte), `static/bc/leiste.js` (Meldung beim Speichern der Darstellung, Beschriftungen), `templates/emails/base.html` (Layout-Texte, `lang`), Zustandsausgabe in der Leiste über `|zustand`.
- [ ] **Step 2:** `code.toml`: `hc/lib/date.py` (Einheiten, Plural, Kurzformen h/min/s), `static/js/dates.js` (`de-DE`), Meldungen, Feldnamen, Hilfetexte und `ValidationError` in `hc/front/views.py`, `hc/accounts/views.py`, `hc/accounts/forms.py`, `hc/front/forms.py` und weiteren Fundstellen (Suche: `messages.`, `ValidationError(`, `help_text=`, `label=`, `add_error(`), Sätze in eigenen Skripten unter `static/js/`.
- [ ] **Step 3:** `tools/dev.py einsetzen`, Server neu starten, Leiste und eine Detailseite ansehen; Einheitstest für deutsche Dauern gegen die angepasste `date.py` (`tests/test_sprache_vollstaendig.py` mit `importorskip("django")`).
- [ ] **Step 4: Commit** „Katalog: Werkbank und Code“.

### Task 6: Katalog Oberfläche

**Files:** Create `werkbank/deutsch/oberflaeche.toml`

- [ ] **Step 1:** Inventur: `python werkbank/sprache.py inventur --wurzel .upstream/v4.4 --werkbank werkbank --datei "templates/*" --global-ab 3 > artefakte/inventur-oberflaeche.toml`.
- [ ] **Step 2:** Übersetzen nach Begriffen und Ton der Spec; wiederkehrende Stücke als `datei = "*"`; Sätze mit Tags oder Variablen als Quelltext; Datumsformate (`M j` → `j. M` usw.); Zustandswörter über `|zustand`.
- [ ] **Step 3:** Inventur erneut: null englische Reste in `templates/` außerhalb Doku und Mails; Seiten lokal ansehen.
- [ ] **Step 4: Commit** „Katalog: Oberfläche“.

### Task 7: Katalog Integrationen

**Files:** Create `werkbank/deutsch/integrationen.toml`

- [ ] **Step 1–3** wie Task 6 für `hc/integrations/*/templates/*.html`: Einrichtungsseiten, Formulare, Titel und Nachrichten (`*_message.html`, `*_title.html`, `*_description.html`), Zustände in Nachrichten über `|zustand`.
- [ ] **Step 4: Commit** „Katalog: Integrationen“.

### Task 8: Katalog Mails

**Files:** Create `werkbank/deutsch/mails.toml`

- [ ] **Step 1:** Rahmen: Quelltext-Einträge setzen `alert-body-html.html` und `verify-email-body-html.html` in das Layout (`{% extends "emails/base.html" %}`, `{% block content %}` … `{% endblock %}`); je Mailart Blöcke `etikett`, `ueberschrift`, `vorschau` und bei Bedarf `grund`.
- [ ] **Step 2:** Texte aller Mails (`*-subject.html`, `*-body-text.html`, `*-body-html.html`, `*-summary-html.html`, `report-when.html`): Anrede „Hallo,“, Gruß „Viele Grüße“ mit Instanzname, Betreff der Alarm-Mail „… ist ausgefallen“ / „… ist wieder in Ordnung“; Hausampel in den Tabellen der Alarm- und Bericht-Mails (Pink, Limette, Gelb, Schrift Tinte); Nur-Text-Fassungen mit Zeilen bis 78 Zeichen.
- [ ] **Step 3:** `tools/dev.py mails`, Bilder ansehen, Kontrastlauf.
- [ ] **Step 4: Commit** „Katalog: Mails“.

### Task 9: Vollständigkeit und Browsertests

**Files:** Create `tests/test_sprache_vollstaendig.py`; Modify `tests/e2e/leiste.spec.mjs`, `tests/e2e/seiten.spec.mjs`, `tests/e2e/hilfen.mjs`, `werkbank/stil.css`

- [ ] **Step 1:** Vollständigkeitstest: Katalog auf eine Kopie von `.upstream/<stand>` anwenden (ohne Doku), null englische Reste, null Einträge ohne Fundstelle; übersprungen, wenn `.upstream/<stand>` fehlt.
- [ ] **Step 2:** Browsertests auf Deutsch: Leiste („Ereignisse“, Zustand „ausgefallen“, Meldung beim Speichern); neue Tests: Zeitstempel im Log mit Punkt und Live-Update antwortet 200; Zustände, Dauern, Datumsangaben deutsch (nur bei `WB_HC_VERSION` = Stand).
- [ ] **Step 3:** Breiten- und Überdeckungstests laufen lassen; zu lange Beschriftungen in `stil.css` lösen (etwa Knopf „Integration hinzufügen“).
- [ ] **Step 4:** Volle Prüfung lokal: pytest, Lint, `tools/dev.py pruefen`, Bilder ansehen (Seiten hell/dunkel, Handy, Mails).
- [ ] **Step 5: Commit** „Vollständigkeit und Browsertests auf Deutsch“.

### Task 10: CI, Bericht und Hinweis

**Files:** Create `tools/ci/hinweis.sh`, `tests/test_hinweis.py`; Modify `tools/ci/bericht.py`, `.github/workflows/build.yml`

- [ ] **Step 1:** `bericht.py` gibt den Abschnitt „Übersetzung“ aus (Zahlen, Tabellen mit höchstens `WB_BERICHT_ZEILEN` Zeilen, Mail-Hinweise).
- [ ] **Step 2:** `hinweis.sh` liest den Bericht: bei Hinweisen Issue mit Label `WB_HINWEIS_LABEL` (Vorgabe `uebersetzung`) anlegen oder ergänzen, Titel „Healthchecks <Version>: <n> Texte noch englisch“ (bei nur Mail-Hinweisen „Healthchecks <Version>: Hinweise zu den Mails“); ohne Hinweise offene Issues mit diesem Label schließen. Tests mit nachgebautem `gh`.
- [ ] **Step 3:** Workflow: `WB_HC_VERSION` für die Browserprüfung, Bericht als eigenes Artefakt, Job „Veröffentlichen“ lädt ihn und ruft `hinweis.sh` (Rechte `issues: write`).
- [ ] **Step 4:** Shellcheck-Tauglichkeit prüfen (keine `sudo … > datei`, Arrays gequotet), YAML laden, pytest. **Step 5: Commit** „CI: Abschnitt Übersetzung und Hinweis-Issue“.

### Task 11: Dokumentation und Fassung

**Files:** Modify `VERSION`, `CHANGELOG.md`, `README.md`, `docs/superpowers/specs/2026-10-05-healthchecks-werkbank-design.md`

- [ ] **Step 1:** `VERSION` 1.1.0; CHANGELOG-Abschnitt 1.1.0; README: Sprache und Katalog (Aufbau, Einträge, Inventur, Hinweis-Issue), Einstellungen `WB_SPRACHE`, `WB_KATALOG`, `WB_HINWEIS_LABEL`, Mail-Einstellungen, Zeile für eigene `local_settings.py`, Mails im Hausdesign, Bilder; Spec 1.0: Zeile „Texte“ verweist auf die Spec 1.1.
- [ ] **Step 2:** Texte auf Gegenüberstellungen und Zeitangaben prüfen. **Step 3: Commit** „Dokumentation und Fassung 1.1.0“.

### Task 12: Abschluss und Auslieferung

- [ ] **Step 1:** Volle Prüfung auf dem Zweig (pytest, Lint, Browser), dann superpowers:finishing-a-development-branch: Zweig `deutsch` per Fast-Forward nach `main`, löschen.
- [ ] **Step 2:** `git push origin main`, CI beobachten (`gh run watch` im Hintergrund), bei Rot Ursache beheben und neu pushen.
- [ ] **Step 3:** Veröffentlichung prüfen: `4.4-wb1.1.0` anonym abrufbar, amd64 und arm64; Bilder aus der CI ansehen; Hinweis-Issue erwartet keins.
- [ ] **Step 4:** docker-a1: Protokoll frisch lesen, Eintrag beginnen; zur nächsten Minute 37 den Lauf von `hc-werkbank-update` abwarten (lesend beobachten), danach prüfen: Image `4.4-wb1.1.0`, Sicherung angelegt, Status „OK“, Anmeldeseite deutsch, Check des Updates „up“; Eintrag abschließen.
- [ ] **Step 5:** Gedächtnis aktualisieren, Bericht an Mathias mit Bildern der Live-Seite.

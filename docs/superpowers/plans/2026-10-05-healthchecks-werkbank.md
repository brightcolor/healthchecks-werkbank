# healthchecks-werkbank Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** hc.bcsrv.de bekommt die Werkbank von bright color mit Onyx-Leiste links, und eine eigene Fassung des Images folgt jeder neuen Healthchecks-Version selbstständig über CI und ein Update-Skript auf docker-a1.

**Architecture:** Ein Aufsatz-Image `FROM healthchecks/healthchecks:<version>` setzt zwei Zeilen in `base.html` (Stylesheet und Leiste), leitet alle festen Farben der Stylesheets von Healthchecks auf Werkbank-Rollen um und bündelt alles in `static/bc/werkbank.css`. Die CI auf GitHub baut für arm64 und amd64, prüft im Browser und veröffentlicht nach ghcr.io. docker-a1 holt neue Fassungen per Timer, sichert vorher die SQLite-Datenbank und nimmt ein gescheitertes Update selbst zurück.

**Tech Stack:** Python 3 (nur Standardbibliothek für Bau-Skripte; pytest 9.1.1 für Tests), Django-Vorlagen von Healthchecks v4.4, CSS mit Tokens der Hausschrift, Vanilla-JavaScript, Playwright 1.63.0 (Chrome bzw. Edge), Bash, Docker Buildx, GitHub Actions, systemd.

**Spec:** `docs/superpowers/specs/2026-10-05-healthchecks-werkbank-design.md`

## Global Constraints

- Healthchecks-Basis: `healthchecks/healthchecks:v4.4` (Docker Hub, amd64/arm/arm64); `templates/base.html` ist in v4.3 und v4.4 gleich.
- Repo `brightcolor/healthchecks-werkbank`, öffentlich; Image `ghcr.io/brightcolor/healthchecks-werkbank`; Tags `<HC-Version>-wb<VERSION>` (unveränderlich), `<HC-Version>`, `latest`.
- Oberfläche englisch wie Healthchecks, auch eigene Texte (Leiste, Kopfzeile, Meldungen, Vorlesetexte). Einzige Ausnahme: „Moin.“ auf der Anmeldeseite. Skripte auf dem Server melden auf Deutsch mit echten Umlauten.
- Werkbank-Werte: Leiste 256 px Onyx, Kopfzeile 60 px, Karten 12 px, Felder und Knöpfe 8 px, Vierfarbband 4 px, Hauptknopf Gelb mit Tinte, Anton in Versalien für Seiten- und Kartentitel, Atkinson Hyperlegible für Text, IBM Plex Mono für Code und technische Werte, Fokus hell `#0a86ad`, dunkel Cyan, Textlinks hell `#b3146a`, dunkel Cyan.
- Hausampel: up Limette (als Symbol `--bc-ok-text`, im Dunkeln reine Limette), grace Gelb (`--bc-warn-text` bzw. Gelb), down Pink, started Cyan bzw. `--bc-focus`, paused und new leise.
- Kontrast: Schrift ab 4,8:1 (Tokenpaare), Browserlauf mindestens WCAG AA (4,5:1, groß 3:1), Symbole und Fokusringe ab 3:1, hell und dunkel.
- Breiten 320 bis 1440 px ohne Querscrollen; Leiste klappt unter 900 px weg; Listen unter 640 px zweizeilig.
- Nichts fest im Code: Schwellen, Pfade, Adressen, Namen sind Einstellungen mit Vorgabe an einer Stelle, mit Grenzen und verständlicher Fehlermeldung; Tests prüfen auch andere Werte.
- Fehlermeldungen nennen Ursache und nächsten Schritt; keine Zugangsdaten, Stacktraces oder internen Pfade in Meldungen für Nutzer.
- Keine Zeitangaben in Texten, Commits und Meldungen.
- Arbeit an docker-a1 und uptimekuma.bright-color.de wird im Serverprotokoll unter `C:\Users\brigh\Claude Workingdir\Serverprotokolle\` festgehalten (gezielte Einfügung in die frisch gelesene Datei, Uhrzeit vom System, ohne Zugangsdaten).
- Agenten nur nach Freigabe durch Mathias.
- Commits enden mit `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Lokal gibt es kein Docker. Docker-Bau, Update-Probe und arm64 laufen nur in der CI.

## Dateien

| Datei | Aufgabe |
|---|---|
| `werkbank/einbau.json` | Einbauplan: Anker, Zeilen, Platzhalter der Fassung |
| `werkbank/einbau.py` | setzt die Zeilen in `base.html`, schreibt die Fassung |
| `werkbank/farben.py` | zerlegt CSS, leitet feste Farben auf Rollen um, baut `werkbank.css`, Inventur und Vorschlag |
| `werkbank/farben.json` | Zuordnung fester Farben zu Rollen (erzeugt, dann verfeinert) |
| `werkbank/rollen.css` | eigene Rollen `--wb-*` (Tönungen, Schatten, Zustände) |
| `werkbank/variablen.css` | die 78 Variablen von Healthchecks auf Werkbank-Rollen |
| `werkbank/stil.css` | Stilschicht: Rahmen, Leiste, Kopfzeile, Bausteine, Handy, Anmeldung |
| `werkbank/templates/bc/leiste.html` | Leiste, Kopfzeile, Markenfläche der Anmeldung |
| `werkbank/static/bc/leiste.js` | Akkordeon, Projektliste, Handy-Leiste, Umschalter Hell/Dunkel |
| `vendor/hausschrift/` | Kopie aus dem Skill: Tokens, Schriften, Logo, `bc_check.py`, `check-contrast.js` |
| `tools/dev.py` | lokaler Aufbau ohne Docker, Musterdaten, Browserprüfung |
| `tests/musterdaten.py` | Musterkonten, Projekte, Checks in jedem Zustand, Integrationen, Pings |
| `tests/test_*.py` | Einheitstests (pytest) |
| `tests/e2e/*.mjs` | Browserprüfung (Playwright) |
| `tests/update/` | Update-Probe für die CI |
| `deploy/hc-werkbank-update` | Update-Skript für docker-a1 |
| `deploy/hc-werkbank-update.service`, `.timer`, `hc-werkbank-update.logrotate`, `hc-werkbank.conf.beispiel` | Einbindung auf dem Server |
| `Dockerfile`, `.dockerignore` | Aufsatz-Image |
| `tools/ci/*.sh`, `tools/ci/bericht.py` | Bausteine der CI |
| `.github/workflows/build.yml` | CI |

---

### Task 1: Grundlage, Hausschrift-Kopie und Testumgebung

**Files:**
- Create: `.gitignore`, `VERSION`, `CHANGELOG.md`, `LICENSE`, `UPSTREAM-LICENCE`, `tests/requirements.txt`
- Create: `vendor/hausschrift/QUELLE.md` und Kopien aus dem Skill
- Create: `.venv/` (nicht im Repo)

**Interfaces:**
- Produces: `vendor/hausschrift/assets/css/{bc-fonts.css,bc-tokens.css,bc-workbench.css}`, `vendor/hausschrift/assets/fonts/*`, `vendor/hausschrift/assets/logo/bc-logo-light-noclaim.svg`, `vendor/hausschrift/scripts/{bc_check.py,check-contrast.js}`; `.venv` mit pytest 9.1.1; `.upstream/v4.4/` (Quellcode von Healthchecks, liegt schon vor).

- [ ] **Step 1: Repo-Dateien anlegen**

`.gitignore`:
```
.upstream/
.venv/
node_modules/
artefakte/
fehler/
tests/e2e/ergebnisse/
__pycache__/
*.pyc
.pytest_cache/
```

`VERSION`:
```
1.0.0
```

`CHANGELOG.md`:
```markdown
# Änderungen

## 1.0.0 (unveröffentlicht)

- Werkbank für Healthchecks: Onyx-Leiste mit Projekten als Akkordeon, Kopfzeile mit Umschalter für Hell und Dunkel, Anmeldeseite mit Markenfläche.
- Farbableitung: Jede feste Farbe aus den Stylesheets von Healthchecks bekommt eine Werkbank-Rolle.
- CI folgt neuen Healthchecks-Versionen, prüft im Browser und veröffentlicht nach ghcr.io.
- Update-Skript für docker-a1 mit Sicherung der Datenbank und Rückweg.
```

`tests/requirements.txt`:
```
pytest==9.1.1
```

`.gitattributes` (Skripte laufen unter Linux; Windows darf keine CRLF-Zeilenenden einchecken):
```
* text=auto eol=lf
*.png binary
*.woff2 binary
*.svg text eol=lf
```

- [ ] **Step 2: Lizenzen kopieren**

```bash
cd "/c/Users/brigh/Claude Workingdir/healthchecks-werkbank"
cp ../postal-brightcolor/LICENSE LICENSE
cp .upstream/v4.4/LICENSE UPSTREAM-LICENCE
head -3 LICENSE UPSTREAM-LICENCE
```
Expected: `LICENSE` beginnt mit `BSD 2-Clause License` und `Copyright (c) 2026, bright color`; `UPSTREAM-LICENCE` ist die BSD-3-Lizenz von Healthchecks.

- [ ] **Step 3: Hausschrift kopieren**

```bash
cd "/c/Users/brigh/Claude Workingdir/healthchecks-werkbank"
SKILL="$HOME/.claude/skills/bright-color-design"
mkdir -p vendor/hausschrift/assets/css vendor/hausschrift/assets/fonts vendor/hausschrift/assets/logo vendor/hausschrift/scripts
cp "$SKILL"/assets/css/bc-fonts.css "$SKILL"/assets/css/bc-tokens.css "$SKILL"/assets/css/bc-workbench.css vendor/hausschrift/assets/css/
cp "$SKILL"/assets/fonts/* vendor/hausschrift/assets/fonts/
cp "$SKILL"/assets/logo/bc-logo-light-noclaim.svg vendor/hausschrift/assets/logo/
cp "$SKILL"/scripts/bc_check.py "$SKILL"/scripts/check-contrast.js vendor/hausschrift/scripts/
ls -R vendor/hausschrift
```
Expected: 3 CSS-Dateien, 7 Dateien unter `fonts/` (6 × woff2, `OFL.txt`), 1 Logo, 2 Skripte.

`vendor/hausschrift/QUELLE.md`:
```markdown
# Kopie aus der Hausschrift

Quelle: Skill `bright-color-design` (`~/.claude/skills/bright-color-design`), kopiert am 05.10.2026.

| Datei | Zweck hier |
|---|---|
| `assets/css/bc-fonts.css` | Schriften, erster Teil von `werkbank.css` |
| `assets/css/bc-tokens.css` | Tokens; `werkbank/farben.py` setzt sie auf `:root, body` und `body.dark` |
| `assets/css/bc-workbench.css` | Bausteine von Leiste und Kopfzeile, Teil von `werkbank.css` |
| `assets/fonts/` | Anton, Atkinson Hyperlegible, IBM Plex Mono mit `OFL.txt` |
| `assets/logo/bc-logo-light-noclaim.svg` | Logo in der Leiste und auf der Anmeldeseite |
| `scripts/bc_check.py` | Lint und Kontrastrechnung |
| `scripts/check-contrast.js` | Kontrastlauf im Browser |

Ändert sich die Hausschrift, werden diese Dateien neu aus dem Skill kopiert; danach muss die CI grün bleiben.

Die Logos sind Marken von bright color und von der Lizenz dieses Repos ausgenommen.
```

- [ ] **Step 4: Kopie prüfen**

```bash
python vendor/hausschrift/scripts/bc_check.py contrast "#111111" "#fed329"
python vendor/hausschrift/scripts/bc_check.py lint vendor/hausschrift/assets/css/bc-workbench.css --variant workbench
```
Expected:
```
#111111 auf #fed329: 13.10:1  AAA
1 Datei(en) geprüft: 0 Warnung(en), 0 Hinweis(e).
```

- [ ] **Step 5: Testumgebung**

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -q -r tests/requirements.txt
.venv/Scripts/python -m pytest --version
```
Expected: `pytest 9.1.1`. (Unter Linux heißt der Pfad `.venv/bin/python`.)

- [ ] **Step 6: Commit**

```bash
git add .gitignore .gitattributes VERSION CHANGELOG.md LICENSE UPSTREAM-LICENCE tests/requirements.txt vendor/
git commit -m "Grundlage: Lizenzen, Fassung 1.0.0, Kopie der Hausschrift

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Einbau in die Vorlage

**Files:**
- Create: `werkbank/einbau.json`, `werkbank/einbau.py`, `werkbank/templates/bc/leiste.html` (Grundfassung, Inhalt folgt in Task 6)
- Test: `tests/test_einbau.py`

**Interfaces:**
- Produces: `einbau.Einfuegung(anker: str, zeile: str)`, `einbau.Plan(vorlage: str, einfuegungen: tuple[Einfuegung, ...], platzhalter: str, fassung_in: tuple[str, ...])`, `einbau.lade_plan(pfad: Path) -> Plan`, `einbau.einbauen(wurzel: Path, plan: Plan, fassung: str) -> list[str]`, `einbau.EinbauFehler`, `einbau.PLAN_VORGABE: Path`. Kommandozeile: `python werkbank/einbau.py --wurzel DIR --fassung TAG [--plan DATEI]`, Rückgabe 0 oder 1.

- [ ] **Step 1: Tests schreiben**

`tests/test_einbau.py`:
```python
import sys
from pathlib import Path

import pytest

WURZEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WURZEL / "werkbank"))
import einbau  # noqa: E402

PLATZ = "@@WERKBANK_FASSUNG@@"
BASIS = """<!DOCTYPE html>{% load compress static hc_extras %}
<html><head>
{% compress css %}<link rel="stylesheet" href="x.css">{% endcompress %}
</head>
<body>
    <nav class="navbar navbar-default">menu</nav>
</body></html>
"""
LEISTE = '<nav class="bc-rail">Werkbank ' + PLATZ + "</nav>\n"


def plan(**anders):
    daten = {
        "vorlage": "templates/base.html",
        "einfuegungen": (
            einbau.Einfuegung("</head>", f'<link rel="stylesheet" href="w.css?v={PLATZ}">'),
            einbau.Einfuegung('<nav class="navbar navbar-default">', '{% include "bc/leiste.html" %}'),
        ),
        "platzhalter": PLATZ,
        "fassung_in": ("templates/base.html", "templates/bc/leiste.html"),
    }
    daten.update(anders)
    return einbau.Plan(**daten)


@pytest.fixture
def wurzel(tmp_path):
    (tmp_path / "templates" / "bc").mkdir(parents=True)
    (tmp_path / "templates" / "base.html").write_text(BASIS, encoding="utf-8")
    (tmp_path / "templates" / "bc" / "leiste.html").write_text(LEISTE, encoding="utf-8")
    return tmp_path


def test_setzt_zeilen_direkt_vor_die_anker(wurzel):
    einbau.einbauen(wurzel, plan(), "4.4-wb1.0.0")
    text = (wurzel / "templates/base.html").read_text(encoding="utf-8")
    assert '<link rel="stylesheet" href="w.css?v=4.4-wb1.0.0">\n</head>' in text
    assert '{% include "bc/leiste.html" %}\n<nav class="navbar navbar-default">' in text


def test_setzt_fassung_in_alle_genannten_dateien(wurzel):
    geaendert = einbau.einbauen(wurzel, plan(), "4.4-wb1.0.0")
    assert geaendert == ["templates/base.html", "templates/bc/leiste.html"]
    assert "Werkbank 4.4-wb1.0.0" in (wurzel / "templates/bc/leiste.html").read_text(encoding="utf-8")


def test_fehlender_anker_bricht_ab_und_nennt_ihn(wurzel):
    p = plan(einfuegungen=(einbau.Einfuegung("<footer>", "x"),))
    with pytest.raises(einbau.EinbauFehler, match=r"'<footer>' steht 0-mal in templates/base.html"):
        einbau.einbauen(wurzel, p, "4.4-wb1.0.0")


def test_doppelter_anker_bricht_ab(wurzel):
    (wurzel / "templates/base.html").write_text(BASIS + "</head>", encoding="utf-8")
    with pytest.raises(einbau.EinbauFehler, match="steht 2-mal"):
        einbau.einbauen(wurzel, plan(), "4.4-wb1.0.0")


def test_zweiter_lauf_bricht_ab(wurzel):
    einbau.einbauen(wurzel, plan(), "4.4-wb1.0.0")
    (wurzel / "templates/bc/leiste.html").write_text(LEISTE, encoding="utf-8")
    with pytest.raises(einbau.EinbauFehler, match="bereits"):
        einbau.einbauen(wurzel, plan(), "4.4-wb1.0.1")


def test_bei_fehler_bleibt_jede_datei_unveraendert(wurzel):
    (wurzel / "templates/bc/leiste.html").write_text("ohne Platzhalter", encoding="utf-8")
    with pytest.raises(einbau.EinbauFehler, match="fehlt der Platzhalter"):
        einbau.einbauen(wurzel, plan(), "4.4-wb1.0.0")
    assert (wurzel / "templates/base.html").read_text(encoding="utf-8") == BASIS


@pytest.mark.parametrize("fassung", ["", "4.4 wb1", "-4.4", "ä1", "x" * 65])
def test_ungueltige_fassung(wurzel, fassung):
    with pytest.raises(einbau.EinbauFehler, match="taugt nicht als Image-Tag"):
        einbau.einbauen(wurzel, plan(), fassung)


def test_anderer_plan_mit_anderen_ankern(wurzel):
    p = plan(
        einfuegungen=(einbau.Einfuegung("<body>", "<!-- vorn -->"),),
        platzhalter="%%F%%",
        fassung_in=("templates/bc/leiste.html",),
    )
    (wurzel / "templates/bc/leiste.html").write_text("F=%%F%%", encoding="utf-8")
    einbau.einbauen(wurzel, p, "9.9-wb2.0.0")
    assert "<!-- vorn -->\n<body>" in (wurzel / "templates/base.html").read_text(encoding="utf-8")
    assert (wurzel / "templates/bc/leiste.html").read_text(encoding="utf-8") == "F=9.9-wb2.0.0"


def test_lade_plan_meldet_kaputtes_json(tmp_path):
    datei = tmp_path / "plan.json"
    datei.write_text("{", encoding="utf-8")
    with pytest.raises(einbau.EinbauFehler, match="kein gültiges JSON"):
        einbau.lade_plan(datei)


def test_lade_plan_meldet_fehlende_felder(tmp_path):
    datei = tmp_path / "plan.json"
    datei.write_text('{"vorlage": "x"}', encoding="utf-8")
    with pytest.raises(einbau.EinbauFehler, match="braucht die Felder"):
        einbau.lade_plan(datei)


def test_mitgelieferter_plan_passt_auf_die_echte_vorlage(tmp_path):
    vorlagen = sorted((WURZEL / ".upstream").glob("v*/templates/base.html"))
    if not vorlagen:
        pytest.skip("Keine Vorlage von Healthchecks unter .upstream/; tools/dev.py vorbereiten legt sie an.")
    (tmp_path / "templates" / "bc").mkdir(parents=True)
    (tmp_path / "templates" / "base.html").write_text(vorlagen[-1].read_text(encoding="utf-8"), encoding="utf-8")
    (tmp_path / "templates" / "bc" / "leiste.html").write_text(PLATZ, encoding="utf-8")
    einbau.einbauen(tmp_path, einbau.lade_plan(einbau.PLAN_VORGABE), "4.4-wb1.0.0")
    text = (tmp_path / "templates" / "base.html").read_text(encoding="utf-8")
    assert "{% static 'bc/werkbank.css' %}?v=4.4-wb1.0.0" in text
    assert text.index('{% include "bc/leiste.html" %}') < text.index('<nav class="navbar navbar-default">')


def test_mitgelieferte_leiste_traegt_den_platzhalter():
    text = (WURZEL / "werkbank/templates/bc/leiste.html").read_text(encoding="utf-8")
    assert PLATZ in text


def test_kommandozeile_meldet_fehler_mit_exit_1(wurzel, capsys):
    rc = einbau.main(["--wurzel", str(wurzel), "--fassung", "kaputte fassung"])
    assert rc == 1
    assert "Abbruch:" in capsys.readouterr().err
```

- [ ] **Step 2: Tests laufen lassen, sie scheitern**

Run: `.venv/Scripts/python -m pytest tests/test_einbau.py -q`
Expected: FAIL mit `ModuleNotFoundError: No module named 'einbau'`.

- [ ] **Step 3: Einbauplan, Grundfassung der Leiste und Skript schreiben**

`werkbank/einbau.json`:
```json
{
  "_info": "Einbauplan für Healthchecks. Jede Zeile kommt direkt vor ihren Anker; jeder Anker muss in der Vorlage genau einmal vorkommen. Der Platzhalter wird in den Dateien aus fassung_in durch die Fassung des Images ersetzt.",
  "vorlage": "templates/base.html",
  "einfuegungen": [
    {
      "anker": "</head>",
      "zeile": "<link rel=\"stylesheet\" href=\"{% static 'bc/werkbank.css' %}?v=@@WERKBANK_FASSUNG@@\" type=\"text/css\">"
    },
    {
      "anker": "<nav class=\"navbar navbar-default\">",
      "zeile": "{% include \"bc/leiste.html\" %}"
    }
  ],
  "platzhalter": "@@WERKBANK_FASSUNG@@",
  "fassung_in": ["templates/base.html", "templates/bc/leiste.html"]
}
```

`werkbank/templates/bc/leiste.html` (Grundfassung; Task 6 ersetzt den Inhalt):
```django
{% comment %}Werkbank-Leiste von healthchecks-werkbank, Fassung @@WERKBANK_FASSUNG@@.{% endcomment %}
```

`werkbank/einbau.py`:
```python
#!/usr/bin/env python3
"""Setzt die Werkbank in die Vorlagen von Healthchecks ein.

Liest den Einbauplan (Vorgabe: einbau.json neben diesem Skript), setzt jede
Zeile direkt vor ihren Anker und ersetzt danach den Platzhalter für die
Fassung. Erst wenn jede Prüfung bestanden ist, schreibt das Skript; bei einem
Fehler bleibt jede Datei, wie sie war.

Nur Standardbibliothek: Das Skript läuft beim Bau im Image von Healthchecks.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

PLAN_VORGABE = Path(__file__).resolve().parent / "einbau.json"
FASSUNG_MUSTER = re.compile(r"[0-9A-Za-z][0-9A-Za-z._-]{0,63}")


class EinbauFehler(Exception):
    """Ein Problem, das der Betreiber beheben kann; die Meldung sagt wie."""


@dataclass(frozen=True)
class Einfuegung:
    anker: str
    zeile: str


@dataclass(frozen=True)
class Plan:
    vorlage: str
    einfuegungen: tuple[Einfuegung, ...]
    platzhalter: str
    fassung_in: tuple[str, ...]


def lade_plan(pfad: Path) -> Plan:
    try:
        daten = json.loads(pfad.read_text(encoding="utf-8"))
    except FileNotFoundError as err:
        raise EinbauFehler(f"Der Einbauplan {pfad} fehlt. Den Pfad mit --plan prüfen.") from err
    except json.JSONDecodeError as err:
        raise EinbauFehler(
            f"{pfad} ist kein gültiges JSON (Zeile {err.lineno}, Spalte {err.colno}: {err.msg})."
        ) from err
    try:
        einfuegungen = tuple(Einfuegung(e["anker"], e["zeile"]) for e in daten["einfuegungen"])
        plan = Plan(daten["vorlage"], einfuegungen, daten["platzhalter"], tuple(daten["fassung_in"]))
    except (KeyError, TypeError) as err:
        raise EinbauFehler(
            f"{pfad} braucht die Felder vorlage, einfuegungen (je anker und zeile), platzhalter "
            f"und fassung_in. Es fehlt: {err}."
        ) from err
    if not plan.einfuegungen:
        raise EinbauFehler(f"{pfad} nennt keine Einfügung. Mindestens eine Zeile mit Anker eintragen.")
    if not plan.platzhalter.strip():
        raise EinbauFehler(
            f"Der Platzhalter in {pfad} ist leer. Einen eindeutigen Text wie @@WERKBANK_FASSUNG@@ eintragen."
        )
    return plan


def pruefe_fassung(fassung: str) -> None:
    if not FASSUNG_MUSTER.fullmatch(fassung):
        raise EinbauFehler(
            f"Die Fassung {fassung!r} taugt nicht als Image-Tag. Erlaubt sind 1 bis 64 Zeichen aus "
            "Buchstaben, Ziffern, Punkt, Minus und Unterstrich, am Anfang ein Buchstabe oder eine "
            "Ziffer, etwa 4.4-wb1.0.0."
        )


def einfuegen(text: str, einfuegungen: tuple[Einfuegung, ...], platzhalter: str, datei: str) -> str:
    for e in einfuegungen:
        anzahl = text.count(e.anker)
        if anzahl != 1:
            raise EinbauFehler(
                f"Der Anker {e.anker!r} steht {anzahl}-mal in {datei}, erwartet ist genau einmal. "
                "Healthchecks hat die Vorlage geändert: werkbank/einbau.json an die neue Fassung anpassen."
            )
        kern = e.zeile.split(platzhalter)[0]
        if kern and kern in text:
            raise EinbauFehler(
                f"{datei} enthält die Zeile {e.zeile!r} bereits. Der Einbau läuft nur auf der "
                "unveränderten Vorlage aus dem Basis-Image."
            )
    for e in einfuegungen:
        text = text.replace(e.anker, f"{e.zeile}\n{e.anker}", 1)
    return text


def setze_fassung(text: str, platzhalter: str, fassung: str, datei: str) -> str:
    if platzhalter not in text:
        raise EinbauFehler(
            f"In {datei} fehlt der Platzhalter {platzhalter}. Die Datei gehört zur Werkbank und muss ihn enthalten."
        )
    return text.replace(platzhalter, fassung)


def einbauen(wurzel: Path, plan: Plan, fassung: str) -> list[str]:
    """Baut ein und gibt die geänderten Dateien relativ zur Wurzel zurück."""
    pruefe_fassung(fassung)
    neu: dict[str, str] = {}

    def lies(rel: str) -> str:
        if rel in neu:
            return neu[rel]
        pfad = wurzel / rel
        try:
            return pfad.read_text(encoding="utf-8")
        except FileNotFoundError as err:
            raise EinbauFehler(f"{pfad} fehlt. Ist --wurzel der Ordner von Healthchecks?") from err

    neu[plan.vorlage] = einfuegen(lies(plan.vorlage), plan.einfuegungen, plan.platzhalter, plan.vorlage)
    for rel in plan.fassung_in:
        neu[rel] = setze_fassung(lies(rel), plan.platzhalter, fassung, rel)
    for rel, text in neu.items():
        (wurzel / rel).write_text(text, encoding="utf-8")
    return sorted(neu)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Setzt die Werkbank in die Vorlagen von Healthchecks ein.")
    p.add_argument("--wurzel", required=True, help="Ordner von Healthchecks, etwa /opt/healthchecks")
    p.add_argument("--fassung", required=True, help="Fassung des Images, etwa 4.4-wb1.0.0")
    p.add_argument("--plan", default=str(PLAN_VORGABE), help="Einbauplan (Vorgabe %(default)s)")
    args = p.parse_args(argv)
    try:
        geaendert = einbauen(Path(args.wurzel), lade_plan(Path(args.plan)), args.fassung)
    except EinbauFehler as err:
        print(f"Abbruch: {err}", file=sys.stderr)
        return 1
    print(f"Werkbank eingesetzt (Fassung {args.fassung}): {', '.join(geaendert)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Tests laufen lassen, sie bestehen**

Run: `.venv/Scripts/python -m pytest tests/test_einbau.py -q`
Expected: `17 passed` (der Test mit der echten Vorlage nutzt `.upstream/v4.4`).

- [ ] **Step 5: Commit**

```bash
git add werkbank/einbau.json werkbank/einbau.py werkbank/templates/bc/leiste.html tests/test_einbau.py
git commit -m "Einbau: Stylesheet und Leiste per Anker in base.html

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Farbableitung, Kern

**Files:**
- Create: `werkbank/farben.py` (Kern; Task 4 ergänzt Bündel und Kommandozeile)
- Test: `tests/test_farben.py`

**Interfaces:**
- Produces:
  - `farben.einstellung(name: str) -> str`, `farben.VORGABEN: dict[str, str]`, `farben.FarbFehler`
  - `farben.parse_css(css: str) -> list`, `farben.walk_rules(nodes)`, `farben.parse_decls(body: str) -> list[Decl]`, `farben.split_top(text, sep) -> list[str]`, Datenklassen `Decl(prop, value, important)`, `Rule(selector, decls)`, `Block(prelude, children)`, `AtDecls(prelude)`
  - `farben.normalise(farbe: str) -> str` (`#rrggbb`, `#rrggbbaa` oder `rgba(r,g,b,a)`), `farben.rgba(farbe) -> tuple[int, int, int, float]`, `farben.colours_in(wert) -> list[str]`, `farben.COLOUR_PROPS: dict[str, str]`, `farben.KEEP: set[str]`
  - `farben.auto_rolle(farbe: str, art: str, dunkel: bool = False) -> str`
  - `farben.kontext_rolle(farbe: str, flaeche: str | None) -> str | None`
  - `farben.Zuordnung(daten: dict)`, `Zuordnung.lade(pfad: Path)`, `Zuordnung.rolle(farbe, art, selektor="", dunkel=False, flaeche=None) -> tuple[str, bool]` (zweiter Wert: automatisch gewählt)
  - `farben.ist_dunkel(selektor: str, merkmal: str) -> bool`
  - `farben.Fund(farbe, art, eigenschaft, selektor, rolle, datei="")`, `farben.Ableitung(zeilen: list[str], funde: list[Fund], deklarationen: int)`
  - `farben.ableiten(css: str, zuordnung: Zuordnung, datei: str, dunkel_merkmal: str) -> Ableitung`

- [ ] **Step 1: Tests schreiben**

`tests/test_farben.py`:
```python
import sys
from pathlib import Path

import pytest

WURZEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WURZEL / "werkbank"))
import farben  # noqa: E402

LEER = farben.Zuordnung({})


def ableiten(css, zuordnung=LEER, merkmal="body.dark"):
    return farben.ableiten(css, zuordnung, "x.css", merkmal)


def text(css, zuordnung=LEER):
    return "\n".join(ableiten(css, zuordnung).zeilen)


@pytest.mark.parametrize("roh, erwartet", [
    ("#FFF", "#ffffff"),
    ("#22BC66", "#22bc66"),
    ("white", "#ffffff"),
    ("rgb(34, 188, 102)", "#22bc66"),
    ("rgba(0, 0, 0, 0.075)", "rgba(0,0,0,0.075)"),
    ("rgba(0,0,0,1)", "#000000"),
    ("#aaaaaa99", "#aaaaaa99"),
    ("#aaaaaaff", "#aaaaaa"),
    ("hsl(0, 0%, 100%)", "#ffffff"),
    ("hsl(120, 100%, 25%)", "#008000"),
])
def test_normalise(roh, erwartet):
    assert farben.normalise(roh) == erwartet


@pytest.mark.parametrize("farbe, art, dunkel, rolle", [
    ("#22bc66", "background", False, "var(--bc-lime)"),
    ("#dff0d8", "background", False, "var(--wb-ok-tint)"),
    ("#d9534f", "background", False, "var(--bc-pink)"),
    ("#a94442", "text", False, "var(--bc-bad-text)"),
    ("#f0ad4e", "background", False, "var(--bc-yellow)"),
    ("#8a6d3b", "text", False, "var(--bc-warn-text)"),
    ("#5bc0de", "background", False, "var(--bc-cyan)"),
    ("#0091ea", "border", False, "var(--bc-focus)"),
    ("#ffffff", "background", False, "var(--bc-surface)"),
    ("#ffffff", "text", False, "var(--bc-white)"),
    ("#f5f5f5", "background", False, "var(--bc-head)"),
    ("#dddddd", "border", False, "var(--bc-rule)"),
    ("#333333", "text", False, "var(--bc-text)"),
    ("#999999", "text", False, "var(--bc-text-quiet)"),
    ("#000000", "background", False, "var(--bc-ink)"),
    ("rgba(0,0,0,0.075)", "shadow", False, "var(--wb-schatten)"),
    ("rgba(102,175,233,0.2)", "shadow", False, "var(--wb-fokus-hof)"),
    ("rgba(0,0,0,0.15)", "border", False, "var(--bc-rule)"),
    ("rgba(0,0,0,0)", "border", False, "transparent"),
    ("#f8f8f2", "text", True, "var(--bc-text-loud)"),
    ("#29292c", "background", True, "var(--bc-hover)"),
    ("#ae81ff", "text", True, "var(--bc-link)"),
])
def test_auto_rolle(farbe, art, dunkel, rolle):
    assert farben.auto_rolle(farbe, art, dunkel) == rolle


def test_helle_schrift_auf_kraeftiger_flaeche_wird_tinte():
    zeilen = text(".btn-primary { color: #fff; background-color: #22bc66; border-color: #1ea65a }")
    assert "color: var(--bc-ink);" in zeilen
    assert "background-color: var(--bc-lime);" in zeilen
    assert "border-color: var(--bc-ok-deep);" in zeilen


def test_weisse_schrift_auf_pink_bleibt_weiss():
    assert "color: var(--bc-white);" in text(".btn-danger { color: #fff; background-color: #d9534f }")


def test_ausnahme_je_selektor_geht_vor():
    z = farben.Zuordnung({"selektoren": {".btn-primary": {"text": {"#fff": "var(--bc-text-loud)"}}}})
    assert "color: var(--bc-text-loud);" in text(".btn-primary { color: #fff; background-color: #22bc66 }", z)


def test_eintrag_geht_vor_automatik_und_automatik_steht_im_bericht():
    z = farben.Zuordnung({"farben": {"#22bc66": {"text": "var(--bc-text)"}}})
    erg = ableiten(".a { color: #22bc66 } .b { color: #123456 }", z)
    assert ".a {\n\tcolor: var(--bc-text);\n}" in "\n".join(erg.zeilen)
    assert [f.farbe for f in erg.funde] == ["#123456"]
    assert erg.funde[0].datei == "x.css"
    assert erg.funde[0].rolle == "var(--bc-link)"


def test_dunkle_regeln_nutzen_ihren_eigenen_teil():
    z = farben.Zuordnung({"farben": {"#333333": {"text": "var(--bc-text)"}},
                          "farben_dunkel": {"#333333": {"text": "var(--bc-text-quiet)"}}})
    zeilen = text(".a { color: #333 } body.dark .a { color: #333 }", z)
    assert ".a {\n\tcolor: var(--bc-text);\n}" in zeilen
    assert "body.dark .a {\n\tcolor: var(--bc-text-quiet);\n}" in zeilen


def test_var_werte_und_reihenfolge_bleiben():
    zeilen = text(".x { color: #333 } .x { color: var(--text-color) }")
    assert zeilen.index("var(--bc-text)") < zeilen.index("var(--text-color)")


def test_farbwoerter_in_var_namen_zaehlen_nicht():
    erg = ableiten(".x { color: var(--btn-red) }")
    assert erg.funde == []
    assert "color: var(--btn-red);" in "\n".join(erg.zeilen)


def test_kurzformen_werden_langformen():
    zeilen = text(".x { border: 1px solid #ddd; background: #fff url(a.png) no-repeat; outline: 0 }")
    assert "border-color: var(--bc-rule);" in zeilen
    assert "background-color: var(--bc-surface);" in zeilen
    assert "url(" not in zeilen
    assert "outline" not in zeilen


def test_verlauf_behaelt_bildschichten():
    zeilen = text(".x { background-image: url(a.png), linear-gradient(#fff, #f5f5f5) }")
    assert "background-image: url(a.png), linear-gradient(var(--bc-surface), var(--bc-head));" in zeilen


def test_important_media_und_font_face():
    zeilen = text("@charset \"UTF-8\"; @font-face { font-family: x; src: url(a.woff2) } "
                  "@media (min-width: 768px) { .x { color: #fff !important } }")
    assert "@media (min-width: 768px) {" in zeilen
    assert "\t\tcolor: var(--bc-white) !important;" in zeilen
    assert "font-face" not in zeilen


def test_keyword_werte_kommen_mit():
    zeilen = text(".x { color: inherit; box-shadow: none; background: none }")
    assert "color: inherit;" in zeilen
    assert "box-shadow: none;" in zeilen
    assert "background-color: transparent;" in zeilen
    assert "background-image: none;" in zeilen


def test_dunkle_regeln_erkennen():
    assert farben.ist_dunkel("body.dark .highlight .k", "body.dark")
    assert not farben.ist_dunkel(".highlight .k", "body.dark")
    assert not farben.ist_dunkel("body.dark .a, .b", "body.dark")
    assert not farben.ist_dunkel("body.darker .a", "body.dark")
    assert farben.ist_dunkel("html.nacht .a", "html.nacht")


def test_zuordnung_meldet_kaputtes_json(tmp_path):
    datei = tmp_path / "farben.json"
    datei.write_text("{", encoding="utf-8")
    with pytest.raises(farben.FarbFehler, match="kein gültiges JSON"):
        farben.Zuordnung.lade(datei)


def test_unlesbare_farbe_meldet_sich():
    with pytest.raises(farben.FarbFehler, match="kann farben.py nicht lesen"):
        farben.rgba("lab(50% 40 59)")
```

- [ ] **Step 2: Tests laufen lassen, sie scheitern**

Run: `.venv/Scripts/python -m pytest tests/test_farben.py -q`
Expected: FAIL mit `ModuleNotFoundError: No module named 'farben'`.

- [ ] **Step 3: Kern schreiben**

`werkbank/farben.py`:
```python
#!/usr/bin/env python3
"""Baut werkbank.css: die Werkbank von bright color für Healthchecks.

Die festen Farben aus den Stylesheets von Healthchecks werden auf
Werkbank-Rollen umgeleitet. Jede Deklaration einer Farbeigenschaft kommt mit
demselben Selektor wieder; feste Farben werden zu Rollen wie var(--bc-text),
Werte mit var() und Schlüsselwörter kommen unverändert mit. So bleibt die
Reihenfolge der Kaskade von Healthchecks erhalten.

Zuordnung (werkbank/farben.json), in dieser Reihenfolge:
  1. selektoren: Ausnahmen je Selektor und Art
  2. Fläche derselben Regel: neutrale Schrift auf kräftiger Fläche
  3. farben (helle Regeln) und farben_dunkel (Regeln unter body.dark)
  4. automatisch nach Farbton und Helligkeit; landet im Bericht

Befehle:
  farben.py bauen --wurzel DIR --hausschrift DIR --werkbank DIR --fassung TAG [--bericht DATEI]
  farben.py inventur --wurzel DIR
  farben.py vorschlag --wurzel DIR [--behalte farben.json]

Grundlage: tools/derive.py aus postal-brightcolor. Nur Standardbibliothek.
"""

from __future__ import annotations

import argparse
import colorsys
import json
import os
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

# Jede Einstellung mit ihrer Vorgabe an einer Stelle; Umgebungsvariablen
# gleichen Namens gehen vor.
VORGABEN = {
    "WB_BASIS_VORLAGE": "templates/base.html",
    "WB_STATIC": "static",
    "WB_VARIABLEN_CSS": "css/variables.css",
    "WB_ZIEL": "bc/werkbank.css",
    "WB_ZIEL_FARBEN": "bc/farben.css",
    "WB_DUNKEL_SELEKTOR": "body.dark",
}


def einstellung(name: str) -> str:
    return os.environ.get(name, VORGABEN[name])


class FarbFehler(Exception):
    """Ein Problem, das der Betreiber beheben kann; die Meldung sagt wie."""


# --- CSS zerlegen (aus tools/derive.py von postal-brightcolor) -----------------


@dataclass
class Decl:
    prop: str
    value: str
    important: bool = False


@dataclass
class Rule:
    selector: str
    decls: list[Decl]


@dataclass
class Block:
    """Eine At-Regel mit verschachtelten Regeln, etwa @media."""

    prelude: str
    children: list = field(default_factory=list)


@dataclass
class AtDecls:
    """Eine At-Regel mit Deklarationen, etwa @font-face; bleibt außen vor."""

    prelude: str


def strip_comments(css: str) -> str:
    out = []
    i = 0
    quote = ""
    while i < len(css):
        c = css[i]
        if quote:
            out.append(c)
            if c == "\\" and i + 1 < len(css):
                out.append(css[i + 1])
                i += 2
                continue
            if c == quote:
                quote = ""
        elif c in "\"'":
            quote = c
            out.append(c)
        elif css.startswith("/*", i):
            end = css.find("*/", i + 2)
            i = len(css) if end < 0 else end + 2
            continue
        else:
            out.append(c)
        i += 1
    return "".join(out)


def split_top(text: str, sep: str) -> list[str]:
    """Teilt an sep außerhalb von Anführungszeichen und Klammern."""
    parts, depth, quote, start = [], 0, "", 0
    i = 0
    while i < len(text):
        c = text[i]
        if quote:
            if c == "\\":
                i += 2
                continue
            if c == quote:
                quote = ""
        elif c in "\"'":
            quote = c
        elif c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
        elif c == sep and depth == 0:
            parts.append(text[start:i])
            start = i + 1
        i += 1
    parts.append(text[start:])
    return parts


def find_block_end(css: str, open_at: int) -> int:
    depth, quote, i = 0, "", open_at
    while i < len(css):
        c = css[i]
        if quote:
            if c == "\\":
                i += 2
                continue
            if c == quote:
                quote = ""
        elif c in "\"'":
            quote = c
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    raise FarbFehler(
        "Ein Stylesheet endet mitten in einer Regel. Die Datei im Basis-Image ist wohl unvollständig; "
        "den Bau neu starten."
    )


def parse_decls(body: str) -> list[Decl]:
    decls = []
    for chunk in split_top(body, ";"):
        if ":" not in chunk:
            continue
        prop, value = chunk.split(":", 1)
        prop, value = prop.strip().lower(), value.strip()
        if not prop or not value:
            continue
        important = False
        m = re.search(r"\s*!\s*important\s*$", value, re.I)
        if m:
            important = True
            value = value[: m.start()].strip()
        decls.append(Decl(prop, value, important))
    return decls


NESTING_AT_RULES = ("@media", "@supports", "@document", "@layer", "@container")


def parse_css(css: str) -> list:
    css = strip_comments(css)
    nodes: list = []
    i = 0
    while i < len(css):
        while i < len(css) and css[i] in " \t\r\n;":
            i += 1
        if i >= len(css):
            break
        brace = css.find("{", i)
        if brace < 0:
            break
        prelude = css[i:brace]
        semikolon = prelude.rfind(";")
        if semikolon >= 0 and prelude.lstrip().startswith("@"):
            # Anweisungen ohne Block wie @charset oder @import überspringen.
            i += semikolon + 1
            continue
        prelude = prelude.strip()
        end = find_block_end(css, brace)
        body = css[brace + 1 : end]
        lower = prelude.lower()
        if lower.startswith(NESTING_AT_RULES):
            nodes.append(Block(prelude, parse_css(body)))
        elif lower.startswith("@"):
            nodes.append(AtDecls(prelude))
        else:
            nodes.append(Rule(prelude, parse_decls(body)))
        i = end + 1
    return nodes


def walk_rules(nodes: list):
    for node in nodes:
        if isinstance(node, Rule):
            yield node
        elif isinstance(node, Block):
            yield from walk_rules(node.children)


# --- Farben ---------------------------------------------------------------------

NAMED = {"white": "#ffffff", "black": "#000000", "green": "#008000", "red": "#ff0000", "blue": "#0000ff",
         "grey": "#808080", "gray": "#808080", "orange": "#ffa500", "yellow": "#ffff00", "silver": "#c0c0c0"}
KEEP = {"transparent", "inherit", "initial", "unset", "revert", "currentcolor", "none"}
COLOUR_RE = re.compile(
    r"#[0-9a-fA-F]{3,8}\b|rgba?\([^)]*\)|hsla?\([^)]*\)|\b(?:" + "|".join(NAMED) + r")\b", re.I
)
# url(...) und var(...) gehören nicht zur Farbe einer Deklaration.
SCHUTZ_RE = re.compile(r"url\([^)]*\)|var\((?:[^()]|\([^()]*\))*\)", re.I)

COLOUR_PROPS = {
    "color": "text", "-webkit-text-fill-color": "text", "caret-color": "text",
    "background": "background", "background-color": "background", "background-image": "background",
    "border": "border", "border-color": "border", "border-top": "border", "border-right": "border",
    "border-bottom": "border", "border-left": "border", "border-top-color": "border",
    "border-right-color": "border", "border-bottom-color": "border", "border-left-color": "border",
    "outline": "border", "outline-color": "border", "column-rule": "border",
    "box-shadow": "shadow", "text-shadow": "shadow",
    "fill": "graphic", "stroke": "graphic",
}


def colours_in(value: str) -> list[str]:
    return [c for c in COLOUR_RE.findall(SCHUTZ_RE.sub(" ", value)) if c.lower() not in KEEP]


def normalise(colour: str) -> str:
    c = colour.strip().lower()
    if c in NAMED:
        return NAMED[c]
    if c.startswith("#"):
        h = c[1:]
        if len(h) in (3, 4):
            h = "".join(ch * 2 for ch in h)
        if len(h) == 8 and h.endswith("ff"):
            h = h[:6]
        return "#" + h
    m = re.match(r"(rgba?|hsla?)\(([^)]*)\)", c)
    if not m:
        return c
    teile = [p for p in re.split(r"[,\s/]+", m.group(2).strip()) if p]
    if m.group(1).startswith("hsl"):
        h = float(teile[0].removesuffix("deg")) / 360
        s = float(teile[1].rstrip("%")) / 100
        l = float(teile[2].rstrip("%")) / 100
        r, g, b = (round(x * 255) for x in colorsys.hls_to_rgb(h, l, s))
    else:
        r, g, b = (round(float(p.rstrip("%")) * (2.55 if p.endswith("%") else 1)) for p in teile[:3])
    a = teile[3] if len(teile) > 3 else "1"
    alpha = float(a.rstrip("%")) / (100 if a.endswith("%") else 1)
    if alpha >= 1:
        return "#%02x%02x%02x" % (r, g, b)
    return "rgba(%d,%d,%d,%s)" % (r, g, b, "%g" % alpha)


def rgba(farbe: str) -> tuple[int, int, int, float]:
    c = normalise(farbe)
    if c.startswith("#") and len(c) in (7, 9):
        alpha = int(c[7:9], 16) / 255 if len(c) == 9 else 1.0
        return int(c[1:3], 16), int(c[3:5], 16), int(c[5:7], 16), alpha
    m = re.fullmatch(r"rgba\((\d+),(\d+),(\d+),([\d.]+)\)", c)
    if m:
        return int(m.group(1)), int(m.group(2)), int(m.group(3)), float(m.group(4))
    raise FarbFehler(
        f"Die Farbe {farbe!r} kann farben.py nicht lesen. Als Hex-, rgb()- oder hsl()-Wert schreiben "
        "oder die Stelle in farben.json unter selektoren eintragen."
    )


# --- Rollen ---------------------------------------------------------------------

# Je Farbfamilie: Schrift, Fläche (blass, kräftig), Rand (blass, kräftig).
FAMILIEN = {
    "bad": {"text": "var(--bc-bad-text)",
            "background": ("var(--bc-bad-tint)", "var(--bc-pink)"),
            "border": ("var(--wb-bad-rand)", "var(--bc-bad-deep)")},
    "warn": {"text": "var(--bc-warn-text)",
             "background": ("var(--wb-warn-tint)", "var(--bc-yellow)"),
             "border": ("var(--wb-warn-rand)", "var(--bc-primary-deep)")},
    "ok": {"text": "var(--bc-ok-text)",
           "background": ("var(--wb-ok-tint)", "var(--bc-lime)"),
           "border": ("var(--wb-ok-rand)", "var(--bc-ok-deep)")},
    "info": {"text": "var(--bc-link)",
             "background": ("var(--wb-info-tint)", "var(--bc-cyan)"),
             "border": ("var(--wb-info-rand)", "var(--bc-focus)")},
    "signal": {"text": "var(--bc-link)",
               "background": ("var(--wb-signal-tint)", "var(--bc-violet)"),
               "border": ("var(--bc-rule-loud)", "var(--bc-violet)")},
}

# Flächen, auf denen neutrale Schrift zur Tinte oder zu Weiß wird.
STARK_HELL = frozenset({"var(--bc-lime)", "var(--bc-ok)", "var(--bc-yellow)", "var(--bc-warn)",
                        "var(--bc-cyan)", "var(--bc-info)", "var(--bc-primary)", "var(--bc-primary-deep)",
                        "var(--bc-ok-deep)", "var(--bc-ok-mid)"})
STARK_DUNKEL = frozenset({"var(--bc-pink)", "var(--bc-bad)", "var(--bc-bad-deep)", "var(--bc-ink)",
                          "var(--bc-violet)", "var(--bc-violet-deep)"})


def _familie(grad: float) -> str:
    if grad < 15 or grad >= 330:
        return "bad"
    if grad < 70:
        return "warn"
    if grad < 170:
        return "ok"
    if grad < 260:
        return "info"
    return "signal"


def _neutral(hell: float, art: str) -> str:
    if art in ("text", "graphic"):
        if hell >= 0.9:
            return "var(--bc-white)"
        if hell >= 0.45:
            return "var(--bc-text-quiet)"
        if hell >= 0.15:
            return "var(--bc-text)"
        return "var(--bc-text-loud)"
    if art == "background":
        if hell >= 0.97:
            return "var(--bc-surface)"
        if hell >= 0.92:
            return "var(--bc-head)"
        if hell >= 0.8:
            return "var(--bc-hover)"
        if hell >= 0.45:
            return "var(--bc-rule-loud)"
        return "var(--bc-ink)"
    if hell >= 0.82:
        return "var(--bc-rule)"
    if hell >= 0.6:
        return "var(--bc-rule-loud)"
    if hell >= 0.35:
        return "var(--bc-field-edge)"
    return "var(--bc-text-loud)"


def _ist_neutral(s: float, l: float) -> bool:
    return s < 0.2 or l >= 0.95 or l <= 0.1


def auto_rolle(farbe: str, art: str, dunkel: bool = False) -> str:
    """Rolle nach Farbton und Helligkeit; in dunklen Regeln gespiegelt."""
    r, g, b, a = rgba(farbe)
    if a == 0:
        return "transparent"
    h, l, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
    neutral = _ist_neutral(s, l)
    if neutral and a < 1:
        l = 1 - a * (1 - l)  # über Weiß gemischt
    grad = h * 360
    if art == "shadow":
        return "var(--wb-fokus-hof)" if (not neutral and 170 <= grad < 260) else "var(--wb-schatten)"
    hell = 1 - l if dunkel else l
    if neutral:
        return _neutral(hell, art)
    familie = FAMILIEN[_familie(grad)]
    rolle = familie.get(art, familie["text"])
    if isinstance(rolle, tuple):
        return rolle[0] if (hell >= 0.8 or a < 1) else rolle[1]
    return rolle


def kontext_rolle(farbe: str, flaeche: str | None) -> str | None:
    """Neutrale Schrift auf kräftiger Fläche derselben Regel: Tinte oder Weiß."""
    if not flaeche:
        return None
    r, g, b, _ = rgba(farbe)
    _, l, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
    if not _ist_neutral(s, l):
        return None
    if flaeche in STARK_HELL:
        return "var(--bc-ink)"
    if flaeche in STARK_DUNKEL:
        return "var(--bc-white)"
    return None


class Zuordnung:
    def __init__(self, daten: dict):
        self.farben = {normalise(k): v for k, v in daten.get("farben", {}).items()}
        self.farben_dunkel = {normalise(k): v for k, v in daten.get("farben_dunkel", {}).items()}
        self.selektoren = {
            self.selektor_schluessel(sel): {
                art: {normalise(c): rolle for c, rolle in rollen.items()} for art, rollen in arten.items()
            }
            for sel, arten in daten.get("selektoren", {}).items()
        }

    @classmethod
    def lade(cls, pfad: Path) -> "Zuordnung":
        if not pfad.is_file():
            raise FarbFehler(f"Die Farbzuordnung {pfad} fehlt. Mit 'farben.py vorschlag' eine erzeugen.")
        try:
            return cls(json.loads(pfad.read_text(encoding="utf-8")))
        except json.JSONDecodeError as err:
            raise FarbFehler(
                f"{pfad} ist kein gültiges JSON (Zeile {err.lineno}, Spalte {err.colno}: {err.msg})."
            ) from err

    @staticmethod
    def selektor_schluessel(selektor: str) -> str:
        return re.sub(r"\s+", " ", selektor.strip())

    def rolle(self, farbe: str, art: str, selektor: str = "", dunkel: bool = False,
              flaeche: str | None = None) -> tuple[str, bool]:
        schluessel = normalise(farbe)
        sonder = self.selektoren.get(self.selektor_schluessel(selektor), {}).get(art, {}).get(schluessel)
        if sonder is not None:
            return sonder, False
        if art == "text":
            kontext = kontext_rolle(schluessel, flaeche)
            if kontext is not None:
                return kontext, False
        eintrag = (self.farben_dunkel if dunkel else self.farben).get(schluessel, {})
        if art in eintrag:
            return eintrag[art], False
        return auto_rolle(schluessel, art, dunkel), True


# --- Ableitung -------------------------------------------------------------------------

RAND_KURZ = {"border": "border-color", "border-top": "border-top-color", "border-right": "border-right-color",
             "border-bottom": "border-bottom-color", "border-left": "border-left-color",
             "outline": "outline-color", "column-rule": "column-rule-color"}


@dataclass
class Fund:
    farbe: str
    art: str
    eigenschaft: str
    selektor: str
    rolle: str
    datei: str = ""


@dataclass
class Ableitung:
    zeilen: list[str]
    funde: list[Fund]
    deklarationen: int


def ist_dunkel(selektor: str, merkmal: str) -> bool:
    """Wahr, wenn jeder Teil der Selektorliste unter dem dunklen Merkmal steht."""
    muster = re.compile(r"(?:^|[\s>+~(])" + re.escape(merkmal) + r"(?![\w-])")
    teile = [t.strip() for t in split_top(selektor, ",") if t.strip()]
    return bool(teile) and all(muster.search(" " + t) for t in teile)


def _ausserhalb_schutz(wert: str, ersetze) -> str:
    teile, zuletzt = [], 0
    for m in SCHUTZ_RE.finditer(wert):
        teile.append(ersetze(wert[zuletzt:m.start()]))
        teile.append(m.group(0))
        zuletzt = m.end()
    teile.append(ersetze(wert[zuletzt:]))
    return "".join(teile)


def ersetze_farben(wert: str, art: str, zuordnung: Zuordnung, selektor: str, dunkel: bool,
                   flaeche: str | None, notiz) -> str:
    def repl(m: re.Match) -> str:
        roh = m.group(0)
        if roh.lower() in KEEP:
            return roh
        rolle, automatisch = zuordnung.rolle(roh, art, selektor, dunkel, flaeche)
        if automatisch:
            notiz(normalise(roh), rolle)
        return rolle

    return _ausserhalb_schutz(wert, lambda stueck: COLOUR_RE.sub(repl, stueck))


def ohne_feste_farbe(d: Decl) -> list[str]:
    """Werte ohne feste Farbe kommen mit, damit die Reihenfolge der Kaskade bleibt."""
    wert = d.value.strip()
    low = wert.lower()
    if d.prop in RAND_KURZ:
        teile = [t.strip() for t in split_top(wert, " ")
                 if t.strip().lower().startswith("var(") or t.strip().lower() in KEEP - {"none"}]
        return [f"{RAND_KURZ[d.prop]}: {teile[-1]}"] if teile else []
    if d.prop == "background":
        if low in ("none", "transparent"):
            return ["background-color: transparent"] + (["background-image: none"] if low == "none" else [])
        teile = [t.strip() for t in split_top(wert, " ") if t.strip().lower().startswith("var(")]
        return [f"background-color: {teile[-1]}"] if teile else []
    if d.prop == "background-image":
        return []
    if "var(" in low or low in KEEP:
        return [f"{d.prop}: {wert}"]
    return []


def leite_ab(d: Decl, selektor: str, zuordnung: Zuordnung, dunkel: bool, flaeche: str | None,
             funde: list[Fund]) -> list[str]:
    art = COLOUR_PROPS.get(d.prop)
    if not art:
        return []
    gefunden = colours_in(d.value)
    if not gefunden:
        return ohne_feste_farbe(d)

    def ersetze(stueck: str, art_hier: str) -> str:
        return ersetze_farben(stueck, art_hier, zuordnung, selektor, dunkel, flaeche,
                              lambda farbe, rolle: funde.append(Fund(farbe, art_hier, d.prop, selektor, rolle)))

    if d.prop in ("background", "background-image"):
        if "gradient(" in d.value.lower():
            schichten = [ersetze(t.strip(), "background") for t in split_top(d.value, ",") if t.strip()]
            return [f"background-image: {', '.join(schichten)}"]
        farbe = None
        for token in split_top(d.value, " "):
            token = token.strip().rstrip(",").strip()
            if token and COLOUR_RE.fullmatch(token) and token.lower() not in KEEP:
                farbe = ersetze(token, "background")
        return [f"background-color: {farbe}"] if farbe is not None else []
    if d.prop in RAND_KURZ:
        return [f"{RAND_KURZ[d.prop]}: {ersetze(gefunden[-1], art)}"]
    return [f"{d.prop}: {ersetze(d.value, art)}"]


def flaechen_rolle(rule: Rule, zuordnung: Zuordnung, dunkel: bool) -> str | None:
    for d in rule.decls:
        if COLOUR_PROPS.get(d.prop) == "background":
            gefunden = colours_in(d.value)
            if gefunden:
                return zuordnung.rolle(gefunden[-1], "background", rule.selector, dunkel, None)[0]
    return None


def ableiten(css: str, zuordnung: Zuordnung, datei: str, dunkel_merkmal: str) -> Ableitung:
    funde: list[Fund] = []
    zahl = 0

    def regel(rule: Rule, einzug: str) -> list[str]:
        nonlocal zahl
        dunkel = ist_dunkel(rule.selector, dunkel_merkmal)
        flaeche = flaechen_rolle(rule, zuordnung, dunkel)
        innen = []
        for d in rule.decls:
            wichtig = " !important" if d.important else ""
            for zeile in leite_ab(d, rule.selector, zuordnung, dunkel, flaeche, funde):
                innen.append(f"{einzug}\t{zeile}{wichtig};")
        zahl += len(innen)
        return [f"{einzug}{rule.selector} {{", *innen, f"{einzug}}}"] if innen else []

    def render(nodes: list, einzug: str) -> list[str]:
        aus: list[str] = []
        for node in nodes:
            if isinstance(node, Block):
                innen = render(node.children, einzug + "\t")
                if innen:
                    aus += [f"{einzug}{node.prelude} {{", *innen, f"{einzug}}}"]
            elif isinstance(node, Rule):
                aus += regel(node, einzug)
        return aus

    zeilen = render(parse_css(css), "")
    for f in funde:
        f.datei = datei
    return Ableitung(zeilen, funde, zahl)
```

- [ ] **Step 4: Tests laufen lassen, sie bestehen**

Run: `.venv/Scripts/python -m pytest tests/test_farben.py -q`
Expected: alle Tests grün. Scheitert ein Fall aus `test_auto_rolle`, die Schwelle in `_neutral` oder `_familie` prüfen und die Zahl im Test nur ändern, wenn die neue Zuordnung für die Werkbank richtiger ist; beides im Commit-Text begründen.

- [ ] **Step 5: Commit**

```bash
git add werkbank/farben.py tests/test_farben.py
git commit -m "Farbableitung: CSS zerlegen, Rollen nach Zuordnung, Fläche und Farbton

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Werkbank-Bündel: Tokens, Rollen, Variablen, Bauen

**Files:**
- Modify: `werkbank/farben.py` (am Ende anfügen)
- Create: `werkbank/rollen.css`, `werkbank/variablen.css`, `werkbank/stil.css` (Kopf; Inhalt folgt in Task 6 und 7), `werkbank/farben.json` (erzeugt)
- Test: `tests/test_farben.py` (anfügen), `tests/test_kontrast_paare.py`

**Interfaces:**
- Consumes: alles aus Task 3.
- Produces:
  - `farben.token_bloecke(tokens_css) -> dict[str, str]` mit Schlüsseln `grund`, `werkbank`, `dunkel`
  - `farben.token_werte(*koerper: str) -> dict[str, str]`, `farben.aufloesen(ausdruck: str, werte: dict) -> str`
  - `farben.tokens_fuer_healthchecks(tokens_css: str, dunkel: str) -> str`
  - `farben.stylesheets(base_html: str) -> list[str]`
  - `farben.pruefe_variablen(oben_css, zuordnung_css, dunkel) -> tuple[dict[str, list[str]], list[str]]`
  - `farben.bauen(wurzel: Path, hausschrift: Path, werkbank: Path, fassung: str) -> tuple[str, str, dict]` (werkbank.css, farben.css, Bericht mit `fassung`, `stylesheets`, `deklarationen`, `automatisch`, `variablen_entfallen`)
  - `farben.schreibe(wurzel: Path, werkbank_css: str, farben_css: str) -> None`
  - `farben.inventur(wurzel: Path) -> list[dict]`, `farben.vorschlag(wurzel: Path, behalte: Path | None) -> dict`
  - `farben.main(argv) -> int` mit `bauen`, `inventur`, `vorschlag`; Rückgabe 0 oder 1

- [ ] **Step 1: Tests anfügen**

Ans Ende von `tests/test_farben.py`:
```python
TOKENS = (WURZEL / "vendor/hausschrift/assets/css/bc-tokens.css").read_text(encoding="utf-8")


def test_tokens_auf_root_body_und_dunkel():
    t = farben.tokens_fuer_healthchecks(TOKENS, "body.dark")
    assert ":root,\nbody {" in t
    assert "--bc-primary: var(--bc-yellow);" in t
    assert t.index("body.dark {") < t.index("--bc-surface: #141415;")
    assert "html.nacht {" in farben.tokens_fuer_healthchecks(TOKENS, "html.nacht")


def test_tokens_ohne_werkbank_block_melden_sich():
    with pytest.raises(farben.FarbFehler, match="fehlen die Blöcke"):
        farben.token_bloecke(":root { --bc-ink: #111111; }")


def test_aufloesen_folgt_verweisen():
    werte = {"--a": "var(--b)", "--b": "#fed329"}
    assert farben.aufloesen("--a", werte) == "#fed329"
    with pytest.raises(farben.FarbFehler, match="gibt es in den Tokens nicht"):
        farben.aufloesen("--fehlt", werte)


def test_neue_und_entfallene_variablen():
    oben = ":root { --a: #fff; --b: #000 } body.dark { --a: #111; --c: #222 }"
    unsere = ":root, body, body.dark { --a: var(--bc-text); --alt: var(--bc-text) }"
    neu, entfallen = farben.pruefe_variablen(oben, unsere, "body.dark")
    assert neu == {"hell": ["--b"], "dunkel": ["--c"]}
    assert entfallen == ["--alt"]


def test_variablen_css_deckt_healthchecks_ab():
    quellen = sorted((WURZEL / ".upstream").glob("v*/static/css/variables.css"))
    if not quellen:
        pytest.skip("Keine Quelle von Healthchecks unter .upstream/.")
    unsere = (WURZEL / "werkbank/variablen.css").read_text(encoding="utf-8")
    neu, entfallen = farben.pruefe_variablen(quellen[-1].read_text(encoding="utf-8"), unsere, "body.dark")
    assert neu == {"hell": [], "dunkel": []}
    assert entfallen == []


def test_stylesheets_in_reihenfolge():
    base = ("{% compress css %}<link href=\"{% static 'css/a.css' %}\"><link href=\"{% static 'css/b.css' %}\">"
            "{% endcompress %}{% compress js %}<script src=\"{% static 'js/x.js' %}\"></script>{% endcompress %}")
    assert farben.stylesheets(base) == ["css/a.css", "css/b.css"]


def test_stylesheets_ohne_compress_block_melden_sich():
    with pytest.raises(farben.FarbFehler, match="compress css"):
        farben.stylesheets("<html></html>")


def mini_healthchecks(ordner, variablen=":root { --text-color: #333 } body.dark { --text-color: #eee }"):
    (ordner / "templates").mkdir(parents=True)
    (ordner / "static/css").mkdir(parents=True)
    (ordner / "templates/base.html").write_text(
        "{% compress css %}<link href=\"{% static 'css/variables.css' %}\">"
        "<link href=\"{% static 'css/base.css' %}\">{% endcompress %}", encoding="utf-8")
    (ordner / "static/css/variables.css").write_text(variablen, encoding="utf-8")
    (ordner / "static/css/base.css").write_text(
        ".status.ic-up { color: #22bc66 } .btn-primary { color: #fff; background-color: #22bc66 }",
        encoding="utf-8")
    return ordner


def mini_werkbank(ordner, variablen_css=":root,\nbody,\nbody.dark {\n\t--text-color: var(--bc-text);\n}\n"):
    ordner.mkdir(parents=True)
    for name in ("rollen.css", "stil.css"):
        (ordner / name).write_text((WURZEL / "werkbank" / name).read_text(encoding="utf-8"), encoding="utf-8")
    (ordner / "variablen.css").write_text(variablen_css, encoding="utf-8")
    (ordner / "farben.json").write_text("{}", encoding="utf-8")
    return ordner


def test_bauen_setzt_alles_in_reihenfolge(tmp_path):
    hc = mini_healthchecks(tmp_path / "hc")
    werkbank = mini_werkbank(tmp_path / "werkbank")
    css, farben_css, bericht = farben.bauen(hc, WURZEL / "vendor/hausschrift", werkbank, "4.4-wb1.0.0")
    marken = ['url("fonts/anton-400.woff2")', ":root,\nbody {", "--wb-ok-tint:", "--text-color: var(--bc-text)",
              "/* css/base.css */", ".bc-rail {", "/* healthchecks-werkbank: Stilschicht"]
    stellen = [css.index(m) for m in marken]
    assert stellen == sorted(stellen)
    assert "body.dark .bc-mode" in css
    assert '[data-theme="dark"]' not in css
    assert "/* css/variables.css */" not in css
    assert bericht["stylesheets"] == 1
    assert bericht["deklarationen"] == 3
    assert {(f["farbe"], f["art"]) for f in bericht["automatisch"]} == {("#22bc66", "text"), ("#22bc66", "background")}
    assert farben_css.startswith("/* healthchecks-werkbank 4.4-wb1.0.0.")


def test_bauen_bricht_bei_neuer_variable_ab(tmp_path):
    hc = mini_healthchecks(tmp_path / "hc", ":root { --text-color: #333; --neu-farbe: #f00 }")
    werkbank = mini_werkbank(tmp_path / "werkbank")
    with pytest.raises(farben.FarbFehler, match="--neu-farbe"):
        farben.bauen(hc, WURZEL / "vendor/hausschrift", werkbank, "4.4-wb1.0.0")


def test_bauen_mit_anderem_dunklen_selektor(tmp_path, monkeypatch):
    monkeypatch.setenv("WB_DUNKEL_SELEKTOR", "html.nacht")
    hc = mini_healthchecks(tmp_path / "hc", ":root { --text-color: #333 } html.nacht { --text-color: #eee }")
    werkbank = mini_werkbank(tmp_path / "werkbank")
    css, _, _ = farben.bauen(hc, WURZEL / "vendor/hausschrift", werkbank, "x")
    assert "html.nacht .bc-mode" in css
    assert "html.nacht {" in css


def test_schreibe_legt_beide_dateien_ab(tmp_path):
    farben.schreibe(tmp_path, "A", "B")
    assert (tmp_path / "static/bc/werkbank.css").read_text(encoding="utf-8") == "A"
    assert (tmp_path / "static/bc/farben.css").read_text(encoding="utf-8") == "B"


def test_vorschlag_behaelt_vorhandene_eintraege(tmp_path):
    hc = mini_healthchecks(tmp_path / "hc")
    alt = tmp_path / "alt.json"
    alt.write_text('{"selektoren": {".x": {"text": {"#fff": "var(--bc-ink)"}}},'
                   ' "farben": {"#22bc66": {"text": "var(--bc-text)"}}}', encoding="utf-8")
    daten = farben.vorschlag(hc, alt)
    assert daten["selektoren"] == {".x": {"text": {"#fff": "var(--bc-ink)"}}}
    assert daten["farben"]["#22bc66"]["text"] == "var(--bc-text)"
    assert daten["farben"]["#22bc66"]["background"] == "var(--bc-lime)"
    assert daten["farben"]["#ffffff"]["text"] == "var(--bc-white)"


def test_echte_ableitung_ohne_automatik():
    quellen = sorted(p.parents[2] for p in (WURZEL / ".upstream").glob("v*/static/css/variables.css"))
    if not quellen:
        pytest.skip("Keine Quelle von Healthchecks unter .upstream/.")
    css, _, bericht = farben.bauen(quellen[-1], WURZEL / "vendor/hausschrift", WURZEL / "werkbank", "test")
    assert bericht["automatisch"] == [], bericht["automatisch"][:5]
    assert bericht["deklarationen"] > 500
    assert "var(--bc-lime)" in css


def test_kommandozeile_bauen_meldet_fehlende_wurzel(tmp_path, capsys):
    rc = farben.main(["bauen", "--wurzel", str(tmp_path / "fehlt"), "--hausschrift",
                      str(WURZEL / "vendor/hausschrift"), "--werkbank", str(WURZEL / "werkbank"), "--fassung", "x"])
    assert rc == 1
    assert "Abbruch:" in capsys.readouterr().err
```

`tests/test_kontrast_paare.py`:
```python
"""Kontrast der wichtigsten Paare aus den Tokens, hell und dunkel.

Schrift ab 4,8:1 (Ziel der Hausschrift), Symbole und Fokusringe ab 3:1.
Zustände, die der Browserlauf nicht sieht (Hover, gedrückte Knöpfe, Leiste),
stehen hier.
"""
import sys
from pathlib import Path

import pytest

WURZEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WURZEL / "werkbank"))
import farben  # noqa: E402

BLOECKE = farben.token_bloecke((WURZEL / "vendor/hausschrift/assets/css/bc-tokens.css").read_text(encoding="utf-8"))
HELL = farben.token_werte(BLOECKE["grund"], BLOECKE["werkbank"])
DUNKEL = {**HELL, **farben.token_werte(BLOECKE["dunkel"])}

FLAECHEN_HELL = ["--bc-surface", "--bc-ground", "--bc-head", "--bc-hover"]
FLAECHEN_DUNKEL = ["--bc-ground", "--bc-surface", "--bc-head", "--bc-hover", "--bc-overlay", "--bc-raised"]

PAARE = [
    ("hell", "--bc-text", FLAECHEN_HELL, 4.8),
    ("hell", "--bc-text-quiet", FLAECHEN_HELL, 4.8),
    ("hell", "--bc-link", FLAECHEN_HELL, 4.8),
    ("hell", "--bc-ok-text", ["--bc-surface", "--bc-head"], 4.8),
    ("hell", "--bc-warn-text", ["--bc-surface", "--bc-head"], 4.8),
    ("hell", "--bc-bad-text", ["--bc-surface", "--bc-head", "--bc-bad-tint"], 4.8),
    ("hell", "--bc-on-primary", ["--bc-primary", "--bc-primary-deep", "--bc-lime"], 4.8),
    ("hell", "--bc-white", ["--bc-pink", "--bc-bad-deep"], 4.8),
    ("hell", "--bc-deep", ["--bc-cyan"], 4.8),
    ("hell", "--bc-rail-text", ["--bc-rail", "--bc-rail-2"], 4.8),
    ("hell", "--bc-rail-muted", ["--bc-rail", "--bc-rail-2"], 4.8),
    ("hell", "--bc-pink", ["--bc-surface"], 3.0),
    ("hell", "--bc-focus", ["--bc-surface", "--bc-ground"], 3.0),
    ("dunkel", "--bc-text", FLAECHEN_DUNKEL, 4.8),
    ("dunkel", "--bc-text-quiet", FLAECHEN_DUNKEL, 4.8),
    ("dunkel", "--bc-link", FLAECHEN_DUNKEL, 4.8),
    ("dunkel", "--bc-ok-text", ["--bc-surface", "--bc-head"], 4.8),
    ("dunkel", "--bc-warn-text", ["--bc-surface", "--bc-head"], 4.8),
    ("dunkel", "--bc-bad-text", ["--bc-surface", "--bc-head", "--bc-bad-tint"], 4.8),
    ("dunkel", "--bc-rail-text", ["--bc-rail", "--bc-rail-2"], 4.8),
    ("dunkel", "--bc-rail-muted", ["--bc-rail", "--bc-rail-2"], 4.8),
    ("dunkel", "--bc-pink", ["--bc-surface", "--bc-head"], 3.0),
    ("dunkel", "--bc-focus", ["--bc-surface", "--bc-ground"], 3.0),
]


def leuchtdichte(hexwert: str) -> float:
    h = hexwert.lstrip("#")
    kanaele = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    linear = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in kanaele]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def kontrast(a: str, b: str) -> float:
    hell_, dunkel_ = sorted((leuchtdichte(a), leuchtdichte(b)), reverse=True)
    return (hell_ + 0.05) / (dunkel_ + 0.05)


@pytest.mark.parametrize("modus, schrift, flaechen, mindest", PAARE, ids=[f"{m}{s}" for m, s, _, _ in PAARE])
def test_paar(modus, schrift, flaechen, mindest):
    werte = HELL if modus == "hell" else DUNKEL
    vorne = farben.normalise(farben.aufloesen(schrift, werte))
    for flaeche in flaechen:
        hinten = farben.normalise(farben.aufloesen(flaeche, werte))
        wert = kontrast(vorne, hinten)
        assert wert >= mindest, f"{schrift} ({vorne}) auf {flaeche} ({hinten}), {modus}: {wert:.2f}:1, gebraucht {mindest}:1"
```

- [ ] **Step 2: Tests laufen lassen, sie scheitern**

Run: `.venv/Scripts/python -m pytest tests/test_farben.py tests/test_kontrast_paare.py -q`
Expected: FAIL mit `AttributeError: module 'farben' has no attribute 'tokens_fuer_healthchecks'` (bzw. `token_bloecke`).

- [ ] **Step 3: Bündel, Inventur, Vorschlag und Kommandozeile anfügen**

Ans Ende von `werkbank/farben.py`:
```python
# --- Tokens, Variablen, Bündel ---------------------------------------------------------

TOKEN_BLOECKE = {
    ":root": "grund",
    '[data-bc-variant="workbench"]': "werkbank",
    '[data-bc-variant="workbench"][data-theme="dark"]': "dunkel",
}


def token_bloecke(tokens_css: str) -> dict[str, str]:
    """Die Deklarationen der Blöcke :root, Werkbank hell und Werkbank dunkel aus bc-tokens.css."""
    gefunden: dict[str, str] = {}
    for rule in walk_rules(parse_css(tokens_css)):
        name = TOKEN_BLOECKE.get(re.sub(r"\s+", "", rule.selector))
        if name:
            gefunden[name] = "\n".join(f"\t{d.prop}: {d.value};" for d in rule.decls)
    fehlt = [n for n in TOKEN_BLOECKE.values() if n not in gefunden]
    if fehlt:
        raise FarbFehler(
            f"In bc-tokens.css fehlen die Blöcke {', '.join(fehlt)}. Die Datei muss eine unveränderte Kopie "
            "aus der Hausschrift sein (vendor/hausschrift/QUELLE.md)."
        )
    return gefunden


def token_werte(*koerper: str) -> dict[str, str]:
    werte: dict[str, str] = {}
    for k in koerper:
        for d in parse_decls(k.replace("\n", ";")):
            if d.prop.startswith("--"):
                werte[d.prop] = d.value
    return werte


def aufloesen(ausdruck: str, werte: dict[str, str], tiefe: int = 0) -> str:
    if tiefe > 12:
        raise FarbFehler(f"Die Rolle {ausdruck} verweist im Kreis auf sich selbst. Die Tokens prüfen.")
    ausdruck = ausdruck.strip()
    m = re.fullmatch(r"var\(\s*(--[\w-]+)\s*(?:,\s*(.+))?\)", ausdruck)
    if m:
        name, ersatz = m.group(1), m.group(2)
        if name in werte:
            return aufloesen(werte[name], werte, tiefe + 1)
        if ersatz:
            return aufloesen(ersatz, werte, tiefe + 1)
        raise FarbFehler(f"Die Rolle {name} gibt es in den Tokens nicht. Die Schreibweise prüfen.")
    if ausdruck.startswith("--"):
        return aufloesen(f"var({ausdruck})", werte, tiefe + 1)
    return ausdruck


def tokens_fuer_healthchecks(tokens_css: str, dunkel: str) -> str:
    """Hell auf :root und body, dunkel auf dem dunklen Selektor von Healthchecks.

    Auf body stehen die Tokens zusätzlich, damit abgeleitete Tokens wie
    --bc-link-hover dort mit den dunklen Werten neu berechnet werden.
    """
    b = token_bloecke(tokens_css)
    return "\n".join([
        "/* Tokens der Hausschrift: Grundwerte und Werkbank hell, auf :root und body */",
        ":root,",
        "body {",
        b["grund"],
        b["werkbank"],
        "}",
        "",
        "/* Tokens der Hausschrift: Werkbank dunkel */",
        f"{dunkel} {{",
        b["dunkel"],
        "}",
    ])


def schriften(fonts_css: str) -> str:
    """bc-fonts.css liegt in css/, werkbank.css liegt neben fonts/."""
    return fonts_css.replace("../fonts/", "fonts/")


def werkbank_bausteine(css: str, dunkel: str) -> str:
    """bc-workbench.css schaltet dunkel über [data-theme="dark"], Healthchecks über body.dark."""
    return css.replace('[data-theme="dark"]', dunkel)


def stylesheets(base_html: str) -> list[str]:
    m = re.search(r"{%\s*compress\s+css\s*%}(.*?){%\s*endcompress\s*%}", base_html, re.S)
    if not m:
        raise FarbFehler(
            "In templates/base.html fehlt der Block {% compress css %}. Healthchecks hat die Vorlage umgebaut: "
            "werkbank/farben.py an die neue Fassung anpassen."
        )
    return re.findall(r"{%\s*static\s+['\"]([^'\"]+\.css)['\"]\s*%}", m.group(1))


def variablen_namen(css: str) -> dict[str, set[str]]:
    namen: dict[str, set[str]] = {}
    for rule in walk_rules(parse_css(css)):
        selektor = re.sub(r"\s+", " ", rule.selector.strip())
        namen.setdefault(selektor, set()).update(d.prop for d in rule.decls if d.prop.startswith("--"))
    return namen


def pruefe_variablen(oben_css: str, zuordnung_css: str, dunkel: str) -> tuple[dict[str, list[str]], list[str]]:
    """Neue Variablen von Healthchecks, getrennt nach hell und dunkel, und entfallene der Zuordnung."""
    oben = variablen_namen(oben_css)
    hell, dunkel_namen = oben.get(":root", set()), oben.get(dunkel, set())
    unsere: set[str] = set().union(*variablen_namen(zuordnung_css).values())
    neu = {"hell": sorted(hell - unsere), "dunkel": sorted(dunkel_namen - unsere)}
    return neu, sorted(unsere - hell - dunkel_namen)


def lies(pfad: Path) -> str:
    try:
        return pfad.read_text(encoding="utf-8")
    except FileNotFoundError as err:
        raise FarbFehler(f"{pfad} fehlt. Die Pfade --wurzel, --hausschrift und --werkbank prüfen.") from err


def bauen(wurzel: Path, hausschrift: Path, werkbank: Path, fassung: str) -> tuple[str, str, dict]:
    """werkbank.css, farben.css und Bericht; schreibt nichts."""
    static = wurzel / einstellung("WB_STATIC")
    dunkel = einstellung("WB_DUNKEL_SELEKTOR")
    variablen_rel = einstellung("WB_VARIABLEN_CSS")
    zuordnung = Zuordnung.lade(werkbank / "farben.json")
    variablen_css = lies(werkbank / "variablen.css")

    neu, entfallen = pruefe_variablen(lies(static / variablen_rel), variablen_css, dunkel)
    if neu["hell"] or neu["dunkel"]:
        alle = sorted(set(neu["hell"]) | set(neu["dunkel"]))
        raise FarbFehler(
            f"Healthchecks bringt neue Variablen mit, die werkbank/variablen.css noch nicht zuordnet: {', '.join(alle)} "
            f"(hell: {', '.join(neu['hell']) or 'keine'}; dunkel: {', '.join(neu['dunkel']) or 'keine'}). "
            "Jede braucht dort eine Zeile mit einer Werkbank-Rolle."
        )

    abgeleitet: list[str] = []
    funde: list[Fund] = []
    zahl = 0
    dateien = [rel for rel in stylesheets(lies(wurzel / einstellung("WB_BASIS_VORLAGE"))) if rel != variablen_rel]
    for rel in dateien:
        ergebnis = ableiten(lies(static / rel), zuordnung, rel, dunkel)
        if ergebnis.zeilen:
            abgeleitet += [f"/* {rel} */", *ergebnis.zeilen]
        funde += ergebnis.funde
        zahl += ergebnis.deklarationen

    kopf = (f"/* healthchecks-werkbank {fassung}. Erzeugt von werkbank/farben.py; "
            "Änderungen in werkbank/ vornehmen und neu bauen. */")
    farben_css = "\n".join([kopf, *abgeleitet]) + "\n"
    werkbank_css = "\n".join([
        kopf,
        schriften(lies(hausschrift / "assets" / "css" / "bc-fonts.css")),
        tokens_fuer_healthchecks(lies(hausschrift / "assets" / "css" / "bc-tokens.css"), dunkel),
        lies(werkbank / "rollen.css"),
        variablen_css,
        "/* Feste Farben von Healthchecks, auf Werkbank-Rollen umgeleitet */",
        *abgeleitet,
        "/* Bausteine der Hausschrift: bc-workbench.css */",
        werkbank_bausteine(lies(hausschrift / "assets" / "css" / "bc-workbench.css"), dunkel),
        lies(werkbank / "stil.css"),
    ]) + "\n"
    bericht = {
        "fassung": fassung,
        "stylesheets": len(dateien),
        "deklarationen": zahl,
        "automatisch": [asdict(f) for f in funde],
        "variablen_entfallen": entfallen,
    }
    return werkbank_css, farben_css, bericht


def schreibe(wurzel: Path, werkbank_css: str, farben_css: str) -> None:
    static = wurzel / einstellung("WB_STATIC")
    for rel, inhalt in ((einstellung("WB_ZIEL"), werkbank_css), (einstellung("WB_ZIEL_FARBEN"), farben_css)):
        ziel = static / rel
        ziel.parent.mkdir(parents=True, exist_ok=True)
        ziel.write_text(inhalt, encoding="utf-8")


def inventur(wurzel: Path) -> list[dict]:
    """Jede feste Farbe je Art und Modus mit Fundstellen, als Grundlage für farben.json."""
    static = wurzel / einstellung("WB_STATIC")
    dunkel = einstellung("WB_DUNKEL_SELEKTOR")
    variablen_rel = einstellung("WB_VARIABLEN_CSS")
    gesehen: dict[tuple[str, str, bool], dict] = {}
    for rel in stylesheets(lies(wurzel / einstellung("WB_BASIS_VORLAGE"))):
        if rel == variablen_rel:
            continue
        for rule in walk_rules(parse_css(lies(static / rel))):
            ist = ist_dunkel(rule.selector, dunkel)
            for d in rule.decls:
                art = COLOUR_PROPS.get(d.prop)
                if not art:
                    continue
                for c in colours_in(d.value):
                    schluessel = (normalise(c), art, ist)
                    e = gesehen.setdefault(schluessel, {"farbe": schluessel[0], "art": art, "dunkel": ist,
                                                        "anzahl": 0, "beispiele": []})
                    e["anzahl"] += 1
                    if len(e["beispiele"]) < 4:
                        e["beispiele"].append(f"{rel}: {rule.selector} {{ {d.prop}: {d.value} }}")
    return sorted(gesehen.values(), key=lambda e: (e["dunkel"], e["farbe"], e["art"]))


def vorschlag(wurzel: Path, behalte: Path | None) -> dict:
    alt = json.loads(behalte.read_text(encoding="utf-8")) if behalte and behalte.is_file() else {}
    daten = {
        "_info": ("Zuordnung fester Farben von Healthchecks zu Werkbank-Rollen. Erzeugt mit 'farben.py vorschlag', "
                  "danach von Hand verfeinert. selektoren geht vor farben; farben gilt für helle Regeln, "
                  "farben_dunkel für Regeln unter body.dark."),
        "selektoren": alt.get("selektoren", {}),
        "farben": dict(alt.get("farben", {})),
        "farben_dunkel": dict(alt.get("farben_dunkel", {})),
    }
    for e in inventur(wurzel):
        ziel = daten["farben_dunkel" if e["dunkel"] else "farben"].setdefault(e["farbe"], {})
        ziel.setdefault(e["art"], auto_rolle(e["farbe"], e["art"], e["dunkel"]))
    for teil in ("farben", "farben_dunkel"):
        daten[teil] = dict(sorted(daten[teil].items()))
    return daten


def main(argv: list[str] | None = None) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description="Baut werkbank.css aus den Stylesheets von Healthchecks.")
    unter = p.add_subparsers(dest="befehl", required=True)
    b = unter.add_parser("bauen", help="werkbank.css und farben.css schreiben")
    b.add_argument("--wurzel", required=True, help="Ordner von Healthchecks")
    b.add_argument("--hausschrift", required=True, help="Kopie der Hausschrift (vendor/hausschrift)")
    b.add_argument("--werkbank", required=True, help="Ordner werkbank/ mit farben.json, rollen.css, variablen.css, stil.css")
    b.add_argument("--fassung", required=True, help="Fassung des Images, etwa 4.4-wb1.0.0")
    b.add_argument("--bericht", help="Bericht zusätzlich als JSON in diese Datei schreiben")
    i = unter.add_parser("inventur", help="alle festen Farben mit Fundstellen als JSON ausgeben")
    i.add_argument("--wurzel", required=True)
    v = unter.add_parser("vorschlag", help="farben.json aus der Inventur vorschlagen")
    v.add_argument("--wurzel", required=True)
    v.add_argument("--behalte", help="vorhandene farben.json; ihre Einträge bleiben")
    args = p.parse_args(argv)
    try:
        if args.befehl == "bauen":
            css, farben_css, bericht = bauen(Path(args.wurzel), Path(args.hausschrift), Path(args.werkbank), args.fassung)
            schreibe(Path(args.wurzel), css, farben_css)
            if args.bericht:
                Path(args.bericht).write_text(json.dumps(bericht, indent=2, ensure_ascii=False), encoding="utf-8")
            print(f"werkbank.css gebaut: {bericht['deklarationen']} Farbangaben aus {bericht['stylesheets']} "
                  f"Stylesheets, {len(bericht['automatisch'])} automatisch zugeordnet.")
            if bericht["variablen_entfallen"]:
                print("Hinweis: Diese Variablen gibt es in Healthchecks nicht mehr: "
                      + ", ".join(bericht["variablen_entfallen"]))
        elif args.befehl == "inventur":
            print(json.dumps(inventur(Path(args.wurzel)), indent=2, ensure_ascii=False))
        else:
            daten = vorschlag(Path(args.wurzel), Path(args.behalte) if args.behalte else None)
            print(json.dumps(daten, indent=2, ensure_ascii=False))
            print(f"Vorschlag: {len(daten['farben'])} Farben in hellen Regeln, "
                  f"{len(daten['farben_dunkel'])} in dunklen.", file=sys.stderr)
    except FarbFehler as err:
        print(f"Abbruch: {err}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Rollen, Variablen und Kopf der Stilschicht anlegen**

`werkbank/rollen.css`:
```css
/* healthchecks-werkbank: eigene Rollen neben den Tokens der Hausschrift.
   Hell auf :root und body, dunkel auf body.dark. Die Tönungen mischen die
   Signalfarben mit der Kartenfläche und folgen so dem Modus. */

:root,
body {
	--wb-ok-tint: color-mix(in srgb, var(--bc-lime) 24%, var(--bc-surface));
	--wb-warn-tint: color-mix(in srgb, var(--bc-yellow) 26%, var(--bc-surface));
	--wb-info-tint: color-mix(in srgb, var(--bc-cyan) 16%, var(--bc-surface));
	--wb-signal-tint: color-mix(in srgb, var(--bc-violet) 14%, var(--bc-surface));
	--wb-ok-rand: color-mix(in srgb, var(--bc-lime) 65%, var(--bc-surface));
	--wb-warn-rand: color-mix(in srgb, var(--bc-yellow) 75%, var(--bc-surface));
	--wb-bad-rand: color-mix(in srgb, var(--bc-pink) 45%, var(--bc-surface));
	--wb-info-rand: color-mix(in srgb, var(--bc-cyan) 55%, var(--bc-surface));
	--wb-schatten: rgba(17, 17, 17, .08);
	--wb-fokus-hof: color-mix(in srgb, var(--bc-focus) 22%, transparent);
	/* Hausampel als Symbol: Limette und Gelb als Textton, im Dunkeln rein. */
	--wb-zustand-up: var(--bc-ok-text);
	--wb-zustand-grace: var(--bc-warn-text);
	--wb-zustand-down: var(--bc-pink);
	--wb-zustand-started: var(--bc-focus);
}

body.dark {
	--wb-schatten: rgba(0, 0, 0, .5);
}
```

`werkbank/variablen.css`:
```css
/* healthchecks-werkbank: die Variablen von Healthchecks (static/css/variables.css)
   auf Werkbank-Rollen. Ein Block für beide Modi: die Rollen selbst wechseln mit
   body.dark. body.dark steht im Selektor, damit dieser Block den dunklen Block
   von Healthchecks überschreibt. Bringt ein Update eine neue Variable, bricht
   farben.py ab und nennt sie; dann hier eine Zeile ergänzen. */

:root,
body,
body.dark {
	--account-warning-bg: var(--bc-yellow);
	--alert-no-data-bg: var(--bc-head);
	--alert-no-data-border: var(--bc-rule);
	--alert-no-data-color: var(--bc-text-quiet);
	--alert-success-bg: var(--wb-ok-tint);
	--alert-success-border: var(--wb-ok-rand);
	--alert-success-color: var(--bc-text);
	--body-bg: var(--bc-ground);
	--border-color: var(--bc-rule);
	--border-muted: var(--bc-rule-soft);
	--breadcrumb-active-color: var(--bc-text-quiet);
	--breadcrumb-bg: var(--bc-head);
	--btn-active-bg: var(--bc-hover);
	--btn-active-border: var(--bc-text-quiet);
	--btn-active-color: var(--bc-text-loud);
	--btn-default-bg: var(--bc-control);
	--btn-default-border: var(--bc-field-edge);
	--btn-default-color: var(--bc-text-loud);
	--btn-remove-bg: var(--bc-control);
	--btn-remove-color: var(--bc-bad-text);
	--btn-remove-hover: var(--bc-bad-tint);
	--channel-off-color: var(--bc-rule);
	--channel-off-inside-color: var(--bc-surface);
	--cheatsheet-example-bg: var(--bc-head);
	--cheatsheet-dotted-color: var(--bc-rule-loud);
	--close-color: var(--bc-text-loud);
	--debug-warning-bg: var(--bc-bad-tint);
	--dropdown-bg: var(--bc-overlay);
	--dropdown-link-hover-bg: var(--bc-hover);
	--get-started-bg: var(--bc-head);
	--input-bg-disabled: var(--bc-head);
	--input-border: var(--bc-field-edge);
	--input-color: var(--bc-text);
	--input-group-addon-bg: var(--bc-head);
	--jumbotron-bg: var(--bc-head);
	--label-ign-bg: var(--bc-head);
	--label-ign-color: var(--bc-text);
	--label-start-color: var(--bc-ok-text);
	--link-color: var(--bc-link);
	--link-hover-color: var(--bc-link-hover);
	--log-flip-bg: var(--bc-head);
	--modal-content-bg: var(--bc-overlay);
	--nav-link-hover-bg: var(--bc-hover);
	--panel-bg: var(--bc-surface);
	--panel-default-heading-bg: var(--bc-head);
	--panel-success-bg: var(--wb-ok-tint);
	--plan-business-border: var(--bc-cyan);
	--plan-business-color: var(--bc-text);
	--plan-business-plus-border: var(--bc-violet);
	--plan-business-plus-color: var(--bc-text);
	--plan-hobbyist-border: var(--bc-lime);
	--plan-hobbyist-color: var(--bc-text);
	--plan-supporter-border: var(--bc-yellow);
	--plan-supporter-color: var(--bc-text);
	--pre-bg: var(--bc-head);
	--ts-tag-bg: var(--bc-head);
	--small-text-color: var(--bc-text-loud);
	--state-info-bg: var(--wb-info-tint);
	--state-info-border: var(--wb-info-rand);
	--state-info-color: var(--bc-text);
	--status-new-color: var(--bc-text-quiet);
	--table-bg-hover: var(--bc-hover);
	--tag-bg: var(--bc-head);
	--tag-checked-bg: var(--bc-text-loud);
	--tag-checked-border: var(--bc-text-loud);
	--tag-checked-color: var(--bc-surface);
	--tag-checked-shadow: var(--bc-rule);
	--tag-color: var(--bc-text);
	--tag-up-bg: var(--bc-surface);
	--tag-up-border: var(--bc-rule);
	--tag-up-color: var(--bc-text);
	--text-color: var(--bc-text);
	--text-muted: var(--bc-text-quiet);
	--text-success: var(--bc-ok-text);
	--text-warning: var(--bc-warn-text);
	--text-danger: var(--bc-bad-text);
	--log-new-row-bg: var(--wb-info-tint);
	--log-new-row-border: var(--wb-info-rand);
}
```

`werkbank/stil.css` (Kopf; Task 6 und 7 füllen die Abschnitte):
```css
/* healthchecks-werkbank: Stilschicht.
   Letzter Teil von werkbank.css, nach Tokens, Rollen, Variablen, abgeleiteten
   Farben und den Bausteinen der Hausschrift. Farben nur über Tokens. */
```

- [ ] **Step 5: Inventur ansehen und farben.json erzeugen**

```bash
.venv/Scripts/python werkbank/farben.py inventur --wurzel .upstream/v4.4 > "$TEMP/wb-inventur.json"
.venv/Scripts/python -c "import json,os; d=json.load(open(os.path.join(os.environ['TEMP'],'wb-inventur.json'),encoding='utf-8')); print(len(d), 'Einträge,', sum(e['dunkel'] for e in d), 'davon dunkel')"
.venv/Scripts/python werkbank/farben.py vorschlag --wurzel .upstream/v4.4 > werkbank/farben.json
```
Expected: rund 200 Einträge in der Inventur; auf stderr eine Zeile `Vorschlag: N Farben in hellen Regeln, M in dunklen.` Die Zahlen gehen in den Commit-Text.

- [ ] **Step 6: Tests laufen lassen, sie bestehen**

Run: `.venv/Scripts/python -m pytest -q`
Expected: alle Tests grün, darunter `test_echte_ableitung_ohne_automatik` und alle 23 Kontrastpaare.

- [ ] **Step 7: Lint auf die neuen Stylesheets**

Run: `.venv/Scripts/python vendor/hausschrift/scripts/bc_check.py lint werkbank --variant workbench`
Expected: `0 Warnung(en)`. Meldet der Lint eine Farbe außerhalb der Palette in `rollen.css`, den Wert durch einen Token oder `color-mix()` mit Tokens ersetzen.

- [ ] **Step 8: Commit**

```bash
git add werkbank/farben.py werkbank/farben.json werkbank/rollen.css werkbank/variablen.css werkbank/stil.css tests/test_farben.py tests/test_kontrast_paare.py
git commit -m "Werkbank-Bündel: Tokens auf body, 78 Variablen, Farbzuordnung aus der Inventur

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Lokaler Aufbau mit Musterdaten und Browserprüfung

**Files:**
- Create: `tests/musterdaten.py`, `tools/dev.py`, `werkbank/static/bc/leiste.js` (Kopf; Inhalt folgt in Task 6)
- Create: `package.json`, `package-lock.json` (erzeugt), `playwright.config.mjs`, `tests/e2e/hilfen.mjs`, `tests/e2e/grundlage.spec.mjs`

**Interfaces:**
- Consumes: `einbau.einbauen`, `einbau.lade_plan`, `einbau.PLAN_VORGABE`, `farben.bauen`, `farben.schreibe`.
- Produces:
  - `tests/musterdaten.py`: liest `WB_TEST_PASSWORT`, schreibt als letzte Zeile `MUSTERDATEN: {"nutzer": {"hell", "dunkel"}, "projekte": [{"name", "code"}], "checks": {"up", "grace", "down", "started", "paused", "new"}, "seiten": {"anmeldung", "projekte", "checks", "details", "log", "integrations", "badges", "projekt", "konto", "darstellung", "docs"}}`
  - `tools/dev.py vorbereiten|einsetzen|starten|pruefen`
  - `tests/e2e/hilfen.mjs`: `daten`, `passwort`, `bilder`, `breiten`, `angemeldeteSeiten`, `anmelden(page, wer)`, `konsolenfehler(page)`, `kontrast(page)`, `werkbankGeladen(page)`
  - Umgebung der Browserprüfung: `WB_BASIS_URL`, `WB_TEST_PASSWORT`, `WB_MUSTERDATEN`, `WB_BROWSER_KANAL`, `WB_BILDER`, `WB_BREITEN`, `WB_KONSOLE_ERLAUBT`, `WB_TEST_FRIST`

- [ ] **Step 1: Musterdaten schreiben**

`tests/musterdaten.py`:
```python
"""Musterdaten für die Browserprüfung. Aufruf: ./manage.py shell < tests/musterdaten.py

Legt zwei Konten an (hell: Superuser mit heller Darstellung, dunkel:
Teammitglied mit dunkler Darstellung), zwei Projekte, Checks in jedem Zustand,
zwei Integrationen und Pings. Am Ende steht eine Zeile "MUSTERDATEN: {json}"
mit Konten, Codes und Seitenadressen. Das Passwort kommt aus WB_TEST_PASSWORT.
Alle Namen und Adressen sind erfunden; das Skript lässt sich mehrfach ausführen.
"""

import json
import os
from datetime import timedelta

from django.contrib.auth.models import User
from django.urls import reverse
from django.utils.timezone import now

from hc.accounts.models import Member, Profile, Project
from hc.api.models import Channel, Check, Flip, Ping

passwort = os.environ.get("WB_TEST_PASSWORT", "")
if len(passwort) < 12:
    raise SystemExit("WB_TEST_PASSWORT fehlt oder ist kürzer als 12 Zeichen. "
                     "tools/dev.py oder tools/ci/testinstanz.sh setzen es.")
jetzt = now()


def konto(email, theme, admin):
    nutzer, _ = User.objects.get_or_create(username=email.split("@")[0], defaults={"email": email})
    nutzer.email = email
    nutzer.is_staff = nutzer.is_superuser = admin
    nutzer.set_password(passwort)
    nutzer.save()
    profil, _ = Profile.objects.get_or_create(user=nutzer)
    profil.theme = theme
    profil.save()
    return nutzer


hell = konto("hell@example.org", "", True)
dunkel = konto("dunkel@example.org", "dark", False)


def projekt(name, schluessel):
    p = Project.objects.filter(owner=hell, name=name).first()
    if p is None:
        p = Project(owner=hell, name=name, badge_key=schluessel)
        p.save()
    Member.objects.get_or_create(user=dunkel, project=p, defaults={"role": Member.Role.REGULAR})
    return p


nord = projekt("Projekt Nord", "wb-nord")
sued = projekt("Projekt Süd", "wb-sued")


def check(projekt_, name, **felder):
    c = Check.objects.filter(project=projekt_, name=name).first() or Check(project=projekt_, name=name)
    for schluessel, wert in felder.items():
        setattr(c, schluessel, wert)
    c.save()
    return c


stunde = timedelta(hours=1)
checks = {
    "up": check(nord, "backup-nacht", tags="sicherung nord", timeout=timedelta(days=1), grace=stunde,
                status="up", last_ping=jetzt - timedelta(minutes=20), n_pings=3),
    "grace": check(nord, "zertifikate-erneuern", tags="zertifikate", timeout=timedelta(days=1),
                   grace=timedelta(hours=6), status="up", last_ping=jetzt - timedelta(days=1, hours=2)),
    "down": check(nord, "statistik-archiv", tags="statistik", timeout=timedelta(minutes=15),
                  grace=timedelta(minutes=10), status="down", last_ping=jetzt - timedelta(hours=3)),
    "started": check(nord, "replikation", tags="replikation", timeout=stunde, grace=timedelta(minutes=30),
                     status="up", last_ping=jetzt - timedelta(minutes=50), last_start=jetzt - timedelta(minutes=2)),
    "paused": check(sued, "mailing-test", tags="mailing", status="paused"),
    "new": check(sued, "neuer-lauf", kind="cron", schedule="*/5 * * * *", tz="Europe/Berlin"),
}


def kanal(name, adresse):
    k = Channel.objects.filter(project=nord, name=name).first()
    if k is None:
        k = Channel(project=nord, name=name, kind="email", email_verified=True,
                    value=json.dumps({"value": adresse, "up": True, "down": True}))
        k.save()
    return k


alarm = kanal("Alarm-Mail", "alarm@example.org")
bericht = kanal("Bericht-Mail", "bericht@example.org")
for c in checks.values():
    if c.project_id == nord.id:
        c.channel_set.add(alarm)
checks["up"].channel_set.add(bericht)

if not Ping.objects.filter(owner=checks["up"]).exists():
    for n, (vor, art, text) in enumerate([
        (timedelta(days=2), None, b"backup fertig"),
        (timedelta(days=1), "fail", b"backup abgebrochen: kein Platz auf dem Ziel"),
        (timedelta(minutes=20), None, b"backup fertig"),
    ], start=1):
        Ping.objects.create(owner=checks["up"], n=n, created=jetzt - vor, kind=art, scheme="http",
                            method="POST", remote_addr="192.0.2.10", ua="curl/8.5.0", body_raw=text)
    for vor, alt, neu in ((timedelta(days=1), "up", "down"), (timedelta(hours=23), "down", "up")):
        Flip.objects.create(owner=checks["up"], created=jetzt - vor, processed=jetzt - vor,
                            old_status=alt, new_status=neu)

seiten = {
    "anmeldung": reverse("hc-login"),
    "projekte": reverse("hc-index"),
    "checks": reverse("hc-checks", args=[nord.code]),
    "details": reverse("hc-details", args=[checks["up"].code]),
    "log": reverse("hc-log", args=[checks["up"].code]),
    "integrations": reverse("hc-channels", args=[nord.code]),
    "badges": reverse("hc-badges", args=[nord.code]),
    "projekt": reverse("hc-project-settings", args=[nord.code]),
    "konto": reverse("hc-profile"),
    "darstellung": reverse("hc-appearance"),
    "docs": reverse("hc-docs"),
}
print("MUSTERDATEN: " + json.dumps({
    "nutzer": {"hell": hell.email, "dunkel": dunkel.email},
    "projekte": [{"name": p.name, "code": str(p.code)} for p in (nord, sued)],
    "checks": {name: str(c.code) for name, c in checks.items()},
    "seiten": seiten,
}, ensure_ascii=False))
```

- [ ] **Step 2: Kopf von leiste.js anlegen**

`werkbank/static/bc/leiste.js`:
```js
/* healthchecks-werkbank: Leiste, Kopfzeile und Umschalter für die Darstellung. */
```

- [ ] **Step 3: Lokalen Aufbau schreiben**

`tools/dev.py`:
```python
#!/usr/bin/env python3
"""Lokaler Aufbau von Healthchecks mit der Werkbank, ohne Docker.

  python tools/dev.py vorbereiten   Quelle holen, venv füllen, Werkbank einsetzen, Datenbank und Musterdaten
  python tools/dev.py einsetzen     nur die Werkbank neu einsetzen (nach Änderungen in werkbank/)
  python tools/dev.py starten       Server auf WB_DEV_ADRESSE starten (vorher vorbereiten)
  python tools/dev.py pruefen       Browserprüfung gegen den laufenden Server

Einstellungen über Umgebungsvariablen; die Vorgaben stehen in VORGABEN.
Der Zugang der Musterkonten liegt in .upstream/dev-zugang.txt (nicht im Repo).
"""

from __future__ import annotations

import argparse
import json
import os
import secrets
import shutil
import subprocess
import sys
import venv
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WURZEL / "werkbank"))
import einbau  # noqa: E402
import farben  # noqa: E402

VORGABEN = {
    "HC_VERSION": "v4.4",
    "HC_REPO": "https://github.com/healthchecks/healthchecks.git",
    "WB_DEV_ADRESSE": "127.0.0.1:8000",
    "WB_DEV_SITE_ROOT": "http://localhost:8000",
    "WB_BROWSER_KANAL": "msedge",
}

UPSTREAM = WURZEL / ".upstream"
VENV = WURZEL / ".venv"
ZUGANG = UPSTREAM / "dev-zugang.txt"
MUSTERDATEN = WURZEL / "tests" / "e2e" / "ergebnisse" / "musterdaten.json"


def einstellung(name: str) -> str:
    return os.environ.get(name, VORGABEN[name])


class DevFehler(Exception):
    """Ein Problem beim lokalen Aufbau; die Meldung sagt, was zu tun ist."""


def lauf(befehl: list, **kw) -> None:
    print("$", " ".join(str(b) for b in befehl), flush=True)
    if subprocess.run([str(b) for b in befehl], **kw).returncode != 0:
        raise DevFehler(f"{Path(str(befehl[0])).name} ist gescheitert; die Ausgabe darüber nennt den Grund.")


def venv_python() -> Path:
    return VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def quelle(version: str) -> Path:
    ziel = UPSTREAM / version
    if not (ziel / "manage.py").is_file():
        UPSTREAM.mkdir(exist_ok=True)
        lauf(["git", "-c", "core.longpaths=true", "clone", "-q", "--depth", "1", "--branch", version,
              einstellung("HC_REPO"), ziel])
    return ziel


def arbeitskopie(version: str) -> Path:
    ziel = UPSTREAM / f"arbeit-{version}"
    if ziel.exists():
        shutil.rmtree(ziel)
    shutil.copytree(quelle(version), ziel, ignore=shutil.ignore_patterns(".git", "static-collected"))
    return ziel


def einsetzen(arbeit: Path) -> dict:
    werkbank = WURZEL / "werkbank"
    hausschrift = WURZEL / "vendor" / "hausschrift"
    shutil.copytree(werkbank / "templates" / "bc", arbeit / "templates" / "bc", dirs_exist_ok=True)
    bc = arbeit / "static" / "bc"
    (bc / "logo").mkdir(parents=True, exist_ok=True)
    shutil.copytree(hausschrift / "assets" / "fonts", bc / "fonts", dirs_exist_ok=True)
    for logo in (hausschrift / "assets" / "logo").glob("*.svg"):
        shutil.copy2(logo, bc / "logo" / logo.name)
    shutil.copy2(werkbank / "static" / "bc" / "leiste.js", bc / "leiste.js")
    einbau.einbauen(arbeit, einbau.lade_plan(einbau.PLAN_VORGABE), "dev")
    css, farben_css, bericht = farben.bauen(arbeit, hausschrift, werkbank, "dev")
    farben.schreibe(arbeit, css, farben_css)
    (UPSTREAM / "dev-bericht.json").write_text(json.dumps(bericht, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Werkbank eingesetzt: {bericht['deklarationen']} Farbangaben, "
          f"{len(bericht['automatisch'])} automatisch zugeordnet (Liste in .upstream/dev-bericht.json).")
    return bericht


def zugang() -> str:
    if not ZUGANG.is_file():
        UPSTREAM.mkdir(exist_ok=True)
        ZUGANG.write_text(secrets.token_hex(12), encoding="utf-8")
    return ZUGANG.read_text(encoding="utf-8").strip()


def umgebung(version: str) -> dict[str, str]:
    return dict(
        os.environ,
        DEBUG="False",
        SECRET_KEY=f"nur-lokal-{version}",
        SITE_ROOT=einstellung("WB_DEV_SITE_ROOT"),
        ALLOWED_HOSTS="localhost,127.0.0.1",
        DB_NAME=str(UPSTREAM / f"dev-{version}.sqlite"),
        REGISTRATION_OPEN="False",
        SITE_NAME="Healthchecks",
        PYTHONUTF8="1",
        PYTHONIOENCODING="utf-8",
        WB_TEST_PASSWORT=zugang(),
    )


def venv_bereit(arbeit: Path) -> Path:
    py = venv_python()
    if not py.is_file():
        venv.create(VENV, with_pip=True)
    anforderungen = [arbeit / "requirements.txt", WURZEL / "tests" / "requirements.txt"]
    stand = "".join(p.read_text(encoding="utf-8") for p in anforderungen)
    marke = VENV / ".werkbank-anforderungen"
    if not marke.is_file() or marke.read_text(encoding="utf-8") != stand:
        argumente = [x for p in anforderungen for x in ("-r", p)]
        lauf([py, "-m", "pip", "install", "-q", *argumente])
        marke.write_text(stand, encoding="utf-8")
    return py


def statische_dateien(py: Path, arbeit: Path, env: dict) -> None:
    lauf([py, "manage.py", "collectstatic", "--noinput", "-v", "0"], cwd=arbeit, env=env)
    lauf([py, "manage.py", "compress", "--force", "-v", "0"], cwd=arbeit, env=env)


def musterdaten(py: Path, arbeit: Path, env: dict) -> None:
    skript = (WURZEL / "tests" / "musterdaten.py").read_text(encoding="utf-8")
    ergebnis = subprocess.run([str(py), "manage.py", "shell"], cwd=arbeit, env=env, input=skript,
                              capture_output=True, text=True, encoding="utf-8")
    zeilen = [z for z in ergebnis.stdout.splitlines() if z.startswith("MUSTERDATEN: ")]
    if ergebnis.returncode != 0 or not zeilen:
        raise DevFehler("Die Musterdaten wurden nicht angelegt. Ausgabe von manage.py shell:\n"
                        + (ergebnis.stderr or ergebnis.stdout)[-3000:])
    MUSTERDATEN.parent.mkdir(parents=True, exist_ok=True)
    MUSTERDATEN.write_text(zeilen[-1].removeprefix("MUSTERDATEN: "), encoding="utf-8")
    print(f"Musterdaten: {MUSTERDATEN.relative_to(WURZEL)}")


def vorbereiten(version: str) -> None:
    arbeit = arbeitskopie(version)
    einsetzen(arbeit)
    py = venv_bereit(arbeit)
    env = umgebung(version)
    lauf([py, "manage.py", "migrate", "-v", "0"], cwd=arbeit, env=env)
    statische_dateien(py, arbeit, env)
    musterdaten(py, arbeit, env)


def nur_einsetzen(version: str) -> None:
    arbeit = arbeitskopie(version)
    einsetzen(arbeit)
    statische_dateien(venv_python(), arbeit, umgebung(version))
    print("Den Server neu starten, damit Django die Vorlagen neu lädt: python tools/dev.py starten")


def starten(version: str) -> None:
    arbeit = UPSTREAM / f"arbeit-{version}"
    if not (arbeit / "manage.py").is_file():
        raise DevFehler(f"{arbeit} fehlt. Zuerst python tools/dev.py vorbereiten ausführen.")
    lauf([venv_python(), "manage.py", "runserver", einstellung("WB_DEV_ADRESSE"), "--insecure", "--noreload"],
         cwd=arbeit, env=umgebung(version))


def pruefen(argumente: list[str]) -> None:
    npx = shutil.which("npx")
    if not npx:
        raise DevFehler("npx fehlt. Node.js 22 oder neuer installieren.")
    env = dict(os.environ, WB_BASIS_URL=einstellung("WB_DEV_SITE_ROOT"), WB_TEST_PASSWORT=zugang(),
               WB_MUSTERDATEN=str(MUSTERDATEN), WB_BROWSER_KANAL=einstellung("WB_BROWSER_KANAL"))
    lauf([npx, "playwright", "test", *argumente], cwd=WURZEL, env=env)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Lokaler Aufbau von Healthchecks mit der Werkbank.")
    p.add_argument("--version", default=einstellung("HC_VERSION"), help="Healthchecks-Version, etwa v4.4")
    p.add_argument("befehl", choices=["vorbereiten", "einsetzen", "starten", "pruefen"])
    p.add_argument("rest", nargs=argparse.REMAINDER, help="bei pruefen: weitere Argumente für Playwright")
    args = p.parse_args(argv)
    try:
        if args.befehl == "vorbereiten":
            vorbereiten(args.version)
        elif args.befehl == "einsetzen":
            nur_einsetzen(args.version)
        elif args.befehl == "starten":
            starten(args.version)
        else:
            pruefen(args.rest)
    except (DevFehler, einbau.EinbauFehler, farben.FarbFehler) as err:
        print(f"Abbruch: {err}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Lokal vorbereiten**

Run: `.venv/Scripts/python tools/dev.py vorbereiten`
Expected (Auszug):
```
Werkbank eingesetzt: … Farbangaben, 0 automatisch zugeordnet (Liste in .upstream/dev-bericht.json).
$ …python.exe -m pip install -q -r …requirements.txt -r …tests\requirements.txt
$ …python.exe manage.py migrate -v 0
$ …python.exe manage.py collectstatic --noinput -v 0
$ …python.exe manage.py compress --force -v 0
Musterdaten: tests\e2e\ergebnisse\musterdaten.json
```
Scheitert `pip install` an einem Paket, die Fehlermeldung lesen; `pycurl` und `psycopg` haben Wheels für Windows und Python 3.13.

- [ ] **Step 5: Browserprüfung einrichten**

`package.json`:
```json
{
  "name": "healthchecks-werkbank-pruefung",
  "private": true,
  "type": "module",
  "description": "Browserprüfung der Werkbank für Healthchecks",
  "scripts": {
    "pruefen": "playwright test"
  },
  "devDependencies": {
    "@playwright/test": "1.63.0"
  }
}
```

`playwright.config.mjs`:
```js
// Browserprüfung der Werkbank. Einstellungen über Umgebungsvariablen:
// WB_BASIS_URL (Vorgabe http://localhost:8000), WB_BROWSER_KANAL (chrome, msedge oder chromium),
// WB_TEST_FRIST (Frist je Test in Millisekunden, Vorgabe 120000).
import { defineConfig } from '@playwright/test';

const kanal = process.env.WB_BROWSER_KANAL || 'chrome';

export default defineConfig({
  testDir: './tests/e2e',
  outputDir: './tests/e2e/ergebnisse/playwright',
  fullyParallel: false,
  workers: 1,
  timeout: Number(process.env.WB_TEST_FRIST || 120000),
  reporter: [['list'], ['html', { outputFolder: 'tests/e2e/ergebnisse/bericht', open: 'never' }]],
  use: {
    baseURL: process.env.WB_BASIS_URL || 'http://localhost:8000',
    channel: kanal === 'chromium' ? undefined : kanal,
    viewport: { width: 1280, height: 900 },
    screenshot: 'only-on-failure',
  },
});
```

`tests/e2e/hilfen.mjs`:
```js
// Gemeinsame Hilfen der Browserprüfung.
import { mkdirSync, readFileSync } from 'node:fs';

export const daten = JSON.parse(readFileSync(process.env.WB_MUSTERDATEN || 'tests/e2e/ergebnisse/musterdaten.json', 'utf8'));
export const passwort = process.env.WB_TEST_PASSWORT || '';
export const bilder = process.env.WB_BILDER || 'tests/e2e/ergebnisse/bilder';
export const breiten = (process.env.WB_BREITEN || '320,390,768,1024,1280,1440').split(',').map(Number);
export const angemeldeteSeiten = Object.entries(daten.seiten).filter(([name]) => name !== 'anmeldung');

const erlaubt = process.env.WB_KONSOLE_ERLAUBT ? new RegExp(process.env.WB_KONSOLE_ERLAUBT) : null;
const kontrastSkript = readFileSync('vendor/hausschrift/scripts/check-contrast.js', 'utf8');
mkdirSync(bilder, { recursive: true });

export async function anmelden(page, wer) {
  if (!passwort) {
    throw new Error('WB_TEST_PASSWORT fehlt. Die Prüfung über tools/dev.py pruefen starten oder tools/ci/testinstanz.sh vorher laufen lassen.');
  }
  await page.goto(daten.seiten.anmeldung);
  await page.fill('#login-form input[name="email"]', daten.nutzer[wer]);
  await page.fill('#login-form input[name="password"]', passwort);
  await Promise.all([
    page.waitForURL((url) => url.pathname !== daten.seiten.anmeldung),
    page.click('#login-form button[type="submit"]'),
  ]);
}

export function konsolenfehler(page) {
  const fehler = [];
  page.on('console', (meldung) => {
    if (meldung.type() === 'error' && !(erlaubt && erlaubt.test(meldung.text()))) fehler.push(meldung.text());
  });
  page.on('pageerror', (fehlerObjekt) => fehler.push(String(fehlerObjekt)));
  return fehler;
}

export async function kontrast(page) {
  return page.evaluate(kontrastSkript);
}

export async function werkbankGeladen(page) {
  return page.evaluate(() => [...document.styleSheets].some((blatt) => (blatt.href || '').includes('/bc/werkbank.css')));
}
```

`tests/e2e/grundlage.spec.mjs`:
```js
// Grundlage: Healthchecks lädt werkbank.css, die Tokens der Hausschrift sind da.
import { test, expect } from '@playwright/test';
import { daten, konsolenfehler, werkbankGeladen } from './hilfen.mjs';

test('Anmeldeseite lädt werkbank.css mit den Tokens', async ({ page }) => {
  const fehler = konsolenfehler(page);
  const antwort = await page.goto(daten.seiten.anmeldung);
  expect(antwort.status()).toBe(200);
  expect(await werkbankGeladen(page)).toBe(true);
  const gelb = await page.evaluate(() => getComputedStyle(document.body).getPropertyValue('--bc-yellow').trim());
  expect(gelb).toBe('#fed329');
  expect(fehler).toEqual([]);
});
```

Run: `npm install`
Expected: `package-lock.json` entsteht, `@playwright/test` 1.63.0 liegt unter `node_modules/`. Browser lädt Playwright dabei keine; geprüft wird mit dem installierten Edge (lokal) bzw. Chrome (CI).

- [ ] **Step 6: Server starten und prüfen**

Den Server im Hintergrund starten (Bash mit `run_in_background`): `.venv/Scripts/python tools/dev.py starten`
Dann: `.venv/Scripts/python tools/dev.py pruefen`
Expected: `1 passed`.

- [ ] **Step 7: Commit**

```bash
git add tests/musterdaten.py tools/dev.py werkbank/static/bc/leiste.js package.json package-lock.json playwright.config.mjs tests/e2e/hilfen.mjs tests/e2e/grundlage.spec.mjs
git commit -m "Lokaler Aufbau ohne Docker, Musterdaten und erste Browserprüfung

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: Leiste, Kopfzeile und Anmeldeseite

**Files:**
- Modify: `werkbank/templates/bc/leiste.html` (Inhalt ersetzen), `werkbank/static/bc/leiste.js` (Inhalt ersetzen), `werkbank/stil.css` (anfügen)
- Test: `tests/e2e/leiste.spec.mjs`

**Interfaces:**
- Consumes: Kontext von `base.html` (`page`, `project`, `check`, `request.user`, `request.profile.theme`, `site_name`), URL-Namen `hc-index`, `hc-checks`, `hc-channels`, `hc-badges`, `hc-project-settings`, `hc-details`, `hc-projects-menu`, `hc-appearance`, `hc-docs`, `hc-profile`, `hc-login`, `hc-logout`, `admin:index`; Tag `{% site_version %}` aus `hc_extras`; Projektmenü `/projects/menu/` (`li.project-item a` mit `.status.ic-up|ic-grace|ic-down` und `.name`); Dialog `#add-project-modal`.
- Produces (DOM, auf das Task 7 und die Tests bauen): `.wb-sprung`, `.bc-brandbar`, `.wb-marke` (nur Anmeldung), `.wb-app[data-rail]` mit `data-muster`, `data-ziel-checks|integrations|badges|settings`, `data-projektmenue`, `data-darstellung`, `data-aktuell`; `#wb-leiste.bc-rail` mit `.wb-projekte > .wb-projekt[data-code] > .bc-rail__item[aria-expanded][aria-controls]` und `ul.bc-rail__sub#wb-sub-<code>`; `.wb-zustand.ic-<zustand>` und `.wb-zustand__text`; `.wb-leiste__hinweis`; `.wb-konto`; `.bc-shade`; `header.bc-topbar.wb-kopf` mit `.bc-burger`, `.bc-crumbs`, `.bc-mode [data-mode]`, `form.bc-user`; `.wb-meldung[role=alert]`; `#wb-inhalt`.

- [ ] **Step 1: Tests schreiben**

`tests/e2e/leiste.spec.mjs`:
```js
// Leiste, Kopfzeile, Anmeldeseite und Umschalter für Hell und Dunkel.
import { test, expect } from '@playwright/test';
import { anmelden, bilder, daten, konsolenfehler, kontrast } from './hilfen.mjs';

test('Anmeldeseite mit Markenfläche', async ({ page }) => {
  const fehler = konsolenfehler(page);
  await page.goto(daten.seiten.anmeldung);
  await expect(page.locator('.wb-marke')).toBeVisible();
  await expect(page.locator('#wb-leiste')).toHaveCount(0);
  await expect(page.locator('body > nav.navbar')).toBeHidden();
  await page.screenshot({ path: `${bilder}/anmeldung.png`, fullPage: true });
  const k = await kontrast(page);
  expect(k.findings, k.summary).toEqual([]);
  expect(fehler).toEqual([]);
});

test('Leiste zeigt jedes Projekt als Modul, eines ist offen', async ({ page }) => {
  await anmelden(page, 'hell');
  await page.goto(daten.seiten.checks);
  const module = page.locator('.wb-projekt > .bc-rail__item');
  await expect(module).toHaveCount(daten.projekte.length);
  await expect(module.first()).toHaveAttribute('aria-expanded', 'true');
  await expect(page.locator('.bc-rail__link[aria-current="page"]')).toHaveText('Checks');
  await module.nth(1).click();
  await expect(module.nth(1)).toHaveAttribute('aria-expanded', 'true');
  await expect(module.first()).toHaveAttribute('aria-expanded', 'false');
  const ziel = await page.locator(`#wb-sub-${daten.projekte[1].code} a`).first().getAttribute('href');
  expect(ziel).toContain(daten.projekte[1].code);
  await module.nth(1).click();
  await expect(module.nth(1)).toHaveAttribute('aria-expanded', 'false');
});

test('Zustand des Projekts steht als Punkt und als Wort in der Leiste', async ({ page }) => {
  await anmelden(page, 'hell');
  await page.goto(daten.seiten.checks);
  const nord = page.locator(`.wb-projekt[data-code="${daten.projekte[0].code}"]`);
  await expect(nord.locator('.wb-zustand')).toHaveClass(/ic-down/);
  await expect(nord.locator('.wb-zustand__text')).toHaveText(/\(down\)/);
});

test('Brotkrumen nennen Projekt und Seite', async ({ page }) => {
  await anmelden(page, 'hell');
  await page.goto(daten.seiten.log);
  const krumen = page.locator('.bc-crumbs');
  await expect(krumen).toContainText(daten.projekte[0].name);
  await expect(krumen.locator('[aria-current="page"]')).toHaveText('Log');
});

test('Sprunglink ist das erste Ziel der Tastatur', async ({ page }) => {
  await anmelden(page, 'hell');
  await page.goto(daten.seiten.checks);
  await page.keyboard.press('Tab');
  await expect(page.locator('.wb-sprung')).toBeFocused();
});

test('Leiste auf dem Handy: Menüknopf, Escape und Schleier', async ({ page }) => {
  await anmelden(page, 'hell');
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(daten.seiten.checks);
  const leiste = page.locator('#wb-leiste');
  const knopf = page.locator('.bc-burger');
  await expect(leiste).toBeHidden();
  await knopf.click();
  await expect(leiste).toBeVisible();
  await expect(knopf).toHaveAttribute('aria-expanded', 'true');
  await page.screenshot({ path: `${bilder}/leiste-handy.png` });
  await page.keyboard.press('Escape');
  await expect(leiste).toBeHidden();
  await expect(knopf).toBeFocused();
  await knopf.click();
  await page.locator('.bc-shade').click({ position: { x: 360, y: 420 } });
  await expect(leiste).toBeHidden();
});

test('Umschalter speichert die Darstellung', async ({ page }) => {
  await anmelden(page, 'hell');
  await page.goto(daten.seiten.checks);
  await page.click('.bc-mode [data-mode="dark"]');
  await expect(page.locator('body')).toHaveClass(/\bdark\b/);
  await page.reload();
  await expect(page.locator('body')).toHaveClass(/\bdark\b/);
  await page.click('.bc-mode [data-mode="light"]');
  await expect(page.locator('body')).not.toHaveClass(/\bdark\b/);
  await page.reload();
  await expect(page.locator('body')).not.toHaveClass(/\bdark\b/);
});

test('Umschalter: scheitert das Speichern, springt der Modus zurück und eine Meldung erscheint', async ({ page }) => {
  await anmelden(page, 'hell');
  await page.goto(daten.seiten.checks);
  await page.route((url) => url.pathname === daten.seiten.darstellung, (route) => route.abort());
  await page.click('.bc-mode [data-mode="dark"]');
  const meldung = page.locator('.wb-meldung');
  await expect(meldung).toBeVisible();
  await expect(meldung).toContainText('Reload the page');
  await expect(page.locator('body')).not.toHaveClass(/\bdark\b/);
});
```

- [ ] **Step 2: Tests laufen lassen, sie scheitern**

Run: `.venv/Scripts/python tools/dev.py einsetzen`, Server neu starten (Hintergrundprozess beenden, `.venv/Scripts/python tools/dev.py starten` erneut im Hintergrund), dann `.venv/Scripts/python tools/dev.py pruefen tests/e2e/leiste.spec.mjs`
Expected: FAIL, etwa `locator('.wb-marke')` nicht gefunden.

- [ ] **Step 3: Vorlage der Leiste schreiben**

`werkbank/templates/bc/leiste.html`:
```django
{% load static hc_extras %}{% comment %}
Leiste, Kopfzeile und Markenfläche von healthchecks-werkbank, Fassung @@WERKBANK_FASSUNG@@.
templates/base.html bindet diese Datei vor der Navigation von Healthchecks ein.
Texte englisch wie Healthchecks; Adressen nur über {% url %}.
{% endcomment %}
<a class="wb-sprung" href="#wb-inhalt">Skip to content</a>
<div class="bc-brandbar" aria-hidden="true"></div>
<script src="{% static 'bc/leiste.js' %}?v=@@WERKBANK_FASSUNG@@" defer></script>
{% if page == "login" %}
<aside class="wb-marke" aria-label="{{ site_name }}">
    <img src="{% static 'bc/logo/bc-logo-light-noclaim.svg' %}" alt="bright color" width="170" height="28">
    <p class="wb-marke__gruss" aria-hidden="true">Moin.</p>
    <p class="wb-marke__name">{{ site_name }}</p>
</aside>
{% else %}
{% with muster="00000000-0000-0000-0000-000000000000" %}
<div class="bc-app wb-app" data-rail="closed"
    data-muster="{{ muster }}"
    data-ziel-checks="{% url 'hc-checks' muster %}"
    data-ziel-integrations="{% url 'hc-channels' muster %}"
    data-ziel-badges="{% url 'hc-badges' muster %}"
    data-ziel-settings="{% url 'hc-project-settings' muster %}"
    {% if request.user.is_authenticated %}data-projektmenue="{% url 'hc-projects-menu' %}" data-darstellung="{% url 'hc-appearance' %}"{% endif %}
    {% if project %}data-aktuell="{{ project.code }}"{% endif %}>
    <nav class="bc-rail" id="wb-leiste" aria-label="Navigation">
        <div class="bc-rail__brand">
            <a href="{% url 'hc-index' %}"><img src="{% static 'bc/logo/bc-logo-light-noclaim.svg' %}" alt="bright color: {{ site_name }}" width="170" height="28"></a>
            <span class="bc-rail__area">{{ site_name }}</span>
        </div>
        {% if request.user.is_authenticated %}
        <ul class="bc-rail__nav wb-projekte">
            {% if project %}
            <li class="wb-projekt" data-code="{{ project.code }}">
                <button class="bc-rail__item" type="button" aria-expanded="true" aria-controls="wb-sub-{{ project.code }}">
                    <span class="wb-zustand" aria-hidden="true"></span>
                    <span class="wb-projekt__name">{{ project }}</span>
                    <span class="bc-sr wb-zustand__text"></span>
                    <svg class="bc-rail__chev" viewBox="0 0 24 24" aria-hidden="true"><path d="M9 6l6 6-6 6"/></svg>
                </button>
                <ul class="bc-rail__sub" id="wb-sub-{{ project.code }}">
                    <li><a class="bc-rail__link" href="{% url 'hc-checks' project.code %}"{% if page == "checks" %} aria-current="page"{% elif page == "details" or page == "log" %} aria-current="location"{% endif %}>Checks</a></li>
                    <li><a class="bc-rail__link" href="{% url 'hc-channels' project.code %}"{% if page == "channels" %} aria-current="page"{% endif %}>Integrations{% if project.have_channel_issues %} <span class="wb-hinweis ic-grace" title="Some integrations need attention"></span><span class="bc-sr"> (needs attention)</span>{% endif %}</a></li>
                    <li><a class="bc-rail__link" href="{% url 'hc-badges' project.code %}"{% if page == "badges" %} aria-current="page"{% endif %}>Badges</a></li>
                    <li><a class="bc-rail__link" href="{% url 'hc-project-settings' project.code %}"{% if page == "project" %} aria-current="page"{% endif %}>Settings</a></li>
                </ul>
            </li>
            {% endif %}
        </ul>
        <p class="wb-leiste__hinweis" role="status" hidden>The other projects can’t be shown right now. Reload the page to load them again.</p>
        <ul class="bc-rail__nav wb-konto">
            <li><a class="bc-rail__item" href="{% url 'hc-index' %}" data-wb-neues-projekt>New Project</a></li>
            <li><a class="bc-rail__item" href="{% url 'hc-docs' %}"{% if page == "docs" or page == "docs-cron" %} aria-current="page"{% endif %}>Docs</a></li>
            <li><a class="bc-rail__item" href="{% url 'hc-profile' %}"{% if page == "profile" or page == "appearance" %} aria-current="page"{% endif %}>Account Settings</a></li>
            {% if request.user.is_superuser %}<li><a class="bc-rail__item" href="{% url 'admin:index' %}">Site Administration</a></li>{% endif %}
            <li>
                <form method="post" action="{% url 'hc-logout' %}">{% csrf_token %}<button class="bc-rail__item" type="submit">Log Out</button></form>
            </li>
        </ul>
        {% if request.user.is_superuser %}<div class="bc-rail__foot">Healthchecks {% site_version %} · Werkbank @@WERKBANK_FASSUNG@@</div>{% endif %}
        {% else %}
        <ul class="bc-rail__nav wb-konto">
            <li><a class="bc-rail__item" href="{% url 'hc-docs' %}"{% if page == "docs" or page == "docs-cron" %} aria-current="page"{% endif %}>Docs</a></li>
            <li><a class="bc-rail__item" href="{% url 'hc-login' %}">Log In</a></li>
        </ul>
        {% endif %}
    </nav>
    <div class="bc-shade" hidden></div>
</div>
{% endwith %}
<header class="bc-topbar wb-kopf">
    <button class="bc-burger" type="button" aria-controls="wb-leiste" aria-expanded="false">
        <svg class="bc-icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M3 6h18M3 12h18M3 18h18"/></svg>
        <span class="bc-sr">Menu</span>
    </button>
    <nav class="bc-crumbs" aria-label="Breadcrumb">
        {% if project %}<a href="{% url 'hc-checks' project.code %}">{{ project }}</a><span aria-hidden="true">›</span>{% endif %}
        {% if page == "details" or page == "log" %}
            <a href="{% url 'hc-checks' project.code %}">Checks</a><span aria-hidden="true">›</span>
            {% if page == "log" %}
            <a href="{% url 'hc-details' check.code %}">{{ check.name_then_code }}</a><span aria-hidden="true">›</span><span aria-current="page">Log</span>
            {% else %}
            <span aria-current="page">{{ check.name_then_code }}</span>
            {% endif %}
        {% elif page == "checks" %}<span aria-current="page">Checks</span>
        {% elif page == "channels" %}<span aria-current="page">Integrations</span>
        {% elif page == "badges" %}<span aria-current="page">Badges</span>
        {% elif page == "project" %}<span aria-current="page">Settings</span>
        {% elif page == "profile" %}<span aria-current="page">Account Settings</span>
        {% elif page == "appearance" %}<a href="{% url 'hc-profile' %}">Account Settings</a><span aria-hidden="true">›</span><span aria-current="page">Appearance</span>
        {% elif page == "projects" %}<span aria-current="page">Projects</span>
        {% elif page == "docs" or page == "docs-cron" %}<span aria-current="page">Docs</span>
        {% else %}<span aria-current="page">{{ site_name }}</span>{% endif %}
    </nav>
    <span class="bc-topbar__spacer"></span>
    {% if request.user.is_authenticated %}
    <div class="bc-mode" role="group" aria-label="Appearance">
        <button type="button" data-mode="light" aria-pressed="{% if request.profile.theme == 'dark' %}false{% else %}true{% endif %}">
            <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>
            <span class="bc-sr">Light</span>
        </button>
        <button type="button" data-mode="dark" aria-pressed="{% if request.profile.theme == 'dark' %}true{% else %}false{% endif %}">
            <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20 14.5A8 8 0 1 1 9.5 4a6.5 6.5 0 0 0 10.5 10.5z"/></svg>
            <span class="bc-sr">Dark</span>
        </button>
    </div>
    <form class="bc-user" method="post" action="{% url 'hc-logout' %}">
        {% csrf_token %}
        <span class="bc-avatar" aria-hidden="true">{{ request.user.email|first|upper }}</span>
        <span class="bc-user__text">
            <span class="bc-user__name">{{ request.user.email }}</span>
            <button class="bc-logout" type="submit">Log Out</button>
        </span>
    </form>
    {% endif %}
</header>
<p class="wb-meldung" role="alert" hidden></p>
{% endif %}
<div id="wb-inhalt" tabindex="-1"></div>
```

- [ ] **Step 4: Skript der Leiste schreiben**

`werkbank/static/bc/leiste.js`:
```js
/* healthchecks-werkbank: Leiste, Kopfzeile und Umschalter für die Darstellung.
   Alle Adressen kommen aus data-Attributen von bc/leiste.html. */
(function () {
	'use strict';

	var app = document.querySelector('.wb-app');
	if (!app) return;
	var leiste = app.querySelector('.bc-rail');
	var schleier = app.querySelector('.bc-shade');
	var projekte = leiste.querySelector('.wb-projekte');
	var menueknopf = document.querySelector('.bc-burger');
	var meldung = document.querySelector('.wb-meldung');
	var UUID = /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/;
	var ZUSTAENDE = ['down', 'grace', 'up'];
	var UNTERPUNKTE = [
		['zielChecks', 'Checks'],
		['zielIntegrations', 'Integrations'],
		['zielBadges', 'Badges'],
		['zielSettings', 'Settings']
	];
	var TEXTE = {
		sitzung: 'Your appearance setting wasn’t saved because your session has expired or the page is outdated. Reload the page, log in if asked, and try again.',
		antwort: 'Your appearance setting wasn’t saved: Healthchecks answered with an error (HTTP {status}). Reload the page and try again; if it happens again, check the server log.',
		netz: 'Your appearance setting wasn’t saved because Healthchecks didn’t respond. Check your connection, reload the page and try again.'
	};

	/* Akkordeon: ein Modul offen; ein Klick auf das offene klappt es zu. */
	function klappe(modul) {
		var offen = modul.getAttribute('aria-expanded') === 'true';
		leiste.querySelectorAll('.wb-projekt > .bc-rail__item').forEach(function (anderes) {
			anderes.setAttribute('aria-expanded', 'false');
			var sub = document.getElementById(anderes.getAttribute('aria-controls'));
			if (sub) sub.hidden = true;
		});
		modul.setAttribute('aria-expanded', String(!offen));
		var meins = document.getElementById(modul.getAttribute('aria-controls'));
		if (meins) meins.hidden = offen;
	}

	leiste.addEventListener('click', function (ereignis) {
		var modul = ereignis.target.closest('.wb-projekt > .bc-rail__item');
		if (modul) klappe(modul);
	});

	/* Projekte aus dem Projektmenü von Healthchecks. */
	function winkel() {
		var svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
		svg.setAttribute('class', 'bc-rail__chev');
		svg.setAttribute('viewBox', '0 0 24 24');
		svg.setAttribute('aria-hidden', 'true');
		var pfad = document.createElementNS('http://www.w3.org/2000/svg', 'path');
		pfad.setAttribute('d', 'M9 6l6 6-6 6');
		svg.appendChild(pfad);
		return svg;
	}

	function setzeZustand(punkt, zustand) {
		if (!punkt) return;
		ZUSTAENDE.forEach(function (z) { punkt.classList.remove('ic-' + z); });
		punkt.classList.add('ic-' + zustand);
		var text = punkt.parentElement.querySelector('.wb-zustand__text');
		if (text) text.textContent = ' (' + zustand + ')';
	}

	function zustandAus(element) {
		for (var i = 0; i < ZUSTAENDE.length; i++) {
			if (element && element.classList.contains('ic-' + ZUSTAENDE[i])) return ZUSTAENDE[i];
		}
		return 'up';
	}

	function modul(code, name, zustand) {
		var eintrag = document.createElement('li');
		eintrag.className = 'wb-projekt';
		eintrag.dataset.code = code;
		var knopf = document.createElement('button');
		knopf.className = 'bc-rail__item';
		knopf.type = 'button';
		knopf.setAttribute('aria-expanded', 'false');
		knopf.setAttribute('aria-controls', 'wb-sub-' + code);
		var punkt = document.createElement('span');
		punkt.className = 'wb-zustand';
		punkt.setAttribute('aria-hidden', 'true');
		var titel = document.createElement('span');
		titel.className = 'wb-projekt__name';
		titel.textContent = name;
		var text = document.createElement('span');
		text.className = 'bc-sr wb-zustand__text';
		knopf.append(punkt, titel, text, winkel());
		var sub = document.createElement('ul');
		sub.className = 'bc-rail__sub';
		sub.id = 'wb-sub-' + code;
		sub.hidden = true;
		UNTERPUNKTE.forEach(function (punktDaten) {
			var li = document.createElement('li');
			var a = document.createElement('a');
			a.className = 'bc-rail__link';
			a.href = app.dataset[punktDaten[0]].split(app.dataset.muster).join(code);
			a.textContent = punktDaten[1];
			li.appendChild(a);
			sub.appendChild(li);
		});
		eintrag.append(knopf, sub);
		setzeZustand(punkt, zustand);
		return eintrag;
	}

	function ladeProjekte() {
		if (!app.dataset.projektmenue || !projekte) return;
		fetch(app.dataset.projektmenue, { credentials: 'same-origin', headers: { 'X-Requested-With': 'XMLHttpRequest' } })
			.then(function (antwort) {
				if (!antwort.ok) throw new Error('HTTP ' + antwort.status);
				return antwort.text();
			})
			.then(function (html) {
				var vorlage = document.createElement('template');
				vorlage.innerHTML = html;
				vorlage.content.querySelectorAll('li.project-item a').forEach(function (link) {
					var treffer = (link.getAttribute('href') || '').match(UUID);
					if (!treffer) return;
					var code = treffer[0];
					var zustand = zustandAus(link.querySelector('.status'));
					var vorhanden = projekte.querySelector('.wb-projekt[data-code="' + code + '"]');
					if (vorhanden) {
						setzeZustand(vorhanden.querySelector('.wb-zustand'), zustand);
						return;
					}
					var name = (link.querySelector('.name') || link).textContent.trim();
					projekte.appendChild(modul(code, name, zustand));
				});
			})
			.catch(function () {
				var hinweis = leiste.querySelector('.wb-leiste__hinweis');
				if (hinweis) hinweis.hidden = false;
			});
	}

	/* Neues Projekt: der Dialog von Healthchecks, wo die Seite ihn mitbringt. */
	var neu = leiste.querySelector('[data-wb-neues-projekt]');
	if (neu && document.getElementById('add-project-modal')) {
		neu.setAttribute('data-toggle', 'modal');
		neu.setAttribute('data-target', '#add-project-modal');
		neu.setAttribute('role', 'button');
	}

	/* Schmale Bildschirme: Menüknopf, Schleier, Escape. */
	function zeigeLeiste(offen) {
		app.setAttribute('data-rail', offen ? 'open' : 'closed');
		if (menueknopf) menueknopf.setAttribute('aria-expanded', String(offen));
		if (schleier) schleier.hidden = !offen;
		if (offen) {
			var erstes = leiste.querySelector('a[href], button');
			if (erstes) erstes.focus();
		} else if (menueknopf) {
			menueknopf.focus();
		}
	}

	if (menueknopf) {
		menueknopf.addEventListener('click', function () {
			zeigeLeiste(app.getAttribute('data-rail') !== 'open');
		});
	}
	if (schleier) schleier.addEventListener('click', function () { zeigeLeiste(false); });
	document.addEventListener('keydown', function (ereignis) {
		if (ereignis.key === 'Escape' && app.getAttribute('data-rail') === 'open') zeigeLeiste(false);
	});

	/* Hell und dunkel: dieselbe Einstellung wie im Profil von Healthchecks. */
	var modusKnoepfe = document.querySelectorAll('.bc-mode [data-mode]');

	function zeigeModus(dunkel) {
		document.body.classList.toggle('dark', dunkel);
		modusKnoepfe.forEach(function (knopf) {
			knopf.setAttribute('aria-pressed', String((knopf.dataset.mode === 'dark') === dunkel));
		});
	}

	function melde(text) {
		if (!meldung) return;
		meldung.textContent = text;
		meldung.hidden = false;
	}

	zeigeModus(document.body.classList.contains('dark'));
	modusKnoepfe.forEach(function (knopf) {
		knopf.addEventListener('click', function () {
			var vorher = document.body.classList.contains('dark');
			var dunkel = knopf.dataset.mode === 'dark';
			if (dunkel === vorher || !app.dataset.darstellung) return;
			zeigeModus(dunkel);
			var token = document.querySelector('.wb-kopf input[name="csrfmiddlewaretoken"]');
			var formular = new URLSearchParams();
			formular.set('csrfmiddlewaretoken', token ? token.value : '');
			formular.set('theme', dunkel ? 'dark' : '');
			fetch(app.dataset.darstellung, {
				method: 'POST',
				credentials: 'same-origin',
				headers: { 'X-Requested-With': 'XMLHttpRequest' },
				body: formular
			})
				.then(function (antwort) {
					if (antwort.status === 403) throw { art: 'sitzung' };
					if (!antwort.ok) throw { art: 'antwort', status: antwort.status };
					if (meldung) meldung.hidden = true;
				})
				.catch(function (fehler) {
					zeigeModus(vorher);
					var art = fehler && fehler.art ? fehler.art : 'netz';
					melde(TEXTE[art].replace('{status}', fehler && fehler.status ? fehler.status : ''));
				});
		});
	});

	ladeProjekte();
})();
```

- [ ] **Step 5: Stilschicht für Rahmen, Leiste, Kopfzeile und Anmeldung anfügen**

Ans Ende von `werkbank/stil.css`:
```css

/* Grund ------------------------------------------------------------------- */

html { background: var(--bc-ground); }

body {
	padding-top: 4px;
	font-family: var(--bc-font-text);
	font-size: var(--bc-size-body);
	line-height: var(--bc-leading);
	-webkit-font-smoothing: antialiased;
}

a { text-underline-offset: 3px; }
:focus-visible { outline: 3px solid var(--bc-focus); outline-offset: 2px; }
::selection { background: var(--bc-yellow); color: var(--bc-ink); }

.wb-sprung {
	position: absolute;
	top: -200px;
	left: 12px;
	z-index: 1100;
	padding: 8px 14px;
	background: var(--bc-yellow);
	border-radius: var(--bc-radius-sm);
	color: var(--bc-ink);
	font-weight: 700;
}

.wb-sprung:focus,
.wb-sprung:hover { top: 12px; color: var(--bc-ink); }
#wb-inhalt:focus { outline: 0; }

/* Rahmen: Leiste links, Inhalt daneben ---------------------------------------- */

body:has(.wb-app) { padding-left: var(--bc-rail-w); }

body:has(.wb-app) > .navbar,
body.page-login > .navbar { display: none; }

body:has(.wb-app) > .container,
body:has(.wb-app) > .container-fluid {
	width: auto;
	max-width: 1240px;
	margin-right: 0;
	margin-left: 0;
	padding: 28px 32px 48px;
}

body:has(.wb-app) > .container-fluid { max-width: none; }

.footer { border-top: 1px solid var(--bc-rule); color: var(--bc-text-quiet); font-size: 13px; }
.footer a { color: var(--bc-text-quiet); }

body:has(.wb-app) > .footer > .container,
body:has(.wb-app) > .footer > .container-fluid { width: auto; margin-left: 0; padding: 16px 32px; }

/* Leiste --------------------------------------------------------------------- */

.bc-rail { font-family: var(--bc-font-text); }
.bc-rail form { margin: 0; }

.bc-rail__nav.wb-konto { margin: 4px 12px 0; padding: 12px 0 24px; border-top: 1px solid var(--bc-rail-line); }

.bc-rail a.bc-rail__item,
.bc-rail a.bc-rail__link { text-decoration: none; }

.bc-rail__item[aria-current] { background: var(--bc-rail-2); color: var(--bc-white); }

.bc-rail__item[aria-current]::before {
	content: "";
	position: absolute;
	top: 8px;
	bottom: 8px;
	left: -12px;
	width: 4px;
	border-radius: 0 3px 3px 0;
	background: var(--bc-yellow);
}

.bc-rail__link[aria-current="location"] { color: var(--bc-white); }
.bc-rail__link[aria-current="location"]::before { background: var(--bc-cyan); }

.wb-projekt__name { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

.wb-zustand { flex: none; width: 10px; height: 10px; border-radius: 50%; background: var(--bc-rail-muted); }
.wb-zustand.wb-zustand::before { content: none; }
.wb-zustand.ic-up { background: var(--bc-lime); }
.wb-zustand.ic-grace { background: var(--bc-yellow); }
.wb-zustand.ic-down { background: var(--bc-pink); }

.wb-hinweis { color: var(--bc-yellow); font-size: 12px; }
.wb-leiste__hinweis { margin: 0 22px 12px; color: var(--bc-rail-text); font-size: 12.5px; line-height: 1.4; }
.bc-rail__foot { font-family: var(--bc-font-mono); font-size: 11px; }

/* Kopfzeile -------------------------------------------------------------------- */

.wb-kopf form.bc-user { margin: 0; }

.wb-meldung {
	margin: 0;
	padding: 12px 32px;
	background: var(--bc-bad-tint);
	border-bottom: 1px solid var(--bc-pink);
	color: var(--bc-text);
	font-weight: 700;
}

/* Anmeldeseite: Onyx-Fläche links, Karte rechts ------------------------------------ */

body.page-login { padding-left: 50vw; }

.wb-marke {
	position: fixed;
	top: 4px;
	bottom: 0;
	left: 0;
	display: flex;
	flex-direction: column;
	justify-content: space-between;
	gap: var(--bc-space-4);
	width: 50vw;
	padding: 48px;
	background: var(--bc-ink);
	color: var(--bc-on-ink);
}

.wb-marke img { display: block; width: 170px; height: auto; }

.wb-marke__gruss {
	margin: 0;
	font-family: var(--bc-font-display);
	font-size: clamp(3rem, 2rem + 4vw, 5.5rem);
	line-height: 1.06;
	letter-spacing: .015em;
	text-transform: uppercase;
	color: var(--bc-on-ink);
}

.wb-marke__name { margin: 0; color: var(--bc-on-ink-quiet); font-size: 11px; letter-spacing: .14em; text-transform: uppercase; }

body.page-login > .container { width: auto; max-width: 34rem; margin: 0 auto; padding: 48px 24px; }
body.page-login > .footer > .container { width: auto; }

/* Schmale Bildschirme: Rahmen ---------------------------------------------------- */

@media (max-width: 900px) {
	body:has(.wb-app) { padding-left: 0; }

	body:has(.wb-app) > .container,
	body:has(.wb-app) > .container-fluid { padding: 20px 16px 40px; }

	body:has(.wb-app) > .footer > .container,
	body:has(.wb-app) > .footer > .container-fluid { padding: 16px; }

	.wb-meldung { padding: 12px 16px; }
	body.page-login { padding-left: 0; }
	.wb-marke { position: static; width: auto; padding: 32px 24px; }
	.wb-marke__gruss { font-size: 3rem; }
}

@media (prefers-reduced-motion: reduce) {
	.bc-rail,
	.bc-rail__chev,
	.bc-rail__item { transition: none !important; }
}
```

- [ ] **Step 6: Einsetzen, neu starten, Tests bestehen**

Run: `.venv/Scripts/python tools/dev.py einsetzen`, Server neu starten, dann `.venv/Scripts/python tools/dev.py pruefen tests/e2e/leiste.spec.mjs tests/e2e/grundlage.spec.mjs`
Expected: `9 passed`. Scheitert der Test zum Zustand, in der Konsole von Edge den Abruf von `/projects/menu/` prüfen.

- [ ] **Step 7: Bilder ansehen**

`tests/e2e/ergebnisse/bilder/anmeldung.png` und `leiste-handy.png` mit dem Read-Werkzeug ansehen. Prüfen: Logo in der Leiste und auf der Markenfläche, „MOIN.“ in Anton, gelbe Kante am offenen Projekt, Cyan-Punkt am aktuellen Eintrag, Vierfarbband oben, Kopfzeile mit Brotkrumen und Umschalter. Abweichungen in `stil.css` beheben, einsetzen, neu starten, Tests wiederholen.

- [ ] **Step 8: Lint und Commit**

Run: `.venv/Scripts/python vendor/hausschrift/scripts/bc_check.py lint werkbank --variant workbench`
Expected: `0 Warnung(en)`.

```bash
git add werkbank/templates/bc/leiste.html werkbank/static/bc/leiste.js werkbank/stil.css tests/e2e/leiste.spec.mjs
git commit -m "Leiste mit Projekten als Akkordeon, Kopfzeile, Umschalter, Anmeldeseite

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7: Stilschicht für den Inhalt, Handy-Listen und Prüfung aller Seiten

**Files:**
- Modify: `werkbank/stil.css` (anfügen), `werkbank/farben.json` (nur bei Befunden: Einträge unter `selektoren`)
- Test: `tests/e2e/seiten.spec.mjs`

**Interfaces:**
- Consumes: DOM aus Task 6; Markup von Healthchecks: `#checks-table` (erste Zeile Kopf, Zeilen `tr.checks-row` mit 7 Zellen: Zustand, Name mit Tags, Ping-Adresse, Integrationen, Zeitplan mit Karenz, letzter Ping, Aktionen), `.channels-table` (Zeilen `tr.channel-row` mit 6 Zellen: Symbol, Name, zugeordnete Checks, Status, letzte Benachrichtigung, Aktionen), `#log` (Zeilen mit Nummer, Datum, Uhrzeit, Ereignis, Einzelheiten), Bootstrap-3-Klassen.
- Produces: fertige `werkbank.css`; Bilder unter `tests/e2e/ergebnisse/bilder/`.

- [ ] **Step 1: Tests schreiben**

`tests/e2e/seiten.spec.mjs`:
```js
// Jede Seite hell und dunkel, Kontrast, Breiten ohne Querscrollen, Listen auf dem Handy.
import { test, expect } from '@playwright/test';
import { anmelden, angemeldeteSeiten, bilder, breiten, daten, konsolenfehler, kontrast, werkbankGeladen } from './hilfen.mjs';

for (const wer of ['hell', 'dunkel']) {
  for (const [name, pfad] of angemeldeteSeiten) {
    test(`${name} ${wer}`, async ({ page }) => {
      const fehler = konsolenfehler(page);
      await anmelden(page, wer);
      const antwort = await page.goto(pfad);
      expect(antwort.status(), `${pfad} antwortet`).toBe(200);
      await page.waitForLoadState('networkidle');
      await expect(page.locator('#wb-leiste')).toBeVisible();
      await expect(page.locator('body > nav.navbar')).toBeHidden();
      expect(await werkbankGeladen(page), 'werkbank.css ist geladen').toBe(true);
      expect(await page.evaluate(() => document.body.classList.contains('dark'))).toBe(wer === 'dunkel');
      await page.screenshot({ path: `${bilder}/${name}-${wer}.png`, fullPage: true });
      const k = await kontrast(page);
      expect(k.findings, `Kontrast ${name} ${wer}: ${k.summary}`).toEqual([]);
      expect(fehler, 'Konsole ohne Fehler').toEqual([]);
    });
  }
}

for (const breite of breiten) {
  test(`Breite ${breite} px ohne Querscrollen`, async ({ page }) => {
    await anmelden(page, 'hell');
    await page.setViewportSize({ width: breite, height: 900 });
    const zuBreit = [];
    for (const [name, pfad] of angemeldeteSeiten) {
      await page.goto(pfad);
      await page.waitForLoadState('networkidle');
      const ueber = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
      if (ueber > 0) zuBreit.push(`${name}: ${ueber} px zu breit`);
      if (breite <= 390) await page.screenshot({ path: `${bilder}/${name}-${breite}.png`, fullPage: true });
    }
    expect(zuBreit).toEqual([]);
  });
}

test('Check-Liste auf dem Handy zweizeilig', async ({ page }) => {
  await anmelden(page, 'hell');
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(daten.seiten.checks);
  const zeile = page.locator('#checks-table tr.checks-row').first();
  const name = await zeile.locator('td').nth(1).boundingBox();
  const ping = await zeile.locator('td').nth(5).boundingBox();
  expect(ping, 'letzter Ping ist sichtbar').not.toBeNull();
  expect(ping.width).toBeGreaterThan(0);
  expect(ping.y, 'letzter Ping steht unter dem Namen').toBeGreaterThanOrEqual(name.y + name.height - 2);
});

test('Integrationen auf dem Handy zweizeilig', async ({ page }) => {
  await anmelden(page, 'hell');
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(daten.seiten.integrations);
  const zeile = page.locator('.channels-table tr.channel-row').first();
  const name = await zeile.locator('td').nth(1).boundingBox();
  const status = await zeile.locator('td').nth(3).boundingBox();
  expect(status, 'Status ist sichtbar').not.toBeNull();
  expect(status.y, 'Status steht unter dem Namen').toBeGreaterThanOrEqual(name.y + name.height - 2);
});
```

- [ ] **Step 2: Tests laufen lassen und Befunde notieren**

Run: `.venv/Scripts/python tools/dev.py pruefen tests/e2e/seiten.spec.mjs`
Expected: FAIL. Typische Befunde: Querscrollen (feste Breite von `.container`), einzeilige Listen auf dem Handy, Kontrast auf Bootstrap-Bausteinen.

- [ ] **Step 3: Stilschicht für den Inhalt anfügen**

Ans Ende von `werkbank/stil.css`:
```css

/* Schrift ---------------------------------------------------------------------- */

h1, h2, .h1, .h2, .modal-title {
	font-family: var(--bc-font-display);
	font-weight: 400;
	line-height: 1.06;
	letter-spacing: .02em;
	text-transform: uppercase;
	color: var(--bc-text-loud);
}

h1, .h1 { font-size: var(--bc-size-h1); }
h2, .h2 { font-size: var(--bc-size-h2); letter-spacing: .03em; }
.modal-title { font-size: 19px; letter-spacing: .03em; }

h3, h4, h5, h6, .h3, .h4, .h5, .h6 { font-family: var(--bc-font-text); font-weight: 700; color: var(--bc-text-loud); }

code, kbd, pre, samp, .my-checks-url, .cron-expression, .highlight { font-family: var(--bc-font-mono); }
code { padding: .05em .35em; background: var(--bc-head); border: 1px solid var(--bc-rule); border-radius: 4px; color: var(--bc-text); font-size: .875em; }
pre { border-color: var(--bc-rule); border-radius: var(--bc-radius-sm); }
pre code { padding: 0; background: transparent; border: 0; }

/* Karten, Dialoge, Menüs ------------------------------------------------------- */

.panel { background-color: var(--panel-bg); border: 1px solid var(--bc-rule); border-radius: var(--bc-radius); box-shadow: var(--bc-shadow); }
.panel > .panel-heading { border-radius: var(--bc-radius) var(--bc-radius) 0 0; }
.panel > .panel-footer { border-radius: 0 0 var(--bc-radius) var(--bc-radius); }
.panel-heading, .panel-footer { border-color: var(--bc-rule); }

.modal-content { background-color: var(--modal-content-bg); border: 1px solid var(--bc-rule); border-radius: var(--bc-radius); box-shadow: var(--bc-shadow-pop); }
.modal-header, .modal-footer { border-color: var(--bc-rule); }

.dropdown-menu { border: 1px solid var(--bc-rule); border-radius: var(--bc-radius-sm); box-shadow: var(--bc-shadow-pop); }

.tooltip-inner { background-color: var(--bc-ink); border-radius: 6px; color: var(--bc-white); }
.tooltip.top .tooltip-arrow { border-top-color: var(--bc-ink); }
.tooltip.right .tooltip-arrow { border-right-color: var(--bc-ink); }
.tooltip.bottom .tooltip-arrow { border-bottom-color: var(--bc-ink); }
.tooltip.left .tooltip-arrow { border-left-color: var(--bc-ink); }

.nav-tabs { border-bottom-color: var(--bc-rule); }
.nav-tabs > li > a { border-radius: 0; color: var(--bc-text-quiet); }

.nav-tabs > li.active > a,
.nav-tabs > li.active > a:hover,
.nav-tabs > li.active > a:focus {
	background: transparent;
	border: 0;
	border-bottom: 3px solid var(--bc-magenta);
	color: var(--bc-text-loud);
	font-weight: 700;
}

/* Knöpfe ------------------------------------------------------------------------ */

.btn { border-radius: var(--bc-radius-sm); font-weight: 700; }
.btn:where(:not(.btn-sm, .btn-xs, .btn-lg, .btn-link)) { padding-top: 8px; padding-bottom: 8px; }

.btn-primary,
.btn-primary:focus,
.btn-primary.focus { background-color: var(--bc-primary); border-color: var(--bc-primary); color: var(--bc-on-primary); }

.btn-primary:hover,
.btn-primary:active,
.btn-primary.active,
.btn-primary:active:hover,
.btn-primary:active:focus,
.open > .dropdown-toggle.btn-primary { background-color: var(--bc-primary-deep); border-color: var(--bc-primary-deep); color: var(--bc-on-primary); }

.btn-primary.disabled,
.btn-primary[disabled],
.btn-primary.disabled:hover,
.btn-primary[disabled]:hover { background-color: var(--bc-primary); border-color: var(--bc-primary); color: var(--bc-on-primary); }

.btn-success,
.btn-success:focus { background-color: var(--bc-lime); border-color: var(--bc-lime); color: var(--bc-ink); }

.btn-success:hover,
.btn-success:active,
.btn-success.active { background-color: var(--bc-ok-deep); border-color: var(--bc-ok-deep); color: var(--bc-ink); }

.btn-warning,
.btn-warning:focus { background-color: var(--bc-yellow); border-color: var(--bc-yellow); color: var(--bc-ink); }

.btn-warning:hover,
.btn-warning:active,
.btn-warning.active { background-color: var(--bc-primary-deep); border-color: var(--bc-primary-deep); color: var(--bc-ink); }

.btn-info,
.btn-info:focus { background-color: var(--bc-cyan); border-color: var(--bc-cyan); color: var(--bc-deep); }

.btn-info:hover,
.btn-info:active,
.btn-info.active { background-color: var(--bc-cyan); border-color: var(--bc-deep); color: var(--bc-deep); }

.btn-danger,
.btn-danger:focus { background-color: var(--bc-pink); border-color: var(--bc-pink); color: var(--bc-white); }

.btn-danger:hover,
.btn-danger:active,
.btn-danger.active,
.btn-danger:active:hover { background-color: var(--bc-bad-deep); border-color: var(--bc-bad-deep); color: var(--bc-white); }

/* Felder ------------------------------------------------------------------------ */

.form-control {
	background-color: var(--bc-control);
	border-color: var(--bc-field-edge);
	border-radius: var(--bc-radius-sm);
	box-shadow: none;
	color: var(--bc-text);
}

.form-control:where(:not(.input-sm, .input-lg, textarea, select[multiple])) { height: 38px; }
.form-control:focus { border-color: var(--bc-focus); box-shadow: 0 0 0 3px var(--wb-fokus-hof); outline: 0; }
.form-control::placeholder { color: var(--bc-text-quiet); opacity: 1; }

.input-group-addon { background-color: var(--bc-head); border-color: var(--bc-field-edge); color: var(--bc-text-quiet); font-weight: 700; }

.input-group .form-control:first-child,
.input-group-addon:first-child,
.input-group-btn:first-child > .btn { border-radius: var(--bc-radius-sm) 0 0 var(--bc-radius-sm); }

.input-group .form-control:last-child,
.input-group-addon:last-child,
.input-group-btn:last-child > .btn { border-radius: 0 var(--bc-radius-sm) var(--bc-radius-sm) 0; }

.help-block { color: var(--bc-text-quiet); }
.has-error .form-control { border-color: var(--bc-pink); }
.has-error .form-control:focus { box-shadow: 0 0 0 3px color-mix(in srgb, var(--bc-pink) 18%, transparent); }
.has-error .help-block, .has-error .control-label { color: var(--bc-bad-text); }

/* Etiketten und Zustände ---------------------------------------------------------- */

.label { padding: .2em .7em .25em; border-radius: 99px; font-size: 11.5px; font-weight: 700; letter-spacing: .02em; }
.label-success, .label-primary { background-color: var(--bc-lime); color: var(--bc-ink); }
.label-warning { background-color: var(--bc-yellow); color: var(--bc-ink); }
.label-danger { background-color: var(--bc-pink); color: var(--bc-white); }
.label-info { background-color: var(--bc-cyan); color: var(--bc-deep); }
.label-default { background-color: var(--bc-head); box-shadow: inset 0 0 0 1px var(--bc-rule); color: var(--bc-text-quiet); }

.status.ic-up { color: var(--wb-zustand-up); }
.status.ic-grace { color: var(--wb-zustand-grace); }
.status.ic-down { color: var(--wb-zustand-down); }
.status.ic-new, .status.ic-paused { color: var(--status-new-color); }

.spinner.started { animation-name: wb-puls; }

@keyframes wb-puls {
	0%, 100% {
		background: color-mix(in srgb, var(--wb-zustand-started) 30%, transparent);
		box-shadow: 8px 0 var(--wb-zustand-started), -8px 0 transparent;
	}
	50% {
		background: var(--wb-zustand-started);
		box-shadow: 8px 0 transparent, -8px 0 var(--wb-zustand-started);
	}
}

/* Hinweise -------------------------------------------------------------------- */

.alert { background-color: var(--bc-surface); border: 1px solid var(--bc-rule); border-left-width: 4px; border-radius: var(--bc-radius-sm); color: var(--bc-text); }
.alert a, .alert .alert-link { color: var(--bc-link); }
.alert-success { background-color: var(--wb-ok-tint); border-left-color: var(--bc-lime); }
.alert-info { background-color: var(--wb-info-tint); border-left-color: var(--bc-cyan); }
.alert-warning { background-color: var(--wb-warn-tint); border-left-color: var(--bc-yellow); }
.alert-danger { background-color: var(--bc-bad-tint); border-color: var(--bc-pink); }

/* Tabellen -------------------------------------------------------------------- */

.table > tbody > tr > td,
.table > thead > tr > th { border-top-color: var(--bc-rule-soft); vertical-align: middle; }

#checks-table > tbody > tr:first-child > th,
.channels-table > tbody > tr:first-child > th,
.table > thead > tr > th {
	background-color: var(--bc-head);
	border-bottom: 1px solid var(--bc-rule);
	color: var(--bc-text-quiet);
	font-size: 11px;
	font-weight: 700;
	letter-spacing: .12em;
	text-transform: uppercase;
}

#checks-table > tbody > tr:first-child > th a { color: var(--bc-text-quiet); }

/* Listen auf dem Handy: oben der Titel, darunter leise der Rest --------------------- */

@media (max-width: 640px) {
	#checks-table,
	#checks-table > tbody,
	.channels-table,
	.channels-table > tbody,
	#log,
	#log > tbody { display: block; }

	#checks-table > tbody > tr:first-child,
	.channels-table > tbody > tr:first-child { display: none; }

	#checks-table > tbody > tr.checks-row {
		position: relative;
		display: flex;
		flex-wrap: wrap;
		align-items: baseline;
		gap: 2px 6px;
		padding: 10px 76px 10px 32px;
		border-top: 1px solid var(--bc-rule-soft);
	}

	#checks-table > tbody > tr.checks-row > td { display: block; padding: 0; border: 0; }
	#checks-table > tbody > tr.checks-row > td:nth-child(1) { position: absolute; top: 12px; left: 4px; }
	#checks-table > tbody > tr.checks-row > td:nth-child(2) { flex: 1 0 100%; min-width: 0; font-weight: 700; }

	#checks-table > tbody > tr.checks-row > td:nth-child(3),
	#checks-table > tbody > tr.checks-row > td:nth-child(4) { display: none !important; }

	#checks-table > tbody > tr.checks-row > td.hidden-xs:nth-child(5),
	#checks-table > tbody > tr.checks-row > td.hidden-xs:nth-child(6) { display: block !important; color: var(--bc-text-quiet); font-size: 13px; }

	#checks-table > tbody > tr.checks-row > td:nth-child(6) { order: 1; }
	#checks-table > tbody > tr.checks-row > td:nth-child(5) { order: 2; min-width: 0; }
	#checks-table > tbody > tr.checks-row > td:nth-child(5)::before { content: "· "; }
	#checks-table > tbody > tr.checks-row > td:nth-child(7) { position: absolute; top: 8px; right: 4px; }

	#checks-table > tbody > tr.checks-row br,
	#checks-table > tbody > tr.checks-row .checks-subline { display: none; }

	#checks-table > tbody > tr.checks-row .cron-expression,
	#checks-table > tbody > tr.checks-row .timeout-grace,
	#checks-table > tbody > tr.checks-row .last-ping { display: inline; }

	.channels-table > tbody > tr.channel-row {
		position: relative;
		display: flex;
		flex-wrap: wrap;
		align-items: baseline;
		gap: 2px 6px;
		padding: 12px 4px 12px 44px;
		border-top: 1px solid var(--bc-rule-soft);
	}

	.channels-table > tbody > tr.channel-row > td { display: block; padding: 0; border: 0; color: var(--bc-text-quiet); font-size: 13px; }
	.channels-table > tbody > tr.channel-row > td:nth-child(1) { position: absolute; top: 12px; left: 4px; }
	.channels-table > tbody > tr.channel-row > td:nth-child(2) { flex: 1 0 100%; min-width: 0; color: var(--bc-text); font-size: inherit; font-weight: 700; }
	.channels-table > tbody > tr.channel-row > td:nth-child(3)::before { content: "Checks "; }
	.channels-table > tbody > tr.channel-row .edit-checks { display: inline; }

	.channels-table > tbody > tr.channel-row > td:nth-child(4)::before,
	.channels-table > tbody > tr.channel-row > td:nth-child(5)::before { content: "· "; }

	.channels-table > tbody > tr.channel-row > td:nth-child(6) { flex: 1 0 100%; margin-top: 8px; }
	.channels-table > tbody > tr.channel-row > td.actions form { display: inline; }

	#log > tbody > tr {
		display: flex;
		flex-wrap: wrap;
		align-items: baseline;
		gap: 2px 8px;
		padding: 8px 0;
		border-top: 1px solid var(--bc-rule-soft);
	}

	#log > tbody > tr > td { display: block; padding: 0; border: 0; white-space: normal; }
	#log > tbody > tr > td:empty { display: none; }
	#log > tbody > tr > td:nth-child(1) { color: var(--bc-text-quiet); font-size: 12px; }
	#log > tbody > tr > td:nth-child(4) { order: -1; }
	#log > tbody > tr > td:last-child { flex: 1 0 100%; color: var(--bc-text-quiet); font-size: 13px; overflow-wrap: anywhere; }
}

@media (prefers-reduced-motion: reduce) {
	.spinner.started { animation: none; background: var(--wb-zustand-started); }
}
```

- [ ] **Step 4: Einsetzen, neu starten, prüfen**

Run: `.venv/Scripts/python tools/dev.py einsetzen`, Server neu starten, `.venv/Scripts/python tools/dev.py pruefen`
Expected: alle Tests grün. Bei Befunden Step 5.

- [ ] **Step 5: Befunde beheben, bis alles grün ist**

Für jeden Befund nach diesem Muster vorgehen und danach Step 4 wiederholen:
- **Kontrast:** Der Befund nennt Stelle (`where`), Schrift- und Flächenfarbe. Kommt die Farbe aus der Ableitung, unter `selektoren` in `werkbank/farben.json` eine Rolle für genau diesen Selektor eintragen, etwa `".btn-default .badge": {"text": {"#ffffff": "var(--bc-text-loud)"}}`. Ist der Baustein insgesamt falsch gestaltet, eine Regel im passenden Abschnitt von `stil.css` ergänzen. Danach mit `vendor/hausschrift/scripts/bc_check.py contrast <Schrift> <Fläche>` gegenrechnen: Schrift ab 4,8:1.
- **Querscrollen:** Auf dem Bild der Breite das breite Element suchen; im Browser von `tools/dev.py starten` mit `document.querySelectorAll('*')` nach `scrollWidth > clientWidth` suchen und das Element in `stil.css` einfassen (`min-width: 0`, `overflow-wrap: anywhere`, oder bei echten Datentabellen `overflow-x: auto` am Rahmen).
- **Konsole:** Fehler von Healthchecks selbst, die ohne die Werkbank genauso auftreten, über `WB_KONSOLE_ERLAUBT` (regulärer Ausdruck) zulassen und im Commit-Text nennen; Fehler aus `leiste.js` beheben.

- [ ] **Step 6: Bilder durchgehen**

Jedes Bild unter `tests/e2e/ergebnisse/bilder/` mit dem Read-Werkzeug ansehen, zuerst `checks-hell.png`, `checks-dunkel.png`, `details-hell.png`, `log-dunkel.png`, `integrations-hell.png`, `projekt-hell.png`, `konto-dunkel.png`, `docs-hell.png`, dann die Handy-Bilder `*-390.png` und `*-320.png`. Prüfen:
1. Knopfbeschriftungen sichtbar; Hauptknöpfe gelb mit Tinte, Löschen pink mit Weiß.
2. Anton nur in Versalien und nur in Seiten-, Karten- und Dialogtiteln.
3. Zustände in der Hausampel: up olivgrün bzw. Limette, grace gelbbraun bzw. Gelb, down pink, laufend cyanfarbene Pulse.
4. Karten 12 px rund, Felder und Knöpfe 8 px, weicher Kartenschatten.
5. Handy: Check-Liste und Integrationen zweizeilig, nichts läuft rechts aus dem Bild.
6. Codehervorhebung in den Docs lesbar, hell und dunkel.
Abweichungen wie in Step 5 beheben.

- [ ] **Step 7: Alle Prüfungen zusammen**

```bash
.venv/Scripts/python -m pytest -q
.venv/Scripts/python vendor/hausschrift/scripts/bc_check.py lint werkbank --variant workbench
.venv/Scripts/python tools/dev.py pruefen
```
Expected: pytest grün, Lint `0 Warnung(en)`, Playwright alle Tests grün.

- [ ] **Step 8: Commit**

```bash
git add werkbank/stil.css werkbank/farben.json tests/e2e/seiten.spec.mjs
git commit -m "Stilschicht für Karten, Knöpfe, Felder, Zustände, Tabellen und Handy-Listen

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 8: Update-Skript für docker-a1

**Files:**
- Create: `deploy/hc-werkbank-update`, `deploy/hc-werkbank-update.service`, `deploy/hc-werkbank-update.timer`, `deploy/hc-werkbank-update.logrotate`, `deploy/hc-werkbank.conf.beispiel`
- Create: `tests/update/probe.sh`, `tests/update/kaputt.sh`, `tests/update/markierung.py` (laufen in der CI, Task 9)
- Test: `tests/test_update_einstellungen.py`

**Interfaces:**
- Produces: `hc-werkbank-update [--einstellungen DATEI] [--nur-pruefen]` mit Rückgabe 0/1/2/3; Einstellungen `IMAGE`, `TRACK_TAG`, `COMPOSE_DIR`, `SERVICE`, `TAG_VARIABLE`, `DB_PATH`, `BACKUP_DIR`, `BACKUP_KEEP` (1–100), `WAIT_SECONDS` (30–1800), `APP_PORT` (1–65535), `CHECK_PATHS`, `CHECK_TIMEOUT` (1–120), `STYLE_MARKER`, `LOG_FILE`, `LOCK_FILE`; Umgebung `HC_WERKBANK_EINSTELLUNGEN` (Pfad der Datei) und `HC_WERKBANK_BESITZ_PRUEFEN=nein` (nur für Tests ohne root). Die Spec nennt `CHECK_TIMEOUT` und `LOCK_FILE` noch nicht; Task 10 trägt sie in README und Spec nach.
- Produces für Task 9: `tests/update/probe.sh <Image>` (Rückgabe 0 bei bestandener Probe).

- [ ] **Step 1: Tests schreiben**

`tests/test_update_einstellungen.py`:
```python
"""Prüfung der Einstellungen von deploy/hc-werkbank-update mit --nur-pruefen, ohne Docker."""
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

WURZEL = Path(__file__).resolve().parent.parent
SKRIPT = WURZEL / "deploy" / "hc-werkbank-update"
BASH = os.environ.get("WB_BASH") or shutil.which("bash")
pytestmark = pytest.mark.skipif(BASH is None, reason="bash fehlt; WB_BASH auf den Pfad von bash setzen")


def posix(pfad: Path) -> str:
    """Pfad so, wie bash ihn versteht (Git Bash unter Windows: /c/...)."""
    text = pfad.as_posix()
    m = re.match(r"^([A-Za-z]):/(.*)$", text)
    return f"/{m.group(1).lower()}/{m.group(2)}" if (m and os.name == "nt") else text


@pytest.fixture
def aufbau(tmp_path):
    hc = tmp_path / "hc"
    hc.mkdir()
    (hc / "compose.yaml").write_text("services:\n  healthchecks:\n    image: x:${HC_IMAGE_TAG}\n", encoding="utf-8")
    (hc / ".env").write_text("HC_IMAGE_TAG=4.4-wb1.0.0\nDB_NAME=/data/hc.sqlite\n", encoding="utf-8")
    return tmp_path


def lauf(aufbau, *zeilen, mit_datei=True):
    datei = aufbau / "einstellungen.conf"
    if mit_datei:
        datei.write_text("\n".join([f"COMPOSE_DIR={posix(aufbau / 'hc')}", *zeilen]) + "\n", encoding="utf-8")
    env = dict(os.environ, HC_WERKBANK_BESITZ_PRUEFEN="nein")
    return subprocess.run([BASH, posix(SKRIPT), "--einstellungen", posix(datei), "--nur-pruefen"],
                          capture_output=True, text=True, encoding="utf-8", env=env)


def test_gueltige_einstellungen_auch_abseits_der_vorgaben(aufbau):
    erg = lauf(aufbau, "IMAGE=localhost:5000/hcwb", "TRACK_TAG=stabil", "SERVICE=hc", "BACKUP_KEEP=1",
               "WAIT_SECONDS=1800", "APP_PORT=9000", 'CHECK_PATHS="/api/v3/status/ /x/"', "CHECK_TIMEOUT=120",
               "STYLE_MARKER=werkbank", "LOG_FILE=/tmp/wb.log", "LOCK_FILE=/tmp/wb.lock", "DB_PATH=/daten/x.sqlite",
               "# Kommentar", "")
    assert erg.returncode == 0, erg.stderr
    assert "Einstellungen in Ordnung" in erg.stdout


@pytest.mark.parametrize("zeile, meldung", [
    ("BACKUP_KEEP=0", "BACKUP_KEEP ist 0. Erlaubt sind ganze Zahlen von 1 bis 100."),
    ("BACKUP_KEEP=101", "BACKUP_KEEP ist 101."),
    ("BACKUP_KEEP=zehn", "BACKUP_KEEP ist zehn."),
    ("WAIT_SECONDS=29", "WAIT_SECONDS ist 29. Erlaubt sind ganze Zahlen von 30 bis 1800."),
    ("APP_PORT=70000", "APP_PORT ist 70000."),
    ("CHECK_TIMEOUT=0", "CHECK_TIMEOUT ist 0."),
    ("IMAGE=ghcr.io/brightcolor/healthchecks-werkbank:latest", "ohne Tag"),
    ("TRACK_TAG=la test", "TRACK_TAG ist la test."),
    ("CHECK_PATHS=api/status", "Der Pfad api/status beginnt nicht mit /"),
    ("LOG_FILE=relativ.log", "LOG_FILE ist relativ.log. Erwartet ist ein absoluter Pfad"),
    ("TAG_VARIABLE=FEHLT", "fehlt die Zeile FEHLT="),
    ("TAG_VARIABLE=klein", "Variablenname in Großbuchstaben"),
    ("SERVICE=-x", "SERVICE ist -x."),
    ("STYLE_MARKER=", "STYLE_MARKER ist leer."),
    ("UNBEKANNT=1", "Unbekannte Einstellung UNBEKANNT"),
    ("ohne gleichheitszeichen", "hat nicht die Form NAME=Wert"),
])
def test_ungueltige_einstellung(aufbau, zeile, meldung):
    erg = lauf(aufbau, zeile)
    assert erg.returncode == 2, erg.stdout
    assert meldung in erg.stderr
    assert "Es wurde nichts geändert." in erg.stderr


def test_db_path_fehlt_ohne_db_name(aufbau):
    (aufbau / "hc" / ".env").write_text("HC_IMAGE_TAG=4.4-wb1.0.0\n", encoding="utf-8")
    erg = lauf(aufbau)
    assert erg.returncode == 2
    assert "DB_PATH ist leer" in erg.stderr


def test_compose_dir_ohne_compose_datei(aufbau):
    (aufbau / "hc" / "compose.yaml").unlink()
    erg = lauf(aufbau)
    assert erg.returncode == 2
    assert "keine compose.yaml" in erg.stderr


def test_ohne_datei_gelten_die_vorgaben(aufbau):
    erg = lauf(aufbau, mit_datei=False)
    assert erg.returncode == 2
    assert "Den Ordner /opt/healthchecks gibt es nicht." in erg.stderr


def test_unbekannte_option():
    erg = subprocess.run([BASH, posix(SKRIPT), "--sofort"], capture_output=True, text=True, encoding="utf-8")
    assert erg.returncode == 2
    assert "Unbekannte Option --sofort" in erg.stderr
```

- [ ] **Step 2: Tests laufen lassen, sie scheitern**

Run: `.venv/Scripts/python -m pytest tests/test_update_einstellungen.py -q`
Expected: FAIL, bash meldet `No such file or directory` für `deploy/hc-werkbank-update`.

- [ ] **Step 3: Skript schreiben**

`deploy/hc-werkbank-update`:
```bash
#!/usr/bin/env bash
# hc-werkbank-update: holt die neueste Fassung von healthchecks-werkbank und
# spielt sie mit Sicherung der Datenbank und Rückweg ein.
#
# Aufruf:   hc-werkbank-update [--einstellungen DATEI] [--nur-pruefen]
# Rückgabe: 0 aktuell oder gewechselt, 1 Update gescheitert und zurückgenommen
#           oder Image nicht erreichbar, 2 ungültige Einstellung,
#           3 Rückweg gescheitert.
#
# Läuft als root über hc-werkbank-update.timer, eingehüllt von hc-run.
# Einstellungen: /etc/hc-werkbank.conf (Muster: hc-werkbank.conf.beispiel).
set -euo pipefail

# --- Vorgaben: jede Einstellung mit ihrem Wert an einer Stelle ----------------
IMAGE="ghcr.io/brightcolor/healthchecks-werkbank"
TRACK_TAG="latest"
COMPOSE_DIR="/opt/healthchecks"
SERVICE="healthchecks"
TAG_VARIABLE="HC_IMAGE_TAG"
DB_PATH=""
BACKUP_DIR="/root/backups/healthchecks"
BACKUP_KEEP="10"
WAIT_SECONDS="180"
APP_PORT="8000"
CHECK_PATHS="/api/v3/status/ /accounts/login/"
CHECK_TIMEOUT="10"
STYLE_MARKER="bc/werkbank"
LOG_FILE="/var/log/hc-werkbank-update.log"
LOCK_FILE="/run/lock/hc-werkbank-update.lock"

ERLAUBT="IMAGE TRACK_TAG COMPOSE_DIR SERVICE TAG_VARIABLE DB_PATH BACKUP_DIR BACKUP_KEEP WAIT_SECONDS APP_PORT CHECK_PATHS CHECK_TIMEOUT STYLE_MARKER LOG_FILE LOCK_FILE"
EINSTELLUNGEN="${HC_WERKBANK_EINSTELLUNGEN:-/etc/hc-werkbank.conf}"
COMPOSE_MINDEST="2.21.0"   # ab dieser Fassung kennt docker compose up --wait-timeout
VERSION_LABEL="org.opencontainers.image.version"
TAG_MUSTER='^[A-Za-z0-9_][A-Za-z0-9._-]{0,127}$'
nur_pruefen=nein
compose_datei=""
alt=""
sicherung=""

while [ $# -gt 0 ]; do
	case "$1" in
		--einstellungen) EINSTELLUNGEN="${2:?--einstellungen braucht einen Dateipfad}"; shift 2 ;;
		--nur-pruefen) nur_pruefen=ja; shift ;;
		-h|--help) sed -n '2,13p' "$0"; exit 0 ;;
		*) echo "Unbekannte Option $1. Erlaubt sind --einstellungen DATEI und --nur-pruefen. Es wurde nichts geändert." >&2; exit 2 ;;
	esac
done

abbruch_einstellung() { # Name, Satz
	echo "Einstellung $1: $2 Trage einen gültigen Wert in $EINSTELLUNGEN ein. Es wurde nichts geändert." >&2
	exit 2
}

lies_einstellungen() {
	[ -e "$EINSTELLUNGEN" ] || return 0
	if [ "${HC_WERKBANK_BESITZ_PRUEFEN:-ja}" != nein ]; then
		local besitzer rechte
		besitzer="$(stat -c %u "$EINSTELLUNGEN")"
		rechte="$(stat -c %a "$EINSTELLUNGEN")"
		if [ "$besitzer" != 0 ] || [ $((8#$rechte & 8#022)) -ne 0 ]; then
			echo "$EINSTELLUNGEN gehört nicht root oder ist für andere schreibbar (Besitzer $besitzer, Rechte $rechte). Mit chown root:root und chmod 600 korrigieren. Es wurde nichts geändert." >&2
			exit 2
		fi
	fi
	local zeile schluessel wert nummer=0
	while IFS= read -r zeile || [ -n "$zeile" ]; do
		nummer=$((nummer + 1))
		zeile="${zeile%$'\r'}"
		case "$zeile" in ''|'#'*) continue ;; esac
		if [[ ! "$zeile" =~ ^([A-Z_]+)=(.*)$ ]]; then
			echo "Zeile $nummer in $EINSTELLUNGEN hat nicht die Form NAME=Wert: $zeile. Es wurde nichts geändert." >&2
			exit 2
		fi
		schluessel="${BASH_REMATCH[1]}"
		wert="${BASH_REMATCH[2]}"
		case " $ERLAUBT " in
			*" $schluessel "*) ;;
			*) echo "Unbekannte Einstellung $schluessel in Zeile $nummer von $EINSTELLUNGEN. Erlaubt sind: $ERLAUBT. Es wurde nichts geändert." >&2; exit 2 ;;
		esac
		if [[ "$wert" =~ ^\"(.*)\"$ ]] || [[ "$wert" =~ ^\'(.*)\'$ ]]; then
			wert="${BASH_REMATCH[1]}"
		fi
		printf -v "$schluessel" '%s' "$wert"
	done < "$EINSTELLUNGEN"
}

env_lesen() { # Name; Wert aus der .env von Healthchecks
	local wert=""
	wert="$(grep -E "^$1=" "$COMPOSE_DIR/.env" | tail -n 1 | cut -d= -f2-)" || true
	wert="${wert%$'\r'}"
	if [[ "$wert" =~ ^\"(.*)\"$ ]] || [[ "$wert" =~ ^\'(.*)\'$ ]]; then
		wert="${BASH_REMATCH[1]}"
	fi
	printf '%s' "$wert"
}

env_setzen() { # Name, Wert (ein geprüfter Tag)
	sed -i "s|^$1=.*|$1=$2|" "$COMPOSE_DIR/.env"
}

ganzzahl() { # Name, Wert, Minimum, Maximum
	if ! [[ "$2" =~ ^[0-9]+$ ]] || [ "$2" -lt "$3" ] || [ "$2" -gt "$4" ]; then
		abbruch_einstellung "$1" "$1 ist ${2:-leer}. Erlaubt sind ganze Zahlen von $3 bis $4."
	fi
}

absolut() { # Name, Wert
	[[ "$2" == /* ]] || abbruch_einstellung "$1" "$1 ist ${2:-leer}. Erwartet ist ein absoluter Pfad, der mit / beginnt."
}

pruefe_einstellungen() {
	if ! [[ "$IMAGE" =~ ^[a-z0-9][a-z0-9._:/-]*[a-z0-9]$ ]] || [[ "${IMAGE##*/}" == *:* ]]; then
		abbruch_einstellung IMAGE "IMAGE ist ${IMAGE:-leer}. Erwartet ist ein Image-Name ohne Tag, etwa ghcr.io/brightcolor/healthchecks-werkbank."
	fi
	[[ "$TRACK_TAG" =~ $TAG_MUSTER ]] || abbruch_einstellung TRACK_TAG "TRACK_TAG ist ${TRACK_TAG:-leer}. Erlaubt sind Buchstaben, Ziffern, Punkt, Minus und Unterstrich, etwa latest."
	absolut COMPOSE_DIR "$COMPOSE_DIR"
	[ -d "$COMPOSE_DIR" ] || abbruch_einstellung COMPOSE_DIR "Den Ordner $COMPOSE_DIR gibt es nicht."
	local name
	for name in compose.yaml compose.yml docker-compose.yaml docker-compose.yml; do
		if [ -f "$COMPOSE_DIR/$name" ]; then compose_datei="$COMPOSE_DIR/$name"; break; fi
	done
	[ -n "$compose_datei" ] || abbruch_einstellung COMPOSE_DIR "In $COMPOSE_DIR liegt keine compose.yaml."
	[ -f "$COMPOSE_DIR/.env" ] || abbruch_einstellung COMPOSE_DIR "In $COMPOSE_DIR fehlt die Datei .env, in der $TAG_VARIABLE steht."
	[[ "$SERVICE" =~ ^[A-Za-z0-9][A-Za-z0-9_.-]*$ ]] || abbruch_einstellung SERVICE "SERVICE ist ${SERVICE:-leer}. Erwartet ist der Name des Dienstes aus der Compose-Datei, etwa healthchecks."
	[[ "$TAG_VARIABLE" =~ ^[A-Z_][A-Z0-9_]*$ ]] || abbruch_einstellung TAG_VARIABLE "TAG_VARIABLE ist ${TAG_VARIABLE:-leer}. Erwartet ist ein Variablenname in Großbuchstaben, etwa HC_IMAGE_TAG."
	grep -qE "^${TAG_VARIABLE}=" "$COMPOSE_DIR/.env" || abbruch_einstellung TAG_VARIABLE "In $COMPOSE_DIR/.env fehlt die Zeile ${TAG_VARIABLE}=…; sie hält den Tag der laufenden Fassung."
	if [ -z "$DB_PATH" ]; then DB_PATH="$(env_lesen DB_NAME)"; fi
	[ -n "$DB_PATH" ] || abbruch_einstellung DB_PATH "DB_PATH ist leer, und in $COMPOSE_DIR/.env steht kein DB_NAME. Den Pfad der SQLite-Datei im Container eintragen, etwa /data/hc.sqlite."
	absolut DB_PATH "$DB_PATH"
	absolut BACKUP_DIR "$BACKUP_DIR"
	ganzzahl BACKUP_KEEP "$BACKUP_KEEP" 1 100
	ganzzahl WAIT_SECONDS "$WAIT_SECONDS" 30 1800
	ganzzahl APP_PORT "$APP_PORT" 1 65535
	ganzzahl CHECK_TIMEOUT "$CHECK_TIMEOUT" 1 120
	[ -n "$CHECK_PATHS" ] || abbruch_einstellung CHECK_PATHS "CHECK_PATHS ist leer. Mindestens einen Pfad eintragen, etwa /api/v3/status/."
	local pfad
	for pfad in $CHECK_PATHS; do
		[[ "$pfad" =~ ^/[A-Za-z0-9._~/%-]*$ ]] || abbruch_einstellung CHECK_PATHS "Der Pfad $pfad beginnt nicht mit / oder enthält andere Zeichen als Buchstaben, Ziffern und ._~/%-."
	done
	[ -n "$STYLE_MARKER" ] || abbruch_einstellung STYLE_MARKER "STYLE_MARKER ist leer. Erwartet ist ein Text, den jede geprüfte HTML-Seite enthält, etwa bc/werkbank."
	absolut LOG_FILE "$LOG_FILE"
	absolut LOCK_FILE "$LOCK_FILE"
}

log() {
	local zeile
	zeile="$(date -u +%Y-%m-%dT%H:%M:%SZ) $*"
	echo "$zeile"
	echo "$zeile" >> "$LOG_FILE"
}

compose() { docker compose --project-directory "$COMPOSE_DIR" "$@"; }

pruefe_dienst() {
	local behaelter zustand ergebnis
	behaelter="$(compose ps -q "$SERVICE")"
	if [ -z "$behaelter" ]; then log "Der Container von $SERVICE läuft nicht."; return 1; fi
	zustand="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}ohne Prüfung{{end}}' "$behaelter")"
	if [ "$zustand" != healthy ]; then log "Der Container ist $zustand, erwartet ist healthy."; return 1; fi
	# shellcheck disable=SC2086 # CHECK_PATHS ist eine Liste von Pfaden
	if ! ergebnis="$(compose exec -T "$SERVICE" python - "$APP_PORT" "$CHECK_TIMEOUT" "$STYLE_MARKER" $CHECK_PATHS 2>&1 <<'PY'
import os
import sys
import urllib.error
import urllib.request
from urllib.parse import urlparse

port, frist, merkmal, pfade = sys.argv[1], float(sys.argv[2]), sys.argv[3], sys.argv[4:]
seite = urlparse(os.getenv("SITE_ROOT", "http://localhost:8000"))
basis = seite.path.rstrip("/")
fehler = []
for pfad in pfade:
    anfrage = urllib.request.Request(f"http://localhost:{port}{basis}{pfad}", headers={"Host": seite.netloc})
    try:
        with urllib.request.urlopen(anfrage, timeout=frist) as antwort:
            text = antwort.read().decode("utf-8", "replace")
            if "text/html" in antwort.headers.get("Content-Type", "") and merkmal not in text:
                fehler.append(f"{pfad} enthält {merkmal} nicht")
    except urllib.error.HTTPError as err:
        fehler.append(f"{pfad} antwortet mit HTTP {err.code}")
    except OSError as err:
        fehler.append(f"{pfad} ist nicht erreichbar ({err})")
print("; ".join(fehler) if fehler else "Prüfung bestanden")
sys.exit(1 if fehler else 0)
PY
)"; then
		log "Prüfung im Container gescheitert: $ergebnis"
		return 1
	fi
	log "Prüfung im Container: $ergebnis"
}

sichern() {
	mkdir -p "$BACKUP_DIR"
	chmod 700 "$BACKUP_DIR"
	sicherung="$BACKUP_DIR/healthchecks-${alt:-unbekannt}-$(date -u +%Y%m%dT%H%M%SZ).sqlite"
	local im_behaelter="/tmp/hc-werkbank-sicherung.sqlite" ausgabe
	if ! ausgabe="$(compose exec -T "$SERVICE" python - "$DB_PATH" "$im_behaelter" 2>&1 <<'PY'
import sqlite3
import sys

quelle = sqlite3.connect(f"file:{sys.argv[1]}?mode=ro", uri=True)
ziel = sqlite3.connect(sys.argv[2])
quelle.backup(ziel)
ergebnis = ziel.execute("PRAGMA integrity_check").fetchone()[0]
ziel.close()
quelle.close()
if ergebnis != "ok":
    print(f"Die Integritätsprüfung der Sicherung meldet: {ergebnis}")
    sys.exit(1)
PY
)"; then
		log "Die Sicherung der Datenbank $DB_PATH ist gescheitert: $ausgabe Es wurde nichts geändert; $alt läuft weiter."
		exit 1
	fi
	if ! compose cp "$SERVICE:$im_behaelter" "$sicherung" >/dev/null 2>&1; then
		log "Die Sicherung ließ sich nicht aus dem Container kopieren. Es wurde nichts geändert; $alt läuft weiter."
		exit 1
	fi
	compose exec -T "$SERVICE" rm -f "$im_behaelter" >/dev/null 2>&1 || true
	chmod 600 "$sicherung"
	log "Sicherung angelegt: $sicherung."
	find "$BACKUP_DIR" -maxdepth 1 -name 'healthchecks-*.sqlite' -printf '%T@ %p\n' | sort -rn \
		| tail -n +"$((BACKUP_KEEP + 1))" | cut -d' ' -f2- | xargs -r rm -f --
}

rueckweg() {
	log "Rückweg: zurück auf $alt mit der Datenbank aus $sicherung."
	env_setzen "$TAG_VARIABLE" "$alt"
	compose stop "$SERVICE" >/dev/null 2>&1 || true
	# shellcheck disable=SC2016 # $1 wertet die Shell im Container aus
	if compose run --rm --no-deps -T --user root --entrypoint sh "$SERVICE" \
			-c 'rm -f "$1-wal" "$1-shm" && cat > "$1" && chown --reference="$(dirname "$1")" "$1"' sh "$DB_PATH" \
			< "$sicherung" >/dev/null 2>&1 \
		&& compose up -d --wait --wait-timeout "$WAIT_SECONDS" "$SERVICE" >/dev/null 2>&1 \
		&& pruefe_dienst; then
		log "Rückweg erledigt: $alt läuft wieder mit der Datenbank von vor dem Update."
		exit 1
	fi
	log "Rückweg gescheitert. Handarbeit: In $COMPOSE_DIR/.env steht schon $TAG_VARIABLE=$alt. Die Datenbank aus $sicherung nach $DB_PATH im Volume von $SERVICE kopieren, dann in $COMPOSE_DIR docker compose up -d ausführen."
	exit 3
}

lies_einstellungen
pruefe_einstellungen
if [ "$nur_pruefen" = ja ]; then
	echo "Einstellungen in Ordnung ($EINSTELLUNGEN)."
	exit 0
fi

if ! command -v docker >/dev/null 2>&1; then
	echo "docker fehlt auf diesem System. Das Skript läuft auf dem Docker-Host von Healthchecks. Es wurde nichts geändert." >&2
	exit 2
fi
compose_fassung="$(docker compose version --short 2>/dev/null || true)"
compose_fassung="${compose_fassung#v}"
if [ -z "$compose_fassung" ] || [ "$(printf '%s\n' "$COMPOSE_MINDEST" "$compose_fassung" | sort -V | head -n 1)" != "$COMPOSE_MINDEST" ]; then
	echo "docker compose ${compose_fassung:-fehlt} ist zu alt; gebraucht wird $COMPOSE_MINDEST oder neuer (für --wait-timeout). Es wurde nichts geändert." >&2
	exit 2
fi
compose config --services 2>/dev/null | grep -qx "$SERVICE" || abbruch_einstellung SERVICE "Den Dienst $SERVICE gibt es in $compose_datei nicht."

mkdir -p "$(dirname "$LOG_FILE")" "$(dirname "$LOCK_FILE")"
exec 9>"$LOCK_FILE"
if ! flock -n 9; then
	log "Ein anderer Lauf arbeitet noch (Sperre $LOCK_FILE). Dieser Lauf endet ohne Änderung."
	exit 0
fi

alt="$(env_lesen "$TAG_VARIABLE")"
if ! fehler="$(docker pull -q "$IMAGE:$TRACK_TAG" 2>&1 >/dev/null)"; then
	log "Das Image $IMAGE:$TRACK_TAG ließ sich nicht holen ($fehler). Die laufende Fassung $alt bleibt."
	exit 1
fi
neu="$(docker image inspect -f "{{ index .Config.Labels \"$VERSION_LABEL\" }}" "$IMAGE:$TRACK_TAG" 2>/dev/null || true)"
if ! [[ "$neu" =~ $TAG_MUSTER ]]; then
	log "Das Image $IMAGE:$TRACK_TAG trägt kein gültiges Label $VERSION_LABEL (gefunden: ${neu:-nichts}). Die laufende Fassung $alt bleibt."
	exit 1
fi
if [ "$neu" = "$alt" ]; then
	log "Aktuell: $alt läuft bereits."
	exit 0
fi
if ! docker pull -q "$IMAGE:$neu" >/dev/null 2>&1; then
	log "Der feste Tag $IMAGE:$neu fehlt in der Registry. Die laufende Fassung $alt bleibt."
	exit 1
fi
log "Neue Fassung $neu gefunden, laufend ist $alt."
sichern
env_setzen "$TAG_VARIABLE" "$neu"
log "Starte $SERVICE mit $neu."
if start="$(compose up -d --wait --wait-timeout "$WAIT_SECONDS" "$SERVICE" 2>&1)" && pruefe_dienst; then
	log "Gewechselt auf $neu. Sicherung: $sicherung."
	exit 0
fi
log "Die neue Fassung $neu besteht die Prüfung nicht. ${start##*$'\n'}"
rueckweg
```

- [ ] **Step 4: Tests laufen lassen, sie bestehen**

Run: `.venv/Scripts/python -m pytest tests/test_update_einstellungen.py -q`
Expected: `21 passed`. Findet pytest die falsche bash (etwa `C:\Windows\System32\bash.exe` ohne WSL), `WB_BASH="C:\Program Files\Git\usr\bin\bash.exe"` setzen.

- [ ] **Step 5: Einbindung auf dem Server**

`deploy/hc-werkbank-update.service`:
```ini
[Unit]
Description=healthchecks-werkbank: neue Fassung holen und mit Sicherung einspielen
Documentation=https://github.com/brightcolor/healthchecks-werkbank
Wants=network-online.target
After=network-online.target docker.service
Requires=docker.service

[Service]
Type=oneshot
ExecStart=/usr/local/sbin/hc-run hc-werkbank-update -- /usr/local/sbin/hc-werkbank-update
```

`deploy/hc-werkbank-update.timer`:
```ini
[Unit]
Description=healthchecks-werkbank: stündlich nach einer neuen Fassung sehen

[Timer]
OnCalendar=*-*-* *:37:00
Persistent=true

[Install]
WantedBy=timers.target
```

`deploy/hc-werkbank-update.logrotate`:
```
/var/log/hc-werkbank-update.log {
	monthly
	rotate 12
	compress
	missingok
	notifempty
}
```

`deploy/hc-werkbank.conf.beispiel`:
```
# Einstellungen für hc-werkbank-update. Datei: /etc/hc-werkbank.conf, root:root, Rechte 600.
# Jede Zeile NAME=Wert. Ohne Zeile gilt die Vorgabe, hier jeweils auskommentiert.
# Kommentare beginnen mit # am Zeilenanfang.

# Verfolgtes Image ohne Tag.
#IMAGE=ghcr.io/brightcolor/healthchecks-werkbank
# Beweglicher Tag, auf den das Skript schaut.
#TRACK_TAG=latest
# Ordner mit compose.yaml und .env von Healthchecks.
#COMPOSE_DIR=/opt/healthchecks
# Name des Dienstes in der Compose-Datei.
#SERVICE=healthchecks
# Variable in der .env, die den Tag der laufenden Fassung hält.
#TAG_VARIABLE=HC_IMAGE_TAG
# Pfad der SQLite-Datei im Container; leer: Wert von DB_NAME aus der .env.
#DB_PATH=
# Ablage der Sicherungen und wie viele davon bleiben (1 bis 100).
#BACKUP_DIR=/root/backups/healthchecks
#BACKUP_KEEP=10
# Frist in Sekunden, bis der neue Container gesund sein muss (30 bis 1800).
#WAIT_SECONDS=180
# Port von Healthchecks im Container (1 bis 65535).
#APP_PORT=8000
# Pfade, die nach dem Start mit 200 antworten müssen, durch Leerzeichen getrennt.
#CHECK_PATHS="/api/v3/status/ /accounts/login/"
# Frist in Sekunden je Prüfanfrage (1 bis 120).
#CHECK_TIMEOUT=10
# Text, den jede geprüfte HTML-Seite enthalten muss.
#STYLE_MARKER=bc/werkbank
# Protokoll der Läufe und Sperrdatei.
#LOG_FILE=/var/log/hc-werkbank-update.log
#LOCK_FILE=/run/lock/hc-werkbank-update.lock
```

- [ ] **Step 6: Update-Probe für die CI schreiben**

`tests/update/kaputt.sh`:
```sh
#!/bin/sh
# Fassung für die Update-Probe: löscht die Markierung in der Datenbank und wird nie gesund.
./manage.py shell -c "from hc.api.models import Check; Check.objects.filter(name='probe-markierung').delete()" >/dev/null 2>&1
exec uwsgi /opt/healthchecks/docker/uwsgi.ini
```

`tests/update/markierung.py`:
```python
"""Legt die Markierung der Update-Probe an: ein Check namens probe-markierung."""
from django.contrib.auth.models import User

from hc.accounts.models import Project
from hc.api.models import Check

nutzer, _ = User.objects.get_or_create(username="probe", defaults={"email": "probe@example.org"})
projekt = Project.objects.filter(owner=nutzer).first() or Project.objects.create(owner=nutzer, name="Probe", badge_key="probe")
Check.objects.get_or_create(project=projekt, name="probe-markierung")
```

`tests/update/probe.sh`:
```bash
#!/usr/bin/env bash
# Update-Probe für deploy/hc-werkbank-update; läuft in der CI auf Linux mit Docker und sudo.
# Aufruf: tests/update/probe.sh <gebautes Image, etwa wb-test:lokal>
#
# Baut aus dem Image drei Fassungen (probe-a, probe-b, probe-kaputt), legt sie in
# eine lokale Registry und prüft: Wechsel, gleiche Fassung, Rückweg mit
# zurückgespielter Datenbank, ungültige Einstellung, andere Einstellungen.
set -euo pipefail

BILD="${1:?Aufruf: tests/update/probe.sh <Image>}"
WURZEL="$(cd "$(dirname "$0")/../.." && pwd)"
SKRIPT="$WURZEL/deploy/hc-werkbank-update"
REGISTRY_PORT="${WB_PROBE_REGISTRY_PORT:-5000}"
REGISTRY_IMAGE="${WB_PROBE_REGISTRY_IMAGE:-registry:2}"
FRIST="${WB_PROBE_FRIST:-180}"
REG="localhost:${REGISTRY_PORT}"
ARBEIT="$(mktemp -d)"

aufraeumen() {
	local d
	for d in "$ARBEIT"/hc*; do
		if [ -f "$d/compose.yaml" ]; then docker compose --project-directory "$d" down -v >/dev/null 2>&1 || true; fi
	done
	docker rm -f wb-probe-registry >/dev/null 2>&1 || true
}
trap aufraeumen EXIT

pruefe() { # Beschreibung, Befehl
	local beschreibung="$1"
	shift
	if "$@"; then echo "ok: $beschreibung"; else echo "FEHLER: $beschreibung" >&2; exit 1; fi
}

fassung() { # Name, Zusatzzeilen für das Dockerfile
	local ordner="$ARBEIT/bau-$1"
	mkdir -p "$ordner"
	printf 'FROM %s\nLABEL org.opencontainers.image.version=%s\n%s\n' "$BILD" "$1" "$2" > "$ordner/Dockerfile"
	cp "$WURZEL/tests/update/kaputt.sh" "$ordner/"
	docker build -q -t "$REG/hcwb:$1" "$ordner" >/dev/null
	docker push -q "$REG/hcwb:$1" >/dev/null
}

als_latest() {
	docker tag "$REG/hcwb:$1" "$REG/hcwb:latest"
	docker push -q "$REG/hcwb:latest" >/dev/null
}

aufbau() { # Ordner, Dienst, Tag-Variable, Start-Fassung
	mkdir -p "$1"
	cat > "$1/compose.yaml" <<EOF
services:
  $2:
    image: $REG/hcwb:\${$3}
    env_file: .env
    volumes:
      - daten:/data
volumes:
  daten:
EOF
	cat > "$1/.env" <<EOF
$3=$4
SECRET_KEY=probe-$(openssl rand -hex 16)
DEBUG=False
SITE_ROOT=http://localhost:8000
DB_NAME=/data/hc.sqlite
REGISTRATION_OPEN=False
EOF
	docker compose --project-directory "$1" up -d --wait --wait-timeout "$FRIST" >/dev/null
	docker compose --project-directory "$1" exec -T "$2" ./manage.py shell < "$WURZEL/tests/update/markierung.py" >/dev/null
}

einstellungen() { # Datei, Zeilen
	local datei="$1"
	shift
	printf '%s\n' "$@" | sudo tee "$datei" >/dev/null
	sudo chown root:root "$datei"
	sudo chmod 600 "$datei"
}

update() { # Einstellungsdatei; Ausgabe nach $ARBEIT/ausgabe.txt
	local rc=0
	sudo bash "$SKRIPT" --einstellungen "$1" >"$ARBEIT/ausgabe.txt" 2>&1 || rc=$?
	cat "$ARBEIT/ausgabe.txt"
	return "$rc"
}

env_wert() { grep -E "^$2=" "$1/.env" | cut -d= -f2-; }
gesund() { [ "$(docker inspect -f '{{.State.Health.Status}}' "$(docker compose --project-directory "$1" ps -q "$2")")" = healthy ]; }
markiert() {
	docker compose --project-directory "$1" exec -T "$2" ./manage.py shell -c \
		"from hc.api.models import Check; print('MARKIERUNG', Check.objects.filter(name='probe-markierung').count())" \
		| grep -qx 'MARKIERUNG 1'
}
sicherungen() { sudo find "$1" -maxdepth 1 -name 'healthchecks-*.sqlite' | wc -l; }

docker run -d --name wb-probe-registry -p "127.0.0.1:${REGISTRY_PORT}:5000" "$REGISTRY_IMAGE" >/dev/null
fassung probe-a ""
fassung probe-b ""
fassung probe-kaputt 'COPY kaputt.sh /opt/kaputt.sh
HEALTHCHECK --interval=2s --start-period=2s --retries=1 CMD false
CMD ["sh", "/opt/kaputt.sh"]'

HC="$ARBEIT/hc"
aufbau "$HC" healthchecks HC_IMAGE_TAG probe-a
E1="$ARBEIT/eins.conf"
einstellungen "$E1" "IMAGE=$REG/hcwb" "COMPOSE_DIR=$HC" "BACKUP_DIR=$ARBEIT/sicherung" \
	"LOG_FILE=$ARBEIT/update.log" "LOCK_FILE=$ARBEIT/update.lock" "WAIT_SECONDS=$FRIST"

echo "== 1. Neue Fassung wird übernommen"
als_latest probe-b
rc=0; update "$E1" || rc=$?
pruefe "Rückgabe 0" [ "$rc" -eq 0 ]
pruefe ".env trägt probe-b" [ "$(env_wert "$HC" HC_IMAGE_TAG)" = probe-b ]
pruefe "Container gesund" gesund "$HC" healthchecks
pruefe "eine Sicherung" [ "$(sicherungen "$ARBEIT/sicherung")" -eq 1 ]
pruefe "Markierung vorhanden" markiert "$HC" healthchecks

echo "== 2. Gleiche Fassung: nichts zu tun"
rc=0; update "$E1" || rc=$?
pruefe "Rückgabe 0" [ "$rc" -eq 0 ]
pruefe "Meldung aktuell" grep -q "Aktuell: probe-b" "$ARBEIT/ausgabe.txt"
pruefe "keine neue Sicherung" [ "$(sicherungen "$ARBEIT/sicherung")" -eq 1 ]

echo "== 3. Kaputte Fassung: Rückweg mit Datenbank"
als_latest probe-kaputt
rc=0; update "$E1" || rc=$?
pruefe "Rückgabe 1" [ "$rc" -eq 1 ]
pruefe ".env wieder probe-b" [ "$(env_wert "$HC" HC_IMAGE_TAG)" = probe-b ]
pruefe "Container gesund" gesund "$HC" healthchecks
pruefe "Markierung aus der Sicherung zurück" markiert "$HC" healthchecks
pruefe "Protokoll nennt den Rückweg" sudo grep -q "Rückweg erledigt" "$ARBEIT/update.log"

echo "== 4. Ungültige Einstellung"
E2="$ARBEIT/ungueltig.conf"
einstellungen "$E2" "COMPOSE_DIR=$HC" "BACKUP_KEEP=0"
rc=0; update "$E2" || rc=$?
pruefe "Rückgabe 2" [ "$rc" -eq 2 ]
pruefe "Meldung nennt BACKUP_KEEP" grep -q "BACKUP_KEEP ist 0" "$ARBEIT/ausgabe.txt"
pruefe ".env unverändert" [ "$(env_wert "$HC" HC_IMAGE_TAG)" = probe-b ]

echo "== 5. Andere Einstellungen: Dienst hc, Variable WB_TAG, eine Sicherung"
HC2="$ARBEIT/hc-anders"
aufbau "$HC2" hc WB_TAG probe-b
E3="$ARBEIT/anders.conf"
einstellungen "$E3" "IMAGE=$REG/hcwb" "COMPOSE_DIR=$HC2" "SERVICE=hc" "TAG_VARIABLE=WB_TAG" "BACKUP_KEEP=1" \
	"BACKUP_DIR=$ARBEIT/sicherung-anders" "LOG_FILE=$ARBEIT/anders.log" "LOCK_FILE=$ARBEIT/anders.lock" \
	"CHECK_PATHS=/api/v3/status/" "WAIT_SECONDS=$FRIST"
als_latest probe-a
rc=0; update "$E3" || rc=$?
pruefe "Rückgabe 0" [ "$rc" -eq 0 ]
pruefe "WB_TAG trägt probe-a" [ "$(env_wert "$HC2" WB_TAG)" = probe-a ]
als_latest probe-b
rc=0; update "$E3" || rc=$?
pruefe "zweiter Wechsel" [ "$(env_wert "$HC2" WB_TAG)" = probe-b ]
pruefe "nur eine Sicherung bleibt" [ "$(sicherungen "$ARBEIT/sicherung-anders")" -eq 1 ]

echo "Update-Probe bestanden."
```

- [ ] **Step 7: Syntax prüfen und Ausführrechte setzen**

```bash
bash -n deploy/hc-werkbank-update && bash -n tests/update/probe.sh && sh -n tests/update/kaputt.sh && echo Syntax in Ordnung
git add deploy tests/update tests/test_update_einstellungen.py
git update-index --chmod=+x deploy/hc-werkbank-update tests/update/probe.sh tests/update/kaputt.sh
```
Expected: `Syntax in Ordnung`. Shellcheck läuft in der CI (Task 9).

- [ ] **Step 8: Commit**

```bash
git commit -m "Update-Skript für docker-a1 mit Sicherung, Rückweg und Probe für die CI

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 9: Image und CI

**Files:**
- Create: `Dockerfile`, `.dockerignore`
- Create: `tools/ci/entscheiden.sh`, `tools/ci/schritt.sh`, `tools/ci/testinstanz.sh`, `tools/ci/upstream_aus_image.sh`, `tools/ci/meldung.sh`, `tools/ci/bericht.py`
- Create: `.github/workflows/build.yml`
- Test: `tests/test_entscheiden.py`

**Interfaces:**
- Consumes: `werkbank/einbau.py`, `werkbank/farben.py bauen`, `tests/musterdaten.py`, `tests/e2e/*`, `tests/update/probe.sh`.
- Produces: Image-Labels `org.opencontainers.image.version=<Fassung>`; Datei `/opt/healthchecks/werkbank-bericht.json` im Image; Workflow-Ausgaben `hc_tag`, `fassung`, `bauen`, `veroeffentlichen`; Issue-Label `theme-rot`.

- [ ] **Step 1: Tests für die Entscheidung schreiben**

`tests/test_entscheiden.py`:
```python
"""tools/ci/entscheiden.sh mit nachgebauten gh und curl."""
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

WURZEL = Path(__file__).resolve().parent.parent
SKRIPT = WURZEL / "tools" / "ci" / "entscheiden.sh"
BASH = os.environ.get("WB_BASH") or shutil.which("bash")
pytestmark = pytest.mark.skipif(BASH is None, reason="bash fehlt; WB_BASH auf den Pfad von bash setzen")
FASSUNG = (WURZEL / "VERSION").read_text(encoding="utf-8").strip()

GH = """#!/usr/bin/env bash
echo "${FAKE_RELEASE:-v4.4}"
"""
CURL = """#!/usr/bin/env bash
case "$*" in
  *hub.docker.com*) echo "${FAKE_HUB:-200}" ;;
  *ghcr.io/token*) echo '{"token":"abc"}' ;;
  *ghcr.io/v2/*) echo "${FAKE_GHCR:-404}" ;;
  *) echo "unerwarteter Aufruf: $*" >&2; exit 9 ;;
esac
"""


def posix(pfad: Path) -> str:
    text = pfad.as_posix()
    m = re.match(r"^([A-Za-z]):/(.*)$", text)
    return f"/{m.group(1).lower()}/{m.group(2)}" if (m and os.name == "nt") else text


def lauf(tmp_path, **umgebung):
    bin_ = tmp_path / "bin"
    bin_.mkdir(exist_ok=True)
    for name, inhalt in (("gh", GH), ("curl", CURL)):
        datei = bin_ / name
        datei.write_text(inhalt, encoding="utf-8", newline="\n")
        datei.chmod(0o755)
    ausgabe = tmp_path / "ausgabe.txt"
    ausgabe.write_text("", encoding="utf-8")
    summary = tmp_path / "summary.md"
    env = dict(os.environ, PATH=str(bin_) + os.pathsep + os.environ.get("PATH", ""),
               UPSTREAM="healthchecks/healthchecks", BASIS_IMAGE="healthchecks/healthchecks",
               ZIEL_IMAGE="ghcr.io/brightcolor/healthchecks-werkbank",
               GITHUB_OUTPUT=posix(ausgabe), GITHUB_STEP_SUMMARY=posix(summary), **umgebung)
    erg = subprocess.run([BASH, posix(SKRIPT)], cwd=WURZEL, env=env, capture_output=True, text=True, encoding="utf-8")
    werte = dict(z.split("=", 1) for z in ausgabe.read_text(encoding="utf-8").splitlines() if "=" in z)
    return erg, werte, (summary.read_text(encoding="utf-8") if summary.exists() else "")


def test_zeitplan_neue_version_wird_gebaut_und_veroeffentlicht(tmp_path):
    erg, werte, _ = lauf(tmp_path, EREIGNIS="schedule")
    assert erg.returncode == 0, erg.stderr
    assert werte == {"hc_tag": "v4.4", "fassung": f"4.4-wb{FASSUNG}", "bauen": "true", "veroeffentlichen": "true"}


def test_zeitplan_vorhandener_tag_baut_nichts(tmp_path):
    _, werte, _ = lauf(tmp_path, EREIGNIS="schedule", FAKE_GHCR="200")
    assert (werte["bauen"], werte["veroeffentlichen"]) == ("false", "false")


def test_zeitplan_basis_fehlt_noch(tmp_path):
    erg, werte, summary = lauf(tmp_path, EREIGNIS="schedule", FAKE_HUB="404")
    assert erg.returncode == 0
    assert (werte["bauen"], werte["veroeffentlichen"]) == ("false", "false")
    assert "liegt noch nicht auf Docker Hub" in summary


def test_push_main_mit_vorhandenem_tag_prueft_nur(tmp_path):
    _, werte, _ = lauf(tmp_path, EREIGNIS="push", REF="refs/heads/main", FAKE_GHCR="200")
    assert (werte["bauen"], werte["veroeffentlichen"]) == ("true", "false")


def test_push_main_mit_neuer_fassung_veroeffentlicht(tmp_path):
    _, werte, _ = lauf(tmp_path, EREIGNIS="push", REF="refs/heads/main")
    assert (werte["bauen"], werte["veroeffentlichen"]) == ("true", "true")


def test_push_anderer_zweig_veroeffentlicht_nicht(tmp_path):
    _, werte, _ = lauf(tmp_path, EREIGNIS="push", REF="refs/heads/probe")
    assert (werte["bauen"], werte["veroeffentlichen"]) == ("true", "false")


def test_pull_request_prueft_nur(tmp_path):
    _, werte, _ = lauf(tmp_path, EREIGNIS="pull_request")
    assert (werte["bauen"], werte["veroeffentlichen"]) == ("true", "false")


def test_handstart_mit_version_und_erzwingen(tmp_path):
    _, werte, _ = lauf(tmp_path, EREIGNIS="workflow_dispatch", EINGABE="v4.3", ERZWINGEN="true", FAKE_GHCR="200")
    assert werte["hc_tag"] == "v4.3"
    assert werte["fassung"] == f"4.3-wb{FASSUNG}"
    assert (werte["bauen"], werte["veroeffentlichen"]) == ("true", "true")


def test_handstart_ohne_erzwingen_bei_vorhandenem_tag(tmp_path):
    _, werte, _ = lauf(tmp_path, EREIGNIS="workflow_dispatch", ERZWINGEN="false", FAKE_GHCR="200")
    assert (werte["bauen"], werte["veroeffentlichen"]) == ("false", "false")


def test_ungueltige_version(tmp_path):
    erg, _, _ = lauf(tmp_path, EREIGNIS="workflow_dispatch", EINGABE="4.4")
    assert erg.returncode == 1
    assert "hat nicht die Form v4.4" in erg.stdout


def test_unbekanntes_ereignis(tmp_path):
    erg, _, _ = lauf(tmp_path, EREIGNIS="release")
    assert erg.returncode == 1
    assert "Unbekanntes Ereignis" in erg.stdout
```

- [ ] **Step 2: Tests laufen lassen, sie scheitern**

Run: `.venv/Scripts/python -m pytest tests/test_entscheiden.py -q`
Expected: FAIL, das Skript fehlt.

- [ ] **Step 3: Bausteine der CI schreiben**

`tools/ci/entscheiden.sh`:
```bash
#!/usr/bin/env bash
# Entscheidet, welche Healthchecks-Version die CI baut und ob sie veröffentlicht.
# Umgebung: UPSTREAM, BASIS_IMAGE, ZIEL_IMAGE, EREIGNIS, REF, EINGABE, ERZWINGEN,
# GITHUB_OUTPUT, GITHUB_STEP_SUMMARY.
set -euo pipefail

: "${UPSTREAM:?}" "${BASIS_IMAGE:?}" "${ZIEL_IMAGE:?}" "${EREIGNIS:?}" "${GITHUB_OUTPUT:?}"
ZUSAMMENFASSUNG="${GITHUB_STEP_SUMMARY:-/dev/null}"

ausgabe() { printf '%s=%s\n' "$1" "$2" >> "$GITHUB_OUTPUT"; }
notiz() { printf '%s\n' "$*" >> "$ZUSAMMENFASSUNG"; }

hc_tag="${EINGABE:-}"
if [ -z "$hc_tag" ]; then
	hc_tag="$(gh api "repos/${UPSTREAM}/releases/latest" --jq .tag_name)"
fi
if ! [[ "$hc_tag" =~ ^v[0-9]+(\.[0-9]+)*$ ]]; then
	echo "::error::Die Version '${hc_tag}' hat nicht die Form v4.4. Beim Handstart eine Version wie v4.4 eingeben oder das Feld leer lassen."
	exit 1
fi
theme="$(tr -d '[:space:]' < VERSION)"
if ! [[ "$theme" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
	echo "::error::VERSION enthält '${theme}', erwartet ist eine Fassung wie 1.0.0."
	exit 1
fi
fassung="${hc_tag#v}-wb${theme}"
ausgabe hc_tag "$hc_tag"
ausgabe fassung "$fassung"

hub="$(curl -s -o /dev/null -w '%{http_code}' "https://hub.docker.com/v2/repositories/${BASIS_IMAGE}/tags/${hc_tag}")"
if [ "$hub" != 200 ]; then
	notiz "Das Basis-Image ${BASIS_IMAGE}:${hc_tag} liegt noch nicht auf Docker Hub (HTTP ${hub}). Der nächste Lauf versucht es erneut."
	ausgabe bauen false
	ausgabe veroeffentlichen false
	exit 0
fi

pfad="${ZIEL_IMAGE#ghcr.io/}"
token="$(curl -fsSL "https://ghcr.io/token?scope=repository:${pfad}:pull&service=ghcr.io" | sed -n 's/.*"token":"\([^"]*\)".*/\1/p' || true)"
vorhanden=false
if [ -n "$token" ]; then
	code="$(curl -s -o /dev/null -w '%{http_code}' -H "Authorization: Bearer ${token}" \
		-H 'Accept: application/vnd.oci.image.index.v1+json' \
		-H 'Accept: application/vnd.docker.distribution.manifest.list.v2+json' \
		"https://ghcr.io/v2/${pfad}/manifests/${fassung}")"
	if [ "$code" = 200 ]; then vorhanden=true; fi
fi

case "$EREIGNIS" in
	schedule)
		if [ "$vorhanden" = true ]; then bauen=false; else bauen=true; fi
		veroeffentlichen="$bauen" ;;
	push)
		bauen=true
		if [ "${REF:-}" = refs/heads/main ] && [ "$vorhanden" = false ]; then veroeffentlichen=true; else veroeffentlichen=false; fi ;;
	pull_request)
		bauen=true
		veroeffentlichen=false ;;
	workflow_dispatch)
		if [ "${ERZWINGEN:-false}" = true ] || [ "$vorhanden" = false ]; then
			bauen=true
			veroeffentlichen=true
		else
			bauen=false
			veroeffentlichen=false
		fi ;;
	*)
		echo "::error::Unbekanntes Ereignis '${EREIGNIS}'. Die CI kennt schedule, push, pull_request und workflow_dispatch."
		exit 1 ;;
esac
ausgabe bauen "$bauen"
ausgabe veroeffentlichen "$veroeffentlichen"
notiz "Healthchecks ${hc_tag}, Fassung ${fassung}: schon veröffentlicht ${vorhanden}, bauen ${bauen}, veröffentlichen ${veroeffentlichen}."
```

`tools/ci/schritt.sh`:
```bash
#!/usr/bin/env bash
# Führt einen Prüfschritt aus, hält die Ausgabe in artefakte/logs/<name>.log fest
# und schreibt bei Fehlschlag einen Auszug nach fehler/<arch>-<name>.md für das Issue.
# Aufruf: tools/ci/schritt.sh <name> -- <befehl ...>
set -uo pipefail

name="${1:?Aufruf: tools/ci/schritt.sh <name> -- <befehl>}"
shift
if [ "${1:-}" = "--" ]; then shift; fi
mkdir -p artefakte/logs fehler
"$@" 2>&1 | tee "artefakte/logs/${name}.log"
rc=${PIPESTATUS[0]}
if [ "$rc" -ne 0 ]; then
	{
		echo "### ${name} (${WB_ARCH:-unbekannt})"
		echo
		echo '```'
		tail -n "${WB_AUSZUG_ZEILEN:-40}" "artefakte/logs/${name}.log"
		echo '```'
		echo
	} > "fehler/${WB_ARCH:-unbekannt}-${name}.md"
fi
exit "$rc"
```

`tools/ci/testinstanz.sh`:
```bash
#!/usr/bin/env bash
# Startet eine Testinstanz des gebauten Images und legt die Musterdaten an.
# Aufruf: tools/ci/testinstanz.sh <Image>
# Schreibt tests/e2e/ergebnisse/musterdaten.json und WB_TEST_PASSWORT nach GITHUB_ENV.
set -euo pipefail

BILD="${1:?Aufruf: tools/ci/testinstanz.sh <Image>}"
NAME="${WB_TESTINSTANZ:-wb-test}"
PORT="${WB_TESTPORT:-8000}"
ERGEBNIS="${WB_MUSTERDATEN:-tests/e2e/ergebnisse/musterdaten.json}"
FRIST="${WB_START_FRIST:-180}"

passwort="$(openssl rand -hex 16)"
echo "::add-mask::${passwort}"
docker rm -f "$NAME" >/dev/null 2>&1 || true
docker run -d --name "$NAME" -p "127.0.0.1:${PORT}:8000" \
	-e SECRET_KEY="$(openssl rand -hex 32)" -e DEBUG=False -e SITE_ROOT="http://localhost:${PORT}" \
	-e DB_NAME=/data/hc.sqlite -e REGISTRATION_OPEN=False -e SITE_NAME=Healthchecks \
	"$BILD" >/dev/null

zustand=""
ende=$((SECONDS + FRIST))
while [ "$SECONDS" -lt "$ende" ]; do
	zustand="$(docker inspect -f '{{.State.Health.Status}}' "$NAME")"
	if [ "$zustand" = healthy ]; then break; fi
	sleep 2
done
if [ "$zustand" != healthy ]; then
	docker logs "$NAME" 2>&1 | tail -n 40
	echo "::error::Die Testinstanz wurde nicht gesund (Zustand: ${zustand:-unbekannt}). Das Log steht darüber."
	exit 1
fi

mkdir -p "$(dirname "$ERGEBNIS")"
if ! docker exec -i -e WB_TEST_PASSWORT="$passwort" "$NAME" ./manage.py shell < tests/musterdaten.py \
		| sed -n 's/^MUSTERDATEN: //p' > "$ERGEBNIS" || [ ! -s "$ERGEBNIS" ]; then
	echo "::error::Die Musterdaten wurden nicht angelegt. Die Ausgabe von manage.py shell steht im Log des Schritts."
	exit 1
fi
echo "WB_TEST_PASSWORT=${passwort}" >> "${GITHUB_ENV:-/dev/null}"
echo "Testinstanz ${NAME} läuft auf Port ${PORT}, Musterdaten in ${ERGEBNIS}."
```

`tools/ci/upstream_aus_image.sh`:
```bash
#!/usr/bin/env bash
# Holt Vorlagen und Stylesheets aus dem Basis-Image nach .upstream/<version> für die Einheitstests.
# Aufruf: tools/ci/upstream_aus_image.sh <Image> <Zielordner>
set -euo pipefail

BILD="${1:?Aufruf: tools/ci/upstream_aus_image.sh <Image> <Zielordner>}"
ZIEL="${2:?Zielordner fehlt}"
WURZEL_IM_IMAGE="${WB_HC_WURZEL:-/opt/healthchecks}"

docker pull -q "$BILD" >/dev/null
behaelter="$(docker create "$BILD")"
trap 'docker rm -f "$behaelter" >/dev/null' EXIT
mkdir -p "$ZIEL"
docker cp "$behaelter:$WURZEL_IM_IMAGE/templates" "$ZIEL/templates"
docker cp "$behaelter:$WURZEL_IM_IMAGE/static" "$ZIEL/static"
echo "Vorlagen und Stylesheets aus $BILD liegen in $ZIEL."
```

`tools/ci/meldung.sh`:
```bash
#!/usr/bin/env bash
# Hält den Zustand der Werkbank-Prüfung in einem Issue fest.
#   tools/ci/meldung.sh rot    legt das Issue der Healthchecks-Version an oder ergänzt es
#   tools/ci/meldung.sh gruen  schließt das offene Issue der Version
set -euo pipefail

ART="${1:?Aufruf: tools/ci/meldung.sh rot|gruen}"
HC_TAG="${HC_TAG:-unbekannt}"
LAUF_URL="${LAUF_URL:?LAUF_URL fehlt}"
LABEL="${WB_ISSUE_LABEL:-theme-rot}"
TITEL="Healthchecks ${HC_TAG}: Werkbank-Prüfung rot"

nummer="$(gh issue list --label "$LABEL" --state open --json number,title \
	--jq "map(select(.title == \"${TITEL}\")) | .[0].number // empty" 2>/dev/null || true)"

case "$ART" in
	rot)
		if [ -n "$nummer" ] && [ "${EREIGNIS:-}" = schedule ]; then
			echo "Issue #${nummer} ist schon offen; ein Lauf aus dem Zeitplan ergänzt es nicht erneut."
			exit 0
		fi
		koerper="$(mktemp)"
		{
			echo "Die Prüfung für Healthchecks ${HC_TAG} (Fassung ${FASSUNG:-unbekannt}) ist rot. Es wurde nichts veröffentlicht; docker-a1 behält die laufende Fassung."
			echo
			echo "Lauf: ${LAUF_URL}"
			echo
			if compgen -G "fehler/*.md" >/dev/null; then
				cat fehler/*.md
			else
				echo "Ein Auszug fehlt; die Ursache steht im Log des Laufs."
			fi
			echo
			echo "Nächster Schritt: das Theme in einer Sitzung anpassen und auf main pushen. Der nächste grüne Lauf veröffentlicht und schließt dieses Issue."
		} > "$koerper"
		gh label create "$LABEL" --color d61f7a --description "Werkbank-Prüfung rot" >/dev/null 2>&1 || true
		if [ -n "$nummer" ]; then
			gh issue comment "$nummer" --body-file "$koerper"
		else
			gh issue create --title "$TITEL" --label "$LABEL" --body-file "$koerper"
		fi
		;;
	gruen)
		if [ -n "$nummer" ]; then
			gh issue close "$nummer" --comment "Wieder grün und veröffentlicht als ${FASSUNG:-unbekannt}: ${LAUF_URL}"
		else
			echo "Kein offenes Issue für Healthchecks ${HC_TAG}."
		fi
		;;
	*)
		echo "Unbekannte Art '${ART}'. Erlaubt sind rot und gruen." >&2
		exit 2
		;;
esac
```

`tools/ci/bericht.py`:
```python
#!/usr/bin/env python3
"""Schreibt den Bericht der Farbableitung als Markdown für die Zusammenfassung des CI-Laufs."""
import json
import os
import sys


def zelle(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


def main(pfad: str) -> int:
    with open(pfad, encoding="utf-8") as datei:
        bericht = json.load(datei)
    grenze = int(os.environ.get("WB_BERICHT_ZEILEN", "50"))
    print(f"### Farbableitung {bericht['fassung']}")
    print()
    print(f"{bericht['deklarationen']} Farbangaben aus {bericht['stylesheets']} Stylesheets abgeleitet.")
    auto = bericht.get("automatisch", [])
    if auto:
        print()
        print(f"**Hinweis:** {len(auto)} Farbangaben ohne Eintrag in `werkbank/farben.json` bekamen ihre Rolle "
              "nach Farbton und Helligkeit. Passt eine Rolle nicht, den Eintrag in farben.json ergänzen.")
        print()
        print("| Farbe | Art | Rolle | Datei | Selektor |")
        print("|---|---|---|---|---|")
        for f in auto[:grenze]:
            print(f"| `{f['farbe']}` | {f['art']} | `{f['rolle']}` | {f['datei']} | `{zelle(f['selektor'])[:90]}` |")
        if len(auto) > grenze:
            print(f"\nDazu {len(auto) - grenze} weitere; die volle Liste steht in artefakte/werkbank-bericht.json.")
    entfallen = bericht.get("variablen_entfallen", [])
    if entfallen:
        print()
        print("**Hinweis:** Diese Variablen gibt es in Healthchecks nicht mehr; ihre Zeilen in "
              "`werkbank/variablen.css` können entfallen: " + ", ".join(f"`{n}`" for n in entfallen))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
```

- [ ] **Step 4: Tests laufen lassen, sie bestehen**

Run: `.venv/Scripts/python -m pytest tests/test_entscheiden.py -q`
Expected: `11 passed`.

- [ ] **Step 5: Image beschreiben**

`Dockerfile`:
```dockerfile
# syntax=docker/dockerfile:1
# healthchecks-werkbank: das offizielle Image von Healthchecks mit der Werkbank von bright color.
ARG HC_VERSION=v4.4
FROM healthchecks/healthchecks:${HC_VERSION}

ARG WERKBANK_FASSUNG=lokal
USER root
COPY werkbank/ /tmp/werkbank/
COPY vendor/hausschrift/ /tmp/hausschrift/
RUN set -eu; \
    cp -r /tmp/werkbank/templates/bc templates/bc; \
    mkdir -p static/bc/logo; \
    cp -r /tmp/hausschrift/assets/fonts static/bc/fonts; \
    cp /tmp/hausschrift/assets/logo/*.svg static/bc/logo/; \
    cp /tmp/werkbank/static/bc/leiste.js static/bc/; \
    python /tmp/werkbank/einbau.py --wurzel /opt/healthchecks --fassung "$WERKBANK_FASSUNG"; \
    python /tmp/werkbank/farben.py bauen --wurzel /opt/healthchecks --hausschrift /tmp/hausschrift \
        --werkbank /tmp/werkbank --fassung "$WERKBANK_FASSUNG" --bericht /opt/healthchecks/werkbank-bericht.json; \
    DEBUG=False SECRET_KEY=build-key ./manage.py collectstatic --noinput; \
    DEBUG=False SECRET_KEY=build-key ./manage.py compress --force; \
    rm -rf /tmp/werkbank /tmp/hausschrift
USER hc
LABEL org.opencontainers.image.version="${WERKBANK_FASSUNG}" \
      org.opencontainers.image.title="healthchecks-werkbank"
```

`.dockerignore`:
```
.git
.github
.upstream
.venv
node_modules
artefakte
fehler
docs
tests
tools
deploy
**/__pycache__
```

- [ ] **Step 6: Workflow schreiben**

`.github/workflows/build.yml`:
```yaml
name: Bauen, prüfen, veröffentlichen

# Folgt neuen Healthchecks-Versionen: baut das Werkbank-Image für amd64 und arm64,
# prüft im Browser und mit der Update-Probe und veröffentlicht nach ghcr.io.
# Bei Rot geht nichts raus; ein Issue nennt die gescheiterte Prüfung.

on:
  schedule:
    - cron: '23 */6 * * *'
  push:
    branches: [main]
  pull_request:
  workflow_dispatch:
    inputs:
      hc_version:
        description: 'Healthchecks-Version, etwa v4.4 (leer: neuestes Release)'
        required: false
        default: ''
      force:
        description: 'Neu bauen und veröffentlichen, auch wenn der Tag schon existiert'
        type: boolean
        default: false

concurrency:
  group: werkbank-${{ github.ref }}
  cancel-in-progress: false

permissions:
  contents: read

env:
  UPSTREAM: healthchecks/healthchecks
  BASIS_IMAGE: healthchecks/healthchecks
  ZIEL_IMAGE: ghcr.io/${{ github.repository_owner }}/healthchecks-werkbank
  NODE_VERSION: '22'
  PYTHON_VERSION: '3.13'

defaults:
  run:
    shell: bash

jobs:
  entscheiden:
    name: Entscheiden
    runs-on: ubuntu-latest
    outputs:
      hc_tag: ${{ steps.e.outputs.hc_tag }}
      fassung: ${{ steps.e.outputs.fassung }}
      bauen: ${{ steps.e.outputs.bauen }}
      veroeffentlichen: ${{ steps.e.outputs.veroeffentlichen }}
    steps:
      - uses: actions/checkout@v4
      - id: e
        name: Version und Auftrag bestimmen
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          EINGABE: ${{ inputs.hc_version }}
          ERZWINGEN: ${{ inputs.force }}
          EREIGNIS: ${{ github.event_name }}
          REF: ${{ github.ref }}
        run: tools/ci/entscheiden.sh

  bauen:
    name: Bauen und prüfen (${{ matrix.arch }})
    needs: entscheiden
    if: needs.entscheiden.outputs.bauen == 'true'
    strategy:
      fail-fast: false
      matrix:
        include:
          - arch: amd64
            runner: ubuntu-latest
          - arch: arm64
            runner: ubuntu-24.04-arm
    runs-on: ${{ matrix.runner }}
    permissions:
      contents: read
      packages: write
    env:
      HC_TAG: ${{ needs.entscheiden.outputs.hc_tag }}
      FASSUNG: ${{ needs.entscheiden.outputs.fassung }}
      VEROEFFENTLICHEN: ${{ needs.entscheiden.outputs.veroeffentlichen }}
      WB_ARCH: ${{ matrix.arch }}
    steps:
      - uses: actions/checkout@v4

      - uses: docker/setup-buildx-action@v3

      - name: Image bauen
        run: |
          tools/ci/schritt.sh bau -- docker buildx build --load --progress plain -t wb-test:lokal \
            --build-arg "HC_VERSION=$HC_TAG" --build-arg "WERKBANK_FASSUNG=$FASSUNG" \
            --label "org.opencontainers.image.source=https://github.com/${{ github.repository }}" \
            --label "org.opencontainers.image.base.name=docker.io/$BASIS_IMAGE:$HC_TAG" \
            --label "org.opencontainers.image.licenses=BSD-3-Clause AND BSD-2-Clause AND OFL-1.1" \
            .

      - uses: actions/setup-python@v5
        if: matrix.arch == 'amd64'
        with:
          python-version: ${{ env.PYTHON_VERSION }}

      - name: Einheitstests
        if: matrix.arch == 'amd64'
        run: |
          python -m pip install -q -r tests/requirements.txt
          tools/ci/upstream_aus_image.sh "$BASIS_IMAGE:$HC_TAG" ".upstream/$HC_TAG"
          tools/ci/schritt.sh einheitstests -- python -m pytest -q

      - name: Quelltext prüfen
        if: matrix.arch == 'amd64'
        run: |
          tools/ci/schritt.sh shellcheck -- shellcheck deploy/hc-werkbank-update tools/ci/*.sh tests/update/*.sh
          tools/ci/schritt.sh lint -- python vendor/hausschrift/scripts/bc_check.py lint werkbank --variant workbench

      - name: Testinstanz mit Musterdaten
        run: tools/ci/schritt.sh testinstanz -- tools/ci/testinstanz.sh wb-test:lokal

      - name: Werkbank auf der Anmeldeseite
        if: matrix.arch == 'arm64'
        run: tools/ci/schritt.sh anmeldeseite -- bash -c 'curl -fsS http://localhost:8000/accounts/login/ | grep -q "bc/werkbank.css"'

      - uses: actions/setup-node@v4
        if: matrix.arch == 'amd64'
        with:
          node-version: ${{ env.NODE_VERSION }}

      - name: Browserprüfung
        if: matrix.arch == 'amd64'
        env:
          WB_BROWSER_KANAL: chrome
          WB_BASIS_URL: http://localhost:8000
        run: |
          npm ci
          tools/ci/schritt.sh browser -- npx playwright test

      - name: Update-Probe
        if: matrix.arch == 'amd64'
        run: tools/ci/schritt.sh update-probe -- tests/update/probe.sh wb-test:lokal

      - name: Bericht der Farbableitung
        if: always() && matrix.arch == 'amd64'
        run: |
          mkdir -p artefakte
          if docker run --rm --entrypoint cat wb-test:lokal /opt/healthchecks/werkbank-bericht.json > artefakte/werkbank-bericht.json; then
            python tools/ci/bericht.py artefakte/werkbank-bericht.json >> "$GITHUB_STEP_SUMMARY"
          fi

      - name: Ergebnisse sichern
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: pruefung-${{ matrix.arch }}
          path: |
            artefakte/
            tests/e2e/ergebnisse/
          if-no-files-found: ignore

      - name: Auszug für das Issue sichern
        if: failure()
        uses: actions/upload-artifact@v4
        with:
          name: fehler-${{ matrix.arch }}
          path: fehler/
          if-no-files-found: ignore

      - name: Bei ghcr.io anmelden
        if: env.VEROEFFENTLICHEN == 'true'
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Image je Plattform hochladen
        if: env.VEROEFFENTLICHEN == 'true'
        run: |
          docker tag wb-test:lokal "$ZIEL_IMAGE:ci-$WB_ARCH"
          docker push -q "$ZIEL_IMAGE:ci-$WB_ARCH"
          mkdir -p digest
          docker inspect -f '{{index .RepoDigests 0}}' "$ZIEL_IMAGE:ci-$WB_ARCH" > "digest/$WB_ARCH.txt"
          cat "digest/$WB_ARCH.txt"

      - name: Digest weitergeben
        if: env.VEROEFFENTLICHEN == 'true'
        uses: actions/upload-artifact@v4
        with:
          name: digest-${{ matrix.arch }}
          path: digest/

  veroeffentlichen:
    name: Veröffentlichen
    needs: [entscheiden, bauen]
    if: needs.entscheiden.outputs.veroeffentlichen == 'true' && needs.bauen.result == 'success'
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
      issues: write
    env:
      HC_TAG: ${{ needs.entscheiden.outputs.hc_tag }}
      FASSUNG: ${{ needs.entscheiden.outputs.fassung }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/download-artifact@v4
        with:
          pattern: digest-*
          merge-multiple: true
          path: digest
      - uses: docker/setup-buildx-action@v3
      - uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - name: Tags für beide Plattformen setzen
        run: |
          docker buildx imagetools create \
            -t "$ZIEL_IMAGE:$FASSUNG" -t "$ZIEL_IMAGE:${HC_TAG#v}" -t "$ZIEL_IMAGE:latest" \
            "$(cat digest/amd64.txt)" "$(cat digest/arm64.txt)"
          docker buildx imagetools inspect "$ZIEL_IMAGE:$FASSUNG"
          {
            echo "### Veröffentlicht: \`$FASSUNG\`"
            echo
            echo '```'
            echo "docker pull $ZIEL_IMAGE:$FASSUNG"
            echo '```'
          } >> "$GITHUB_STEP_SUMMARY"
      - name: Offenes Issue der Version schließen
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          GH_REPO: ${{ github.repository }}
          LAUF_URL: ${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}
        run: tools/ci/meldung.sh gruen

  meldung:
    name: Meldung bei Rot
    needs: [entscheiden, bauen, veroeffentlichen]
    if: >-
      always() && github.event_name != 'pull_request' &&
      (needs.entscheiden.result == 'failure' || needs.bauen.result == 'failure' || needs.veroeffentlichen.result == 'failure')
    runs-on: ubuntu-latest
    permissions:
      contents: read
      issues: write
    env:
      HC_TAG: ${{ needs.entscheiden.outputs.hc_tag }}
      FASSUNG: ${{ needs.entscheiden.outputs.fassung }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/download-artifact@v4
        continue-on-error: true
        with:
          pattern: fehler-*
          merge-multiple: true
          path: fehler
      - name: Issue anlegen oder ergänzen
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          GH_REPO: ${{ github.repository }}
          EREIGNIS: ${{ github.event_name }}
          LAUF_URL: ${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}
        run: tools/ci/meldung.sh rot
```

- [ ] **Step 7: Syntax prüfen, Ausführrechte setzen, Commit**

```bash
for s in tools/ci/*.sh; do bash -n "$s" || echo "Syntaxfehler in $s"; done
.venv/Scripts/python -c "import yaml" 2>/dev/null || .venv/Scripts/python -m pip install -q pyyaml==6.0.3
.venv/Scripts/python -c "import yaml; yaml.safe_load(open('.github/workflows/build.yml', encoding='utf-8')); print('YAML in Ordnung')"
.venv/Scripts/python -m pytest -q
git add Dockerfile .dockerignore tools/ci .github tests/test_entscheiden.py
git update-index --chmod=+x tools/ci/entscheiden.sh tools/ci/schritt.sh tools/ci/testinstanz.sh tools/ci/upstream_aus_image.sh tools/ci/meldung.sh tools/ci/bericht.py
git commit -m "Image und CI: bauen für amd64 und arm64, prüfen, veröffentlichen, Issue bei Rot

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
Expected: keine Syntaxfehler, `YAML in Ordnung`, pytest grün. Den Bau selbst prüft erst der erste Lauf in Task 11.

---

### Task 10: Dokumentation

**Files:**
- Create: `README.md`, `docs/bilder/*.png`
- Modify: `CHANGELOG.md`, `docs/superpowers/specs/2026-10-05-healthchecks-werkbank-design.md` (Einstellungen `CHECK_TIMEOUT`, `LOCK_FILE`)

**Interfaces:**
- Consumes: Bilder aus `tests/e2e/ergebnisse/bilder/` (Task 7).

- [ ] **Step 1: Bilder übernehmen**

```bash
mkdir -p docs/bilder
cp tests/e2e/ergebnisse/bilder/checks-hell.png tests/e2e/ergebnisse/bilder/checks-dunkel.png tests/e2e/ergebnisse/bilder/checks-390.png tests/e2e/ergebnisse/bilder/anmeldung.png docs/bilder/
```
Die Bilder enthalten nur die erfundenen Musterdaten.

- [ ] **Step 2: README schreiben**

`README.md`:
````markdown
# Werkbank für Healthchecks

Die Oberfläche von [Healthchecks](https://github.com/healthchecks/healthchecks) in der Werkbank von bright color: Onyx-Leiste links mit den Projekten als Akkordeon, Kopfzeile mit Brotkrumen und Umschalter für Hell und Dunkel, warmes Papier als Grund, weiße Karten mit Rundung, Gelb als Aktionsfarbe, Anton in Versalien für Titel, Atkinson Hyperlegible für Text und das Vierfarbband am oberen Rand.

Das Image baut auf dem offiziellen Image von Healthchecks auf und folgt jeder neuen Version: Die CI baut, prüft im Browser und veröffentlicht nach `ghcr.io/brightcolor/healthchecks-werkbank`. Auf dem Server holt ein Timer neue Fassungen, sichert vorher die Datenbank und nimmt ein gescheitertes Update selbst zurück.

![Checks, hell](docs/bilder/checks-hell.png)
![Checks, dunkel](docs/bilder/checks-dunkel.png)

**Stand: 1.0.0**, geprüft gegen Healthchecks v4.4.

## Was es macht

- **Leiste links.** Jedes Projekt ist ein Modul im Akkordeon, sein Punkt zeigt den Zustand in der Hausampel. Das offene Projekt führt zu Checks, Integrations, Badges und Settings. Darunter stehen New Project, Docs, Account Settings und Log Out.
- **Hell und dunkel.** Der Umschalter in der Kopfzeile speichert in dieselbe Darstellungs-Einstellung wie das Profil von Healthchecks; „System“ bleibt dort wählbar.
- **Vollständig.** Die 78 Farbvariablen von Healthchecks zeigen auf Werkbank-Rollen. Jede feste Farbe aus den Stylesheets (in v4.4 sind es 627 Angaben) bekommt beim Bau eine Rolle; eine Farbe ohne Eintrag wird nach Farbton und Helligkeit zugeordnet und im CI-Lauf genannt.
- **Handy.** Unter 900 px fährt die Leiste über den Menüknopf herein. Unter 640 px zeigen Checks, Integrationen und Log jede Zeile zweizeilig.
- **Barrierefrei.** Kontrast nach WCAG AA in beiden Modi, Schrift aus den Tokens ab 4,8:1, sichtbarer Fokus, Sprunglink, ruhige Leiste bei `prefers-reduced-motion`.
- **Texte.** Die Oberfläche bleibt englisch wie Healthchecks; die Anmeldeseite grüßt mit „Moin.“.

## So funktioniert es

```
healthchecks/healthchecks:<version>
  └─ Dockerfile dieses Repos
       ├─ werkbank/einbau.py   setzt zwei Zeilen in templates/base.html: Stylesheet und Leiste
       ├─ werkbank/farben.py   baut static/bc/werkbank.css aus Schriften, Tokens, Rollen,
       │                       Variablen, abgeleiteten Farben und der Stilschicht
       └─ collectstatic und compress wie im offiziellen Image
```

Der Code von Healthchecks bleibt unverändert. Findet `einbau.py` einen Anker nicht genau einmal, oder bringt Healthchecks eine neue Farbvariable mit, bricht der Bau ab und nennt die Stelle.

| Datei | Inhalt |
|---|---|
| `werkbank/einbau.json` | Anker und Zeilen für `base.html` |
| `werkbank/farben.json` | Zuordnung fester Farben zu Rollen, je Art und Modus, mit Ausnahmen je Selektor |
| `werkbank/variablen.css` | die 78 Variablen von Healthchecks auf Rollen |
| `werkbank/rollen.css` | eigene Rollen: Tönungen, Schatten, Zustände |
| `werkbank/stil.css` | Stilschicht |
| `werkbank/templates/bc/leiste.html`, `werkbank/static/bc/leiste.js` | Leiste und Kopfzeile |
| `vendor/hausschrift/` | Kopie der Hausschrift von bright color (Tokens, Schriften, Logo, Prüfwerkzeuge) |

## Fassungen und Tags

| Tag | Bedeutung |
|---|---|
| `4.4-wb1.0.0` | Healthchecks 4.4 mit Werkbank 1.0.0; bleibt unverändert und trägt den Rückweg |
| `4.4` | neueste Werkbank für Healthchecks 4.4 |
| `latest` | neueste Fassung insgesamt; diesem Tag folgt das Update-Skript |

Eine Theme-Änderung erhöht `VERSION`. Ein Push auf `main` ohne neue Fassung wird gebaut und geprüft, veröffentlicht wird erst mit erhöhter Fassung.

## Neue Healthchecks-Version

Die CI schaut viermal täglich nach einem neuen Release. Liegt das Basis-Image auf Docker Hub, baut sie für amd64 und arm64 und prüft:

- Einheitstests, Shellcheck und Lint der Hausschrift,
- jede Seite hell und dunkel im Browser mit Kontrastlauf, sechs Breiten ohne Querscrollen, Listen auf dem Handy,
- die Update-Probe gegen eine lokale Registry: Wechsel, gleiche Fassung, Rückweg mit Datenbank, ungültige und abweichende Einstellungen.

Ist alles grün, gehen die Tags nach ghcr.io. Ist etwas rot, geht nichts raus: Ein Issue mit dem Label `theme-rot` nennt die gescheiterte Prüfung mit Auszug und Link zum Lauf, und GitHub schickt eine Mail. Nach der Anpassung und einem Push auf `main` schließt der nächste grüne Lauf das Issue.

## Auf dem Server

In der `compose.yaml` von Healthchecks:
```yaml
services:
  healthchecks:
    image: ghcr.io/brightcolor/healthchecks-werkbank:${HC_IMAGE_TAG}
```
und in der `.env`:
```
HC_IMAGE_TAG=4.4-wb1.0.0
```

Das Update-Skript und seine Einbindung:
```bash
sudo install -m 755 deploy/hc-werkbank-update /usr/local/sbin/
sudo install -m 644 deploy/hc-werkbank-update.service deploy/hc-werkbank-update.timer /etc/systemd/system/
sudo install -m 644 deploy/hc-werkbank-update.logrotate /etc/logrotate.d/hc-werkbank-update
sudo install -m 600 deploy/hc-werkbank.conf.beispiel /etc/hc-werkbank.conf
sudo hc-werkbank-update --nur-pruefen
sudo systemctl daemon-reload && sudo systemctl enable --now hc-werkbank-update.timer
```
Der Dienst ruft das Skript über `hc-run hc-werkbank-update` auf; die Ping-Adresse des zugehörigen Checks liegt in `/etc/hc-run.d/hc-werkbank-update.url`.

Ein Lauf sieht nach `latest`, liest die Fassung aus dem Label `org.opencontainers.image.version` und tut nichts, wenn sie schon läuft. Sonst sichert er die SQLite-Datenbank mit der Sicherungsfunktion von SQLite, prüft die Kopie, setzt den festen Tag in die `.env`, startet neu und prüft Container, Statusadresse und Anmeldeseite. Scheitert das, geht er auf den alten Tag zurück, spielt die Datenbank zurück und meldet den Grund. Pings, die zwischen Sicherung und Rückweg ankommen, gehen dabei verloren.

| Einstellung | Vorgabe | Bedeutung | Grenzen |
|---|---|---|---|
| `IMAGE` | `ghcr.io/brightcolor/healthchecks-werkbank` | verfolgtes Image | Image-Name ohne Tag |
| `TRACK_TAG` | `latest` | beweglicher Tag | gültiger Tag |
| `COMPOSE_DIR` | `/opt/healthchecks` | Ordner mit `compose.yaml` und `.env` | vorhandener Ordner |
| `SERVICE` | `healthchecks` | Dienst in der Compose-Datei | Dienst muss existieren |
| `TAG_VARIABLE` | `HC_IMAGE_TAG` | Variable in der `.env` mit dem Tag | Name in Großbuchstaben, muss in der `.env` stehen |
| `DB_PATH` | Wert von `DB_NAME` aus der `.env` | SQLite-Datei im Container | absoluter Pfad |
| `BACKUP_DIR` | `/root/backups/healthchecks` | Ablage der Sicherungen | absoluter Pfad |
| `BACKUP_KEEP` | `10` | Zahl der Sicherungen, die bleiben | 1 bis 100 |
| `WAIT_SECONDS` | `180` | Frist, bis der Container gesund sein muss | 30 bis 1800 |
| `APP_PORT` | `8000` | Port von Healthchecks im Container | 1 bis 65535 |
| `CHECK_PATHS` | `/api/v3/status/ /accounts/login/` | Pfade, die mit 200 antworten müssen | Pfade mit `/` am Anfang |
| `CHECK_TIMEOUT` | `10` | Frist je Prüfanfrage in Sekunden | 1 bis 120 |
| `STYLE_MARKER` | `bc/werkbank` | Text, den jede geprüfte HTML-Seite enthält | mindestens ein Zeichen |
| `LOG_FILE` | `/var/log/hc-werkbank-update.log` | Protokoll der Läufe | absoluter Pfad |
| `LOCK_FILE` | `/run/lock/hc-werkbank-update.lock` | Sperre gegen doppelte Läufe | absoluter Pfad |

Rückgabewerte: 0 aktuell oder gewechselt, 1 gescheitert und zurückgenommen, 2 ungültige Einstellung, 3 Rückweg gescheitert (das Protokoll nennt dann die Sicherung und die Handgriffe).

**Rückweg von Hand:** Timer stoppen (`systemctl disable --now hc-werkbank-update.timer`), in der `.env` den gewünschten Tag eintragen oder in der `compose.yaml` wieder `healthchecks/healthchecks:<version>` nennen, die Datenbank aus `BACKUP_DIR` zurückspielen, `docker compose up -d`.

## Erste Einrichtung einer frischen Instanz

Healthchecks legt das erste Admin-Konto über die Kommandozeile im Container an, die nur der Betreiber erreicht:
```bash
docker compose exec healthchecks ./manage.py createsuperuser
```
Danach meldet sich das Konto auf der Anmeldeseite an.

## Lokal entwickeln

Lokal braucht es kein Docker; Healthchecks läuft direkt mit Python 3.13 und Node.js 22:
```bash
python -m venv .venv
.venv/Scripts/python tools/dev.py vorbereiten
.venv/Scripts/python tools/dev.py starten
.venv/Scripts/python tools/dev.py pruefen
```
`vorbereiten` holt Healthchecks nach `.upstream/`, setzt die Werkbank ein und legt Musterdaten an; der Zugang der Musterkonten steht in `.upstream/dev-zugang.txt`. Nach Änderungen in `werkbank/` reicht `tools/dev.py einsetzen` und ein Neustart des Servers. Unter Linux heißt der Pfad `.venv/bin/python`.

Weitere Prüfungen:
```bash
.venv/Scripts/python -m pytest -q
.venv/Scripts/python vendor/hausschrift/scripts/bc_check.py lint werkbank --variant workbench
```

## Lizenz

Der Code dieses Repos steht unter der BSD 2-Clause License (`LICENSE`). Healthchecks steht unter der BSD 3-Clause License (`UPSTREAM-LICENCE`). Die Schriften stehen unter der SIL Open Font License (`vendor/hausschrift/assets/fonts/OFL.txt`). Die Logos sind Marken von bright color und von der Lizenz dieses Repos ausgenommen.
````

- [ ] **Step 3: Spec und Änderungsliste nachziehen**

In der Spec, Abschnitt 7, Tabelle der Einstellungen, nach der Zeile `APP_PORT` diese Zeile ergänzen:
```markdown
| `CHECK_TIMEOUT` | `10` | Frist je Prüfanfrage in Sekunden | 1 bis 120 |
```
und nach der Zeile `LOG_FILE`:
```markdown
| `LOCK_FILE` | `/run/lock/hc-werkbank-update.lock` | Sperre gegen doppelte Läufe | absoluter Pfad |
```
In `CHANGELOG.md` unter 1.0.0 ergänzen:
```markdown
- Einstellungen des Update-Skripts mit Grenzen und Prüfung (`--nur-pruefen`), darunter `CHECK_TIMEOUT` und `LOCK_FILE`.
```

- [ ] **Step 4: Texte prüfen und Commit**

README und CHANGELOG auf Gegenüberstellungen („X statt Y“, „nicht X, sondern Y“) und Zeitangaben durchsehen; Verneinungen bleiben nur, wo sie selbst die Information sind.

```bash
git add README.md CHANGELOG.md docs/bilder docs/superpowers/specs/2026-10-05-healthchecks-werkbank-design.md
git commit -m "Dokumentation: README mit Aufbau, Tags, Server, Einstellungen und lokaler Entwicklung

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 11: GitHub-Repo und erster Lauf

**Files:** keine neuen; Repo auf GitHub.

**Interfaces:**
- Produces: `https://github.com/brightcolor/healthchecks-werkbank` (öffentlich), Paket `ghcr.io/brightcolor/healthchecks-werkbank` mit `4.4-wb1.0.0`, `4.4`, `latest`, anonym abrufbar.

- [ ] **Step 1: Freigabe einholen**

Das Repo wird öffentlich; das ist eine Veröffentlichung. Mathias kurz fragen: „Ich lege jetzt brightcolor/healthchecks-werkbank öffentlich auf GitHub an und pushe main. Einverstanden?“ Erst nach einem klaren Ja weiter.

- [ ] **Step 2: Repo anlegen und pushen**

```bash
gh repo create brightcolor/healthchecks-werkbank --public --source . --remote origin \
  --description "Healthchecks in der Werkbank von bright color: Leiste, Hell und Dunkel, CI folgt jeder neuen Version"
git push -u origin main
```
Expected: Der Push startet den Workflow (Ereignis `push`, Fassung `4.4-wb1.0.0`, veröffentlichen `true`).

- [ ] **Step 3: Ersten Lauf beobachten**

Run (im Hintergrund): `gh run watch "$(gh run list --workflow build.yml --limit 1 --json databaseId --jq '.[0].databaseId')" --exit-status`
Expected: Alle Jobs grün. Ist ein Job rot: `gh run view --log-failed` lesen, die Ursache beheben (meist Linux-Unterschiede gegenüber dem lokalen Lauf: Schriftglättung beim Kontrast, Pfade, Ausführrechte), Fassung in `VERSION` bleibt 1.0.0, Commit und Push. Das Issue `Healthchecks v4.4: Werkbank-Prüfung rot` schließt der nächste grüne Lauf.

- [ ] **Step 4: Bilder aus der CI ansehen**

```bash
gh run download --name pruefung-amd64 --dir artefakte/ci
```
Die Bilder unter `artefakte/ci/tests/e2e/ergebnisse/bilder/` ansehen, vor allem `checks-dunkel.png`, `docs-hell.png`, `checks-390.png`. Sie müssen den lokalen Bildern entsprechen.

- [ ] **Step 5: Paket anonym abrufbar machen**

```bash
token="$(curl -fsSL 'https://ghcr.io/token?scope=repository:brightcolor/healthchecks-werkbank:pull&service=ghcr.io' | sed -n 's/.*"token":"\([^"]*\)".*/\1/p')"
curl -s -o /dev/null -w '%{http_code}\n' -H "Authorization: Bearer $token" -H 'Accept: application/vnd.oci.image.index.v1+json' \
  https://ghcr.io/v2/brightcolor/healthchecks-werkbank/manifests/4.4-wb1.0.0
```
Expected: `200`. Bei `401` oder `403` ist das Paket privat: Mathias stellt unter github.com → Packages → healthchecks-werkbank → Package settings → Change visibility auf Public um (eine Kontoeinstellung, die er selbst vornimmt). Danach die Abfrage wiederholen.

- [ ] **Step 6: Plattformen prüfen**

Run: `docker buildx imagetools inspect ghcr.io/brightcolor/healthchecks-werkbank:4.4-wb1.0.0` geht lokal mangels Docker nicht; stattdessen in der Zusammenfassung des Jobs „Veröffentlichen“ nachsehen.
Expected: `linux/amd64` und `linux/arm64` aufgeführt.

---

### Task 12: Umstellung auf docker-a1

**Files:**
- Modify (Server): `/opt/healthchecks/compose.yaml`, `/opt/healthchecks/.env`
- Create (Server): `/usr/local/sbin/hc-run`, `/usr/local/sbin/hc-werkbank-update`, `/etc/hc-werkbank.conf`, `/etc/systemd/system/hc-werkbank-update.{service,timer}`, `/etc/logrotate.d/hc-werkbank-update`, `/etc/hc-run.d/hc-werkbank-update.url`
- Modify (lokal): `C:\Users\brigh\Claude Workingdir\Serverprotokolle\docker-a1.md`, `…\uptimekuma.bright-color.de.md`

**Interfaces:**
- Consumes: veröffentlichtes `ghcr.io/brightcolor/healthchecks-werkbank:4.4-wb1.0.0` (Task 11), `deploy/*` (Task 8).

- [ ] **Step 1: Freigabe einholen**

Mathias fragen: „Ich stelle hc.bcsrv.de jetzt auf das Werkbank-Image um. Dabei läuft das Update von Healthchecks v4.3 auf v4.4 mit Datenbankänderungen; vorher sichere ich Datenbank, compose.yaml und .env. Einverstanden?“ Erst nach einem klaren Ja weiter.

- [ ] **Step 2: Protokolleintrag beginnen und lesend prüfen**

Das Serverprotokoll `docker-a1.md` frisch lesen. Dann:
```bash
ssh oracle-a1 'date -Is; cd /opt/healthchecks && sudo docker compose ps --format "{{.Image}} {{.Status}}" && sudo grep -E "^(DB_NAME|SITE_NAME|SITE_ROOT|HC_IMAGE_TAG)=" .env; docker compose version --short; df -h / | tail -1'
```
Einen Eintrag „Healthchecks auf das Werkbank-Image umgestellt“ mit der Startzeit vom Server direkt unter dem Steckbrief einfügen (gezielte Einfügung). Steht `SITE_NAME` nicht in der `.env`, heißt die Instanz „Mychecks“: Mathias fragen, welcher Name in der Leiste stehen soll. Liegt die Fassung von docker compose unter 2.21, hier anhalten und Mathias den Befund nennen.

- [ ] **Step 3: Sichern**

Mit dem Pfad aus `DB_NAME` (Vorgabe `/data/hc.sqlite`):
```bash
ssh oracle-a1 'set -e; z=$(date -u +%Y%m%dT%H%M%SZ); ziel=/root/backups/healthchecks; sudo mkdir -p $ziel; sudo chmod 700 $ziel; cd /opt/healthchecks
sudo cp -p compose.yaml $ziel/compose.yaml.vor-werkbank-$z; sudo cp -p .env $ziel/env.vor-werkbank-$z
sudo docker compose exec -T healthchecks python - /data/hc.sqlite /tmp/vor-werkbank.sqlite <<PY
import sqlite3, sys
quelle = sqlite3.connect(f"file:{sys.argv[1]}?mode=ro", uri=True)
ziel = sqlite3.connect(sys.argv[2])
quelle.backup(ziel)
print("Integrität:", ziel.execute("PRAGMA integrity_check").fetchone()[0])
ziel.close(); quelle.close()
PY
sudo docker compose cp healthchecks:/tmp/vor-werkbank.sqlite $ziel/healthchecks-v4.3-vor-werkbank-$z.sqlite
sudo docker compose exec -T healthchecks rm -f /tmp/vor-werkbank.sqlite
sudo chmod 600 $ziel/*; sudo ls -l $ziel'
```
Expected: `Integrität: ok` und drei Dateien in `/root/backups/healthchecks`.

- [ ] **Step 4: Umstellen**

```bash
ssh oracle-a1 'set -e; cd /opt/healthchecks
sudo sed -i "s|^\(\s*\)image: healthchecks/healthchecks:latest|\1image: ghcr.io/brightcolor/healthchecks-werkbank:\${HC_IMAGE_TAG}|" compose.yaml
grep -n "image:" compose.yaml
sudo grep -q "^HC_IMAGE_TAG=" .env || echo "HC_IMAGE_TAG=4.4-wb1.0.0" | sudo tee -a .env >/dev/null
sudo grep -n "^HC_IMAGE_TAG=" .env
sudo docker compose pull healthchecks
sudo docker compose up -d --wait --wait-timeout 300 healthchecks
sudo docker compose ps --format "{{.Image}} {{.Status}}"
sudo docker compose logs --since 10m healthchecks | grep -E "Applying|Error|Traceback" | tail -20'
```
Expected: `image: ghcr.io/brightcolor/healthchecks-werkbank:${HC_IMAGE_TAG}`, `HC_IMAGE_TAG=4.4-wb1.0.0`, Container `healthy`, Migrationen von v4.4 als `Applying …`, keine Traceback-Zeilen. Wird der Container nicht gesund: Rückweg aus der Spec (Image `healthchecks/healthchecks:v4.3`, Datenbank aus der Sicherung) und Mathias informieren.

- [ ] **Step 5: Von außen prüfen**

```bash
curl -fsS https://hc.bcsrv.de/api/v3/status/; echo
curl -fsS https://hc.bcsrv.de/accounts/login/ | grep -c "bc/werkbank.css"
```
Expected: `OK` und `1`. Dann Mathias bitten, hc.bcsrv.de im Browser zu öffnen (hell, dunkel, Handy) und zu bestätigen, dass die Checks weiter Pings bekommen.

- [ ] **Step 6: hc-run, Skript und Timer einrichten**

```bash
ssh sidecar 'sudo cat /usr/local/sbin/hc-run' | ssh oracle-a1 'sudo install -m 755 -o root -g root /dev/stdin /usr/local/sbin/hc-run && sudo head -3 /usr/local/sbin/hc-run'
cd "/c/Users/brigh/Claude Workingdir/healthchecks-werkbank"
scp deploy/hc-werkbank-update deploy/hc-werkbank-update.service deploy/hc-werkbank-update.timer deploy/hc-werkbank-update.logrotate deploy/hc-werkbank.conf.beispiel oracle-a1:/tmp/
ssh oracle-a1 'set -e
sudo install -m 755 -o root -g root /tmp/hc-werkbank-update /usr/local/sbin/hc-werkbank-update
sudo install -m 644 -o root -g root /tmp/hc-werkbank-update.service /tmp/hc-werkbank-update.timer /etc/systemd/system/
sudo install -m 644 -o root -g root /tmp/hc-werkbank-update.logrotate /etc/logrotate.d/hc-werkbank-update
[ -e /etc/hc-werkbank.conf ] || sudo install -m 600 -o root -g root /tmp/hc-werkbank.conf.beispiel /etc/hc-werkbank.conf
rm -f /tmp/hc-werkbank-update /tmp/hc-werkbank-update.service /tmp/hc-werkbank-update.timer /tmp/hc-werkbank-update.logrotate /tmp/hc-werkbank.conf.beispiel
sudo /usr/local/sbin/hc-werkbank-update --nur-pruefen'
```
Expected: `Einstellungen in Ordnung (/etc/hc-werkbank.conf).`

- [ ] **Step 7: Check in Healthchecks anlegen**

Zuerst lesend Projekte und Kanäle ansehen, um das Projekt mit dem OpsKnight-Kanal zu finden:
```bash
ssh oracle-a1 'cd /opt/healthchecks && sudo docker compose exec -T healthchecks ./manage.py shell -c "from hc.accounts.models import Project; [print(p.name, [c.kind for c in p.channel_set.all()]) for p in Project.objects.all()]"'
```
Ist das Projekt eindeutig (heute „Thor“ mit dem Webhook-Kanal), dieses Skript als Datei im Scratchpad anlegen (Projektname anpassen) und ausführen; die Ping-Adresse geht per Pipe direkt in die Datei auf dem Server und erscheint nirgends:

`<scratchpad>/wb-check.py`:
```python
from datetime import timedelta

from hc.accounts.models import Project
from hc.api.models import Check

projekt = Project.objects.get(name="Thor")
name = "docker-a1 · Werkbank-Update für Healthchecks"
check = Check.objects.filter(project=projekt, name=name).first()
if check is None:
    check = Check(
        project=projekt, name=name, tags="docker-a1 aktualisierung", kind="cron", schedule="37 * * * *",
        tz="UTC", grace=timedelta(minutes=30),
        desc=("Stündlicher Lauf von hc-werkbank-update auf docker-a1: holt neue Fassungen von "
              "healthchecks-werkbank, sichert die Datenbank und spielt sie ein. Rot heißt: Lauf gescheitert "
              "oder ausgeblieben. Prüfen: /var/log/hc-werkbank-update.log und journalctl -u hc-werkbank-update."),
    )
    check.save()
    check.assign_all_channels()
print(check.url())
```
```bash
scp "<scratchpad>/wb-check.py" oracle-a1:/tmp/wb-check.py
ssh oracle-a1 'set -e; cd /opt/healthchecks; sudo mkdir -p /etc/hc-run.d
sudo docker compose exec -T healthchecks ./manage.py shell < /tmp/wb-check.py | grep -E "^https://hc\.bcsrv\.de/ping/" | sudo install -m 600 -o root -g root /dev/stdin /etc/hc-run.d/hc-werkbank-update.url
rm -f /tmp/wb-check.py; sudo wc -c /etc/hc-run.d/hc-werkbank-update.url'
```
Expected: eine Bytezahl über 40; die Adresse selbst wird nicht ausgegeben.

- [ ] **Step 8: Timer starten und ersten Lauf prüfen**

```bash
ssh oracle-a1 'set -e; sudo systemctl daemon-reload; sudo systemctl enable --now hc-werkbank-update.timer
sudo systemctl start hc-werkbank-update.service; sudo systemctl status hc-werkbank-update.service --no-pager | tail -5
sudo tail -3 /var/log/hc-werkbank-update.log; systemctl list-timers hc-werkbank-update.timer --no-pager'
```
Expected: im Log `Aktuell: 4.4-wb1.0.0 läuft bereits.`, nächster Lauf zur Minute 37; der neue Check in Healthchecks steht auf up.

- [ ] **Step 9: Monitor in Uptime Kuma**

Mathias legt den Monitor in Uptime Kuma (uptimekuma.bright-color.de) selbst an, mit diesen Werten: Typ „HTTP(s) – Keyword“, Name „hc.bcsrv.de“, URL `https://hc.bcsrv.de/api/v3/status/`, Keyword `OK`, Benachrichtigungen wie bei den übrigen Monitoren. Nach seiner Bestätigung einen kurzen Eintrag in `uptimekuma.bright-color.de.md` einfügen (frisch lesen, gezielt einfügen, Uhrzeit vom System).

- [ ] **Step 10: Protokoll abschließen und Erinnerung festhalten**

Den Eintrag in `docker-a1.md` frisch lesen und gezielt vervollständigen: Ablauf mit Uhrzeiten, Sicherungen mit Pfaden, geänderte Dateien, Prüfungen, Rückweg, offene Punkte. Danach eine Erinnerung in diesem Sitzungsspeicher anlegen: hc.bcsrv.de läuft auf `ghcr.io/brightcolor/healthchecks-werkbank`, Repo `brightcolor/healthchecks-werkbank`, Update-Skript `hc-werkbank-update` mit Timer zur Minute 37, Issue-Label `theme-rot` bei roter CI.


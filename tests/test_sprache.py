import gettext
import json
import re
import sys
import tomllib
from pathlib import Path

import pytest

WURZEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WURZEL / "werkbank"))
import sprache  # noqa: E402

KATALOG_KONFIG = """
[katalog]
stand = "v9.9"

[bereich]
vorlagen = ["templates/**/*.html"]
ausnahmen = ["templates/docs/**"]

[zustaende]
down = "ausgefallen"

[arten]
shell = "Shell-Befehl"

[rollen]
r = "Nur lesen"

[[django]]
en = "%(delta)s ago"
de = "vor %(delta)s"

[[django]]
kontext = "naturaltime-past"
en = "%(num)d day"
plural = "%(num)d days"
de = ["%(num)d Tag", "%(num)d Tagen"]
"""

ERWEITERUNG = """
[[quelltext]]
datei = "hc/extras.py"
anzahl = 1
en = '''
register = 1
'''
de = '''
register = 1
erweitert = True
'''
"""

EINSTELLUNGEN = 'SPRACHE = "@@WB_SPRACHE@@"\nZUSTAENDE = @@WB_ZUSTAENDE@@\nARTEN = @@WB_ARTEN@@\nROLLEN = @@WB_ROLLEN@@\nLOCALE = "@@WB_LOCALE@@"\nFORMATE = "@@WB_FORMATMODUL@@"\n'


def aufbau(tmp_path, katalog="", dateien=None, erweiterung=ERWEITERUNG, konfig=KATALOG_KONFIG):
    wurzel = tmp_path / "hc-wurzel"
    werkbank = tmp_path / "werkbank"
    formate = werkbank / "django" / "werkbank_formate" / "de"
    (werkbank / "deutsch").mkdir(parents=True)
    formate.mkdir(parents=True)
    (werkbank / "deutsch" / "katalog.toml").write_bytes(konfig.encode())
    (werkbank / "deutsch" / "test.toml").write_bytes(katalog.encode())
    (werkbank / "erweiterungen.toml").write_bytes(erweiterung.encode())
    (werkbank / "django" / "werkbank_einstellungen.py").write_bytes(EINSTELLUNGEN.encode())
    (werkbank / "django" / "werkbank_formate" / "__init__.py").write_bytes(b"")
    (formate / "__init__.py").write_bytes(b"")
    (formate / "formats.py").write_bytes(b'DECIMAL_SEPARATOR = "."\n')
    alle = {"hc/extras.py": "import x\nregister = 1\n"}
    alle.update(dateien or {})
    for rel, inhalt in alle.items():
        pfad = wurzel / rel
        pfad.parent.mkdir(parents=True, exist_ok=True)
        pfad.write_bytes(inhalt.encode("utf-8"))
    return wurzel, werkbank


def lies(wurzel, rel):
    return (wurzel / rel).read_bytes().decode("utf-8")


def text(datei, en, de):
    return f'[[text]]\ndatei = "{datei}"\nen = "{en}"\nde = "{de}"\n\n'


def test_text_ersetzt_ganze_stuecke_und_behaelt_leerraum(tmp_path):
    katalog = text("templates/a.html", "Last Ping", "Letzter Ping") + text("templates/a.html", "Log", "Protokoll")
    wurzel, werkbank = aufbau(tmp_path, katalog, {"templates/a.html": "<th>\n  Last   Ping\n</th><a>Login</a><b>Log</b>"})
    sprache.bauen(wurzel, werkbank)
    assert lies(wurzel, "templates/a.html") == "<th>\n  Letzter Ping\n</th><a>Login</a><b>Protokoll</b>"


def test_sichtbare_attribute_und_knoepfe(tmp_path):
    katalog = (text("*", "Search", "Suchen") + text("*", "Save", "Speichern") + text("*", "Close", "Schließen")
               + text("*", "Logo", "Logo der Instanz"))
    quelle = ('<input type="text" placeholder="Search" value="Save" class="Save">'
              '<input type="submit" value="Save"><button title="Close" aria-label="Close">x</button>'
              '<img alt="Logo" src="Logo"><a href="Close">y</a>')
    wurzel, werkbank = aufbau(tmp_path, katalog, {"templates/b.html": quelle})
    sprache.bauen(wurzel, werkbank)
    assert lies(wurzel, "templates/b.html") == (
        '<input type="text" placeholder="Suchen" value="Save" class="Save">'
        '<input type="submit" value="Speichern"><button title="Schließen" aria-label="Schließen">x</button>'
        '<img alt="Logo der Instanz" src="Logo"><a href="Close">y</a>')


def test_django_bedingungen_in_tags(tmp_path):
    katalog = text("*", "Add Check", "Check anlegen") + text("*", "no matching checks found", "keine passenden Checks")
    quelle = ('<button class="btn"\n  {% if num_available <= 0 %}disabled{% endif %}>\n  Add Check\n</button>'
              '<div id="x" {% if n > 0 %}style="display: none"{% endif %}>no matching checks found</div>')
    wurzel, werkbank = aufbau(tmp_path, katalog, {"templates/p.html": quelle})
    bericht = sprache.bauen(wurzel, werkbank)
    assert lies(wurzel, "templates/p.html") == quelle.replace("Add Check", "Check anlegen").replace(
        "no matching checks found", "keine passenden Checks")
    assert bericht["englisch"] == []


def test_opake_bereiche_und_kommentare_bleiben(tmp_path):
    quelle = ("<script>var t = 'Close';</script><style>.Close{}</style><pre>Close</pre><code>Close</code>"
              "<textarea>Close</textarea><!-- Close -->{# Close #}{% comment %}Close{% endcomment %}<p>Close</p>")
    wurzel, werkbank = aufbau(tmp_path, text("*", "Close", "Schließen"), {"templates/c.html": quelle})
    sprache.bauen(wurzel, werkbank)
    assert lies(wurzel, "templates/c.html") == quelle.replace("<p>Close</p>", "<p>Schließen</p>")



def test_attribute_am_oeffnenden_tag_opaker_bereiche(tmp_path):
    quelle = ('<textarea placeholder="Your notes" rows="3">Your notes</textarea>'
              '<pre title="Raw output">Raw output</pre><textarea placeholder="{{ x }}">y</textarea>')
    wurzel, werkbank = aufbau(tmp_path, text("*", "Your notes", "Deine Notizen"), {"templates/t.html": quelle})
    bericht = sprache.bauen(wurzel, werkbank)
    assert lies(wurzel, "templates/t.html") == quelle.replace('placeholder="Your notes"', 'placeholder="Deine Notizen"')
    assert [r["text"] for r in bericht["englisch"]] == ["Raw output"]

def test_quelltext_ersetzt_alle_und_prueft_die_anzahl(tmp_path):
    katalog = """
[[quelltext]]
datei = "hc/views.py"
en = '"Saved!"'
de = '"Gespeichert."'

[[quelltext]]
datei = "hc/views.py"
anzahl = 1
en = '"Removed"'
de = '"Entfernt"'
"""
    quelle = 'a = "Saved!"\nb = "Saved!"\nc = "Removed"\nd = "Removed"\n'
    wurzel, werkbank = aufbau(tmp_path, katalog, {"hc/views.py": quelle})
    bericht = sprache.bauen(wurzel, werkbank)
    assert lies(wurzel, "hc/views.py") == 'a = "Gespeichert."\nb = "Gespeichert."\nc = "Removed"\nd = "Removed"\n'
    assert bericht["ohne_fundstelle"] == [
        {"datei": "hc/views.py", "art": "quelltext", "en": '"Removed"', "grund": "2-mal gefunden, erwartet 1"}]


def test_dateieigene_eintraege_gehen_vor(tmp_path):
    katalog = text("*", "Close", "Schließen") + text("templates/d.html", "Close", "Zu")
    wurzel, werkbank = aufbau(tmp_path, katalog, {"templates/d.html": "<b>Close</b>", "templates/e.html": "<b>Close</b>"})
    sprache.bauen(wurzel, werkbank)
    assert lies(wurzel, "templates/d.html") == "<b>Zu</b>"
    assert lies(wurzel, "templates/e.html") == "<b>Schließen</b>"


def test_erkennung_meldet_nur_unberuehrte_englische_stuecke(tmp_path):
    katalog = text("*", "Last Ping", "Letzter Ping") + text("*", "Slack", "Slack") + """
[[quelltext]]
datei = "templates/f.html"
en = "<p>Run <b>now</b></p>"
de = "<p>Jetzt <b>starten</b></p>"
"""
    quelle = "<h1>Hello world</h1><td>Last Ping</td><i>Slack</i><p>Run <b>now</b></p>{{ check.name }}"
    wurzel, werkbank = aufbau(tmp_path, katalog, {"templates/f.html": quelle})
    bericht = sprache.bauen(wurzel, werkbank)
    assert bericht["englisch"] == [{"datei": "templates/f.html", "text": "Hello world"}]


def test_erkennung_uebergeht_ausdruecke_und_nummern(tmp_path):
    quelle = ('<!DOCTYPE html><a title="{{ project }}">x</a><i>4.4-wb1.1.0</i><b>v4.4</b><b>Werkbank 0.0.0-dev</b>'
              '<p>{{ n }} checks</p><s>&#8204;&nbsp;&#x2014;</s>')
    wurzel, werkbank = aufbau(tmp_path, dateien={"templates/o.html": quelle})
    bericht = sprache.bauen(wurzel, werkbank)
    assert [r["text"] for r in bericht["englisch"]] == ["Werkbank 0.0.0-dev", "checks"]


def test_fehlende_datei_und_unbenutzte_globale_eintraege(tmp_path):
    katalog = text("templates/fehlt.html", "Hello", "Hallo") + text("*", "Nowhere", "Nirgends")
    wurzel, werkbank = aufbau(tmp_path, katalog, {"templates/g.html": "<b>x</b>"})
    bericht = sprache.bauen(wurzel, werkbank)
    assert {"datei": "templates/fehlt.html", "art": "text", "en": "Hello", "grund": "Datei fehlt"} in bericht["ohne_fundstelle"]
    assert {"datei": "*", "art": "text", "en": "Nowhere", "grund": "in keiner Vorlage gefunden"} in bericht["ohne_fundstelle"]


def test_ausnahmen_bleiben_unberuehrt_und_ungemeldet(tmp_path):
    wurzel, werkbank = aufbau(tmp_path, text("*", "Hello", "Hallo"),
                              {"templates/docs/x.html": "<p>Hello</p><p>Docs only</p>", "templates/h.html": "<p>Hello</p>"})
    bericht = sprache.bauen(wurzel, werkbank)
    assert lies(wurzel, "templates/docs/x.html") == "<p>Hello</p><p>Docs only</p>"
    assert lies(wurzel, "templates/h.html") == "<p>Hallo</p>"
    assert bericht["englisch"] == []


def test_englisch_laesst_die_texte_stehen(tmp_path, monkeypatch):
    monkeypatch.setenv("WB_SPRACHE", "en")
    wurzel, werkbank = aufbau(tmp_path, text("*", "Hello", "Hallo"), {"templates/i.html": "<p>Hello</p>"})
    bericht = sprache.bauen(wurzel, werkbank)
    assert lies(wurzel, "templates/i.html") == "<p>Hello</p>"
    assert bericht["sprache"] == "en"
    assert 'SPRACHE = "en"' in lies(wurzel, "hc/werkbank_einstellungen.py")
    assert "ZUSTAENDE = {}" in lies(wurzel, "hc/werkbank_einstellungen.py")
    assert "ARTEN = {}" in lies(wurzel, "hc/werkbank_einstellungen.py")
    assert "ROLLEN = {}" in lies(wurzel, "hc/werkbank_einstellungen.py")
    assert "erweitert = True" in lies(wurzel, "hc/extras.py")


def test_einstellungsmodul_formatmodul_und_local_settings(tmp_path):
    wurzel, werkbank = aufbau(tmp_path)
    sprache.bauen(wurzel, werkbank)
    modul = lies(wurzel, "hc/werkbank_einstellungen.py")
    assert 'SPRACHE = "de"' in modul
    assert 'ZUSTAENDE = {"down": "ausgefallen"}' in modul
    assert 'ARTEN = {"shell": "Shell-Befehl"}' in modul
    assert 'ROLLEN = {"r": "Nur lesen"}' in modul
    assert 'FORMATE = "hc.werkbank_formate"' in modul
    assert lies(wurzel, "hc/werkbank_formate/de/formats.py") == 'DECIMAL_SEPARATOR = "."\n'
    assert lies(wurzel, "hc/local_settings.py").startswith("from hc.werkbank_einstellungen import *")



@pytest.mark.parametrize("abschnitt, meldung", [
    ('[zustaende]\ndown = ""\n', "[zustaende] ordnet jedem Zustand ein Wort zu"),
    ('[arten]\nshell = " "\n', "[arten] ordnet jeder Integrationsart ein Wort zu"),
    ('[arten]\nshell = 1\n', "[arten] ordnet jeder Integrationsart ein Wort zu"),
    ('[rollen]\nm = ""\n', "[rollen] ordnet jeder Rolle im Projekt ein Wort zu"),
    ('[rolen]\nm = "Manager"\n', "unbekannte Abschnitte [rolen]"),
])
def test_woerter_im_katalog_werden_geprueft(tmp_path, abschnitt, meldung):
    konfig = '[katalog]\nstand = "v9.9"\n\n[bereich]\nvorlagen = ["templates/**/*.html"]\n\n' + abschnitt
    wurzel, werkbank = aufbau(tmp_path, konfig=konfig)
    with pytest.raises(sprache.SprachFehler, match=re.escape(meldung)):
        sprache.bauen(wurzel, werkbank)


def test_andere_woerter_fuer_arten(tmp_path):
    konfig = KATALOG_KONFIG.replace('shell = "Shell-Befehl"', 'call = "Telefonanruf"')
    wurzel, werkbank = aufbau(tmp_path, konfig=konfig)
    sprache.bauen(wurzel, werkbank)
    assert 'ARTEN = {"call": "Telefonanruf"}' in lies(wurzel, "hc/werkbank_einstellungen.py")


def mo_laden(pfad):
    with open(pfad, "rb") as datei:
        return gettext.GNUTranslations(datei)


def test_django_texte_landen_in_einer_mo_datei(tmp_path):
    wurzel, werkbank = aufbau(tmp_path)
    sprache.bauen(wurzel, werkbank)
    texte = mo_laden(wurzel / "hc/werkbank_locale/de/LC_MESSAGES/django.mo")
    assert texte.gettext("%(delta)s ago") == "vor %(delta)s"
    assert texte.npgettext("naturaltime-past", "%(num)d day", "%(num)d days", 1) == "%(num)d Tag"
    assert texte.npgettext("naturaltime-past", "%(num)d day", "%(num)d days", 3) == "%(num)d Tagen"
    assert texte.gettext("unbekannt") == "unbekannt"
    assert 'LOCALE = "werkbank_locale"' in lies(wurzel, "hc/werkbank_einstellungen.py")


def test_mo_datei_mit_umlauten_und_anderem_ort(tmp_path, monkeypatch):
    monkeypatch.setenv("WB_LOCALE", "hc/sprachen/korrektur")
    konfig = KATALOG_KONFIG + '\n[[django]]\nkontext = "monat"\nen = "March"\nde = "März"\n'
    wurzel, werkbank = aufbau(tmp_path, konfig=konfig)
    sprache.bauen(wurzel, werkbank)
    texte = mo_laden(wurzel / "hc/sprachen/korrektur/de/LC_MESSAGES/django.mo")
    assert texte.pgettext("monat", "March") == "März"
    assert 'LOCALE = "sprachen/korrektur"' in lies(wurzel, "hc/werkbank_einstellungen.py")


def test_englisch_schreibt_keine_mo_datei(tmp_path, monkeypatch):
    monkeypatch.setenv("WB_SPRACHE", "en")
    wurzel, werkbank = aufbau(tmp_path)
    sprache.bauen(wurzel, werkbank)
    assert not (wurzel / "hc/werkbank_locale").exists()


@pytest.mark.parametrize("eintrag, meldung", [
    ('[[django]]\nen = "A"\n', "de fehlt"),
    ('[[django]]\nen = "A"\nde = ["B", "C"]\n', "de ist ein Text"),
    ('[[django]]\nen = "A"\nplural = "As"\nde = "B"\n', "de ist eine Liste mit 2 Formen"),
    ('[[django]]\nen = "A"\nplural = "As"\nde = ["B"]\n', "de ist eine Liste mit 2 Formen"),
    ('[[django]]\nen = "A"\nde = "B"\nfarbe = "rot"\n', "unbekannte Schlüssel farbe"),
    ('[[django]]\nen = "%(delta)s ago"\nde = "B"\n', "doppelt"),
])
def test_django_eintraege_werden_geprueft(tmp_path, eintrag, meldung):
    wurzel, werkbank = aufbau(tmp_path, konfig=KATALOG_KONFIG + "\n" + eintrag)
    with pytest.raises(sprache.SprachFehler, match=re.escape(meldung)):
        sprache.bauen(wurzel, werkbank)

def test_andere_ziele_fuer_module(tmp_path, monkeypatch):
    monkeypatch.setenv("WB_EINSTELLUNGSMODUL", "hc/eigene_einstellungen.py")
    monkeypatch.setenv("WB_FORMATMODUL", "hc/eigene_formate")
    monkeypatch.setenv("WB_LOCAL_SETTINGS", "hc/andere_settings.py")
    wurzel, werkbank = aufbau(tmp_path)
    sprache.bauen(wurzel, werkbank)
    assert 'FORMATE = "hc.eigene_formate"' in lies(wurzel, "hc/eigene_einstellungen.py")
    assert (wurzel / "hc/eigene_formate/de/formats.py").is_file()
    assert lies(wurzel, "hc/andere_settings.py").startswith("from hc.eigene_einstellungen import *")


@pytest.mark.parametrize("katalog, meldung", [
    ("text = [", "kein gültiges TOML"),
    ("[[foo]]\nx = 1\n", "unbekannte Abschnitte foo"),
    ('[[text]]\ndatei = "*"\nen = "A"\ndee = "B"\n', "unbekannte Schlüssel dee"),
    ('[[text]]\ndatei = "*"\nen = "A"\nde = " "\n', "de fehlt oder ist leer"),
    ('[[text]]\ndatei = "*"\nen = "A"\nde = "B"\nanzahl = 2\n', "anzahl gilt nur für"),
    ('[[quelltext]]\ndatei = "x.py"\nen = "A"\nde = "B"\nanzahl = 0\n', "anzahl ist 0"),
    ('[[quelltext]]\ndatei = "*"\nen = "A"\nde = "B"\n', "brauchen eine bestimmte Datei"),
    (text("*", "A", "B") + text("*", "A", "C"), "doppelt"),
])
def test_ungueltiger_katalog(tmp_path, katalog, meldung):
    wurzel, werkbank = aufbau(tmp_path, katalog)
    with pytest.raises(sprache.SprachFehler, match=meldung):
        sprache.bauen(wurzel, werkbank)


def test_attribut_ersatz_mit_anfuehrungszeichen(tmp_path):
    katalog = '[[text]]\ndatei = "*"\nen = "Close"\nde = \'Das "Ende"\'\n'
    wurzel, werkbank = aufbau(tmp_path, katalog, {"templates/j.html": '<a title="Close">x</a>'})
    with pytest.raises(sprache.SprachFehler, match="Anführungszeichen"):
        sprache.bauen(wurzel, werkbank)


@pytest.mark.parametrize("name, wert, meldung", [
    ("WB_SPRACHE", "fr", "WB_SPRACHE ist 'fr'"),
    ("WB_KATALOG", "fehlt", "Den Katalog-Ordner"),
    ("WB_LOCAL_SETTINGS", "../draussen.py", "WB_LOCAL_SETTINGS ist '../draussen.py'"),
])
def test_ungueltige_einstellungen(tmp_path, monkeypatch, name, wert, meldung):
    monkeypatch.setenv(name, wert)
    wurzel, werkbank = aufbau(tmp_path)
    with pytest.raises(sprache.SprachFehler, match=meldung):
        sprache.bauen(wurzel, werkbank)


def test_erweiterung_ohne_anker_bricht_ab(tmp_path):
    wurzel, werkbank = aufbau(tmp_path, dateien={"hc/extras.py": "import x\n"})
    with pytest.raises(sprache.SprachFehler, match="Anker steht 0-mal in hc/extras.py"):
        sprache.bauen(wurzel, werkbank)


def test_crlf_bleibt_erhalten(tmp_path):
    wurzel, werkbank = aufbau(tmp_path, text("*", "Hello", "Hallo"), {"templates/k.html": "<p>\r\nHello\r\n</p>\r\n"})
    sprache.bauen(wurzel, werkbank)
    assert lies(wurzel, "templates/k.html") == "<p>\r\nHallo\r\n</p>\r\n"


def test_inventur_liefert_gueltiges_toml(tmp_path):
    wurzel, werkbank = aufbau(tmp_path, dateien={
        "templates/l.html": '<p>Hello world</p><b>Cancel</b><p>Say "hi"</p>',
        "templates/m.html": "<b>Cancel</b>"})
    geruest = tomllib.loads(sprache.inventur(wurzel, werkbank, global_ab=2))
    eintraege = {(e["datei"], e["en"]) for e in geruest["text"]}
    assert ("*", "Cancel") in eintraege
    assert ("templates/l.html", "Hello world") in eintraege
    assert ("templates/l.html", 'Say "hi"') in eintraege
    assert all(e["de"] == "" for e in geruest["text"])
    assert lies(wurzel, "templates/l.html").startswith("<p>Hello world</p>")


def test_bericht_wird_als_abschnitt_eingefuegt(tmp_path):
    wurzel, werkbank = aufbau(tmp_path, text("*", "Hello", "Hallo"), {"templates/n.html": "<p>Hello</p>"})
    bericht = tmp_path / "bericht.json"
    bericht.write_text(json.dumps({"fassung": "x"}), encoding="utf-8")
    sprache.bauen(wurzel, werkbank, bericht)
    daten = json.loads(bericht.read_text(encoding="utf-8"))
    assert daten["fassung"] == "x"
    assert daten["uebersetzung"]["ersetzt"] == 1
    assert daten["uebersetzung"]["stand"] == "v9.9"

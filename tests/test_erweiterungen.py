"""Filter und Tags, die werkbank/erweiterungen.toml in hc/front/templatetags/hc_extras.py einsetzt."""
import html
import tomllib
from pathlib import Path
from types import SimpleNamespace

WURZEL = Path(__file__).resolve().parent.parent
ANKER = "register = template.Library()"
ERWEITERUNGEN = tomllib.loads((WURZEL / "werkbank" / "erweiterungen.toml").read_text(encoding="utf-8"))["quelltext"]


def format_html(vorlage: str, *werte) -> str:
    """Steht für Djangos format_html, das hc_extras selbst importiert."""
    return vorlage.format(*(html.escape(str(w)) for w in werte))


class Sammler:
    """Steht für template.Library(): gibt die Funktionen unverändert zurück."""

    def filter(self, funktion):
        return funktion

    def simple_tag(self, funktion):
        return funktion


def laden(**einstellungen):
    (eintrag,) = [e for e in ERWEITERUNGEN if e["datei"] == "hc/front/templatetags/hc_extras.py"]
    assert ANKER in eintrag["en"] and ANKER in eintrag["de"]
    namen = {"register": Sammler(), "settings": SimpleNamespace(**einstellungen),
             "format_html": format_html, "escape": html.escape}
    exec(compile(eintrag["de"].replace(ANKER, ""), "erweiterungen.toml", "exec"), namen)
    return namen


class Kanal:
    def __init__(self, kind, anzeige):
        self.kind = kind
        self._anzeige = anzeige

    def get_kind_display(self):
        return self._anzeige


def test_zustand_nutzt_die_woerter_aus_den_einstellungen():
    zustand = laden(WERKBANK_ZUSTAENDE={"down": "ausgefallen", "up": "läuft"})["zustand"]
    assert zustand("down") == "ausgefallen"
    assert zustand("up") == "läuft"
    assert zustand("grace") == "grace"


def test_zustand_ohne_einstellung_bleibt_unveraendert():
    assert laden()["zustand"]("down") == "down"


def test_art_nutzt_die_woerter_aus_den_einstellungen():
    art = laden(WERKBANK_ARTEN={"shell": "Shell-Befehl", "call": "Telefonanruf"})["art"]
    assert art(Kanal("shell", "Shell Command")) == "Shell-Befehl"
    assert art(Kanal("call", "Phone Call")) == "Telefonanruf"


def test_art_ohne_eintrag_zeigt_den_namen_aus_healthchecks():
    assert laden(WERKBANK_ARTEN={"shell": "Shell-Befehl"})["art"](Kanal("slack", "Slack")) == "Slack"
    assert laden()["art"](Kanal("shell", "Shell Command")) == "Shell Command"


class Mitglied:
    def __init__(self, role, anzeige):
        self.role = role
        self._anzeige = anzeige

    def get_role_display(self):
        return self._anzeige


def test_rolle_nutzt_die_woerter_aus_den_einstellungen():
    rolle = laden(WERKBANK_ROLLEN={"r": "Nur lesen", "m": "Leitung"})["rolle"]
    assert rolle(Mitglied("r", "Read-only")) == "Nur lesen"
    assert rolle(Mitglied("m", "Manager")) == "Leitung"


def test_rolle_ohne_eintrag_zeigt_den_namen_aus_healthchecks():
    assert laden(WERKBANK_ROLLEN={"r": "Nur lesen"})["rolle"](Mitglied("w", "Member")) == "Member"
    assert laden()["rolle"](Mitglied("r", "Read-only")) == "Read-only"


def test_werkbank_mail_liefert_einstellung_oder_leer():
    tag = laden(WB_MAIL_IMPRESSUM_URL="https://example.org/impressum")["werkbank_mail"]
    assert tag("WB_MAIL_IMPRESSUM_URL") == "https://example.org/impressum"
    assert tag("WB_MAIL_DATENSCHUTZ_URL") == ""


def test_werkbank_name_setzt_namen_mit_marke_in_bc_brand():
    tag = laden(SITE_NAME="bright color | health", WERKBANK_MARKEN=["bright color"])["werkbank_name"]
    assert tag() == '<span class="bc-brand">bright color | health</span>'


def test_werkbank_name_findet_jede_marke_der_liste_in_jeder_schreibung():
    tag = laden(SITE_NAME="Monitoring by ACME", WERKBANK_MARKEN=["bright color", "acme"])["werkbank_name"]
    assert tag() == '<span class="bc-brand">Monitoring by ACME</span>'


def test_werkbank_name_ohne_marke_bleibt_beim_namen():
    assert laden(SITE_NAME="Healthchecks", WERKBANK_MARKEN=["bright color"])["werkbank_name"]() == "Healthchecks"
    assert laden(SITE_NAME="bright color | health", WERKBANK_MARKEN=[])["werkbank_name"]() == "bright color | health"
    assert laden(SITE_NAME="bright color | health")["werkbank_name"]() == "bright color | health"


def test_werkbank_name_maskiert_html():
    tag = laden(SITE_NAME="<b>bright color</b> & Co", WERKBANK_MARKEN=["bright color"])["werkbank_name"]
    assert tag() == '<span class="bc-brand">&lt;b&gt;bright color&lt;/b&gt; &amp; Co</span>'
    assert laden(SITE_NAME="A & B", WERKBANK_MARKEN=[])["werkbank_name"]() == "A &amp; B"


def test_katalog_uebersetzt_die_anmeldung_mit_werkbank_name():
    # Der Katalog läuft nach den Erweiterungen; sein Anker ist deren Ersatz.
    (anmeldung,) = [e for e in ERWEITERUNGEN if e["datei"] == "templates/accounts/login.html"]
    katalog = tomllib.loads((WURZEL / "werkbank" / "deutsch" / "oberflaeche.toml").read_text(encoding="utf-8"))
    eintraege = [e for e in katalog["quelltext"] if e["datei"] == "templates/accounts/login.html" and "<h1>" in e["en"]]
    assert [e["en"] for e in eintraege] == [anmeldung["de"]]
    assert "{% werkbank_name %}" in eintraege[0]["de"]


def test_doku_platzhalter_steht_in_fragment_und_ersetzung():
    (fragment,) = [e for e in ERWEITERUNGEN if e["datei"] == "templates/docs/introduction.html-fragment"]
    (ansicht,) = [e for e in ERWEITERUNGEN if e["datei"] == "hc/front/views.py"]
    assert "WERKBANK_NAME" in fragment["de"] and "SITE_NAME" in fragment["en"]
    assert '"WERKBANK_NAME": werkbank_name(),' in ansicht["de"]

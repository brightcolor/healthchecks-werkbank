"""Filter und Tags, die werkbank/erweiterungen.toml in hc/front/templatetags/hc_extras.py einsetzt."""
import tomllib
from pathlib import Path
from types import SimpleNamespace

WURZEL = Path(__file__).resolve().parent.parent
ANKER = "register = template.Library()"


class Sammler:
    """Steht für template.Library(): gibt die Funktionen unverändert zurück."""

    def filter(self, funktion):
        return funktion

    def simple_tag(self, funktion):
        return funktion


def laden(**einstellungen):
    daten = tomllib.loads((WURZEL / "werkbank" / "erweiterungen.toml").read_text(encoding="utf-8"))
    (eintrag,) = [e for e in daten["quelltext"] if e["datei"] == "hc/front/templatetags/hc_extras.py"]
    assert ANKER in eintrag["en"] and ANKER in eintrag["de"]
    namen = {"register": Sammler(), "settings": SimpleNamespace(**einstellungen)}
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

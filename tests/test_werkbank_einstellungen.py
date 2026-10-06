import sys
import tomllib
from pathlib import Path

import pytest

# Ein Untermodul prüft auf das echte Django: Ohne Django gilt werkbank/django im Suchpfad als Paket "django".
pytest.importorskip("django.core")
from django.core.exceptions import ImproperlyConfigured  # noqa: E402

WURZEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WURZEL / "werkbank"))
import sprache  # noqa: E402

VORLAGE = WURZEL / "werkbank" / "django" / "werkbank_einstellungen.py"
FORMATE = WURZEL / "werkbank" / "django" / "werkbank_formate" / "de" / "formats.py"
MAIL = ("WB_MAIL_ANSCHRIFT", "WB_MAIL_IMPRESSUM_URL", "WB_MAIL_DATENSCHUTZ_URL")


def laden(sprache_="de", zustaende='{"down": "ausgefallen"}', arten='{"shell": "Shell-Befehl"}', rollen='{"r": "Nur lesen"}'):
    text = (VORLAGE.read_text(encoding="utf-8").replace("@@WB_SPRACHE@@", sprache_)
            .replace("@@WB_ZUSTAENDE@@", zustaende).replace("@@WB_ARTEN@@", arten).replace("@@WB_ROLLEN@@", rollen).replace("@@WB_LOCALE@@", "werkbank_locale").replace("@@WB_FORMATMODUL@@", "hc.werkbank_formate"))
    namen: dict = {"__file__": str(VORLAGE)}
    exec(compile(text, str(VORLAGE), "exec"), namen)
    return namen


@pytest.fixture(autouse=True)
def ohne_mail_umgebung(monkeypatch):
    for name in (*MAIL, "WB_MARKEN"):
        monkeypatch.delenv(name, raising=False)


def test_deutsch_schaltet_django_um():
    namen = laden()
    assert namen["USE_I18N"] is True
    assert namen["LANGUAGE_CODE"] == "de"
    assert namen["FORMAT_MODULE_PATH"] == ["hc.werkbank_formate"]
    assert namen["LOCALE_PATHS"] == [str(VORLAGE.parent / "werkbank_locale")]
    assert namen["WERKBANK_ZUSTAENDE"] == {"down": "ausgefallen"}
    assert namen["WERKBANK_ARTEN"] == {"shell": "Shell-Befehl"}
    assert namen["WERKBANK_ROLLEN"] == {"r": "Nur lesen"}
    assert set(namen["__all__"]) >= {"USE_I18N", "LANGUAGE_CODE", "FORMAT_MODULE_PATH", "WB_MAIL_ANSCHRIFT"}
    assert "os" not in namen["__all__"]


def test_englisch_laesst_django_englisch():
    namen = laden("en", "{}", "{}", "{}")
    assert "USE_I18N" not in namen
    assert "USE_I18N" not in namen["__all__"]
    assert namen["WERKBANK_ZUSTAENDE"] == {}
    assert namen["WERKBANK_ARTEN"] == {}
    assert namen["WERKBANK_ROLLEN"] == {}


def test_mail_einstellungen_sind_als_vorgabe_leer():
    namen = laden()
    assert [namen[n] for n in MAIL] == ["", "", ""]


def test_gueltige_mail_einstellungen(monkeypatch):
    monkeypatch.setenv("WB_MAIL_ANSCHRIFT", "  Firma · Straße 1 · 12345 Ort ")
    monkeypatch.setenv("WB_MAIL_IMPRESSUM_URL", "https://example.org/impressum")
    monkeypatch.setenv("WB_MAIL_DATENSCHUTZ_URL", "https://example.org/datenschutz")
    namen = laden()
    assert namen["WB_MAIL_ANSCHRIFT"] == "Firma · Straße 1 · 12345 Ort"
    assert namen["WB_MAIL_IMPRESSUM_URL"] == "https://example.org/impressum"


@pytest.mark.parametrize("name, wert, meldung", [
    ("WB_MAIL_IMPRESSUM_URL", "http://example.org", "WB_MAIL_IMPRESSUM_URL ist 'http://example.org'"),
    ("WB_MAIL_DATENSCHUTZ_URL", "https://example.org/a b", "Erwartet ist eine Adresse mit https://"),
    ("WB_MAIL_ANSCHRIFT", "x" * 201, "hat 201 Zeichen"),
    ("WB_MAIL_ANSCHRIFT", "Zeile 1\nZeile 2", "steht auf mehreren Zeilen"),
])
def test_ungueltige_mail_einstellungen(monkeypatch, name, wert, meldung):
    monkeypatch.setenv(name, wert)
    with pytest.raises(ImproperlyConfigured, match=meldung):
        laden()


def test_marken_vorgabe_ist_bright_color():
    namen = laden()
    assert namen["WERKBANK_MARKEN"] == ["bright color"]
    assert "WERKBANK_MARKEN" in namen["__all__"]


@pytest.mark.parametrize("wert, erwartet", [
    ("acme, Beispiel GmbH ,", ["acme", "Beispiel GmbH"]),
    ("", []),
    (" , ", []),
])
def test_marken_aus_der_umgebung(monkeypatch, wert, erwartet):
    monkeypatch.setenv("WB_MARKEN", wert)
    assert laden()["WERKBANK_MARKEN"] == erwartet


@pytest.mark.parametrize("wert, meldung", [
    (",".join(f"marke{i}" for i in range(11)), "nennt 11 Namen. Erlaubt sind höchstens 10"),
    ("x" * 65, "mit 65 Zeichen. Erlaubt sind höchstens 64"),
])
def test_ungueltige_marken(monkeypatch, wert, meldung):
    monkeypatch.setenv("WB_MARKEN", wert)
    with pytest.raises(ImproperlyConfigured, match=meldung):
        laden()


def test_formatmodul_haelt_den_dezimalpunkt():
    namen: dict = {"__file__": str(VORLAGE)}
    exec(compile(FORMATE.read_text(encoding="utf-8"), str(FORMATE), "exec"), namen)
    assert (namen["DECIMAL_SEPARATOR"], namen["THOUSAND_SEPARATOR"], namen["NUMBER_GROUPING"]) == (".", "", 0)
    assert "DATE_FORMAT" not in namen


def test_erweiterungen_treffen_die_standversion():
    stand = tomllib.loads((WURZEL / "werkbank" / "deutsch" / "katalog.toml").read_text(encoding="utf-8"))["katalog"]["stand"]
    quelle = WURZEL / ".upstream" / stand
    if not (quelle / "hc" / "front" / "templatetags" / "hc_extras.py").is_file():
        pytest.skip(f"Keine Quelle von Healthchecks {stand} unter .upstream/.")
    for e in sprache.lade_eintraege(WURZEL / "werkbank" / "erweiterungen.toml"):
        assert sprache.lies(quelle / e.datei)[0].count(e.en) == e.anzahl, e.herkunft

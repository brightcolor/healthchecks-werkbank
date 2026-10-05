import sys
import tomllib
from pathlib import Path

import pytest

pytest.importorskip("django")
from django.core.exceptions import ImproperlyConfigured  # noqa: E402

WURZEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WURZEL / "werkbank"))
import sprache  # noqa: E402

VORLAGE = WURZEL / "werkbank" / "django" / "werkbank_einstellungen.py"
FORMATE = WURZEL / "werkbank" / "django" / "werkbank_formate" / "de" / "formats.py"
MAIL = ("WB_MAIL_ANSCHRIFT", "WB_MAIL_IMPRESSUM_URL", "WB_MAIL_DATENSCHUTZ_URL")


def laden(sprache_="de", zustaende='{"down": "ausgefallen"}'):
    text = (VORLAGE.read_text(encoding="utf-8").replace("@@WB_SPRACHE@@", sprache_)
            .replace("@@WB_ZUSTAENDE@@", zustaende).replace("@@WB_FORMATMODUL@@", "hc.werkbank_formate"))
    namen: dict = {}
    exec(compile(text, str(VORLAGE), "exec"), namen)
    return namen


@pytest.fixture(autouse=True)
def ohne_mail_umgebung(monkeypatch):
    for name in MAIL:
        monkeypatch.delenv(name, raising=False)


def test_deutsch_schaltet_django_um():
    namen = laden()
    assert namen["USE_I18N"] is True
    assert namen["LANGUAGE_CODE"] == "de"
    assert namen["FORMAT_MODULE_PATH"] == ["hc.werkbank_formate"]
    assert namen["WERKBANK_ZUSTAENDE"] == {"down": "ausgefallen"}
    assert set(namen["__all__"]) >= {"USE_I18N", "LANGUAGE_CODE", "FORMAT_MODULE_PATH", "WB_MAIL_ANSCHRIFT"}
    assert "os" not in namen["__all__"]


def test_englisch_laesst_django_englisch():
    namen = laden("en", "{}")
    assert "USE_I18N" not in namen
    assert "USE_I18N" not in namen["__all__"]
    assert namen["WERKBANK_ZUSTAENDE"] == {}


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


def test_formatmodul_haelt_den_dezimalpunkt():
    namen: dict = {}
    exec(compile(FORMATE.read_text(encoding="utf-8"), str(FORMATE), "exec"), namen)
    assert (namen["DECIMAL_SEPARATOR"], namen["THOUSAND_SEPARATOR"], namen["NUMBER_GROUPING"]) == (".", "", 0)
    assert "DATE_FORMAT" not in namen


def test_erweiterung_trifft_hc_extras_der_standversion():
    stand = tomllib.loads((WURZEL / "werkbank" / "deutsch" / "katalog.toml").read_text(encoding="utf-8"))["katalog"]["stand"]
    ziel = WURZEL / ".upstream" / stand / "hc" / "front" / "templatetags" / "hc_extras.py"
    if not ziel.is_file():
        pytest.skip(f"Keine Quelle von Healthchecks {stand} unter .upstream/.")
    text = sprache.lies(ziel)[0]
    for e in sprache.lade_eintraege(WURZEL / "werkbank" / "erweiterungen.toml"):
        assert text.count(e.en) == e.anzahl, e.herkunft

import sys
from pathlib import Path

import pytest

WURZEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WURZEL / "tools"))
import dev  # noqa: E402

VERSION = "v9.9"


@pytest.fixture
def ablage(tmp_path, monkeypatch):
    """Eine saubere Quelle wie nach git clone, dazu UPSTREAM auf den Testordner."""
    quelle = tmp_path / VERSION
    (quelle / "templates").mkdir(parents=True)
    (quelle / "manage.py").write_text("", encoding="utf-8")
    (quelle / "templates" / "base.html").write_text("sauber", encoding="utf-8")
    monkeypatch.setattr(dev, "UPSTREAM", tmp_path)
    return tmp_path


def arbeitskopie_mit_daten(ablage):
    arbeit = ablage / f"arbeit-{VERSION}"
    (arbeit / "templates").mkdir(parents=True)
    (arbeit / "manage.py").write_text("", encoding="utf-8")
    (arbeit / "search.db").write_text("suchindex", encoding="utf-8")
    (arbeit / "templates" / "base.html").write_text("schon eingebaut", encoding="utf-8")
    return arbeit


def test_arbeitskopie_ersetzt_eine_freie_kopie(ablage):
    arbeit = arbeitskopie_mit_daten(ablage)
    assert dev.arbeitskopie(VERSION) == arbeit
    assert not (arbeit / "search.db").exists()
    assert (arbeit / "templates" / "base.html").read_text(encoding="utf-8") == "sauber"


def test_arbeitskopie_bleibt_ganz_wenn_sie_in_benutzung_ist(ablage, monkeypatch):
    arbeit = arbeitskopie_mit_daten(ablage)

    def gesperrt(self, ziel):
        raise PermissionError(32, "Der Prozess kann nicht auf die Datei zugreifen")

    monkeypatch.setattr(Path, "rename", gesperrt)
    with pytest.raises(dev.DevFehler, match="Server beenden"):
        dev.arbeitskopie(VERSION)
    assert (arbeit / "search.db").read_text(encoding="utf-8") == "suchindex"


def test_einsetzen_laesst_die_arbeitskopie_stehen_und_baut_in_die_saubere_vorlage_ein(ablage, monkeypatch):
    arbeit = arbeitskopie_mit_daten(ablage)
    gesehen = {}
    monkeypatch.setattr(dev, "einsetzen", lambda pfad: gesehen.update(
        vorlage=(pfad / "templates" / "base.html").read_text(encoding="utf-8")))
    monkeypatch.setattr(dev, "lokale_einstellungen", lambda pfad: None)
    dev.nur_einsetzen(VERSION)
    assert gesehen["vorlage"] == "sauber"
    assert (arbeit / "search.db").read_text(encoding="utf-8") == "suchindex"


def test_einsetzen_ohne_arbeitskopie_nennt_den_naechsten_schritt(ablage):
    with pytest.raises(dev.DevFehler, match="vorbereiten"):
        dev.nur_einsetzen(VERSION)

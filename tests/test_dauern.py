"""Deutsche Dauern: code.toml angewendet auf hc/lib/date.py der Standversion."""
import importlib.util
import sys
import tomllib
from datetime import timedelta
from pathlib import Path

import pytest

pytest.importorskip("django")

WURZEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WURZEL / "werkbank"))
import sprache  # noqa: E402


@pytest.fixture(scope="module")
def date(tmp_path_factory):
    stand = tomllib.loads((WURZEL / "werkbank/deutsch/katalog.toml").read_text(encoding="utf-8"))["katalog"]["stand"]
    quelle = WURZEL / ".upstream" / stand / "hc" / "lib" / "date.py"
    if not quelle.is_file():
        pytest.skip(f"Keine Quelle von Healthchecks {stand} unter .upstream/.")
    text = sprache.lies(quelle)[0]
    for e in sprache.lade_eintraege(WURZEL / "werkbank/deutsch/code.toml"):
        if e.datei == "hc/lib/date.py":
            text, _, passt = sprache.quelltext_anwenden(text, e)
            assert passt, e.herkunft
    ziel = tmp_path_factory.mktemp("date") / "date_de.py"
    ziel.write_text(text, encoding="utf-8")
    spec = importlib.util.spec_from_file_location("date_de", ziel)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


@pytest.mark.parametrize("dauer, text", [
    (timedelta(minutes=1), "1 Minute"),
    (timedelta(minutes=5), "5 Minuten"),
    (timedelta(hours=1), "1 Stunde"),
    (timedelta(days=1), "1 Tag"),
    (timedelta(days=2, hours=3), "2 Tage 3 Stunden"),
    (timedelta(days=14), "2 Wochen"),
    (timedelta(days=8), "8 Tage"),
])
def test_format_duration(date, dauer, text):
    assert date.format_duration(dauer) == text


def test_kurzformen(date):
    assert date.format_hms(timedelta(hours=1, minutes=2, seconds=3)) == "1 h 2 min 3 s"
    assert date.format_hms(timedelta(seconds=0.5)) == "0.50 s"
    assert date.format_approx_duration(timedelta(days=2, hours=5)) == "2 Tage 5 h"
    assert date.format_approx_duration(timedelta(days=1, hours=5)) == "1 Tag 5 h"
    assert date.format_approx_duration(timedelta(minutes=3, seconds=4)) == "3 min 4 s"


@pytest.mark.parametrize("dauer, text", [
    (timedelta(days=1, hours=1), "1 Tag, 1 Stunde"),
    (timedelta(days=3, hours=2), "3 Tage, 2 Stunden"),
    (timedelta(hours=1, minutes=5), "1 Stunde, 5 Minuten"),
    (timedelta(minutes=1, seconds=1), "1 Minute, 1 Sekunde"),
    (timedelta(seconds=30), "30 Sekunden"),
])
def test_dauer_im_satz(date, dauer, text):
    assert date.format_duration_for_sentence(dauer) == text

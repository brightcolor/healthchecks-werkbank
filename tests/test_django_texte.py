"""Djangos deutsche Zeitangaben mit den Korrekturen aus [[django]] in werkbank/deutsch/katalog.toml.

Django läuft in einem eigenen Prozess, damit die übrigen Tests ohne konfiguriertes Django bleiben.
"""
import subprocess
import sys
from pathlib import Path

import pytest

pytest.importorskip("django")

WURZEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WURZEL / "werkbank"))
import sprache  # noqa: E402

SKRIPT = r"""
import datetime, sys
import django
from django.conf import settings
settings.configure(
    USE_I18N=True, USE_TZ=True, LANGUAGE_CODE="de",
    LOCALE_PATHS=sys.argv[1:], INSTALLED_APPS=["django.contrib.humanize"],
)
django.setup()
from django.contrib.humanize.templatetags.humanize import naturaltime
from django.utils import timezone, translation
translation.activate("de")
jetzt = timezone.now()
abstaende = [
    datetime.timedelta(days=1, hours=5),
    datetime.timedelta(days=3),
    datetime.timedelta(days=33),
    datetime.timedelta(days=740),
    -datetime.timedelta(days=2, minutes=30),
    datetime.timedelta(hours=3),
]
for abstand in abstaende:
    print(naturaltime(jetzt - abstand).replace("\xa0", " "))
"""


def zeiten(*locale_pfade):
    ergebnis = subprocess.run(
        [sys.executable, "-c", SKRIPT, *map(str, locale_pfade)],
        capture_output=True, text=True, encoding="utf-8", check=True,
    )
    return ergebnis.stdout.splitlines()


def test_relative_zeiten_mit_korrekturen(tmp_path):
    katalog = sprache.lade_katalog(WURZEL / "werkbank" / "deutsch")
    mo = tmp_path / "de" / "LC_MESSAGES" / "django.mo"
    mo.parent.mkdir(parents=True)
    mo.write_bytes(sprache.mo_daten(katalog.django))
    assert zeiten(tmp_path) == [
        "vor 1 Tag, 5 Stunden",
        "vor 3 Tagen",
        "vor 1 Monat",
        "vor 2 Jahren",
        "in 2 Tagen",
        "vor 3 Stunden",
    ]


def test_ohne_korrekturen_bleibt_djangos_text(tmp_path):
    assert zeiten()[0] == "1 Tage, 5 Stunden her"

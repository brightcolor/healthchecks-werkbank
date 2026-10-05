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


def lauf(aufbau, *zeilen, mit_datei=True, optionen=("--nur-pruefen",)):
    datei = aufbau / "einstellungen.conf"
    if mit_datei:
        datei.write_text("\n".join([f"COMPOSE_DIR={posix(aufbau / 'hc')}", *zeilen]) + "\n", encoding="utf-8")
    env = dict(os.environ, HC_WERKBANK_BESITZ_PRUEFEN="nein")
    return subprocess.run([BASH, posix(SKRIPT), "--einstellungen", posix(datei), *optionen],
                          capture_output=True, text=True, encoding="utf-8", env=env)


def test_gueltige_einstellungen_auch_abseits_der_vorgaben(aufbau):
    erg = lauf(aufbau, "IMAGE=localhost:5000/hcwb", "TRACK_TAG=stabil", "SERVICE=hc", "BACKUP_KEEP=1",
               "WAIT_SECONDS=1800", "APP_PORT=9000", 'CHECK_PATHS="/api/v3/status/ /x/"', "CHECK_TIMEOUT=120",
               "STYLE_MARKER=werkbank", "LOG_FILE=/tmp/wb.log", "LOCK_FILE=/tmp/wb.lock",
               "FAILED_FILE=/tmp/wb.failed", "DB_PATH=/daten/x.sqlite", "# Kommentar", "")
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
    ("CHECK_PATHS=api/status", "Der Pfad api/status beginnt nicht mit /."),
    ("CHECK_PATHS=/*", "Der Pfad /* enthält andere Zeichen"),
    ("LOG_FILE=relativ.log", "LOG_FILE ist relativ.log. Erwartet ist ein absoluter Pfad"),
    ("FAILED_FILE=relativ", "FAILED_FILE ist relativ. Erwartet ist ein absoluter Pfad"),
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


def test_ungueltiger_tag_in_der_env(aufbau):
    (aufbau / "hc" / ".env").write_text("HC_IMAGE_TAG=4.4/wb\nDB_NAME=/data/hc.sqlite\n", encoding="utf-8")
    erg = lauf(aufbau)
    assert erg.returncode == 2
    assert "HC_IMAGE_TAG=4.4/wb" in erg.stderr
    assert "kein gültiger Tag" in erg.stderr


def test_compose_dir_ohne_compose_datei(aufbau):
    (aufbau / "hc" / "compose.yaml").unlink()
    erg = lauf(aufbau)
    assert erg.returncode == 2
    assert "keine compose.yaml" in erg.stderr


def test_ohne_datei_gelten_die_vorgaben(aufbau):
    erg = lauf(aufbau, mit_datei=False)
    assert erg.returncode == 2
    assert "Den Ordner /opt/healthchecks gibt es nicht." in erg.stderr


def test_erneut_ist_eine_gueltige_option(aufbau):
    erg = lauf(aufbau, optionen=("--erneut", "--nur-pruefen"))
    assert erg.returncode == 0, erg.stderr


def test_unbekannte_option():
    erg = subprocess.run([BASH, posix(SKRIPT), "--sofort"], capture_output=True, text=True, encoding="utf-8")
    assert erg.returncode == 2
    assert "Unbekannte Option --sofort" in erg.stderr

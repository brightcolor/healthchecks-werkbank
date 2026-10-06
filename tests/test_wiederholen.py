"""tools/ci/wiederholen.sh mit einem Befehl, der erst nach einigen Fehlschlägen gelingt."""
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

WURZEL = Path(__file__).resolve().parent.parent
SKRIPT = WURZEL / "tools" / "ci" / "wiederholen.sh"
BASH = os.environ.get("WB_BASH") or shutil.which("bash")
pytestmark = pytest.mark.skipif(BASH is None, reason="bash fehlt; WB_BASH auf den Pfad von bash setzen")

# Scheitert, bis der Zähler in $ZAEHLER die Zahl $GELINGT_AB erreicht.
BEFEHL = """#!/usr/bin/env bash
n=$(( $(cat "$ZAEHLER" 2>/dev/null || echo 0) + 1 ))
echo "$n" > "$ZAEHLER"
[ "$n" -ge "$GELINGT_AB" ] || { echo "unknown blob" >&2; exit 7; }
echo "hochgeladen"
"""


def posix(pfad: Path) -> str:
    text = pfad.as_posix()
    m = re.match(r"^([A-Za-z]):/(.*)$", text)
    return f"/{m.group(1).lower()}/{m.group(2)}" if (m and os.name == "nt") else text


def lauf(tmp_path, gelingt_ab: int, *argumente: str, **umgebung):
    befehl = tmp_path / "hochladen"
    befehl.write_text(BEFEHL, encoding="utf-8", newline="\n")
    befehl.chmod(0o755)
    zaehler = tmp_path / "zaehler"
    env = dict(os.environ, ZAEHLER=posix(zaehler), GELINGT_AB=str(gelingt_ab), WB_VERSUCH_PAUSE="0")
    env.update(umgebung)
    teile = argumente or ("--", posix(befehl))
    ergebnis = subprocess.run([BASH, posix(SKRIPT), *teile], env=env, capture_output=True, text=True, encoding="utf-8")
    versuche = int(zaehler.read_text().strip()) if zaehler.exists() else 0
    return ergebnis, versuche


def test_gelingt_beim_ersten_versuch(tmp_path):
    ergebnis, versuche = lauf(tmp_path, 1)
    assert ergebnis.returncode == 0
    assert versuche == 1
    assert "::warning::" not in ergebnis.stdout


def test_wiederholt_bis_zum_erfolg(tmp_path):
    ergebnis, versuche = lauf(tmp_path, 3)
    assert ergebnis.returncode == 0
    assert versuche == 3
    assert ergebnis.stdout.count("::warning::") == 2
    assert "Versuch 2 von 3" in ergebnis.stdout


def test_gibt_nach_allen_versuchen_auf(tmp_path):
    ergebnis, versuche = lauf(tmp_path, 9, WB_VERSUCHE="4")
    assert ergebnis.returncode == 7
    assert versuche == 4
    assert "nach 4 Versuchen gescheitert (zuletzt Rückgabe 7)" in ergebnis.stdout


@pytest.mark.parametrize("name, wert", [
    ("WB_VERSUCHE", "0"), ("WB_VERSUCHE", "11"), ("WB_VERSUCHE", "drei"), ("WB_VERSUCH_PAUSE", "301"),
])
def test_ungueltige_einstellung(tmp_path, name, wert):
    ergebnis, versuche = lauf(tmp_path, 1, **{name: wert})
    assert ergebnis.returncode == 2
    assert versuche == 0
    assert f"{name} ist '{wert}'. Erlaubt ist eine ganze Zahl" in ergebnis.stderr


def test_ohne_befehl_nennt_den_aufruf(tmp_path):
    ergebnis, _ = lauf(tmp_path, 1, "docker")
    assert ergebnis.returncode == 2
    assert "Aufruf: tools/ci/wiederholen.sh -- <Befehl>" in ergebnis.stderr

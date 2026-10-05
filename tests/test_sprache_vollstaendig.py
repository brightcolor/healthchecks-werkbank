"""Vollständigkeit: Der Katalog deckt die Healthchecks-Version aus werkbank/deutsch/katalog.toml ab.

Baut wie der Docker-Bau auf eine Kopie von .upstream/<stand> (Vorlagen der Werkbank, Einbau,
Farben, Mail-Layout, Sprache) und erwartet null englische Textstücke und null Einträge ohne
Fundstelle. Liegt diese Quelle nicht vor, etwa in der CI für ein neues Release, überspringt
sich der Test; dann nennt der Hinweis-Issue die Lücken.
"""
import json
import os
import py_compile
import re
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

WURZEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WURZEL / "tools"))
import dev  # noqa: E402

STAND = tomllib.loads((WURZEL / "werkbank/deutsch/katalog.toml").read_text(encoding="utf-8"))["katalog"]["stand"]
QUELLE = WURZEL / ".upstream" / STAND

pytestmark = pytest.mark.skipif(
    not (QUELLE / "manage.py").is_file(), reason=f"Keine Quelle von Healthchecks {STAND} unter .upstream/."
)


@pytest.fixture(scope="module")
def gebaut(tmp_path_factory):
    ordner = tmp_path_factory.mktemp("vollstaendig")
    arbeit = ordner / "healthchecks"
    shutil.copytree(QUELLE, arbeit, ignore=shutil.ignore_patterns(".git", "static-collected", "__pycache__"))
    bericht = ordner / "bericht.json"
    dev.einsetzen(arbeit, bericht)
    return arbeit, json.loads(bericht.read_text(encoding="utf-8"))


def test_keine_englischen_texte(gebaut):
    _, bericht = gebaut
    assert bericht["uebersetzung"]["sprache"] == "de"
    assert bericht["uebersetzung"]["englisch"] == []


def test_jeder_eintrag_findet_seine_stelle(gebaut):
    _, bericht = gebaut
    assert bericht["uebersetzung"]["ohne_fundstelle"] == []


def test_mail_layout_ohne_hinweis(gebaut):
    _, bericht = gebaut
    assert bericht["mails"]["hinweise"] == []


def test_seiten_sagen_deutsch_an(gebaut):
    arbeit, _ = gebaut
    englisch = [
        p.relative_to(arbeit).as_posix()
        for p in (arbeit / "templates").glob("**/*.html")
        if "docs" not in p.relative_to(arbeit).parts and 'lang="en"' in p.read_text(encoding="utf-8")
    ]
    assert englisch == []


def test_python_dateien_kompilieren(gebaut, tmp_path):
    arbeit, _ = gebaut
    fehler = []
    for nr, pfad in enumerate(sorted((arbeit / "hc").glob("**/*.py"))):
        try:
            py_compile.compile(str(pfad), cfile=str(tmp_path / f"{nr}.pyc"), doraise=True)
        except py_compile.PyCompileError as err:
            fehler.append(str(err))
    assert fehler == []


def test_vorlagen_kompilieren(gebaut):
    arbeit, _ = gebaut
    env = dict(os.environ, DEBUG="False", SECRET_KEY="nur-fuer-den-test", SITE_ROOT="http://localhost:8000",
               DB_NAME=str(arbeit / "test.sqlite"), PYTHONUTF8="1")
    skript = (WURZEL / "tests" / "vorlagen" / "pruefen.py").read_text(encoding="utf-8")
    ergebnis = subprocess.run([sys.executable, "manage.py", "shell", "-c", skript], cwd=arbeit, env=env,
                              capture_output=True, text=True, encoding="utf-8")
    if "ModuleNotFoundError" in ergebnis.stderr:
        pytest.skip("Abhängigkeiten von Healthchecks fehlen; die CI kompiliert die Vorlagen in der Testinstanz.")
    zeile = re.search(r"^VORLAGEN: .*$", ergebnis.stdout, re.M)
    assert ergebnis.returncode == 0 and zeile, ergebnis.stdout[-3000:] + ergebnis.stderr[-3000:]
    assert zeile.group(0).endswith(", 0 mit Fehler")

"""tools/ci/hinweis.sh und der Abschnitt Übersetzung in tools/ci/bericht.py, mit nachgebautem gh."""
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

WURZEL = Path(__file__).resolve().parent.parent
SKRIPT = WURZEL / "tools" / "ci" / "hinweis.sh"
BERICHT_PY = WURZEL / "tools" / "ci" / "bericht.py"
BASH = os.environ.get("WB_BASH") or shutil.which("bash")

GH = """#!/usr/bin/env bash
echo "$*" >> "$FAKE_GH_LOG"
case "$*" in
  "issue list"*"number,title"*) echo "${FAKE_NUMMER:-}" ;;
  "issue list"*) echo "${FAKE_OFFEN:-}" ;;
  "issue create"*|"issue edit"*)
    args=("$@")
    for ((i = 0; i < ${#args[@]}; i++)); do
      if [ "${args[$i]}" = "--body-file" ]; then cat "${args[$((i + 1))]}" >> "$FAKE_GH_KOERPER"; fi
    done ;;
esac
"""


def posix(pfad) -> str:
    text = Path(pfad).as_posix()
    m = re.match(r"^([A-Za-z]):/(.*)$", text)
    return f"/{m.group(1).lower()}/{m.group(2)}" if (m and os.name == "nt") else text


def bericht(englisch=0, ohne=0, mails=0, sprache="de"):
    return {
        "fassung": "4.5-wb1.1.0", "deklarationen": 900, "stylesheets": 12, "automatisch": [],
        "uebersetzung": {
            "sprache": sprache, "stand": "v4.4", "ersetzt": 2100,
            "englisch": [{"datei": f"templates/front/neu{i}.html", "text": f"New text {i}"} for i in range(englisch)],
            "ohne_fundstelle": [{"datei": "templates/front/details.html", "art": "text", "en": f"Old {i}",
                                 "grund": "nicht gefunden"} for i in range(ohne)],
        },
        "mails": {"hinweise": [f"Mail-Hinweis {i}" for i in range(mails)]},
    }


@pytest.fixture
def lauf(tmp_path):
    if BASH is None:
        pytest.skip("bash fehlt; WB_BASH auf den Pfad von bash setzen")

    def ausfuehren(daten, **umgebung):
        bin_ = tmp_path / "bin"
        bin_.mkdir(exist_ok=True)
        gh = bin_ / "gh"
        gh.write_text(GH, encoding="utf-8", newline="\n")
        gh.chmod(0o755)
        pfad = tmp_path / "bericht.json"
        if daten is not None:
            pfad.write_text(json.dumps(daten), encoding="utf-8")
        log, koerper = tmp_path / "gh.log", tmp_path / "koerper.md"
        log.write_text("", encoding="utf-8")
        koerper.write_text("", encoding="utf-8")
        env = dict({k: v for k, v in os.environ.items() if k != "GH_TOKEN"},
                   PATH=str(bin_) + os.pathsep + os.environ.get("PATH", ""), HC_TAG="v4.5", FASSUNG="4.5-wb1.1.0",
                   LAUF_URL="https://example.org/lauf/1", WB_PYTHON=posix(sys.executable),
                   FAKE_GH_LOG=posix(log), FAKE_GH_KOERPER=posix(koerper), **umgebung)
        erg = subprocess.run([BASH, posix(SKRIPT), posix(pfad)], cwd=WURZEL, env=env,
                             capture_output=True, text=True, encoding="utf-8")
        return erg, log.read_text(encoding="utf-8").splitlines(), koerper.read_text(encoding="utf-8")

    return ausfuehren


def test_ohne_hinweise_schliesst_offene_issues(lauf):
    erg, aufrufe, _ = lauf(bericht(), FAKE_OFFEN="5 7")
    assert erg.returncode == 0, erg.stderr
    geschlossen = [a for a in aufrufe if a.startswith("issue close")]
    assert [a.split()[2] for a in geschlossen] == ["5", "7"]
    assert not any(a.startswith("issue create") for a in aufrufe)


def test_englische_texte_legen_ein_issue_an(lauf):
    erg, aufrufe, koerper = lauf(bericht(englisch=3, ohne=1))
    assert erg.returncode == 0, erg.stderr
    (anlegen,) = [a for a in aufrufe if a.startswith("issue create")]
    assert "--title Healthchecks v4.5: 3 Texte noch englisch" in anlegen
    assert "--label uebersetzung" in anlegen
    assert "| templates/front/neu2.html | New text 2 |" in koerper
    assert "Einträge ohne Fundstelle" in koerper and "Nächster Schritt" in koerper
    assert "gebaut mit v4.5" in koerper


def test_vorhandenes_issue_der_version_wird_aktualisiert(lauf):
    erg, aufrufe, _ = lauf(bericht(englisch=2), FAKE_NUMMER="12")
    assert erg.returncode == 0, erg.stderr
    (bearbeiten,) = [a for a in aufrufe if a.startswith("issue edit")]
    assert bearbeiten.startswith("issue edit 12 --title Healthchecks v4.5: 2 Texte noch englisch")
    assert not any(a.startswith("issue create") for a in aufrufe)


@pytest.mark.parametrize("daten, titel", [
    (bericht(mails=2), "Healthchecks v4.5: Hinweise zu den Mails"),
    (bericht(ohne=4), "Healthchecks v4.5: 4 Katalog-Einträge ohne Fundstelle"),
])
def test_titel_nach_art_der_hinweise(lauf, daten, titel):
    erg, aufrufe, _ = lauf(daten)
    assert erg.returncode == 0, erg.stderr
    assert any(f"--title {titel}" in a for a in aufrufe if a.startswith("issue create"))


def test_anderes_label(lauf):
    _, aufrufe, _ = lauf(bericht(englisch=1), WB_HINWEIS_LABEL="sprache")
    assert any("--label sprache" in a for a in aufrufe if a.startswith("issue create"))
    assert all("--label uebersetzung" not in a for a in aufrufe)


def test_fehlender_bericht_aendert_nichts(lauf):
    erg, aufrufe, _ = lauf(None)
    assert erg.returncode == 0
    assert "fehlt oder ist leer" in erg.stdout
    assert aufrufe == []


def bericht_py(daten, tmp_path, *argumente, **umgebung):
    pfad = tmp_path / "b.json"
    pfad.write_text(json.dumps(daten), encoding="utf-8")
    env = dict(os.environ, **umgebung)
    return subprocess.run([sys.executable, str(BERICHT_PY), str(pfad), *argumente], env=env,
                          capture_output=True, text=True, encoding="utf-8")


def test_bericht_begrenzt_die_tabellen(tmp_path):
    erg = bericht_py(bericht(englisch=5), tmp_path, "--uebersetzung", WB_BERICHT_ZEILEN="2")
    assert erg.returncode == 0, erg.stderr
    assert erg.stdout.count("| templates/front/neu") == 2
    assert "Dazu 3 weitere" in erg.stdout
    assert "### Farbableitung" not in erg.stdout


def test_bericht_ohne_option_zeigt_beide_abschnitte(tmp_path):
    erg = bericht_py(bericht(), tmp_path)
    assert "### Farbableitung 4.5-wb1.1.0" in erg.stdout
    assert "### Übersetzung" in erg.stdout and "0 Textstücke noch englisch" in erg.stdout


def test_bericht_englische_sprache(tmp_path):
    erg = bericht_py(bericht(sprache="en"), tmp_path, "--uebersetzung")
    assert "Sprache en" in erg.stdout


def test_bericht_prueft_die_zeilenzahl(tmp_path):
    erg = bericht_py(bericht(), tmp_path, WB_BERICHT_ZEILEN="null")
    assert erg.returncode != 0
    assert "WB_BERICHT_ZEILEN ist 'null'" in erg.stderr

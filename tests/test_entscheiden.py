"""tools/ci/entscheiden.sh mit nachgebauten gh und curl."""
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

WURZEL = Path(__file__).resolve().parent.parent
SKRIPT = WURZEL / "tools" / "ci" / "entscheiden.sh"
BASH = os.environ.get("WB_BASH") or shutil.which("bash")
pytestmark = pytest.mark.skipif(BASH is None, reason="bash fehlt; WB_BASH auf den Pfad von bash setzen")
FASSUNG = (WURZEL / "VERSION").read_text(encoding="utf-8").strip()

GH = """#!/usr/bin/env bash
echo "${FAKE_RELEASE:-v4.4}"
"""
CURL = """#!/usr/bin/env bash
if [ -n "${FAKE_CURL_LOG:-}" ]; then
  echo "ARGS $*" >> "$FAKE_CURL_LOG"
  case " $* " in *" -K - "*) echo "STDIN $(cat)" >> "$FAKE_CURL_LOG" ;; esac
fi
case "$*" in
  *hub.docker.com*) echo "${FAKE_HUB:-200}" ;;
  *ghcr.io/token*) echo '{"token":"abc"}' ;;
  *ghcr.io/v2/*) echo "${FAKE_GHCR:-404}" ;;
  *) echo "unerwarteter Aufruf: $*" >&2; exit 9 ;;
esac
"""


def posix(pfad: Path) -> str:
    text = pfad.as_posix()
    m = re.match(r"^([A-Za-z]):/(.*)$", text)
    return f"/{m.group(1).lower()}/{m.group(2)}" if (m and os.name == "nt") else text


def lauf(tmp_path, **umgebung):
    bin_ = tmp_path / "bin"
    bin_.mkdir(exist_ok=True)
    for name, inhalt in (("gh", GH), ("curl", CURL)):
        datei = bin_ / name
        datei.write_text(inhalt, encoding="utf-8", newline="\n")
        datei.chmod(0o755)
    ausgabe = tmp_path / "ausgabe.txt"
    ausgabe.write_text("", encoding="utf-8")
    summary = tmp_path / "summary.md"
    basis = {k: v for k, v in os.environ.items() if k not in ("GH_TOKEN", "GITHUB_ACTOR")}
    env = dict(basis, PATH=str(bin_) + os.pathsep + os.environ.get("PATH", ""),
               UPSTREAM="healthchecks/healthchecks", BASIS_IMAGE="healthchecks/healthchecks",
               ZIEL_IMAGE="ghcr.io/brightcolor/healthchecks-werkbank",
               GITHUB_OUTPUT=posix(ausgabe), GITHUB_STEP_SUMMARY=posix(summary), **umgebung)
    erg = subprocess.run([BASH, posix(SKRIPT)], cwd=WURZEL, env=env, capture_output=True, text=True, encoding="utf-8")
    werte = dict(z.split("=", 1) for z in ausgabe.read_text(encoding="utf-8").splitlines() if "=" in z)
    return erg, werte, (summary.read_text(encoding="utf-8") if summary.exists() else "")


def test_zeitplan_neue_version_wird_gebaut_und_veroeffentlicht(tmp_path):
    erg, werte, _ = lauf(tmp_path, EREIGNIS="schedule")
    assert erg.returncode == 0, erg.stderr
    assert werte == {"hc_tag": "v4.4", "fassung": f"4.4-wb{FASSUNG}", "bauen": "true", "veroeffentlichen": "true"}


def test_zeitplan_vorhandener_tag_baut_nichts(tmp_path):
    _, werte, _ = lauf(tmp_path, EREIGNIS="schedule", FAKE_GHCR="200")
    assert (werte["bauen"], werte["veroeffentlichen"]) == ("false", "false")


def test_zeitplan_basis_fehlt_noch(tmp_path):
    erg, werte, summary = lauf(tmp_path, EREIGNIS="schedule", FAKE_HUB="404")
    assert erg.returncode == 0
    assert (werte["bauen"], werte["veroeffentlichen"]) == ("false", "false")
    assert "liegt noch nicht auf Docker Hub" in summary


def test_push_main_mit_vorhandenem_tag_prueft_nur(tmp_path):
    _, werte, _ = lauf(tmp_path, EREIGNIS="push", REF="refs/heads/main", FAKE_GHCR="200")
    assert (werte["bauen"], werte["veroeffentlichen"]) == ("true", "false")


def test_push_main_mit_neuer_fassung_veroeffentlicht(tmp_path):
    _, werte, _ = lauf(tmp_path, EREIGNIS="push", REF="refs/heads/main")
    assert (werte["bauen"], werte["veroeffentlichen"]) == ("true", "true")


def test_push_anderer_zweig_veroeffentlicht_nicht(tmp_path):
    _, werte, _ = lauf(tmp_path, EREIGNIS="push", REF="refs/heads/probe")
    assert (werte["bauen"], werte["veroeffentlichen"]) == ("true", "false")


def test_pull_request_prueft_nur(tmp_path):
    _, werte, _ = lauf(tmp_path, EREIGNIS="pull_request")
    assert (werte["bauen"], werte["veroeffentlichen"]) == ("true", "false")


def test_handstart_mit_version_und_erzwingen(tmp_path):
    _, werte, _ = lauf(tmp_path, EREIGNIS="workflow_dispatch", EINGABE="v4.3", ERZWINGEN="true", FAKE_GHCR="200")
    assert werte["hc_tag"] == "v4.3"
    assert werte["fassung"] == f"4.3-wb{FASSUNG}"
    assert (werte["bauen"], werte["veroeffentlichen"]) == ("true", "true")


def test_handstart_ohne_erzwingen_bei_vorhandenem_tag(tmp_path):
    _, werte, _ = lauf(tmp_path, EREIGNIS="workflow_dispatch", ERZWINGEN="false", FAKE_GHCR="200")
    assert (werte["bauen"], werte["veroeffentlichen"]) == ("false", "false")


def test_ungueltige_version(tmp_path):
    erg, _, _ = lauf(tmp_path, EREIGNIS="workflow_dispatch", EINGABE="4.4")
    assert erg.returncode == 1
    assert "hat nicht die Form v4.4" in erg.stdout


def test_unbekanntes_ereignis(tmp_path):
    erg, _, _ = lauf(tmp_path, EREIGNIS="release")
    assert erg.returncode == 1
    assert "Unbekanntes Ereignis" in erg.stdout


def test_ghcr_abfrage_meldet_sich_mit_gh_token_an(tmp_path):
    protokoll = tmp_path / "curl.log"
    lauf(tmp_path, EREIGNIS="schedule", GH_TOKEN="geheim", GITHUB_ACTOR="bot", FAKE_CURL_LOG=posix(protokoll))
    zeilen = protokoll.read_text(encoding="utf-8").splitlines()
    assert 'STDIN user = "bot:geheim"' in zeilen
    assert not any("geheim" in z for z in zeilen if z.startswith("ARGS"))


def test_ghcr_abfrage_ohne_gh_token_bleibt_anonym(tmp_path):
    protokoll = tmp_path / "curl.log"
    lauf(tmp_path, EREIGNIS="schedule", FAKE_CURL_LOG=posix(protokoll))
    assert not any(z.startswith("STDIN") for z in protokoll.read_text(encoding="utf-8").splitlines())

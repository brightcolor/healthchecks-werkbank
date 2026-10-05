#!/usr/bin/env python3
"""Lokaler Aufbau von Healthchecks mit der Werkbank, ohne Docker.

  python tools/dev.py vorbereiten   Quelle holen, venv füllen, Werkbank einsetzen, Datenbank und Musterdaten
  python tools/dev.py einsetzen     Vorlagen und Stil neu einsetzen, Arbeitskopie bleibt (danach Server neu starten)
  python tools/dev.py stil          nur werkbank.css und leiste.js neu bauen; der Server läuft weiter
  python tools/dev.py starten       Server auf WB_DEV_ADRESSE starten (vorher vorbereiten)
  python tools/dev.py pruefen       Browserprüfung gegen den laufenden Server

Einstellungen über Umgebungsvariablen; die Vorgaben stehen in VORGABEN.
Der Zugang der Musterkonten liegt in .upstream/dev-zugang.txt (nicht im Repo).
"""

from __future__ import annotations

import argparse
import json
import os
import secrets
import shutil
import subprocess
import sys
import venv
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WURZEL / "werkbank"))
import einbau  # noqa: E402
import farben  # noqa: E402

VORGABEN = {
    "HC_VERSION": "v4.4",
    "HC_REPO": "https://github.com/healthchecks/healthchecks.git",
    "WB_DEV_ADRESSE": "127.0.0.1:8000",
    "WB_DEV_SITE_ROOT": "http://localhost:8000",
    "WB_BROWSER_KANAL": "msedge",
}

UPSTREAM = WURZEL / ".upstream"
VENV = WURZEL / ".venv"
ZUGANG = UPSTREAM / "dev-zugang.txt"
MUSTERDATEN = WURZEL / "tests" / "e2e" / "ergebnisse" / "musterdaten.json"


def einstellung(name: str) -> str:
    return os.environ.get(name, VORGABEN[name])


class DevFehler(Exception):
    """Ein Problem beim lokalen Aufbau; die Meldung sagt, was zu tun ist."""


def lauf(befehl: list, **kw) -> None:
    print("$", " ".join(str(b) for b in befehl), flush=True)
    if subprocess.run([str(b) for b in befehl], **kw).returncode != 0:
        raise DevFehler(f"{Path(str(befehl[0])).name} ist gescheitert; die Ausgabe darüber nennt den Grund.")


def venv_python() -> Path:
    return VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def quelle(version: str) -> Path:
    ziel = UPSTREAM / version
    if not (ziel / "manage.py").is_file():
        UPSTREAM.mkdir(exist_ok=True)
        lauf(["git", "-c", "core.longpaths=true", "clone", "-q", "--depth", "1", "--branch", version,
              einstellung("HC_REPO"), ziel])
    return ziel


def arbeitskopie(version: str) -> Path:
    ziel = UPSTREAM / f"arbeit-{version}"
    if ziel.exists():
        alt = ziel.with_name(f"{ziel.name}-alt")
        if alt.exists():
            shutil.rmtree(alt)
        try:
            # Unter Windows scheitert das Umbenennen, solange eine Datei darin offen ist.
            # So bleibt die Arbeitskopie ganz, wenn der Server noch läuft.
            ziel.rename(alt)
        except OSError as err:
            raise DevFehler(f"{ziel} ist in Benutzung ({err.strerror}). Den Server beenden "
                            "(Strg+C im Fenster von tools/dev.py starten) und den Befehl wiederholen.") from err
        shutil.rmtree(alt)
    shutil.copytree(quelle(version), ziel, ignore=shutil.ignore_patterns(".git", "static-collected"))
    return ziel


def einsetzen(arbeit: Path) -> dict:
    werkbank = WURZEL / "werkbank"
    hausschrift = WURZEL / "vendor" / "hausschrift"
    shutil.copytree(werkbank / "templates" / "bc", arbeit / "templates" / "bc", dirs_exist_ok=True)
    bc = arbeit / "static" / "bc"
    (bc / "logo").mkdir(parents=True, exist_ok=True)
    shutil.copytree(hausschrift / "assets" / "fonts", bc / "fonts", dirs_exist_ok=True)
    for logo in (hausschrift / "assets" / "logo").glob("*.svg"):
        shutil.copy2(logo, bc / "logo" / logo.name)
    shutil.copy2(werkbank / "static" / "bc" / "leiste.js", bc / "leiste.js")
    einbau.einbauen(arbeit, einbau.lade_plan(einbau.PLAN_VORGABE), "dev")
    css, farben_css, bericht = farben.bauen(arbeit, hausschrift, werkbank, "dev")
    farben.schreibe(arbeit, css, farben_css)
    (UPSTREAM / "dev-bericht.json").write_text(json.dumps(bericht, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Werkbank eingesetzt: {bericht['deklarationen']} Farbangaben, "
          f"{len(bericht['automatisch'])} automatisch zugeordnet (Liste in .upstream/dev-bericht.json).")
    return bericht


def zugang() -> str:
    if not ZUGANG.is_file():
        UPSTREAM.mkdir(exist_ok=True)
        ZUGANG.write_text(secrets.token_hex(12), encoding="utf-8")
    return ZUGANG.read_text(encoding="utf-8").strip()


def umgebung(version: str) -> dict[str, str]:
    return dict(
        os.environ,
        DEBUG="False",
        SECRET_KEY=f"nur-lokal-{version}",
        SITE_ROOT=einstellung("WB_DEV_SITE_ROOT"),
        ALLOWED_HOSTS="localhost,127.0.0.1",
        DB_NAME=str(UPSTREAM / f"dev-{version}.sqlite"),
        REGISTRATION_OPEN="False",
        SITE_NAME="Healthchecks",
        PYTHONUTF8="1",
        PYTHONIOENCODING="utf-8",
        WB_TEST_PASSWORT=zugang(),
    )


def venv_bereit(arbeit: Path) -> Path:
    py = venv_python()
    if not py.is_file():
        venv.create(VENV, with_pip=True)
    anforderungen = [arbeit / "requirements.txt", WURZEL / "tests" / "requirements.txt"]
    stand = "".join(p.read_text(encoding="utf-8") for p in anforderungen)
    marke = VENV / ".werkbank-anforderungen"
    if not marke.is_file() or marke.read_text(encoding="utf-8") != stand:
        argumente = [x for p in anforderungen for x in ("-r", p)]
        lauf([py, "-m", "pip", "install", "-q", *argumente])
        marke.write_text(stand, encoding="utf-8")
    return py


LOKALE_EINSTELLUNGEN = '''"""Nur für den lokalen Aufbau (tools/dev.py).

Die Stylesheets laden einzeln in derselben Reihenfolge wie im Bündel. Die
Bündelung (manage.py compress) scheitert unter Windows an gesperrten Dateien;
das Image in der CI bündelt wie Healthchecks selbst.
"""
COMPRESS_ENABLED = False
COMPRESS_OFFLINE = False
'''


def lokale_einstellungen(arbeit: Path) -> None:
    (arbeit / "hc" / "local_settings.py").write_text(LOKALE_EINSTELLUNGEN, encoding="utf-8")


def musterdaten(py: Path, arbeit: Path, env: dict) -> None:
    skript = (WURZEL / "tests" / "musterdaten.py").read_text(encoding="utf-8")
    # Unter Windows liest "manage.py shell" die Standardeingabe zeilenweise wie eine
    # interaktive Konsole; mit -c führt Django das Skript als Ganzes aus.
    ergebnis = subprocess.run([str(py), "manage.py", "shell", "-c", skript], cwd=arbeit, env=env,
                              capture_output=True, text=True, encoding="utf-8")
    zeilen = [z for z in ergebnis.stdout.splitlines() if z.startswith("MUSTERDATEN: ")]
    if ergebnis.returncode != 0 or not zeilen:
        raise DevFehler("Die Musterdaten wurden nicht angelegt. Ausgabe von manage.py shell:\n"
                        + (ergebnis.stderr or ergebnis.stdout)[-3000:])
    MUSTERDATEN.parent.mkdir(parents=True, exist_ok=True)
    MUSTERDATEN.write_text(zeilen[-1].removeprefix("MUSTERDATEN: "), encoding="utf-8")
    print(f"Musterdaten: {MUSTERDATEN.relative_to(WURZEL)}")


def vorbereiten(version: str) -> None:
    arbeit = arbeitskopie(version)
    einsetzen(arbeit)
    lokale_einstellungen(arbeit)
    py = venv_bereit(arbeit)
    env = umgebung(version)
    lauf([py, "manage.py", "migrate", "-v", "0"], cwd=arbeit, env=env)
    musterdaten(py, arbeit, env)


def nur_stil(version: str) -> None:
    """werkbank.css und leiste.js in der laufenden Arbeitskopie neu bauen; der Server lädt sie beim nächsten Abruf."""
    arbeit = UPSTREAM / f"arbeit-{version}"
    if not (arbeit / "manage.py").is_file():
        raise DevFehler(f"{arbeit} fehlt. Zuerst python tools/dev.py vorbereiten ausführen.")
    werkbank = WURZEL / "werkbank"
    shutil.copy2(werkbank / "static" / "bc" / "leiste.js", arbeit / "static" / "bc" / "leiste.js")
    css, farben_css, bericht = farben.bauen(arbeit, WURZEL / "vendor" / "hausschrift", werkbank, "dev")
    farben.schreibe(arbeit, css, farben_css)
    print(f"werkbank.css neu gebaut: {bericht['deklarationen']} Farbangaben, "
          f"{len(bericht['automatisch'])} automatisch zugeordnet.")


def nur_einsetzen(version: str) -> None:
    """Vorlagen und Stil der Werkbank neu einsetzen; die übrigen Dateien der Arbeitskopie bleiben."""
    arbeit = UPSTREAM / f"arbeit-{version}"
    if not (arbeit / "manage.py").is_file():
        raise DevFehler(f"{arbeit} fehlt. Zuerst python tools/dev.py vorbereiten ausführen.")
    vorlage = einbau.lade_plan(einbau.PLAN_VORGABE).vorlage
    shutil.copy2(quelle(version) / vorlage, arbeit / vorlage)
    einsetzen(arbeit)
    lokale_einstellungen(arbeit)
    print("Den Server neu starten, damit Django die Vorlagen neu lädt: python tools/dev.py starten")


def starten(version: str) -> None:
    arbeit = UPSTREAM / f"arbeit-{version}"
    if not (arbeit / "manage.py").is_file():
        raise DevFehler(f"{arbeit} fehlt. Zuerst python tools/dev.py vorbereiten ausführen.")
    lauf([venv_python(), "manage.py", "runserver", einstellung("WB_DEV_ADRESSE"), "--insecure", "--noreload"],
         cwd=arbeit, env=umgebung(version))


# Healthchecks erlaubt je Konto 20 Anmeldungen mit Passwort am Tag. Vor jeder lokalen
# Prüfung wird diese Sperre in der lokalen Testdatenbank gelöst; in der CI ist die
# Datenbank bei jedem Lauf frisch.
ANMELDESPERRE_LOESEN = (
    "from hc.api.models import TokenBucket; "
    "TokenBucket.objects.filter(value__startswith='pw-').delete()"
)


def pruefen(version: str, argumente: list[str]) -> None:
    npx = shutil.which("npx")
    if not npx:
        raise DevFehler("npx fehlt. Node.js 22 oder neuer installieren.")
    arbeit = UPSTREAM / f"arbeit-{version}"
    if not (arbeit / "manage.py").is_file():
        raise DevFehler(f"{arbeit} fehlt. Zuerst python tools/dev.py vorbereiten ausführen.")
    lauf([venv_python(), "manage.py", "shell", "-c", ANMELDESPERRE_LOESEN], cwd=arbeit, env=umgebung(version))
    env = dict(os.environ, WB_BASIS_URL=einstellung("WB_DEV_SITE_ROOT"), WB_TEST_PASSWORT=zugang(),
               WB_MUSTERDATEN=str(MUSTERDATEN), WB_BROWSER_KANAL=einstellung("WB_BROWSER_KANAL"))
    lauf([npx, "playwright", "test", *argumente], cwd=WURZEL, env=env)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Lokaler Aufbau von Healthchecks mit der Werkbank.")
    p.add_argument("--version", default=einstellung("HC_VERSION"), help="Healthchecks-Version, etwa v4.4")
    p.add_argument("befehl", choices=["vorbereiten", "einsetzen", "stil", "starten", "pruefen"])
    p.add_argument("rest", nargs=argparse.REMAINDER, help="bei pruefen: weitere Argumente für Playwright")
    args = p.parse_args(argv)
    try:
        if args.befehl == "vorbereiten":
            vorbereiten(args.version)
        elif args.befehl == "einsetzen":
            nur_einsetzen(args.version)
        elif args.befehl == "stil":
            nur_stil(args.version)
        elif args.befehl == "starten":
            starten(args.version)
        else:
            pruefen(args.version, args.rest)
    except (DevFehler, einbau.EinbauFehler, farben.FarbFehler) as err:
        print(f"Abbruch: {err}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

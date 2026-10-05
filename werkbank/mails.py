#!/usr/bin/env python3
"""Mail-Layout der Werkbank einsetzen.

  python mails.py einsetzen --wurzel /opt/healthchecks --werkbank /tmp/werkbank --hausschrift /tmp/hausschrift [--bericht bericht.json]

Vergleicht Blöcke und Variablen des Mail-Layouts von Healthchecks mit dem Layout der
Werkbank. Fehlt dem Werkbank-Layout etwas, bricht der Bau ab, weil sonst Inhalt der Mails
verloren ginge. Weicht nur die Prüfsumme des Originals ab, entsteht ein Hinweis. Danach
ersetzt das Werkbank-Layout das Original, und das PNG-Logo kommt nach static/.

Einstellungen über Umgebungsvariablen; die Vorgaben stehen in VORGABEN.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
from pathlib import Path

VORGABEN = {
    # Layout von Healthchecks, relativ zu seiner Wurzel.
    "WB_MAIL_LAYOUT": "templates/emails/base.html",
    # Layout der Werkbank und Prüfsumme des Originals, relativ zu werkbank/.
    "WB_MAIL_VORLAGE": "mails/base.html",
    "WB_MAIL_PRUEFSUMME": "mails/original.sha256",
    # Logo für den Tinte-Balken, relativ zur Hausschrift, und sein Ziel in Healthchecks.
    "WB_MAIL_LOGO": "assets/logo/png/bc-logo-light-noclaim.png",
    "WB_MAIL_LOGO_ZIEL": "static/bc/logo/bc-logo-light-noclaim.png",
}
BLOCK = re.compile(r"\{%\s*block\s+(\w+)\s*%\}")
VARIABLE = re.compile(r"\{\{\s*([A-Za-z_]\w*)|\{%\s*(?:if|elif)\s+(?:not\s+)?([A-Za-z_]\w*)")
# Namen, die Django-Vorlagen selbst bereitstellen.
EINGEBAUT = {"block", "forloop", "True", "False", "None"}


class MailFehler(Exception):
    """Ein Problem mit dem Mail-Layout; die Meldung sagt, was zu tun ist."""


def einstellung(name: str) -> str:
    return os.environ.get(name, VORGABEN[name])


def text(pfad: Path) -> str:
    return pfad.read_bytes().decode("utf-8").replace("\r\n", "\n")


def bloecke(vorlage: str) -> set[str]:
    return set(BLOCK.findall(vorlage))


def variablen(vorlage: str) -> set[str]:
    return {a or b for a, b in VARIABLE.findall(vorlage)} - EINGEBAUT


def pfad_einstellung(name: str, ort: str) -> str:
    wert = einstellung(name)
    if not wert or Path(wert).is_absolute() or ".." in Path(wert).parts:
        raise MailFehler(f"{name} ist {wert!r}. Erwartet ist ein Pfad innerhalb {ort}, etwa {VORGABEN[name]}.")
    return wert


def einsetzen(wurzel: Path, werkbank: Path, hausschrift: Path) -> list[str]:
    layout = wurzel / pfad_einstellung("WB_MAIL_LAYOUT", "von Healthchecks")
    vorlage = werkbank / pfad_einstellung("WB_MAIL_VORLAGE", "von werkbank/")
    pruefsumme = werkbank / pfad_einstellung("WB_MAIL_PRUEFSUMME", "von werkbank/")
    logo = hausschrift / pfad_einstellung("WB_MAIL_LOGO", "der Hausschrift")
    logo_ziel = wurzel / pfad_einstellung("WB_MAIL_LOGO_ZIEL", "von Healthchecks")
    for noetig, was in (
        (layout, "Das Mail-Layout von Healthchecks"),
        (vorlage, "Das Mail-Layout der Werkbank"),
        (pruefsumme, "Die Prüfsumme des Originals"),
        (logo, "Das Logo für Mails"),
    ):
        if not noetig.is_file():
            raise MailFehler(f"{was} fehlt unter {noetig}. Pfad und Einstellung prüfen.")
    original = text(layout)
    eigenes = text(vorlage)
    fehlende_bloecke = sorted(bloecke(original) - bloecke(eigenes))
    fehlende_variablen = sorted(variablen(original) - variablen(eigenes))
    if fehlende_bloecke or fehlende_variablen:
        teile = []
        if fehlende_bloecke:
            teile.append("die Blöcke " + ", ".join(fehlende_bloecke))
        if fehlende_variablen:
            teile.append("die Variablen " + ", ".join(fehlende_variablen))
        raise MailFehler(
            f"Das Mail-Layout von Healthchecks nutzt {' und '.join(teile)}. Das Werkbank-Layout {vorlage.name} "
            "stellt sie nicht bereit, und Inhalt der Mails ginge verloren. Das Werkbank-Layout ergänzen."
        )
    hinweise = []
    summe = hashlib.sha256(original.encode("utf-8")).hexdigest()
    erwartet = (text(pruefsumme).split() or [""])[0]
    if summe != erwartet:
        hinweise.append(
            f"Healthchecks hat sein Mail-Layout geändert (sha256 {summe[:12]}…). Blöcke und Variablen sind vollständig. "
            f"Das Werkbank-Layout mit dem neuen Original vergleichen und die Prüfsumme in {pruefsumme.name} eintragen."
        )
    layout.write_bytes(eigenes.encode("utf-8"))
    logo_ziel.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(logo, logo_ziel)
    return hinweise


def bericht_schreiben(pfad: Path, hinweise: list[str]) -> None:
    daten = json.loads(text(pfad)) if pfad.is_file() else {}
    daten["mails"] = {"hinweise": hinweise}
    pfad.write_bytes((json.dumps(daten, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))


def main(argv: list[str] | None = None) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description="Mail-Layout der Werkbank einsetzen.")
    unter = p.add_subparsers(dest="befehl", required=True)
    e = unter.add_parser("einsetzen", help="Blöcke und Variablen prüfen, Layout und Logo einsetzen")
    e.add_argument("--wurzel", required=True, help="Ordner von Healthchecks, etwa /opt/healthchecks")
    e.add_argument("--werkbank", required=True, help="Ordner werkbank/")
    e.add_argument("--hausschrift", required=True, help="Kopie der Hausschrift (vendor/hausschrift)")
    e.add_argument("--bericht", help="Hinweise als Abschnitt mails in diese JSON-Datei schreiben")
    args = p.parse_args(argv)
    try:
        hinweise = einsetzen(Path(args.wurzel), Path(args.werkbank), Path(args.hausschrift))
    except MailFehler as err:
        print(f"Abbruch: {err}", file=sys.stderr)
        return 1
    if args.bericht:
        bericht_schreiben(Path(args.bericht), hinweise)
    print("Mail-Layout der Werkbank eingesetzt." + "".join(f"\nHinweis: {h}" for h in hinweise))
    return 0


if __name__ == "__main__":
    sys.exit(main())

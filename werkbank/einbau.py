#!/usr/bin/env python3
"""Setzt die Werkbank in die Vorlagen von Healthchecks ein.

Liest den Einbauplan (Vorgabe: einbau.json neben diesem Skript), setzt jede
Zeile direkt vor ihren Anker und ersetzt danach den Platzhalter für die
Fassung. Erst wenn jede Prüfung bestanden ist, schreibt das Skript; bei einem
Fehler bleibt jede Datei, wie sie war.

Nur Standardbibliothek: Das Skript läuft beim Bau im Image von Healthchecks.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

PLAN_VORGABE = Path(__file__).resolve().parent / "einbau.json"
FASSUNG_MUSTER = re.compile(r"[0-9A-Za-z][0-9A-Za-z._-]{0,63}")


class EinbauFehler(Exception):
    """Ein Problem, das der Betreiber beheben kann; die Meldung sagt wie."""


@dataclass(frozen=True)
class Einfuegung:
    anker: str
    zeile: str


@dataclass(frozen=True)
class Plan:
    vorlage: str
    einfuegungen: tuple[Einfuegung, ...]
    platzhalter: str
    fassung_in: tuple[str, ...]


def lade_plan(pfad: Path) -> Plan:
    try:
        daten = json.loads(pfad.read_text(encoding="utf-8"))
    except FileNotFoundError as err:
        raise EinbauFehler(f"Der Einbauplan {pfad} fehlt. Den Pfad mit --plan prüfen.") from err
    except json.JSONDecodeError as err:
        raise EinbauFehler(
            f"{pfad} ist kein gültiges JSON (Zeile {err.lineno}, Spalte {err.colno}: {err.msg})."
        ) from err
    try:
        einfuegungen = tuple(Einfuegung(e["anker"], e["zeile"]) for e in daten["einfuegungen"])
        plan = Plan(daten["vorlage"], einfuegungen, daten["platzhalter"], tuple(daten["fassung_in"]))
    except (KeyError, TypeError) as err:
        raise EinbauFehler(
            f"{pfad} braucht die Felder vorlage, einfuegungen (je anker und zeile), platzhalter "
            f"und fassung_in. Es fehlt: {err}."
        ) from err
    if not plan.einfuegungen:
        raise EinbauFehler(f"{pfad} nennt keine Einfügung. Mindestens eine Zeile mit Anker eintragen.")
    if not plan.platzhalter.strip():
        raise EinbauFehler(
            f"Der Platzhalter in {pfad} ist leer. Einen eindeutigen Text wie @@WERKBANK_FASSUNG@@ eintragen."
        )
    return plan


def pruefe_fassung(fassung: str) -> None:
    if not FASSUNG_MUSTER.fullmatch(fassung):
        raise EinbauFehler(
            f"Die Fassung {fassung!r} taugt nicht als Image-Tag. Erlaubt sind 1 bis 64 Zeichen aus "
            "Buchstaben, Ziffern, Punkt, Minus und Unterstrich, am Anfang ein Buchstabe oder eine "
            "Ziffer, etwa 4.4-wb1.0.0."
        )


def einfuegen(text: str, einfuegungen: tuple[Einfuegung, ...], platzhalter: str, datei: str) -> str:
    for e in einfuegungen:
        anzahl = text.count(e.anker)
        if anzahl != 1:
            raise EinbauFehler(
                f"Der Anker {e.anker!r} steht {anzahl}-mal in {datei}, erwartet ist genau einmal. "
                "Healthchecks hat die Vorlage geändert: werkbank/einbau.json an die neue Fassung anpassen."
            )
        kern = e.zeile.split(platzhalter)[0]
        if kern and kern in text:
            raise EinbauFehler(
                f"{datei} enthält die Zeile {e.zeile!r} bereits. Der Einbau läuft nur auf der "
                "unveränderten Vorlage aus dem Basis-Image."
            )
    for e in einfuegungen:
        text = text.replace(e.anker, f"{e.zeile}\n{e.anker}", 1)
    return text


def setze_fassung(text: str, platzhalter: str, fassung: str, datei: str) -> str:
    if platzhalter not in text:
        raise EinbauFehler(
            f"In {datei} fehlt der Platzhalter {platzhalter}. Die Datei gehört zur Werkbank und muss ihn enthalten."
        )
    return text.replace(platzhalter, fassung)


def einbauen(wurzel: Path, plan: Plan, fassung: str) -> list[str]:
    """Baut ein und gibt die geänderten Dateien relativ zur Wurzel zurück."""
    pruefe_fassung(fassung)
    neu: dict[str, str] = {}

    def lies(rel: str) -> str:
        if rel in neu:
            return neu[rel]
        pfad = wurzel / rel
        try:
            return pfad.read_text(encoding="utf-8")
        except FileNotFoundError as err:
            raise EinbauFehler(f"{pfad} fehlt. Ist --wurzel der Ordner von Healthchecks?") from err

    neu[plan.vorlage] = einfuegen(lies(plan.vorlage), plan.einfuegungen, plan.platzhalter, plan.vorlage)
    for rel in plan.fassung_in:
        neu[rel] = setze_fassung(lies(rel), plan.platzhalter, fassung, rel)
    for rel, text in neu.items():
        (wurzel / rel).write_text(text, encoding="utf-8")
    return sorted(neu)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Setzt die Werkbank in die Vorlagen von Healthchecks ein.")
    p.add_argument("--wurzel", required=True, help="Ordner von Healthchecks, etwa /opt/healthchecks")
    p.add_argument("--fassung", required=True, help="Fassung des Images, etwa 4.4-wb1.0.0")
    p.add_argument("--plan", default=str(PLAN_VORGABE), help="Einbauplan (Vorgabe %(default)s)")
    args = p.parse_args(argv)
    try:
        geaendert = einbauen(Path(args.wurzel), lade_plan(Path(args.plan)), args.fassung)
    except EinbauFehler as err:
        print(f"Abbruch: {err}", file=sys.stderr)
        return 1
    print(f"Werkbank eingesetzt (Fassung {args.fassung}): {', '.join(geaendert)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

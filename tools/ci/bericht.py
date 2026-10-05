#!/usr/bin/env python3
"""Schreibt den Bericht des Baus als Markdown für die Zusammenfassung des CI-Laufs.

  python tools/ci/bericht.py <werkbank-bericht.json>                  Farbableitung und Übersetzung
  python tools/ci/bericht.py <werkbank-bericht.json> --uebersetzung   nur die Übersetzung (Hinweis-Issue)

WB_BERICHT_ZEILEN begrenzt jede Tabelle (Vorgabe 50); WB_HC_VERSION nennt die gebaute Version.
"""
import json
import os
import sys

VORGABE_ZEILEN = 50


def zelle(text: str) -> str:
    return str(text).replace("|", r"\|").replace("\n", " ")


def grenze() -> int:
    wert = os.environ.get("WB_BERICHT_ZEILEN", str(VORGABE_ZEILEN))
    if not wert.isdigit() or int(wert) < 1:
        raise SystemExit(f"WB_BERICHT_ZEILEN ist {wert!r}. Erwartet ist eine ganze Zahl ab 1, Vorgabe {VORGABE_ZEILEN}.")
    return int(wert)


def farben(bericht: dict, zeilen: int) -> list[str]:
    aus = [f"### Farbableitung {bericht['fassung']}", "",
           f"{bericht['deklarationen']} Farbangaben aus {bericht['stylesheets']} Stylesheets abgeleitet."]
    auto = bericht.get("automatisch", [])
    if auto:
        einzeln = len(auto) == 1
        aus += ["", f"**Hinweis:** {len(auto)} {'Farbangabe' if einzeln else 'Farbangaben'} ohne Eintrag in "
                f"`werkbank/farben.json` {'bekam' if einzeln else 'bekamen'} ihre Rolle nach Farbton und "
                "Helligkeit. Passt eine Rolle nicht, den Eintrag in farben.json ergänzen.", "",
                "| Farbe | Art | Rolle | Datei | Selektor |", "|---|---|---|---|---|"]
        for f in auto[:zeilen]:
            aus.append(f"| `{f['farbe']}` | {f['art']} | `{f['rolle']}` | {f['datei']} | `{zelle(f['selektor'])[:90]}` |")
        if len(auto) > zeilen:
            aus += ["", f"Dazu {len(auto) - zeilen} weitere; die volle Liste steht in artefakte/werkbank-bericht.json."]
    entfallen = bericht.get("variablen_entfallen", [])
    if entfallen:
        aus += ["", "**Hinweis:** Diese Variablen gibt es in Healthchecks nicht mehr; ihre Zeilen in "
                "`werkbank/variablen.css` können entfallen: " + ", ".join(f"`{n}`" for n in entfallen)]
    return aus


def uebersetzung(bericht: dict, zeilen: int) -> list[str]:
    u = bericht.get("uebersetzung")
    mails = bericht.get("mails", {}).get("hinweise", [])
    version = os.environ.get("WB_HC_VERSION", "")
    if not u:
        return ["### Übersetzung", "", "Der Bericht enthält keinen Abschnitt zur Übersetzung."]
    if u.get("sprache") != "de":
        return ["### Übersetzung", "", f"Sprache {u.get('sprache')}: Der Katalog blieb aus, die Texte von Healthchecks stehen."]
    englisch, ohne = u.get("englisch", []), u.get("ohne_fundstelle", [])
    kopf = f"### Übersetzung (Katalog für Healthchecks {u.get('stand', '?')}"
    kopf += f", gebaut mit {version})" if version else ")"
    aus = [kopf, "", f"{u.get('ersetzt', 0)} Ersetzungen, {len(englisch)} Textstücke noch englisch, "
           f"{len(ohne)} Einträge ohne Fundstelle, {len(mails)} Hinweise zu den Mails."]
    if englisch:
        aus += ["", "**Noch englisch:**", "", "| Datei | Text |", "|---|---|"]
        aus += [f"| {zelle(r['datei'])} | {zelle(r['text'])[:120]} |" for r in englisch[:zeilen]]
        if len(englisch) > zeilen:
            aus += ["", f"Dazu {len(englisch) - zeilen} weitere; die volle Liste steht in artefakte/werkbank-bericht.json."]
    if ohne:
        aus += ["", "**Einträge ohne Fundstelle:**", "", "| Datei | Art | Eintrag | Grund |", "|---|---|---|---|"]
        aus += [f"| {zelle(r['datei'])} | {r['art']} | {zelle(r['en'])[:90]} | {zelle(r['grund'])} |" for r in ohne[:zeilen]]
        if len(ohne) > zeilen:
            aus += ["", f"Dazu {len(ohne) - zeilen} weitere; die volle Liste steht in artefakte/werkbank-bericht.json."]
    if mails:
        aus += ["", "**Hinweise zu den Mails:**", ""] + [f"- {zelle(h)}" for h in mails[:zeilen]]
    return aus


def main(argv: list[str]) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    if not argv or argv[0].startswith("-"):
        print("Aufruf: tools/ci/bericht.py <werkbank-bericht.json> [--uebersetzung]", file=sys.stderr)
        return 2
    with open(argv[0], encoding="utf-8") as datei:
        bericht = json.load(datei)
    zeilen = grenze()
    if "--uebersetzung" in argv[1:]:
        aus = uebersetzung(bericht, zeilen)
    else:
        aus = farben(bericht, zeilen) + [""] + uebersetzung(bericht, zeilen)
    print("\n".join(aus))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

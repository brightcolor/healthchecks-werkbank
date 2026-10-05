#!/usr/bin/env python3
"""Schreibt den Bericht der Farbableitung als Markdown für die Zusammenfassung des CI-Laufs."""
import json
import os
import sys


def zelle(text: str) -> str:
    return text.replace("|", r"\|").replace("\n", " ")


def main(pfad: str) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    with open(pfad, encoding="utf-8") as datei:
        bericht = json.load(datei)
    grenze = int(os.environ.get("WB_BERICHT_ZEILEN", "50"))
    print(f"### Farbableitung {bericht['fassung']}")
    print()
    print(f"{bericht['deklarationen']} Farbangaben aus {bericht['stylesheets']} Stylesheets abgeleitet.")
    auto = bericht.get("automatisch", [])
    if auto:
        print()
        einzeln = len(auto) == 1
        print(f"**Hinweis:** {len(auto)} {'Farbangabe' if einzeln else 'Farbangaben'} ohne Eintrag in "
              f"`werkbank/farben.json` {'bekam' if einzeln else 'bekamen'} ihre Rolle nach Farbton und "
              "Helligkeit. Passt eine Rolle nicht, den Eintrag in farben.json ergänzen.")
        print()
        print("| Farbe | Art | Rolle | Datei | Selektor |")
        print("|---|---|---|---|---|")
        for f in auto[:grenze]:
            print(f"| `{f['farbe']}` | {f['art']} | `{f['rolle']}` | {f['datei']} | `{zelle(f['selektor'])[:90]}` |")
        if len(auto) > grenze:
            print(f"\nDazu {len(auto) - grenze} weitere; die volle Liste steht in artefakte/werkbank-bericht.json.")
    entfallen = bericht.get("variablen_entfallen", [])
    if entfallen:
        print()
        print("**Hinweis:** Diese Variablen gibt es in Healthchecks nicht mehr; ihre Zeilen in "
              "`werkbank/variablen.css` können entfallen: " + ", ".join(f"`{n}`" for n in entfallen))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))

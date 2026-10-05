"""Kompiliert jede Vorlage von Healthchecks, wie Django sie lädt.

Läuft über `manage.py shell -c` in der Wurzel von Healthchecks (Testinstanz, Arbeitskopie).
Ein Katalog-Eintrag, der die Template-Syntax bricht, fällt hier auf: Der Lauf endet mit
Code 1 und nennt Vorlage und Fehler. Am Ende steht eine Zeile "VORLAGEN: …".
"""

from pathlib import Path

from django.template import TemplateSyntaxError
from django.template.loader import get_template

namen = {str(p.relative_to("templates")).replace("\\", "/") for p in Path("templates").glob("**/*.html")}
for ordner in Path("hc").glob("**/templates"):
    namen |= {str(p.relative_to(ordner)).replace("\\", "/") for p in ordner.glob("**/*.html")}
fehler = []
for name in sorted(namen):
    try:
        get_template(name)
    except TemplateSyntaxError as err:
        fehler.append(f"{name}: {err}")
for zeile in fehler:
    print(f"FEHLER {zeile}")
print(f"VORLAGEN: {len(namen)} geprüft, {len(fehler)} mit Fehler")
if fehler:
    raise SystemExit(1)

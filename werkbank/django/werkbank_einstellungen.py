"""Einstellungen der Werkbank für Healthchecks.

Der Bau legt diese Datei als hc/werkbank_einstellungen.py ab, und hc/local_settings.py
lädt sie mit `from hc.werkbank_einstellungen import *`. Wer eine eigene local_settings.py
einhängt, übernimmt diese Zeile.
"""

import os
import re

from django.core.exceptions import ImproperlyConfigured

__all__ = [
    "WERKBANK_SPRACHE",
    "WERKBANK_ZUSTAENDE",
    "WERKBANK_ARTEN",
    "WERKBANK_ROLLEN",
    "WB_MAIL_ANSCHRIFT",
    "WB_MAIL_IMPRESSUM_URL",
    "WB_MAIL_DATENSCHUTZ_URL",
]

# Vom Bau gesetzt: WB_SPRACHE und die Wörtertabellen [zustaende], [arten] und [rollen] des Katalogs.
WERKBANK_SPRACHE = "@@WB_SPRACHE@@"
WERKBANK_ZUSTAENDE = @@WB_ZUSTAENDE@@
WERKBANK_ARTEN = @@WB_ARTEN@@
WERKBANK_ROLLEN = @@WB_ROLLEN@@

if WERKBANK_SPRACHE == "de":
    USE_I18N = True
    LANGUAGE_CODE = "de"
    # Skripte von Healthchecks lesen Zahlen aus den Seiten, etwa den Zeitstempel im Log
    # für Live-Updates. Das Formatmodul hält deshalb den Dezimalpunkt.
    FORMAT_MODULE_PATH = ["@@WB_FORMATMODUL@@"]
    # Korrekturen an Djangos eigenen Übersetzungen, etwa „vor 1 Tag“ ([[django]] im Katalog).
    LOCALE_PATHS = [os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "@@WB_LOCALE@@"))]
    __all__ += ["USE_I18N", "LANGUAGE_CODE", "FORMAT_MODULE_PATH", "LOCALE_PATHS"]

# Mail-Fuß: Anschrift, Impressum und Datenschutz erscheinen, sobald sie gesetzt sind.
MAIL_VORGABEN = {
    "WB_MAIL_ANSCHRIFT": "",
    "WB_MAIL_IMPRESSUM_URL": "",
    "WB_MAIL_DATENSCHUTZ_URL": "",
}
ANSCHRIFT_HOECHSTENS = 200
ADRESSE = re.compile(r"https://[^\s\"'<>]+")


def _mail_einstellung(name: str) -> str:
    wert = os.environ.get(name, MAIL_VORGABEN[name]).strip()
    if not wert:
        return ""
    if name.endswith("_URL"):
        if not ADRESSE.fullmatch(wert):
            raise ImproperlyConfigured(
                f"{name} ist {wert!r}. Erwartet ist eine Adresse mit https://, etwa "
                "https://example.org/impressum. Den Wert korrigieren oder die Einstellung leer lassen."
            )
    elif "\n" in wert:
        raise ImproperlyConfigured(
            f"{name} steht auf mehreren Zeilen. Erlaubt ist eine Zeile, etwa „Firma · Straße 1 · 12345 Ort“."
        )
    elif len(wert) > ANSCHRIFT_HOECHSTENS:
        raise ImproperlyConfigured(
            f"{name} hat {len(wert)} Zeichen. Erlaubt sind höchstens {ANSCHRIFT_HOECHSTENS}; "
            "die Anschrift kürzen, etwa auf „Firma · Straße 1 · 12345 Ort“."
        )
    return wert


WB_MAIL_ANSCHRIFT = _mail_einstellung("WB_MAIL_ANSCHRIFT")
WB_MAIL_IMPRESSUM_URL = _mail_einstellung("WB_MAIL_IMPRESSUM_URL")
WB_MAIL_DATENSCHUTZ_URL = _mail_einstellung("WB_MAIL_DATENSCHUTZ_URL")

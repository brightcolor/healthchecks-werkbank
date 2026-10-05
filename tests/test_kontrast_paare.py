"""Kontrast der wichtigsten Paare aus den Tokens, hell und dunkel.

Schrift ab 4,8:1 (Ziel der Hausschrift), Symbole und Fokusringe ab 3:1.
Zustände, die der Browserlauf nicht sieht (Hover, gedrückte Knöpfe, Leiste),
stehen hier.
"""
import sys
from pathlib import Path

import pytest

WURZEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WURZEL / "werkbank"))
import farben  # noqa: E402

BLOECKE = farben.token_bloecke((WURZEL / "vendor/hausschrift/assets/css/bc-tokens.css").read_text(encoding="utf-8"))
HELL = farben.token_werte(BLOECKE["grund"], BLOECKE["werkbank"])
DUNKEL = {**HELL, **farben.token_werte(BLOECKE["dunkel"])}

FLAECHEN_HELL = ["--bc-surface", "--bc-ground", "--bc-head", "--bc-hover"]
FLAECHEN_DUNKEL = ["--bc-ground", "--bc-surface", "--bc-head", "--bc-hover", "--bc-overlay", "--bc-raised"]

PAARE = [
    ("hell", "--bc-text", FLAECHEN_HELL, 4.8),
    ("hell", "--bc-text-quiet", FLAECHEN_HELL, 4.8),
    ("hell", "--bc-link", FLAECHEN_HELL, 4.8),
    ("hell", "--bc-ok-text", ["--bc-surface", "--bc-head"], 4.8),
    ("hell", "--bc-warn-text", ["--bc-surface", "--bc-head"], 4.8),
    ("hell", "--bc-bad-text", ["--bc-surface", "--bc-head", "--bc-bad-tint"], 4.8),
    ("hell", "--bc-on-primary", ["--bc-primary", "--bc-primary-deep", "--bc-lime"], 4.8),
    ("hell", "--bc-white", ["--bc-pink", "--bc-bad-deep"], 4.8),
    ("hell", "--bc-deep", ["--bc-cyan"], 4.8),
    ("hell", "--bc-rail-text", ["--bc-rail", "--bc-rail-2"], 4.8),
    ("hell", "--bc-rail-muted", ["--bc-rail", "--bc-rail-2"], 4.8),
    ("hell", "--bc-pink", ["--bc-surface"], 3.0),
    ("hell", "--bc-focus", ["--bc-surface", "--bc-ground"], 3.0),
    ("dunkel", "--bc-text", FLAECHEN_DUNKEL, 4.8),
    ("dunkel", "--bc-text-quiet", FLAECHEN_DUNKEL, 4.8),
    ("dunkel", "--bc-link", FLAECHEN_DUNKEL, 4.8),
    ("dunkel", "--bc-ok-text", ["--bc-surface", "--bc-head"], 4.8),
    ("dunkel", "--bc-warn-text", ["--bc-surface", "--bc-head"], 4.8),
    ("dunkel", "--bc-bad-text", ["--bc-surface", "--bc-head", "--bc-bad-tint"], 4.8),
    ("dunkel", "--bc-rail-text", ["--bc-rail", "--bc-rail-2"], 4.8),
    ("dunkel", "--bc-rail-muted", ["--bc-rail", "--bc-rail-2"], 4.8),
    ("dunkel", "--bc-pink", ["--bc-surface", "--bc-head"], 3.0),
    ("dunkel", "--bc-focus", ["--bc-surface", "--bc-ground"], 3.0),
]


def leuchtdichte(hexwert: str) -> float:
    h = hexwert.lstrip("#")
    kanaele = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    linear = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in kanaele]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def kontrast(a: str, b: str) -> float:
    hell_, dunkel_ = sorted((leuchtdichte(a), leuchtdichte(b)), reverse=True)
    return (hell_ + 0.05) / (dunkel_ + 0.05)


@pytest.mark.parametrize("modus, schrift, flaechen, mindest", PAARE, ids=[f"{m}{s}" for m, s, _, _ in PAARE])
def test_paar(modus, schrift, flaechen, mindest):
    werte = HELL if modus == "hell" else DUNKEL
    vorne = farben.normalise(farben.aufloesen(schrift, werte))
    for flaeche in flaechen:
        hinten = farben.normalise(farben.aufloesen(flaeche, werte))
        wert = kontrast(vorne, hinten)
        assert wert >= mindest, f"{schrift} ({vorne}) auf {flaeche} ({hinten}), {modus}: {wert:.2f}:1, gebraucht {mindest}:1"

#!/usr/bin/env python3
"""Baut werkbank.css: die Werkbank von bright color für Healthchecks.

Die festen Farben aus den Stylesheets von Healthchecks werden auf
Werkbank-Rollen umgeleitet. Jede Deklaration einer Farbeigenschaft kommt mit
demselben Selektor wieder; feste Farben werden zu Rollen wie var(--bc-text),
Werte mit var() und Schlüsselwörter kommen unverändert mit. So bleibt die
Reihenfolge der Kaskade von Healthchecks erhalten.

Zuordnung (werkbank/farben.json), in dieser Reihenfolge:
  1. selektoren: Ausnahmen je Selektor und Art
  2. Fläche derselben Regel: neutrale Schrift auf kräftiger Fläche
  3. farben (helle Regeln) und farben_dunkel (Regeln unter body.dark)
  4. automatisch nach Farbton und Helligkeit; landet im Bericht

Befehle:
  farben.py bauen --wurzel DIR --hausschrift DIR --werkbank DIR --fassung TAG [--bericht DATEI]
  farben.py inventur --wurzel DIR
  farben.py vorschlag --wurzel DIR [--behalte farben.json]

Grundlage: tools/derive.py aus postal-brightcolor. Nur Standardbibliothek.
"""

from __future__ import annotations

import argparse
import colorsys
import json
import os
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

# Jede Einstellung mit ihrer Vorgabe an einer Stelle; Umgebungsvariablen
# gleichen Namens gehen vor.
VORGABEN = {
    "WB_BASIS_VORLAGE": "templates/base.html",
    "WB_STATIC": "static",
    "WB_VARIABLEN_CSS": "css/variables.css",
    "WB_ZIEL": "bc/werkbank.css",
    "WB_ZIEL_FARBEN": "bc/farben.css",
    "WB_DUNKEL_SELEKTOR": "body.dark",
}


def einstellung(name: str) -> str:
    return os.environ.get(name, VORGABEN[name])


class FarbFehler(Exception):
    """Ein Problem, das der Betreiber beheben kann; die Meldung sagt wie."""


# --- CSS zerlegen (aus tools/derive.py von postal-brightcolor) -----------------


@dataclass
class Decl:
    prop: str
    value: str
    important: bool = False


@dataclass
class Rule:
    selector: str
    decls: list[Decl]


@dataclass
class Block:
    """Eine At-Regel mit verschachtelten Regeln, etwa @media."""

    prelude: str
    children: list = field(default_factory=list)


@dataclass
class AtDecls:
    """Eine At-Regel mit Deklarationen, etwa @font-face; bleibt außen vor."""

    prelude: str


def strip_comments(css: str) -> str:
    out = []
    i = 0
    quote = ""
    while i < len(css):
        c = css[i]
        if quote:
            out.append(c)
            if c == "\\" and i + 1 < len(css):
                out.append(css[i + 1])
                i += 2
                continue
            if c == quote:
                quote = ""
        elif c in "\"'":
            quote = c
            out.append(c)
        elif css.startswith("/*", i):
            end = css.find("*/", i + 2)
            i = len(css) if end < 0 else end + 2
            continue
        else:
            out.append(c)
        i += 1
    return "".join(out)


def split_top(text: str, sep: str) -> list[str]:
    """Teilt an sep außerhalb von Anführungszeichen und Klammern."""
    parts, depth, quote, start = [], 0, "", 0
    i = 0
    while i < len(text):
        c = text[i]
        if quote:
            if c == "\\":
                i += 2
                continue
            if c == quote:
                quote = ""
        elif c in "\"'":
            quote = c
        elif c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
        elif c == sep and depth == 0:
            parts.append(text[start:i])
            start = i + 1
        i += 1
    parts.append(text[start:])
    return parts


def find_block_end(css: str, open_at: int) -> int:
    depth, quote, i = 0, "", open_at
    while i < len(css):
        c = css[i]
        if quote:
            if c == "\\":
                i += 2
                continue
            if c == quote:
                quote = ""
        elif c in "\"'":
            quote = c
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    raise FarbFehler(
        "Ein Stylesheet endet mitten in einer Regel. Die Datei im Basis-Image ist wohl unvollständig; "
        "den Bau neu starten."
    )


def parse_decls(body: str) -> list[Decl]:
    decls = []
    for chunk in split_top(body, ";"):
        if ":" not in chunk:
            continue
        prop, value = chunk.split(":", 1)
        prop, value = prop.strip().lower(), value.strip()
        if not prop or not value:
            continue
        important = False
        m = re.search(r"\s*!\s*important\s*$", value, re.I)
        if m:
            important = True
            value = value[: m.start()].strip()
        decls.append(Decl(prop, value, important))
    return decls


NESTING_AT_RULES = ("@media", "@supports", "@document", "@layer", "@container")


def parse_css(css: str) -> list:
    css = strip_comments(css)
    nodes: list = []
    i = 0
    while i < len(css):
        while i < len(css) and css[i] in " \t\r\n;":
            i += 1
        if i >= len(css):
            break
        brace = css.find("{", i)
        if brace < 0:
            break
        prelude = css[i:brace]
        semikolon = prelude.rfind(";")
        if semikolon >= 0 and prelude.lstrip().startswith("@"):
            # Anweisungen ohne Block wie @charset oder @import überspringen.
            i += semikolon + 1
            continue
        prelude = prelude.strip()
        end = find_block_end(css, brace)
        body = css[brace + 1 : end]
        lower = prelude.lower()
        if lower.startswith(NESTING_AT_RULES):
            nodes.append(Block(prelude, parse_css(body)))
        elif lower.startswith("@"):
            nodes.append(AtDecls(prelude))
        else:
            nodes.append(Rule(prelude, parse_decls(body)))
        i = end + 1
    return nodes


def walk_rules(nodes: list):
    for node in nodes:
        if isinstance(node, Rule):
            yield node
        elif isinstance(node, Block):
            yield from walk_rules(node.children)


# --- Farben ---------------------------------------------------------------------

NAMED = {"white": "#ffffff", "black": "#000000", "green": "#008000", "red": "#ff0000", "blue": "#0000ff",
         "grey": "#808080", "gray": "#808080", "orange": "#ffa500", "yellow": "#ffff00", "silver": "#c0c0c0"}
KEEP = {"transparent", "inherit", "initial", "unset", "revert", "currentcolor", "none"}
COLOUR_RE = re.compile(
    r"#[0-9a-fA-F]{3,8}\b|rgba?\([^)]*\)|hsla?\([^)]*\)|\b(?:" + "|".join(NAMED) + r")\b", re.I
)
# url(...) und var(...) gehören nicht zur Farbe einer Deklaration.
SCHUTZ_RE = re.compile(r"url\([^)]*\)|var\((?:[^()]|\([^()]*\))*\)", re.I)

COLOUR_PROPS = {
    "color": "text", "-webkit-text-fill-color": "text", "caret-color": "text",
    "background": "background", "background-color": "background", "background-image": "background",
    "border": "border", "border-color": "border", "border-top": "border", "border-right": "border",
    "border-bottom": "border", "border-left": "border", "border-top-color": "border",
    "border-right-color": "border", "border-bottom-color": "border", "border-left-color": "border",
    "outline": "border", "outline-color": "border", "column-rule": "border",
    "box-shadow": "shadow", "text-shadow": "shadow",
    "fill": "graphic", "stroke": "graphic",
}


def colours_in(value: str) -> list[str]:
    return [c for c in COLOUR_RE.findall(SCHUTZ_RE.sub(" ", value)) if c.lower() not in KEEP]


def normalise(colour: str) -> str:
    c = colour.strip().lower()
    if c in NAMED:
        return NAMED[c]
    if c.startswith("#"):
        h = c[1:]
        if len(h) in (3, 4):
            h = "".join(ch * 2 for ch in h)
        if len(h) == 8 and h.endswith("ff"):
            h = h[:6]
        return "#" + h
    m = re.match(r"(rgba?|hsla?)\(([^)]*)\)", c)
    if not m:
        return c
    teile = [p for p in re.split(r"[,\s/]+", m.group(2).strip()) if p]
    if m.group(1).startswith("hsl"):
        h = float(teile[0].removesuffix("deg")) / 360
        s = float(teile[1].rstrip("%")) / 100
        l = float(teile[2].rstrip("%")) / 100
        r, g, b = (round(x * 255) for x in colorsys.hls_to_rgb(h, l, s))
    else:
        r, g, b = (round(float(p.rstrip("%")) * (2.55 if p.endswith("%") else 1)) for p in teile[:3])
    a = teile[3] if len(teile) > 3 else "1"
    alpha = float(a.rstrip("%")) / (100 if a.endswith("%") else 1)
    if alpha >= 1:
        return "#%02x%02x%02x" % (r, g, b)
    return "rgba(%d,%d,%d,%s)" % (r, g, b, "%g" % alpha)


def rgba(farbe: str) -> tuple[int, int, int, float]:
    c = normalise(farbe)
    if c.startswith("#") and len(c) in (7, 9):
        alpha = int(c[7:9], 16) / 255 if len(c) == 9 else 1.0
        return int(c[1:3], 16), int(c[3:5], 16), int(c[5:7], 16), alpha
    m = re.fullmatch(r"rgba\((\d+),(\d+),(\d+),([\d.]+)\)", c)
    if m:
        return int(m.group(1)), int(m.group(2)), int(m.group(3)), float(m.group(4))
    raise FarbFehler(
        f"Die Farbe {farbe!r} kann farben.py nicht lesen. Als Hex-, rgb()- oder hsl()-Wert schreiben "
        "oder die Stelle in farben.json unter selektoren eintragen."
    )


# --- Rollen ---------------------------------------------------------------------

# Je Farbfamilie: Schrift, Fläche (blass, kräftig), Rand (blass, kräftig).
FAMILIEN = {
    "bad": {"text": "var(--bc-bad-text)",
            "background": ("var(--bc-bad-tint)", "var(--bc-pink)"),
            "border": ("var(--wb-bad-rand)", "var(--bc-bad-deep)")},
    "warn": {"text": "var(--bc-warn-text)",
             "background": ("var(--wb-warn-tint)", "var(--bc-yellow)"),
             "border": ("var(--wb-warn-rand)", "var(--bc-primary-deep)")},
    "ok": {"text": "var(--bc-ok-text)",
           "background": ("var(--wb-ok-tint)", "var(--bc-lime)"),
           "border": ("var(--wb-ok-rand)", "var(--bc-ok-deep)")},
    "info": {"text": "var(--bc-link)",
             "background": ("var(--wb-info-tint)", "var(--bc-cyan)"),
             "border": ("var(--wb-info-rand)", "var(--bc-focus)")},
    "signal": {"text": "var(--bc-link)",
               "background": ("var(--wb-signal-tint)", "var(--bc-violet)"),
               "border": ("var(--bc-rule-loud)", "var(--bc-violet)")},
}

# Flächen, auf denen neutrale Schrift zur Tinte oder zu Weiß wird.
STARK_HELL = frozenset({"var(--bc-lime)", "var(--bc-ok)", "var(--bc-yellow)", "var(--bc-warn)",
                        "var(--bc-cyan)", "var(--bc-info)", "var(--bc-primary)", "var(--bc-primary-deep)",
                        "var(--bc-ok-deep)", "var(--bc-ok-mid)"})
STARK_DUNKEL = frozenset({"var(--bc-pink)", "var(--bc-bad)", "var(--bc-bad-deep)", "var(--bc-ink)",
                          "var(--bc-violet)", "var(--bc-violet-deep)"})


def _familie(grad: float) -> str:
    if grad < 15 or grad >= 330:
        return "bad"
    if grad < 70:
        return "warn"
    if grad < 170:
        return "ok"
    if grad < 260:
        return "info"
    return "signal"


def _neutral(hell: float, art: str) -> str:
    if art in ("text", "graphic"):
        if hell >= 0.9:
            return "var(--bc-white)"
        if hell >= 0.45:
            return "var(--bc-text-quiet)"
        if hell >= 0.15:
            return "var(--bc-text)"
        return "var(--bc-text-loud)"
    if art == "background":
        if hell >= 0.97:
            return "var(--bc-surface)"
        if hell >= 0.92:
            return "var(--bc-head)"
        if hell >= 0.8:
            return "var(--bc-hover)"
        if hell >= 0.45:
            return "var(--bc-rule-loud)"
        return "var(--bc-ink)"
    if hell >= 0.82:
        return "var(--bc-rule)"
    if hell >= 0.6:
        return "var(--bc-rule-loud)"
    if hell >= 0.35:
        return "var(--bc-field-edge)"
    return "var(--bc-text-loud)"


def _ist_neutral(s: float, l: float) -> bool:
    return s < 0.2 or l >= 0.95 or l <= 0.1


def auto_rolle(farbe: str, art: str, dunkel: bool = False) -> str:
    """Rolle nach Farbton und Helligkeit; in dunklen Regeln gespiegelt."""
    r, g, b, a = rgba(farbe)
    if a == 0:
        return "transparent"
    h, l, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
    neutral = _ist_neutral(s, l)
    if neutral and a < 1:
        l = 1 - a * (1 - l)  # über Weiß gemischt
    grad = h * 360
    if art == "shadow":
        return "var(--wb-fokus-hof)" if (not neutral and 170 <= grad < 260) else "var(--wb-schatten)"
    hell = 1 - l if dunkel else l
    if neutral:
        return _neutral(hell, art)
    familie = FAMILIEN[_familie(grad)]
    rolle = familie.get(art, familie["text"])
    if isinstance(rolle, tuple):
        return rolle[0] if (hell >= 0.8 or a < 1) else rolle[1]
    return rolle


def kontext_rolle(farbe: str, flaeche: str | None) -> str | None:
    """Neutrale Schrift auf kräftiger Fläche derselben Regel: Tinte oder Weiß."""
    if not flaeche:
        return None
    r, g, b, _ = rgba(farbe)
    _, l, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
    if not _ist_neutral(s, l):
        return None
    if flaeche in STARK_HELL:
        return "var(--bc-ink)"
    if flaeche in STARK_DUNKEL:
        return "var(--bc-white)"
    return None


class Zuordnung:
    def __init__(self, daten: dict):
        self.farben = {normalise(k): v for k, v in daten.get("farben", {}).items()}
        self.farben_dunkel = {normalise(k): v for k, v in daten.get("farben_dunkel", {}).items()}
        self.selektoren = {
            self.selektor_schluessel(sel): {
                art: {normalise(c): rolle for c, rolle in rollen.items()} for art, rollen in arten.items()
            }
            for sel, arten in daten.get("selektoren", {}).items()
        }

    @classmethod
    def lade(cls, pfad: Path) -> "Zuordnung":
        if not pfad.is_file():
            raise FarbFehler(f"Die Farbzuordnung {pfad} fehlt. Mit 'farben.py vorschlag' eine erzeugen.")
        try:
            return cls(json.loads(pfad.read_text(encoding="utf-8")))
        except json.JSONDecodeError as err:
            raise FarbFehler(
                f"{pfad} ist kein gültiges JSON (Zeile {err.lineno}, Spalte {err.colno}: {err.msg})."
            ) from err

    @staticmethod
    def selektor_schluessel(selektor: str) -> str:
        return re.sub(r"\s+", " ", selektor.strip())

    def rolle(self, farbe: str, art: str, selektor: str = "", dunkel: bool = False,
              flaeche: str | None = None) -> tuple[str, bool]:
        schluessel = normalise(farbe)
        sonder = self.selektoren.get(self.selektor_schluessel(selektor), {}).get(art, {}).get(schluessel)
        if sonder is not None:
            return sonder, False
        if art == "text":
            kontext = kontext_rolle(schluessel, flaeche)
            if kontext is not None:
                return kontext, False
        eintrag = (self.farben_dunkel if dunkel else self.farben).get(schluessel, {})
        if art in eintrag:
            return eintrag[art], False
        return auto_rolle(schluessel, art, dunkel), True


# --- Ableitung -------------------------------------------------------------------------

RAND_KURZ = {"border": "border-color", "border-top": "border-top-color", "border-right": "border-right-color",
             "border-bottom": "border-bottom-color", "border-left": "border-left-color",
             "outline": "outline-color", "column-rule": "column-rule-color"}


@dataclass
class Fund:
    farbe: str
    art: str
    eigenschaft: str
    selektor: str
    rolle: str
    datei: str = ""


@dataclass
class Ableitung:
    zeilen: list[str]
    funde: list[Fund]
    deklarationen: int


def ist_dunkel(selektor: str, merkmal: str) -> bool:
    """Wahr, wenn jeder Teil der Selektorliste unter dem dunklen Merkmal steht."""
    muster = re.compile(r"(?:^|[\s>+~(])" + re.escape(merkmal) + r"(?![\w-])")
    teile = [t.strip() for t in split_top(selektor, ",") if t.strip()]
    return bool(teile) and all(muster.search(" " + t) for t in teile)


def _ausserhalb_schutz(wert: str, ersetze) -> str:
    teile, zuletzt = [], 0
    for m in SCHUTZ_RE.finditer(wert):
        teile.append(ersetze(wert[zuletzt:m.start()]))
        teile.append(m.group(0))
        zuletzt = m.end()
    teile.append(ersetze(wert[zuletzt:]))
    return "".join(teile)


def ersetze_farben(wert: str, art: str, zuordnung: Zuordnung, selektor: str, dunkel: bool,
                   flaeche: str | None, notiz) -> str:
    def repl(m: re.Match) -> str:
        roh = m.group(0)
        if roh.lower() in KEEP:
            return roh
        rolle, automatisch = zuordnung.rolle(roh, art, selektor, dunkel, flaeche)
        if automatisch:
            notiz(normalise(roh), rolle)
        return rolle

    return _ausserhalb_schutz(wert, lambda stueck: COLOUR_RE.sub(repl, stueck))


def ohne_feste_farbe(d: Decl) -> list[str]:
    """Werte ohne feste Farbe kommen mit, damit die Reihenfolge der Kaskade bleibt."""
    wert = d.value.strip()
    low = wert.lower()
    if d.prop in RAND_KURZ:
        teile = [t.strip() for t in split_top(wert, " ")
                 if t.strip().lower().startswith("var(") or t.strip().lower() in KEEP - {"none"}]
        return [f"{RAND_KURZ[d.prop]}: {teile[-1]}"] if teile else []
    if d.prop == "background":
        if low in ("none", "transparent"):
            return ["background-color: transparent"] + (["background-image: none"] if low == "none" else [])
        teile = [t.strip() for t in split_top(wert, " ") if t.strip().lower().startswith("var(")]
        return [f"background-color: {teile[-1]}"] if teile else []
    if d.prop == "background-image":
        return []
    if "var(" in low or low in KEEP:
        return [f"{d.prop}: {wert}"]
    return []


def leite_ab(d: Decl, selektor: str, zuordnung: Zuordnung, dunkel: bool, flaeche: str | None,
             funde: list[Fund]) -> list[str]:
    art = COLOUR_PROPS.get(d.prop)
    if not art:
        return []
    gefunden = colours_in(d.value)
    if not gefunden:
        return ohne_feste_farbe(d)

    def ersetze(stueck: str, art_hier: str) -> str:
        return ersetze_farben(stueck, art_hier, zuordnung, selektor, dunkel, flaeche,
                              lambda farbe, rolle: funde.append(Fund(farbe, art_hier, d.prop, selektor, rolle)))

    if d.prop in ("background", "background-image"):
        if "gradient(" in d.value.lower():
            schichten = [ersetze(t.strip(), "background") for t in split_top(d.value, ",") if t.strip()]
            return [f"background-image: {', '.join(schichten)}"]
        farbe = None
        for token in split_top(d.value, " "):
            token = token.strip().rstrip(",").strip()
            if token and COLOUR_RE.fullmatch(token) and token.lower() not in KEEP:
                farbe = ersetze(token, "background")
        return [f"background-color: {farbe}"] if farbe is not None else []
    if d.prop in RAND_KURZ:
        return [f"{RAND_KURZ[d.prop]}: {ersetze(gefunden[-1], art)}"]
    return [f"{d.prop}: {ersetze(d.value, art)}"]


def flaechen_rolle(rule: Rule, zuordnung: Zuordnung, dunkel: bool) -> str | None:
    for d in rule.decls:
        if COLOUR_PROPS.get(d.prop) == "background":
            gefunden = colours_in(d.value)
            if gefunden:
                return zuordnung.rolle(gefunden[-1], "background", rule.selector, dunkel, None)[0]
    return None


def ableiten(css: str, zuordnung: Zuordnung, datei: str, dunkel_merkmal: str) -> Ableitung:
    funde: list[Fund] = []
    zahl = 0

    def regel(rule: Rule, einzug: str) -> list[str]:
        nonlocal zahl
        dunkel = ist_dunkel(rule.selector, dunkel_merkmal)
        flaeche = flaechen_rolle(rule, zuordnung, dunkel)
        innen = []
        for d in rule.decls:
            wichtig = " !important" if d.important else ""
            for zeile in leite_ab(d, rule.selector, zuordnung, dunkel, flaeche, funde):
                innen.append(f"{einzug}\t{zeile}{wichtig};")
        zahl += len(innen)
        return [f"{einzug}{rule.selector} {{", *innen, f"{einzug}}}"] if innen else []

    def render(nodes: list, einzug: str) -> list[str]:
        aus: list[str] = []
        for node in nodes:
            if isinstance(node, Block):
                innen = render(node.children, einzug + "\t")
                if innen:
                    aus += [f"{einzug}{node.prelude} {{", *innen, f"{einzug}}}"]
            elif isinstance(node, Rule):
                aus += regel(node, einzug)
        return aus

    zeilen = render(parse_css(css), "")
    for f in funde:
        f.datei = datei
    return Ableitung(zeilen, funde, zahl)

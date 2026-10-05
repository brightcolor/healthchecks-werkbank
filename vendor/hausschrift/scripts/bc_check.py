#!/usr/bin/env python3
"""bright color design check.

    python bc_check.py contrast FG BG [BG ...]
        WCAG contrast of one text colour against one or more grounds.
        Several grounds (card, hover, table head) report the minimum.

    python bc_check.py pairs
        The approved text/ground pairings, measured.

    python bc_check.py lint PATH [PATH ...] [--variant public|workbench]
        Scan CSS, SCSS, HTML, Twig, Vue, Blade and PHP templates for breaks of
        the house style. Directories are walked. Exit code 1 on warnings.

The palette is read from ../assets/css/bc-tokens.css: every hex value there is
allowed, everything else is reported. Output is German, for people.
"""

from __future__ import annotations

import argparse
import bisect
import re
import sys
from dataclasses import dataclass
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
TOKENS_FILE = SKILL_DIR / "assets" / "css" / "bc-tokens.css"

LINT_SUFFIXES = {".css", ".scss", ".html", ".htm", ".twig", ".vue", ".php", ".blade.php", ".svelte", ".jsx", ".tsx"}
SKIP_DIRS = {"node_modules", "vendor", ".git", ".venv", "dist", "build", "chrome-profile"}

ALLOWED_FONTS = {
    "anton", "atkinson hyperlegible", "ibm plex mono",
    # Legacy: bright-color.de start page and header, ISPConfig theme, print generators.
    "work sans",
    # Fallbacks that may lead a stack in mail and PDF.
    "arial narrow", "impact", "arial", "helvetica", "helvetica neue",
    "system-ui", "-apple-system", "ui-monospace", "sfmono-regular", "menlo", "consolas", "monospace",
    "sans-serif", "inherit", "initial", "unset",
}

HEX_RE = re.compile(r"#([0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3,4})\b")
RGB_RE = re.compile(r"rgba?\(\s*([\d.]+)[\s,]+([\d.]+)[\s,]+([\d.]+)(?:[\s,/]+([\d.]+%?))?\s*\)")
VAR_RE = re.compile(r"var\(\s*(--[\w-]+)\s*(?:,\s*([^)]+))?\)")
BLOCK_RE = re.compile(r"([^{}]*)\{([^{}]*)\}")
COMMENT_RE = re.compile(r"/\*.*?\*/", re.S)
STYLE_TAG_RE = re.compile(r"<style[^>]*>(.*?)</style>", re.S | re.I)
STYLE_ATTR_RE = re.compile(r"""\sstyle\s*=\s*(["'])(.*?)\1""", re.S | re.I)
HEADING_RE = re.compile(r"<(h[12])\b[^>]*>(.*?)</\1>", re.S | re.I)
# Components that set their text in capitals besides h1/h2: labels, tile and
# box titles, footer titles, display text, price names and badges.
CAPS_CLASS_RE = re.compile(
    r"""<(\w+)\b[^>]*\bclass\s*=\s*["'][^"']*\b(bc-eyebrow|bc-footer__title|bc-tile__title|bc-cta__title|"""
    r"""bc-display|bc-price__name|bc-price__badge|bc-figure__value)\b[^"']*["'][^>]*>(.*?)</\1>""",
    re.S | re.I)
QUOTE_RE = re.compile(r"""<figure\b[^>]*\bclass\s*=\s*["'][^"']*\bbc-quote\b[^>]*>.*?<blockquote\b[^>]*>(.*?)</blockquote>""", re.S | re.I)
BRAND_WRONG_RE = re.compile(r"\b(Bright Color|Bright color|bright Color|BRIGHT COLOR|BrightColor)\b")
BRAND_RE = re.compile(r"bright(?:\s|&nbsp;| )+color", re.I)


# --------------------------------------------------------------------------
# Colour maths
# --------------------------------------------------------------------------

def parse_colour(text: str) -> tuple[float, float, float, float] | None:
    text = text.strip().lower()
    m = HEX_RE.fullmatch(text) if text.startswith("#") else None
    if m:
        h = m.group(1)
        if len(h) in (3, 4):
            h = "".join(c * 2 for c in h)
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        a = int(h[6:8], 16) / 255 if len(h) == 8 else 1.0
        return r, g, b, a
    m = RGB_RE.fullmatch(text)
    if m:
        a = m.group(4)
        alpha = 1.0 if a is None else (float(a[:-1]) / 100 if a.endswith("%") else float(a))
        return float(m.group(1)), float(m.group(2)), float(m.group(3)), alpha
    if text in ("white", "#fff"):
        return 255, 255, 255, 1.0
    if text == "black":
        return 0, 0, 0, 1.0
    return None


def composite(top, bottom):
    a = top[3] + bottom[3] * (1 - top[3])
    if a == 0:
        return 0, 0, 0, 0
    mix = [(top[i] * top[3] + bottom[i] * bottom[3] * (1 - top[3])) / a for i in range(3)]
    return mix[0], mix[1], mix[2], a


def luminance(c) -> float:
    def lin(v: float) -> float:
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    return 0.2126 * lin(c[0]) + 0.7152 * lin(c[1]) + 0.0722 * lin(c[2])


def ratio(fg, bg) -> float:
    if fg[3] < 1:
        fg = composite(fg, bg)
    a, b = luminance(fg), luminance(bg)
    return (max(a, b) + 0.05) / (min(a, b) + 0.05)


def hexcode(c) -> str:
    return "#" + "".join(f"{round(v):02x}" for v in c[:3])


def verdict(r: float) -> str:
    if r >= 7:
        return "AAA"
    if r >= 4.5:
        return "AA"
    if r >= 3:
        return "nur große Schrift (ab 24 px, fett ab 18,7 px) und Bedienelemente"
    return "durchgefallen"


# --------------------------------------------------------------------------
# Tokens
# --------------------------------------------------------------------------

@dataclass
class Tokens:
    public: dict[str, str]
    workbench: dict[str, str]
    dark: dict[str, str]
    allowed_hex: set[str]


def load_tokens() -> Tokens:
    if not TOKENS_FILE.exists():
        sys.exit(f"Die Tokendatei fehlt: {TOKENS_FILE}. Ohne sie kennt die Prüfung die Palette nicht.")
    css = COMMENT_RE.sub("", TOKENS_FILE.read_text(encoding="utf-8"))
    groups: dict[str, dict[str, str]] = {"public": {}, "workbench": {}, "dark": {}}
    for m in BLOCK_RE.finditer(css):
        selector, body = m.group(1).strip(), m.group(2)
        if selector.startswith(":root"):
            target = "public"
        elif 'data-theme="dark"' in selector:
            target = "dark"
        elif 'data-bc-variant="workbench"' in selector:
            target = "workbench"
        else:
            continue
        for decl in body.split(";"):
            if ":" in decl:
                name, value = decl.split(":", 1)
                if name.strip().startswith("--"):
                    groups[target][name.strip()] = value.strip()
    allowed = {normalise_hex(h) for h in HEX_RE.findall(css)}
    return Tokens(groups["public"], groups["workbench"], groups["dark"], allowed)


def normalise_hex(h: str) -> str:
    h = h.lower().lstrip("#")
    if len(h) in (3, 4):
        h = "".join(c * 2 for c in h)
    return "#" + h[:6]


def resolve(value: str, table: dict[str, str], depth: int = 0) -> str:
    """Replace var(--bc-*) by its token value, following chains."""
    if depth > 8:
        return value

    def sub(m: re.Match) -> str:
        name, fallback = m.group(1), m.group(2)
        if name in table:
            return resolve(table[name], table, depth + 1)
        return fallback.strip() if fallback else m.group(0)

    return VAR_RE.sub(sub, value)


# --------------------------------------------------------------------------
# Lint
# --------------------------------------------------------------------------

@dataclass
class Finding:
    path: Path
    line: int
    rule: str
    level: str  # "Warnung" or "Hinweis"
    text: str


class Linter:
    def __init__(self, tokens: Tokens, variant: str | None):
        self.tokens = tokens
        self.forced_variant = variant
        self.findings: list[Finding] = []

    def table_for(self, variant: str) -> dict[str, str]:
        table = dict(self.tokens.public)
        if variant == "workbench":
            table.update(self.tokens.workbench)
        return table

    def add(self, path, line, rule, level, text):
        self.findings.append(Finding(path, line, rule, level, text))

    # -- file entry ------------------------------------------------------

    def lint_file(self, path: Path) -> None:
        try:
            source = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            source = path.read_text(encoding="latin-1")
        newlines = [i for i, ch in enumerate(source) if ch == "\n"]

        def line_of(offset: int) -> int:
            return bisect.bisect_right(newlines, offset - 1) + 1

        code = re.sub(r"<!--.*?-->", "", COMMENT_RE.sub("", source), flags=re.S)
        # A project stylesheet for a workbench page rarely carries the marker,
        # but it styles the rail or the top bar.
        variant = self.forced_variant or (
            "workbench" if re.search(r'data-bc-variant\s*=\s*["\']workbench|bc-workbench|\.bc-(rail|topbar)\b|--bc-rail', code) else "public"
        )
        is_css = path.suffix.lower() in (".css", ".scss")
        if path.resolve() == TOKENS_FILE.resolve():
            return  # the palette itself

        if is_css:
            self.lint_css(path, source, 0, line_of, variant)
        else:
            for m in STYLE_TAG_RE.finditer(source):
                self.lint_css(path, m.group(1), m.start(1), line_of, variant)
            for m in STYLE_ATTR_RE.finditer(source):
                self.lint_declarations(path, "[style]", m.group(2), m.start(2), line_of, variant)
            self.lint_text(path, source, line_of)

    # -- CSS ---------------------------------------------------------------

    def lint_css(self, path, css, base, line_of, variant):
        # Blank out comments but keep offsets, so line numbers stay true.
        css = COMMENT_RE.sub(lambda m: re.sub(r"[^\n]", " ", m.group(0)), css)
        # Custom properties a selector receives from any rule that names it,
        # e.g. ".bc-band--ink, .bc-cta { --bc-text: ... }".
        self.local_props: dict[str, dict[str, str]] = {}
        for m in BLOCK_RE.finditer(css):
            props = {
                d.split(":", 1)[0].strip(): d.split(":", 1)[1].strip()
                for d in m.group(2).split(";")
                if ":" in d and d.strip().startswith("--")
            }
            if props:
                for sel in self.split_selectors(m.group(1)):
                    self.local_props.setdefault(sel, {}).update(props)
        for m in BLOCK_RE.finditer(css):
            selector = m.group(1).strip().split(";")[-1].strip()
            if selector.startswith("@font-face") or selector.startswith("@keyframes"):
                continue
            self.lint_declarations(path, selector, m.group(2), base + m.start(2), line_of, variant)
        self.local_props = {}

    @staticmethod
    def split_selectors(selector: str) -> list[str]:
        selector = selector.strip().split(";")[-1]
        selector = re.sub(r"^@media[^{]*", "", selector).strip()
        return [" ".join(s.split()) for s in re.split(r",(?![^(]*\))", selector) if s.strip()]

    def lint_declarations(self, path, selector, body, base, line_of, variant):
        table = self.table_for(variant)
        for sel in self.split_selectors(selector):
            table.update(getattr(self, "local_props", {}).get(sel, {}))
        for d in body.split(";"):
            if ":" in d and d.strip().startswith("--"):
                name, value = d.split(":", 1)
                table[name.strip()] = value.strip()
        decls: dict[str, tuple[str, int]] = {}
        pos = 0
        for raw in body.split(";"):
            offset = base + pos + (len(raw) - len(raw.lstrip()))
            pos += len(raw) + 1
            if ":" not in raw:
                continue
            prop, value = raw.split(":", 1)
            prop, value = prop.strip().lower(), value.strip()
            if not prop or prop.startswith("--"):
                # custom properties may carry any colour; they are checked where used
                if prop.startswith("--"):
                    self.check_colours(path, line_of(offset), prop, value, variant)
                continue
            decls[prop] = (value, offset)
            line = line_of(offset)
            self.check_colours(path, line, prop, value, variant)

            if prop in ("color", "-webkit-text-fill-color"):
                c = parse_colour(resolve(value, table))
                if c and 0 < c[3] < 1:
                    self.add(path, line, "deckkraft", "Warnung",
                             f"{selector}: Schrift mit Transparenz ({value}). Der Kontrast hängt dann vom Untergrund ab; "
                             "einen festen Ton nehmen, auf Tinte etwa #b3aea3 (8,5:1).")

            if variant == "public" and prop.startswith("border") and "radius" in prop:
                if not re.fullmatch(r"(0|0px|0rem|50%|var\(--bc-radius(-sm)?\))(\s+(0|0px|50%))*\s*(!important)?", value):
                    self.add(path, line, "rundung", "Warnung",
                             f"{selector}: border-radius {value}. Im Auftritt sind Kanten eckig (Radius 0); "
                             "Rundungen gehören zur Werkbank.")

            if variant == "public" and prop == "box-shadow" and self.has_soft_shadow(resolve(value, table)):
                self.add(path, line, "schatten", "Warnung",
                         f"{selector}: weicher Schatten ({value}). Im Auftritt entsteht Tiefe durch einen harten Versatz, "
                         "z. B. box-shadow: 3px 3px 0 var(--bc-signal).")

            if prop.startswith("background") and self.has_soft_gradient(value):
                self.add(path, line, "verlauf", "Warnung",
                         f"{selector}: weicher Farbverlauf. Die Handschrift arbeitet mit Vollflächen; "
                         "harte Streifen (z. B. das Vierfarbband) sind erlaubt.")

            if prop == "font-family" or (prop == "font" and "," in value):
                self.check_font(path, line, selector, value, table)

        self.check_anton_caps(path, selector, decls, table, line_of)
        self.check_pair(path, selector, decls, table, line_of)

    def check_colours(self, path, line, prop, value, variant):
        for m in HEX_RE.finditer(value):
            h = normalise_hex(m.group(0))
            if h not in self.tokens.allowed_hex:
                hint = " Tinte ist #111111." if h in ("#000000",) else ""
                self.add(path, line, "farbe", "Warnung",
                         f"{prop}: {m.group(0)} steht nicht in der Palette (bc-tokens.css).{hint}")
        for m in RGB_RE.finditer(value):
            c = (float(m.group(1)), float(m.group(2)), float(m.group(3)))
            h = hexcode(c)
            if h not in self.tokens.allowed_hex and not (c == (0, 0, 0) and m.group(4) is not None):
                self.add(path, line, "farbe", "Warnung",
                         f"{prop}: {m.group(0)} (= {h}) steht nicht in der Palette. "
                         "Transparente Töne nur aus Palettenfarben mischen.")

    @staticmethod
    def has_soft_shadow(value: str) -> bool:
        if value.strip() in ("none", "0", "initial", "unset", "inherit"):
            return False
        for shadow in re.split(r",(?![^(]*\))", value):
            lengths = re.findall(r"(-?[\d.]+)(px|rem|em)?", re.sub(r"(rgba?|hsla?|var)\([^)]*\)|#[0-9a-fA-F]+", "", shadow))
            nums = [float(n) for n, _ in lengths]
            if len(nums) >= 3 and nums[2] > 0:
                return True
        return False

    @staticmethod
    def has_soft_gradient(value: str) -> bool:
        if "radial-gradient" in value or "conic-gradient" in value:
            return True
        for m in re.finditer(r"linear-gradient\((.*)\)", value):
            inner = m.group(1)
            parts = [p.strip() for p in re.split(r",(?![^(]*\))", inner)]
            if parts and re.match(r"^(to |[\d.]+deg|[\d.]+turn)", parts[0]):
                parts = parts[1:]
            colours = []
            hard = True
            for p in parts:
                col = re.match(r"(#[0-9a-fA-F]+|rgba?\([^)]*\)|var\([^)]*\)|[a-z]+)", p)
                if col:
                    colours.append(col.group(1))
                    # a hard stop names two positions: "red 0 25%"
                    if len(re.findall(r"-?[\d.]+%|\b0\b|-?[\d.]+px", p[len(col.group(1)):])) < 2 and len(set(colours)) > 1:
                        hard = False
            if len(set(colours)) > 1 and not hard:
                return True
        return False

    def check_font(self, path, line, selector, value, table):
        family = resolve(value, table).replace("!important", "").strip()
        first = family.split(",")[0].strip().strip("'\"").lower()
        if first.startswith("var("):
            return
        # "font" shorthand: take the part after the size
        if " " in first and first not in ALLOWED_FONTS:
            first = re.split(r"\s", first)[-1].strip("'\"")
        if first and first not in ALLOWED_FONTS:
            self.add(path, line, "schrift", "Warnung",
                     f"{selector}: Schrift „{first}“. Die Handschrift nutzt Anton (Anzeige), "
                     "Atkinson Hyperlegible (Text) und optional IBM Plex Mono.")

    def check_anton_caps(self, path, selector, decls, table, line_of):
        fam = decls.get("font-family") or decls.get("font")
        if not fam:
            return
        family = resolve(fam[0], table).lower()
        if not family.lstrip("'\" ").startswith("anton"):
            return
        transform = decls.get("text-transform", ("", 0))[0].lower()
        if "uppercase" in transform:
            return
        # Figures, prices and counters are digits; capitals change nothing there.
        if re.search(r"figure|value|price|amount|number|num\b|count|step|zahl|preis|betrag|\bdd\b", selector, re.I):
            return
        self.add(path, line_of(fam[1]), "anton-versal", "Hinweis",
                 f"{selector}: Anton ohne text-transform: uppercase in derselben Regel. "
                 "Anton steht nur in Versalien; Ziffern und Preise dürfen so bleiben.")

    def check_pair(self, path, selector, decls, table, line_of):
        fg_decl = decls.get("-webkit-text-fill-color") or decls.get("color")
        bg_decl = decls.get("background-color") or decls.get("background")
        if not fg_decl or not bg_decl:
            return
        fg = parse_colour(resolve(fg_decl[0], table).split()[0]) if resolve(fg_decl[0], table).split() else None
        bg_value = resolve(bg_decl[0], table)
        bg_match = HEX_RE.search(bg_value) or RGB_RE.search(bg_value)
        bg = parse_colour(bg_match.group(0)) if bg_match else None
        if not fg or not bg or bg[3] < 1 or "gradient" in bg_value or "url(" in bg_value:
            return
        r = ratio(fg, bg)
        if r < 4.5:
            level = "Warnung" if r < 3 else "Hinweis"
            self.add(path, line_of(fg_decl[1]), "kontrast", level,
                     f"{selector}: Schrift {hexcode(fg)} auf {hexcode(bg)} ergibt {r:.2f}:1 ({verdict(r)}).")

    # -- text ----------------------------------------------------------------

    def lint_text(self, path, source, line_of):
        stripped = re.sub(r"<(script|style)[^>]*>.*?</\1>", lambda m: re.sub(r"[^\n]", " ", m.group(0)), source, flags=re.S | re.I)
        for m in BRAND_WRONG_RE.finditer(re.sub(r"<[^>]+>", lambda t: " " * len(t.group(0)), stripped)):
            self.add(path, line_of(m.start()), "markenname", "Warnung",
                     f"„{m.group(0)}“: Der Markenname wird immer „bright color“ geschrieben, klein.")
        for m in HEADING_RE.finditer(stripped):
            inner = m.group(2)
            if BRAND_RE.search(inner) and "bc-brand" not in inner:
                self.add(path, line_of(m.start()), "marke-versal", "Warnung",
                         f"<{m.group(1)}> enthält „bright color“ und wird in Versalien gesetzt. "
                         "Überschrift ohne Markennamen formulieren oder den Namen in <span class=\"bc-brand\"> setzen.")
        for m in CAPS_CLASS_RE.finditer(stripped):
            inner = m.group(3)
            if BRAND_RE.search(inner) and "bc-brand" not in inner:
                self.add(path, line_of(m.start()), "marke-versal", "Warnung",
                         f"<{m.group(1)} class=\"{m.group(2)}\"> enthält „bright color“ und steht in Versalien. "
                         "Text ohne Markennamen formulieren oder den Namen in <span class=\"bc-brand\"> setzen.")
        for m in QUOTE_RE.finditer(stripped):
            inner = m.group(1)
            if BRAND_RE.search(inner) and "bc-brand" not in inner:
                self.add(path, line_of(m.start()), "marke-versal", "Warnung",
                         "Das Zitat (bc-quote) enthält „bright color“ und steht in Versalien. "
                         "Satz ohne Markennamen formulieren oder den Namen in <span class=\"bc-brand\"> setzen.")


# --------------------------------------------------------------------------
# Commands
# --------------------------------------------------------------------------

PAIRS = [
    ("#111111", "#f2f0eb", "Tinte auf Papier", "Text, Überschriften"),
    ("#111111", "#ffffff", "Tinte auf Weiß", "Text auf Karten"),
    ("#4a4a4a", "#f2f0eb", "Tinte leise auf Papier", "Nebentext"),
    ("#4a4a4a", "#ffffff", "Tinte leise auf Weiß", "Nebentext auf Karten"),
    ("#8b3a6f", "#f2f0eb", "Verweis-Lila auf Papier", "Textlinks"),
    ("#8b3a6f", "#ffffff", "Verweis-Lila auf Weiß", "Textlinks auf Karten"),
    ("#ffffff", "#111111", "Weiß auf Tinte", "Kopf, Fuß, dunkle Bänder, Hauptknopf"),
    ("#b3aea3", "#111111", "Stein auf Tinte", "Nebentext auf Tinte"),
    ("#fed329", "#111111", "Gelb auf Tinte", "aktueller Menüpunkt, Hover im Kopf"),
    ("#bfd535", "#111111", "Limette auf Tinte", "Hover im Fuß"),
    ("#05202a", "#1dc3f3", "Tiefe auf Cyan", "Text auf Cyan-Band"),
    ("#111111", "#fed329", "Tinte auf Gelb", "Text auf Gelb, Werkbank-Hauptknopf"),
    ("#111111", "#bfd535", "Tinte auf Limette", "Text auf Limette, Status aktiv"),
    ("#ffffff", "#d61f7a", "Weiß auf Aktions-Pink", "Kaufen-Knopf, Fehlerfläche"),
    ("#ffffff", "#aa4b88", "Weiß auf Violett", "violette Kachel"),
    ("#ffffff", "#ee318a", "Weiß auf Logo-Magenta", "NICHT für Text: nur Flächen ohne Schrift"),
    ("#111111", "#ee318a", "Tinte auf Logo-Magenta", "Balkenzahl auf Magenta (Werkbank)"),
    ("#ffffff", "#1dc3f3", "Weiß auf Cyan", "NICHT für Text"),
    ("#8c1a4c", "#fbe3ee", "Fehlertext auf Fehlertönung", "Fehlermeldung"),
    ("#3d5c00", "#ffffff", "Erfolgstext auf Weiß", "Erfolgsmeldung als Text"),
    ("#b3146a", "#ffffff", "Werkbank-Link auf Weiß", "Links hell"),
    ("#5e5b55", "#f7f6f2", "Werkbank leise auf Kopfzeile", "Tabellenkopf"),
    ("#1dc3f3", "#141415", "Cyan auf Werkbank dunkel", "Links dunkel"),
    ("#e6e4de", "#141415", "Werkbank-Text dunkel", "Fließtext dunkel"),
    ("#a3a097", "#141415", "Werkbank leise dunkel", "Nebentext dunkel"),
    ("#ff5ca8", "#141415", "Fehlertext dunkel", "Fehler dunkel"),
]


def cmd_contrast(args) -> int:
    fg = parse_colour(args.fg)
    if not fg:
        print(f"Die Schriftfarbe „{args.fg}“ ist unlesbar. Erwartet wird #rrggbb oder rgb(r, g, b).")
        return 2
    worst = None
    for g in args.bg:
        bg = parse_colour(g)
        if not bg:
            print(f"Die Fläche „{g}“ ist unlesbar. Erwartet wird #rrggbb oder rgb(r, g, b).")
            return 2
        r = ratio(fg, bg)
        worst = r if worst is None else min(worst, r)
        print(f"{args.fg} auf {g}: {r:.2f}:1  {verdict(r)}")
    if len(args.bg) > 1:
        print(f"Minimum über alle Flächen: {worst:.2f}:1  {verdict(worst)}")
    return 0 if worst >= 4.5 else 1


def cmd_pairs(_args) -> int:
    print(f"{'Schrift':9} {'Fläche':9} {'Kontrast':>9}  Bewertung / Einsatz")
    for fg, bg, name, use in PAIRS:
        r = ratio(parse_colour(fg), parse_colour(bg))
        print(f"{fg:9} {bg:9} {r:8.2f}:1  {verdict(r)}  {name}: {use}")
    return 0


def collect(paths: list[str]) -> list[Path]:
    files: list[Path] = []
    for p in map(Path, paths):
        if p.is_dir():
            for f in sorted(p.rglob("*")):
                if f.is_file() and not SKIP_DIRS.intersection(f.parts) and (
                    f.suffix.lower() in LINT_SUFFIXES or f.name.endswith(".blade.php")
                ):
                    files.append(f)
        elif p.is_file():
            files.append(p)
        else:
            print(f"„{p}“ gibt es nicht. Pfad prüfen und erneut aufrufen.")
    return files


def cmd_lint(args) -> int:
    tokens = load_tokens()
    linter = Linter(tokens, args.variant)
    files = collect(args.paths)
    if not files:
        print("Keine prüfbaren Dateien gefunden (css, scss, html, twig, vue, php, jsx, tsx).")
        return 2
    for f in files:
        linter.lint_file(f)
    warnings = [f for f in linter.findings if f.level == "Warnung"]
    for f in sorted(linter.findings, key=lambda x: (str(x.path), x.line)):
        print(f"{f.path}:{f.line}  {f.level:8} [{f.rule}]  {f.text}")
    hints = len(linter.findings) - len(warnings)
    print(f"\n{len(files)} Datei(en) geprüft: {len(warnings)} Warnung(en), {hints} Hinweis(e).")
    return 1 if warnings else 0


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="bright color: Kontrast und Hausstil prüfen")
    sub = parser.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("contrast", help="Kontrast einer Schriftfarbe gegen eine oder mehrere Flächen")
    c.add_argument("fg")
    c.add_argument("bg", nargs="+")
    c.set_defaults(func=cmd_contrast)
    p = sub.add_parser("pairs", help="die freigegebenen Paarungen, gemessen")
    p.set_defaults(func=cmd_pairs)
    lint = sub.add_parser("lint", help="Dateien auf Brüche mit dem Hausstil prüfen")
    lint.add_argument("paths", nargs="+")
    lint.add_argument("--variant", choices=["public", "workbench"], default=None,
                      help="Ausprägung erzwingen; sonst Werkbank, wenn die Datei data-bc-variant=\"workbench\" trägt")
    lint.set_defaults(func=cmd_lint)
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

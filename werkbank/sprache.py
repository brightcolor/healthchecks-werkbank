#!/usr/bin/env python3
"""Übersetzung von Healthchecks beim Bau.

  python sprache.py bauen    --wurzel /opt/healthchecks --werkbank /tmp/werkbank [--bericht bericht.json]
  python sprache.py inventur --wurzel /opt/healthchecks --werkbank /tmp/werkbank [--datei MUSTER] [--global-ab N]

`bauen` setzt in jeder Sprache die Erweiterungen (werkbank/erweiterungen.toml), das
Einstellungsmodul und das Formatmodul ein und wendet bei WB_SPRACHE=de den Katalog
aus werkbank/<WB_KATALOG>/ an. `inventur` gibt die englischen Textstücke ohne Eintrag
als TOML-Gerüst aus.

Ein Katalog besteht aus TOML-Dateien mit zwei Arten von Einträgen:
  [[text]]       datei, en, de   ganzes sichtbares Textstück oder sichtbarer Attributwert;
                                 datei = "*" gilt für alle Vorlagen im Geltungsbereich
  [[quelltext]]  datei, en, de   genaues Stück Quelle, optional anzahl
Ein Eintrag mit gleichem en und de markiert ein geprüftes Wort, das bleibt.

Einstellungen über Umgebungsvariablen; die Vorgaben stehen in VORGABEN.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import shutil
import sys
import tomllib
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

VORGABEN = {
    # Sprache des Images: de wendet den Katalog an, en lässt die Texte von Healthchecks stehen.
    "WB_SPRACHE": "de",
    # Ordner des Katalogs in werkbank/ und seine Datei mit Stand, Geltungsbereich und Zuständen.
    "WB_KATALOG": "deutsch",
    "WB_KATALOG_KONFIG": "katalog.toml",
    # Erweiterungen, die in jeder Sprache greifen müssen, in werkbank/.
    "WB_ERWEITERUNGEN": "erweiterungen.toml",
    # Ziele in Healthchecks, relativ zu seiner Wurzel.
    "WB_EINSTELLUNGSMODUL": "hc/werkbank_einstellungen.py",
    "WB_FORMATMODUL": "hc/werkbank_formate",
    "WB_LOCAL_SETTINGS": "hc/local_settings.py",
}
SPRACHEN = ("de", "en")
PFAD_EINSTELLUNGEN = ("WB_EINSTELLUNGSMODUL", "WB_FORMATMODUL", "WB_LOCAL_SETTINGS")
# Attribute, deren Wert ein Mensch sieht oder hört (HTML); value ist nur an Knöpfen Beschriftung.
SICHTBARE_ATTRIBUTE = ("title", "placeholder", "aria-label", "alt")
KNOPF_TYPEN = ("submit", "button", "reset")
BUCHSTABEN = re.compile(r"[A-Za-z]{2}")
# Template-Ausdrücke tragen keinen Text; Wörter mit Ziffern sind Fassungen, Zeiten oder Adressen.
AUSDRUCK = re.compile(r"\{\{.*?\}\}|\{%.*?%\}|&(?:[A-Za-z]+|#\d+|#x[0-9A-Fa-f]+);", re.S)
TOKEN = re.compile(
    r"\{#.*?#\}"
    r"|\{%\s*comment\s*%\}.*?\{%\s*endcomment\s*%\}"
    r"|\{%.*?%\}"
    r"|\{\{.*?\}\}"
    r"|<!--.*?-->"
    r"|<![A-Za-z][^>]*>"
    r"|<(?P<opak>script|style|pre|code|textarea)\b.*?</(?P=opak)\s*>"
    r"|</?[A-Za-z][^<>]*>",
    re.S | re.I,
)
ATTRIBUT = re.compile(r"""(?P<name>[A-Za-z_:][-A-Za-z0-9_:.]*)\s*=\s*(?P<q>["'])(?P<wert>.*?)(?P=q)""", re.S)
TAGNAME = re.compile(r"<([A-Za-z][A-Za-z0-9-]*)")


class SprachFehler(Exception):
    """Ein Problem im Katalog oder in den Einstellungen; die Meldung sagt, was zu ändern ist."""


@dataclass
class Stueck:
    art: str
    start: int
    ende: int
    roh: str


@dataclass
class Eintrag:
    art: str
    datei: str
    en: str
    de: str
    anzahl: int | None
    herkunft: str


@dataclass
class Katalog:
    stand: str
    vorlagen: list[str]
    ausnahmen: list[str]
    zustaende: dict[str, str]
    eintraege: list[Eintrag]


def einstellung(name: str) -> str:
    return os.environ.get(name, VORGABEN[name])


def norm(text: str) -> str:
    return " ".join(text.split())


def kurz(text: str, laenge: int = 120) -> str:
    text = norm(text)
    return text if len(text) <= laenge else text[: laenge - 1] + "…"


def lies(pfad: Path) -> tuple[str, bool]:
    """Text einer Datei mit LF; der zweite Wert sagt, ob sie CRLF nutzt."""
    roh = pfad.read_bytes().decode("utf-8")
    return roh.replace("\r\n", "\n"), "\r\n" in roh


def schreibe(pfad: Path, text: str, crlf: bool = False) -> None:
    pfad.write_bytes((text.replace("\n", "\r\n") if crlf else text).encode("utf-8"))


def toml_laden(pfad: Path) -> dict:
    try:
        return tomllib.loads(lies(pfad)[0])
    except (tomllib.TOMLDecodeError, UnicodeDecodeError) as err:
        raise SprachFehler(f"{pfad.name} ist kein gültiges TOML ({err}). Die Stelle korrigieren und den Bau wiederholen.") from err


def pfad_einstellung(name: str) -> str:
    wert = einstellung(name)
    teile = Path(wert).parts
    if not wert or Path(wert).is_absolute() or ".." in teile:
        raise SprachFehler(f"{name} ist {wert!r}. Erwartet ist ein Pfad innerhalb von Healthchecks, etwa {VORGABEN[name]}.")
    return wert


def modulname(rel: str) -> str:
    return rel.removesuffix(".py").replace("/", ".").replace("\\", ".")


# --- Zerlegen und Ersetzen ---------------------------------------------------------


def stuecke(quelle: str) -> list[Stueck]:
    """Sichtbare Textstücke und sichtbare Attributwerte einer Vorlage, mit Lage in der Quelle."""
    ergebnis: list[Stueck] = []
    pos = 0
    for treffer in TOKEN.finditer(quelle):
        if treffer.start() > pos:
            ergebnis.append(Stueck("text", pos, treffer.start(), quelle[pos : treffer.start()]))
        roh = treffer.group(0)
        if roh.startswith("<") and not roh.startswith(("<!--", "</")) and not treffer.group("opak"):
            ergebnis.extend(_attribute(roh, treffer.start()))
        pos = treffer.end()
    if pos < len(quelle):
        ergebnis.append(Stueck("text", pos, len(quelle), quelle[pos:]))
    return ergebnis


def _attribute(tag: str, versatz: int) -> list[Stueck]:
    name = TAGNAME.match(tag)
    if not name:
        return []
    werte = {m.group("name").lower(): m for m in ATTRIBUT.finditer(tag)}
    sichtbar = set(SICHTBARE_ATTRIBUTE)
    typ = werte.get("type")
    if name.group(1).lower() == "input" and typ and typ.group("wert").strip().lower() in KNOPF_TYPEN:
        sichtbar.add("value")
    return [
        Stueck("attribut", versatz + m.start("wert"), versatz + m.end("wert"), m.group("wert"))
        for n, m in werte.items()
        if n in sichtbar
    ]


def text_anwenden(quelle: str, woerter: dict[str, str], datei: str) -> tuple[str, set[str], int]:
    """Ersetzt ganze Textstücke und sichtbare Attributwerte; liefert Quelle, genutzte Schlüssel, Zahl."""
    teile: list[str] = []
    pos = 0
    genutzt: set[str] = set()
    zahl = 0
    for stueck in stuecke(quelle):
        kern = norm(stueck.roh)
        if not kern or kern not in woerter:
            continue
        neu = woerter[kern]
        if stueck.art == "text":
            vorn = stueck.roh[: len(stueck.roh) - len(stueck.roh.lstrip())]
            hinten = stueck.roh[len(stueck.roh.rstrip()) :]
            neu = vorn + neu + hinten
        else:
            zeichen = quelle[stueck.start - 1]
            if zeichen in neu:
                raise SprachFehler(
                    f"{datei}: Der Ersatz für „{kern}“ enthält das Anführungszeichen {zeichen} seines Attributs. "
                    "Im Katalog &quot; oder das andere Anführungszeichen verwenden."
                )
        teile.append(quelle[pos : stueck.start])
        teile.append(neu)
        pos = stueck.ende
        genutzt.add(kern)
        zahl += 1
    teile.append(quelle[pos:])
    return "".join(teile), genutzt, zahl


def quelltext_anwenden(quelle: str, eintrag: Eintrag) -> tuple[str, int, bool]:
    """Ersetzt ein genaues Stück Quelle, wenn es so oft vorkommt wie verlangt."""
    gefunden = quelle.count(eintrag.en)
    passt = gefunden > 0 if eintrag.anzahl is None else gefunden == eintrag.anzahl
    return (quelle.replace(eintrag.en, eintrag.de) if passt else quelle), gefunden, passt


def traegt_text(kern: str) -> bool:
    """Ob ein Textstück Wörter trägt: ohne Template-Ausdrücke, Zeichenreferenzen und Wörter mit Ziffern."""
    woerter = [w for w in AUSDRUCK.sub(" ", kern).split() if not any(z.isdigit() for z in w)]
    return bool(BUCHSTABEN.search(" ".join(woerter)))


def englische_reste(original: str, ergebnis: str, gleich: set[str]) -> list[str]:
    """Textstücke des Ergebnisses, die unverändert aus dem Original stammen und Wörter tragen."""
    vorher = {norm(s.roh) for s in stuecke(original)}
    reste: list[str] = []
    for stueck in stuecke(ergebnis):
        kern = norm(stueck.roh)
        if kern in vorher and kern not in gleich and traegt_text(kern) and kern not in reste:
            reste.append(kern)
    return reste


# --- Katalog -------------------------------------------------------------------------


def lade_eintraege(pfad: Path) -> list[Eintrag]:
    daten = toml_laden(pfad)
    fremd = set(daten) - {"text", "quelltext"}
    if fremd:
        raise SprachFehler(f"{pfad.name}: unbekannte Abschnitte {', '.join(sorted(fremd))}. Erlaubt sind [[text]] und [[quelltext]].")
    eintraege: list[Eintrag] = []
    for art in ("quelltext", "text"):
        liste = daten.get(art, [])
        if not isinstance(liste, list):
            raise SprachFehler(f"{pfad.name}: {art} muss als [[{art}]] stehen.")
        for nr, roh in enumerate(liste, 1):
            herkunft = f"{pfad.name}, [[{art}]] Nr. {nr}"
            fremd = set(roh) - {"datei", "en", "de", "anzahl"}
            if fremd:
                raise SprachFehler(f"{herkunft}: unbekannte Schlüssel {', '.join(sorted(fremd))}. Erlaubt sind datei, en, de und anzahl.")
            for schluessel in ("datei", "en", "de"):
                wert = roh.get(schluessel)
                if not isinstance(wert, str) or not wert.strip():
                    raise SprachFehler(f"{herkunft}: {schluessel} fehlt oder ist leer. Jeder Eintrag braucht datei, en und de.")
            anzahl = roh.get("anzahl")
            if anzahl is not None:
                if art == "text":
                    raise SprachFehler(f"{herkunft}: anzahl gilt nur für [[quelltext]].")
                if not isinstance(anzahl, int) or isinstance(anzahl, bool) or anzahl < 1:
                    raise SprachFehler(f"{herkunft}: anzahl ist {anzahl!r}. Erwartet ist eine ganze Zahl ab 1.")
            if art == "quelltext" and roh["datei"] == "*":
                raise SprachFehler(f"{herkunft}: Quelltext-Einträge brauchen eine bestimmte Datei.")
            if art == "text":
                eintraege.append(Eintrag(art, roh["datei"], norm(roh["en"]), roh["de"].strip(), None, herkunft))
            else:
                eintraege.append(Eintrag(art, roh["datei"], roh["en"], roh["de"], anzahl, herkunft))
    return eintraege


def lade_katalog(ordner: Path) -> Katalog:
    if not ordner.is_dir():
        raise SprachFehler(f"Den Katalog-Ordner {ordner} gibt es nicht. WB_KATALOG auf einen Ordner in werkbank/ setzen, Vorgabe {VORGABEN['WB_KATALOG']}.")
    konfig_pfad = ordner / einstellung("WB_KATALOG_KONFIG")
    if not konfig_pfad.is_file():
        raise SprachFehler(f"{konfig_pfad} fehlt. Die Datei nennt Stand, Geltungsbereich und Zustandswörter des Katalogs.")
    konfig = toml_laden(konfig_pfad)
    try:
        stand = konfig["katalog"]["stand"]
        vorlagen = konfig["bereich"]["vorlagen"]
        ausnahmen = konfig["bereich"].get("ausnahmen", [])
        zustaende = konfig.get("zustaende", {})
    except (KeyError, TypeError, AttributeError) as err:
        raise SprachFehler(
            f"{konfig_pfad.name}: {err} fehlt. Erwartet sind [katalog] stand, [bereich] vorlagen und ausnahmen sowie [zustaende]."
        ) from err
    if not isinstance(stand, str) or not all(isinstance(m, str) for m in [*vorlagen, *ausnahmen]):
        raise SprachFehler(f"{konfig_pfad.name}: stand, vorlagen und ausnahmen sind Texte bzw. Listen von Texten.")
    if not all(isinstance(k, str) and isinstance(v, str) and v.strip() for k, v in zustaende.items()):
        raise SprachFehler(f"{konfig_pfad.name}: [zustaende] ordnet jedem Zustand ein Wort zu, etwa down = \"ausgefallen\".")
    eintraege: list[Eintrag] = []
    for pfad in sorted(ordner.glob("*.toml")):
        if pfad.name != konfig_pfad.name:
            eintraege.extend(lade_eintraege(pfad))
    gesehen: dict[tuple[str, str, str], str] = {}
    for e in eintraege:
        schluessel = (e.art, e.datei, e.en)
        if schluessel in gesehen:
            raise SprachFehler(f"{e.herkunft}: doppelt, dieselbe Stelle steht schon in {gesehen[schluessel]}. Einen der beiden Einträge entfernen.")
        gesehen[schluessel] = e.herkunft
    return Katalog(stand, list(vorlagen), list(ausnahmen), dict(zustaende), eintraege)


def bereich_dateien(wurzel: Path, katalog: Katalog) -> list[str]:
    gefunden: set[str] = set()
    for muster in katalog.vorlagen:
        for pfad in wurzel.glob(muster):
            rel = pfad.relative_to(wurzel).as_posix()
            if pfad.is_file() and not any(fnmatch.fnmatch(rel, a) for a in katalog.ausnahmen):
                gefunden.add(rel)
    return sorted(gefunden)


def uebersetzen(wurzel: Path, katalog: Katalog, schreiben: bool = True) -> dict:
    vorlagen = set(bereich_dateien(wurzel, katalog))
    global_text = {e.en: e for e in katalog.eintraege if e.art == "text" and e.datei == "*"}
    je_datei: dict[str, list[Eintrag]] = defaultdict(list)
    for e in katalog.eintraege:
        if e.datei != "*":
            je_datei[e.datei].append(e)
    genutzt_global: set[str] = set()
    ersetzt = 0
    englisch: list[dict] = []
    ohne: list[dict] = []
    for rel in sorted(vorlagen | set(je_datei)):
        pfad = wurzel / rel
        eigene = je_datei.get(rel, [])
        if not pfad.is_file():
            ohne.extend({"datei": rel, "art": e.art, "en": kurz(e.en), "grund": "Datei fehlt"} for e in eigene)
            continue
        original, crlf = lies(pfad)
        text = original
        for e in eigene:
            if e.art != "quelltext":
                continue
            text, gefunden, passt = quelltext_anwenden(text, e)
            if passt:
                ersetzt += gefunden
            else:
                grund = f"{gefunden}-mal gefunden" + (f", erwartet {e.anzahl}" if e.anzahl else "")
                ohne.append({"datei": rel, "art": "quelltext", "en": kurz(e.en), "grund": grund})
        eigene_text = {e.en: e for e in eigene if e.art == "text"}
        if rel in vorlagen:
            woerter = {k: e.de for k, e in global_text.items()}
            woerter.update({k: e.de for k, e in eigene_text.items()})
            text, genutzt, zahl = text_anwenden(text, woerter, rel)
            ersetzt += zahl
            genutzt_global |= genutzt - set(eigene_text)
            ohne.extend(
                {"datei": rel, "art": "text", "en": kurz(k), "grund": "nicht gefunden"} for k in eigene_text if k not in genutzt
            )
            gleich = {k for k, e in global_text.items() if e.en == e.de} | {k for k, e in eigene_text.items() if e.en == e.de}
            englisch.extend({"datei": rel, "text": rest} for rest in englische_reste(original, text, gleich))
        else:
            ohne.extend(
                {"datei": rel, "art": "text", "en": kurz(k), "grund": "Datei liegt außerhalb des Geltungsbereichs"}
                for k in eigene_text
            )
        if schreiben and text != original:
            schreibe(pfad, text, crlf)
    ohne.extend(
        {"datei": "*", "art": "text", "en": kurz(k), "grund": "in keiner Vorlage gefunden"}
        for k in global_text
        if k not in genutzt_global
    )
    return {"eintraege": len(katalog.eintraege), "ersetzt": ersetzt, "englisch": englisch, "ohne_fundstelle": ohne}


# --- Erweiterungen und Einstellungen -----------------------------------------------------


def erweitern(wurzel: Path, werkbank: Path) -> None:
    """Setzt Filter und Tags ein, die die Vorlagen der Werkbank in jeder Sprache brauchen."""
    pfad = werkbank / einstellung("WB_ERWEITERUNGEN")
    if not pfad.is_file():
        raise SprachFehler(f"{pfad} fehlt. Die Datei setzt Filter und Tags ein, die die Vorlagen der Werkbank nutzen.")
    for e in lade_eintraege(pfad):
        if e.art != "quelltext":
            raise SprachFehler(f"{e.herkunft}: Erweiterungen stehen als [[quelltext]] mit Anker (en) und Ersatz (de).")
        ziel = wurzel / e.datei
        if not ziel.is_file():
            raise SprachFehler(f"{e.herkunft}: {e.datei} fehlt. Healthchecks hat die Datei verschoben; den Eintrag in {pfad.name} anpassen.")
        text, crlf = lies(ziel)
        neu, gefunden, passt = quelltext_anwenden(text, e)
        if not passt:
            erwartet = f", erwartet {e.anzahl}-mal" if e.anzahl else ""
            raise SprachFehler(
                f"{e.herkunft}: Der Anker steht {gefunden}-mal in {e.datei}{erwartet}. "
                f"Healthchecks hat die Datei geändert; den Anker in {pfad.name} anpassen."
            )
        schreibe(ziel, neu, crlf)


def einstellungen_schreiben(wurzel: Path, werkbank: Path, sprache: str, zustaende: dict[str, str]) -> None:
    modul_rel, format_rel, local_rel = (pfad_einstellung(n) for n in PFAD_EINSTELLUNGEN)
    vorlage = werkbank / "django" / "werkbank_einstellungen.py"
    formate = werkbank / "django" / "werkbank_formate"
    for noetig in (vorlage, formate):
        if not noetig.exists():
            raise SprachFehler(f"{noetig} fehlt. Die Werkbank braucht die Dateien unter werkbank/django/.")
    text = (
        lies(vorlage)[0]
        .replace("@@WB_SPRACHE@@", sprache)
        .replace("@@WB_ZUSTAENDE@@", json.dumps(zustaende, ensure_ascii=False, sort_keys=True))
        .replace("@@WB_FORMATMODUL@@", modulname(format_rel))
    )
    ziel = wurzel / modul_rel
    ziel.parent.mkdir(parents=True, exist_ok=True)
    schreibe(ziel, text)
    formate_ziel = wurzel / format_rel
    if formate_ziel.exists():
        shutil.rmtree(formate_ziel)
    shutil.copytree(formate, formate_ziel, ignore=shutil.ignore_patterns("__pycache__"))
    local = wurzel / local_rel
    local.parent.mkdir(parents=True, exist_ok=True)
    schreibe(local, f"from {modulname(modul_rel)} import *  # noqa: F401,F403  Werkbank: Sprache und Mail-Einstellungen\n")


def bericht_schreiben(pfad: Path, abschnitt: str, inhalt: dict) -> None:
    daten = json.loads(lies(pfad)[0]) if pfad.is_file() else {}
    daten[abschnitt] = inhalt
    schreibe(pfad, json.dumps(daten, indent=2, ensure_ascii=False) + "\n")


def sprache_pruefen() -> str:
    sprache = einstellung("WB_SPRACHE")
    if sprache not in SPRACHEN:
        raise SprachFehler(
            f"WB_SPRACHE ist {sprache!r}. Erlaubt sind {' und '.join(SPRACHEN)}: de übersetzt, en lässt die Texte von Healthchecks stehen."
        )
    return sprache


def bauen(wurzel: Path, werkbank: Path, bericht: Path | None = None) -> dict:
    sprache = sprache_pruefen()
    for name in PFAD_EINSTELLUNGEN:
        pfad_einstellung(name)
    katalog = lade_katalog(werkbank / einstellung("WB_KATALOG"))
    erweitern(wurzel, werkbank)
    einstellungen_schreiben(wurzel, werkbank, sprache, katalog.zustaende if sprache == "de" else {})
    ergebnis: dict = {"sprache": sprache, "stand": katalog.stand}
    if sprache == "de":
        ergebnis.update(uebersetzen(wurzel, katalog))
    else:
        ergebnis.update({"eintraege": len(katalog.eintraege), "ersetzt": 0, "englisch": [], "ohne_fundstelle": []})
    if bericht:
        bericht_schreiben(bericht, "uebersetzung", ergebnis)
    return ergebnis


def inventur(wurzel: Path, werkbank: Path, muster: str = "*", global_ab: int = 0) -> str:
    """Englische Textstücke ohne Eintrag als TOML-Gerüst; die Dateien bleiben unverändert."""
    katalog = lade_katalog(werkbank / einstellung("WB_KATALOG"))
    reste = [r for r in uebersetzen(wurzel, katalog, schreiben=False)["englisch"] if fnmatch.fnmatch(r["datei"], muster)]
    zaehler = Counter(r["text"] for r in reste)
    global_texte = sorted(t for t, n in zaehler.items() if global_ab and n >= global_ab)
    zeilen = ["# Inventur: englische Textstücke ohne Eintrag. de ausfüllen und in den Katalog übernehmen.", ""]
    for t in global_texte:
        zeilen += ["[[text]]", 'datei = "*"', f"en = {json.dumps(t, ensure_ascii=False)}", 'de = ""', ""]
    for r in reste:
        if r["text"] not in global_texte:
            zeilen += ["[[text]]", f"datei = {json.dumps(r['datei'])}", f"en = {json.dumps(r['text'], ensure_ascii=False)}", 'de = ""', ""]
    return "\n".join(zeilen)


def main(argv: list[str] | None = None) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description="Übersetzung von Healthchecks beim Bau.")
    unter = p.add_subparsers(dest="befehl", required=True)
    b = unter.add_parser("bauen", help="Erweiterungen und Einstellungen einsetzen, bei WB_SPRACHE=de den Katalog anwenden")
    i = unter.add_parser("inventur", help="englische Textstücke ohne Eintrag als TOML-Gerüst ausgeben")
    for u in (b, i):
        u.add_argument("--wurzel", required=True, help="Ordner von Healthchecks, etwa /opt/healthchecks")
        u.add_argument("--werkbank", required=True, help="Ordner werkbank/ mit Katalog und Erweiterungen")
    b.add_argument("--bericht", help="Bericht als Abschnitt uebersetzung in diese JSON-Datei schreiben")
    i.add_argument("--datei", default="*", help="nur Dateien nach diesem Muster, etwa 'templates/front/*'")
    i.add_argument("--global-ab", type=int, default=0, help='Textstücke aus so vielen Dateien als datei = "*" vorschlagen; 0 schaltet das ab')
    args = p.parse_args(argv)
    try:
        if args.befehl == "bauen":
            e = bauen(Path(args.wurzel), Path(args.werkbank), Path(args.bericht) if args.bericht else None)
            if e["sprache"] == "de":
                print(
                    f"Übersetzung: {e['eintraege']} Einträge, {e['ersetzt']} Ersetzungen, "
                    f"{len(e['englisch'])} Textstücke englisch, {len(e['ohne_fundstelle'])} Einträge ohne Fundstelle."
                )
            else:
                print("WB_SPRACHE=en: Katalog übersprungen; Erweiterungen und Einstellungen eingesetzt.")
        else:
            if args.global_ab < 0:
                raise SprachFehler(f"--global-ab ist {args.global_ab}. Erlaubt sind 0 (aus) oder eine Zahl ab 1.")
            print(inventur(Path(args.wurzel), Path(args.werkbank), args.datei, args.global_ab))
    except SprachFehler as err:
        print(f"Abbruch: {err}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

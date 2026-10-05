import sys
from pathlib import Path

import pytest

WURZEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WURZEL / "werkbank"))
import farben  # noqa: E402

LEER = farben.Zuordnung({})


def ableiten(css, zuordnung=LEER, merkmal="body.dark"):
    return farben.ableiten(css, zuordnung, "x.css", merkmal)


def text(css, zuordnung=LEER):
    return "\n".join(ableiten(css, zuordnung).zeilen)


@pytest.mark.parametrize("roh, erwartet", [
    ("#FFF", "#ffffff"),
    ("#22BC66", "#22bc66"),
    ("white", "#ffffff"),
    ("rgb(34, 188, 102)", "#22bc66"),
    ("rgba(0, 0, 0, 0.075)", "rgba(0,0,0,0.075)"),
    ("rgba(0,0,0,1)", "#000000"),
    ("#aaaaaa99", "#aaaaaa99"),
    ("#aaaaaaff", "#aaaaaa"),
    ("hsl(0, 0%, 100%)", "#ffffff"),
    ("hsl(120, 100%, 25%)", "#008000"),
])
def test_normalise(roh, erwartet):
    assert farben.normalise(roh) == erwartet


@pytest.mark.parametrize("farbe, art, dunkel, rolle", [
    ("#22bc66", "background", False, "var(--bc-lime)"),
    ("#dff0d8", "background", False, "var(--wb-ok-tint)"),
    ("#d9534f", "background", False, "var(--bc-pink)"),
    ("#a94442", "text", False, "var(--bc-bad-text)"),
    ("#f0ad4e", "background", False, "var(--bc-yellow)"),
    ("#8a6d3b", "text", False, "var(--bc-warn-text)"),
    ("#5bc0de", "background", False, "var(--bc-cyan)"),
    ("#0091ea", "border", False, "var(--bc-focus)"),
    ("#ffffff", "background", False, "var(--bc-surface)"),
    ("#ffffff", "text", False, "var(--bc-white)"),
    ("#f5f5f5", "background", False, "var(--bc-head)"),
    ("#dddddd", "border", False, "var(--bc-rule)"),
    ("#333333", "text", False, "var(--bc-text)"),
    ("#999999", "text", False, "var(--bc-text-quiet)"),
    ("#000000", "background", False, "var(--bc-ink)"),
    ("rgba(0,0,0,0.075)", "shadow", False, "var(--wb-schatten)"),
    ("rgba(102,175,233,0.2)", "shadow", False, "var(--wb-fokus-hof)"),
    ("rgba(0,0,0,0.15)", "border", False, "var(--bc-rule)"),
    ("rgba(0,0,0,0)", "border", False, "transparent"),
    ("#f8f8f2", "text", True, "var(--bc-text-loud)"),
    ("#29292c", "background", True, "var(--bc-hover)"),
    ("#ae81ff", "text", True, "var(--bc-link)"),
])
def test_auto_rolle(farbe, art, dunkel, rolle):
    assert farben.auto_rolle(farbe, art, dunkel) == rolle


def test_helle_schrift_auf_kraeftiger_flaeche_wird_tinte():
    zeilen = text(".btn-primary { color: #fff; background-color: #22bc66; border-color: #1ea65a }")
    assert "color: var(--bc-ink);" in zeilen
    assert "background-color: var(--bc-lime);" in zeilen
    assert "border-color: var(--bc-ok-deep);" in zeilen


def test_weisse_schrift_auf_pink_bleibt_weiss():
    assert "color: var(--bc-white);" in text(".btn-danger { color: #fff; background-color: #d9534f }")


def test_ausnahme_je_selektor_geht_vor():
    z = farben.Zuordnung({"selektoren": {".btn-primary": {"text": {"#fff": "var(--bc-text-loud)"}}}})
    assert "color: var(--bc-text-loud);" in text(".btn-primary { color: #fff; background-color: #22bc66 }", z)


def test_eintrag_geht_vor_automatik_und_automatik_steht_im_bericht():
    z = farben.Zuordnung({"farben": {"#22bc66": {"text": "var(--bc-text)"}}})
    erg = ableiten(".a { color: #22bc66 } .b { color: #123456 }", z)
    assert ".a {\n\tcolor: var(--bc-text);\n}" in "\n".join(erg.zeilen)
    assert [f.farbe for f in erg.funde] == ["#123456"]
    assert erg.funde[0].datei == "x.css"
    assert erg.funde[0].rolle == "var(--bc-link)"


def test_dunkle_regeln_nutzen_ihren_eigenen_teil():
    z = farben.Zuordnung({"farben": {"#333333": {"text": "var(--bc-text)"}},
                          "farben_dunkel": {"#333333": {"text": "var(--bc-text-quiet)"}}})
    zeilen = text(".a { color: #333 } body.dark .a { color: #333 }", z)
    assert ".a {\n\tcolor: var(--bc-text);\n}" in zeilen
    assert "body.dark .a {\n\tcolor: var(--bc-text-quiet);\n}" in zeilen


def test_var_werte_und_reihenfolge_bleiben():
    zeilen = text(".x { color: #333 } .x { color: var(--text-color) }")
    assert zeilen.index("var(--bc-text)") < zeilen.index("var(--text-color)")


def test_farbwoerter_in_var_namen_zaehlen_nicht():
    erg = ableiten(".x { color: var(--btn-red) }")
    assert erg.funde == []
    assert "color: var(--btn-red);" in "\n".join(erg.zeilen)


def test_kurzformen_werden_langformen():
    zeilen = text(".x { border: 1px solid #ddd; background: #fff url(a.png) no-repeat; outline: 0 }")
    assert "border-color: var(--bc-rule);" in zeilen
    assert "background-color: var(--bc-surface);" in zeilen
    assert "url(" not in zeilen
    assert "outline" not in zeilen


def test_verlauf_behaelt_bildschichten():
    zeilen = text(".x { background-image: url(a.png), linear-gradient(#fff, #f5f5f5) }")
    assert "background-image: url(a.png), linear-gradient(var(--bc-surface), var(--bc-head));" in zeilen


def test_important_media_und_font_face():
    zeilen = text("@charset \"UTF-8\"; @font-face { font-family: x; src: url(a.woff2) } "
                  "@media (min-width: 768px) { .x { color: #fff !important } }")
    assert "@media (min-width: 768px) {" in zeilen
    assert "\t\tcolor: var(--bc-white) !important;" in zeilen
    assert "font-face" not in zeilen


def test_keyword_werte_kommen_mit():
    zeilen = text(".x { color: inherit; box-shadow: none; background: none }")
    assert "color: inherit;" in zeilen
    assert "box-shadow: none;" in zeilen
    assert "background-color: transparent;" in zeilen
    assert "background-image: none;" in zeilen


def test_dunkle_regeln_erkennen():
    assert farben.ist_dunkel("body.dark .highlight .k", "body.dark")
    assert not farben.ist_dunkel(".highlight .k", "body.dark")
    assert not farben.ist_dunkel("body.dark .a, .b", "body.dark")
    assert not farben.ist_dunkel("body.darker .a", "body.dark")
    assert farben.ist_dunkel("html.nacht .a", "html.nacht")


def test_zuordnung_meldet_kaputtes_json(tmp_path):
    datei = tmp_path / "farben.json"
    datei.write_text("{", encoding="utf-8")
    with pytest.raises(farben.FarbFehler, match="kein gültiges JSON"):
        farben.Zuordnung.lade(datei)


def test_unlesbare_farbe_meldet_sich():
    with pytest.raises(farben.FarbFehler, match="kann farben.py nicht lesen"):
        farben.rgba("lab(50% 40 59)")

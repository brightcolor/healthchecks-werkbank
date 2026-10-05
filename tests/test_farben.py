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
    # Werte außerhalb des Bereichs kappt der Browser; tom-select liefert etwa 118,6 % Helligkeit.
    ("hsl(0, 0%, 118.6274509804%)", "#ffffff"),
    ("hsl(480, 100%, 25%)", "#008000"),
    ("rgb(300, -5, 128)", "#ff0080"),
    ("rgba(0, 0, 0, 1.5)", "#000000"),
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


TOKENS = (WURZEL / "vendor/hausschrift/assets/css/bc-tokens.css").read_text(encoding="utf-8")


def test_tokens_auf_root_body_und_dunkel():
    t = farben.tokens_fuer_healthchecks(TOKENS, "body.dark")
    assert ":root,\nbody {" in t
    assert "--bc-primary: var(--bc-yellow);" in t
    # Auch html bekommt die dunklen Tokens, damit die Fläche unter dem Inhalt dunkel ist.
    assert t.index("body.dark,\n:root:has(body.dark) {") < t.index("--bc-surface: #141415;")
    assert "html.nacht,\n:root:has(html.nacht) {" in farben.tokens_fuer_healthchecks(TOKENS, "html.nacht")


def test_rem_werte_der_hausschrift_werden_px():
    # Bootstrap 3 setzt html auf 10 px; die Hausschrift meint rem mit 16 px.
    assert farben.rem_zu_px("a: .9375rem; b: clamp(2.6rem, 1.5rem + 4.4vw, 5.2rem)", 16) == \
        "a: 15px; b: clamp(41.6px, 24px + 4.4vw, 83.2px)"
    assert farben.rem_zu_px("a: 2rem; remove: 1em", 10) == "a: 20px; remove: 1em"


def test_tokens_in_px():
    t = farben.tokens_fuer_healthchecks(TOKENS, "body.dark")
    assert "--bc-size-body: 15px;" in t
    assert "--bc-size-h1: 38px;" in t
    assert "rem" not in t.replace("remain", "")


def test_rem_basis_als_einstellung(tmp_path, monkeypatch):
    monkeypatch.setenv("WB_REM_BASIS", "10")
    hc = mini_healthchecks(tmp_path / "hc")
    werkbank = mini_werkbank(tmp_path / "werkbank")
    css, _, _ = farben.bauen(hc, WURZEL / "vendor/hausschrift", werkbank, "x")
    assert "--bc-size-body: 9.375px;" in css
    monkeypatch.setenv("WB_REM_BASIS", "null")
    with pytest.raises(farben.FarbFehler, match="WB_REM_BASIS"):
        farben.bauen(hc, WURZEL / "vendor/hausschrift", werkbank, "x")


def test_tokens_ohne_werkbank_block_melden_sich():
    with pytest.raises(farben.FarbFehler, match="fehlen die Blöcke"):
        farben.token_bloecke(":root { --bc-ink: #111111; }")


def test_aufloesen_folgt_verweisen():
    werte = {"--a": "var(--b)", "--b": "#fed329"}
    assert farben.aufloesen("--a", werte) == "#fed329"
    with pytest.raises(farben.FarbFehler, match="gibt es in den Tokens nicht"):
        farben.aufloesen("--fehlt", werte)


def test_neue_und_entfallene_variablen():
    oben = ":root { --a: #fff; --b: #000 } body.dark { --a: #111; --c: #222 }"
    unsere = ":root, body, body.dark { --a: var(--bc-text); --alt: var(--bc-text) }"
    neu, entfallen = farben.pruefe_variablen(oben, unsere, "body.dark")
    assert neu == {"hell": ["--b"], "dunkel": ["--c"]}
    assert entfallen == ["--alt"]


def test_variablen_css_deckt_healthchecks_ab():
    quellen = sorted((WURZEL / ".upstream").glob("v*/static/css/variables.css"))
    if not quellen:
        pytest.skip("Keine Quelle von Healthchecks unter .upstream/.")
    unsere = (WURZEL / "werkbank/variablen.css").read_text(encoding="utf-8")
    neu, entfallen = farben.pruefe_variablen(quellen[-1].read_text(encoding="utf-8"), unsere, "body.dark")
    assert neu == {"hell": [], "dunkel": []}
    assert entfallen == []


def test_stylesheets_in_reihenfolge():
    base = ("{% compress css %}<link href=\"{% static 'css/a.css' %}\"><link href=\"{% static 'css/b.css' %}\">"
            "{% endcompress %}{% compress js %}<script src=\"{% static 'js/x.js' %}\"></script>{% endcompress %}")
    assert farben.stylesheets(base) == ["css/a.css", "css/b.css"]


def test_stylesheets_ohne_compress_block_melden_sich():
    with pytest.raises(farben.FarbFehler, match="compress css"):
        farben.stylesheets("<html></html>")


def mini_healthchecks(ordner, variablen=":root { --text-color: #333 } body.dark { --text-color: #eee }"):
    (ordner / "templates").mkdir(parents=True)
    (ordner / "static/css").mkdir(parents=True)
    (ordner / "templates/base.html").write_text(
        "{% compress css %}<link href=\"{% static 'css/variables.css' %}\">"
        "<link href=\"{% static 'css/base.css' %}\">{% endcompress %}", encoding="utf-8")
    (ordner / "static/css/variables.css").write_text(variablen, encoding="utf-8")
    (ordner / "static/css/base.css").write_text(
        ".status.ic-up { color: #22bc66 } .btn-primary { color: #fff; background-color: #22bc66 }",
        encoding="utf-8")
    return ordner


def mini_werkbank(ordner, variablen_css=":root,\nbody,\nbody.dark {\n\t--text-color: var(--bc-text);\n}\n"):
    ordner.mkdir(parents=True)
    for name in ("rollen.css", "stil.css"):
        (ordner / name).write_text((WURZEL / "werkbank" / name).read_text(encoding="utf-8"), encoding="utf-8")
    (ordner / "variablen.css").write_text(variablen_css, encoding="utf-8")
    (ordner / "farben.json").write_text("{}", encoding="utf-8")
    return ordner


def test_bauen_setzt_alles_in_reihenfolge(tmp_path):
    hc = mini_healthchecks(tmp_path / "hc")
    werkbank = mini_werkbank(tmp_path / "werkbank")
    css, farben_css, bericht = farben.bauen(hc, WURZEL / "vendor/hausschrift", werkbank, "4.4-wb1.0.0")
    marken = ['url("fonts/anton-400.woff2")', ":root,\nbody {", "--wb-ok-tint:", "--text-color: var(--bc-text)",
              "/* css/base.css */", ".bc-rail {", "/* healthchecks-werkbank: Stilschicht"]
    stellen = [css.index(m) for m in marken]
    assert stellen == sorted(stellen)
    assert "body.dark .bc-mode" in css
    assert '[data-theme="dark"]' not in css
    assert "/* css/variables.css */" not in css
    assert bericht["stylesheets"] == 1
    assert bericht["deklarationen"] == 3
    assert {(f["farbe"], f["art"]) for f in bericht["automatisch"]} == {("#22bc66", "text"), ("#22bc66", "background")}
    assert farben_css.startswith("/* healthchecks-werkbank 4.4-wb1.0.0.")


def test_bauen_bricht_bei_neuer_variable_ab(tmp_path):
    hc = mini_healthchecks(tmp_path / "hc", ":root { --text-color: #333; --neu-farbe: #f00 }")
    werkbank = mini_werkbank(tmp_path / "werkbank")
    with pytest.raises(farben.FarbFehler, match="--neu-farbe"):
        farben.bauen(hc, WURZEL / "vendor/hausschrift", werkbank, "4.4-wb1.0.0")


def test_bauen_mit_anderem_dunklen_selektor(tmp_path, monkeypatch):
    monkeypatch.setenv("WB_DUNKEL_SELEKTOR", "html.nacht")
    hc = mini_healthchecks(tmp_path / "hc", ":root { --text-color: #333 } html.nacht { --text-color: #eee }")
    werkbank = mini_werkbank(tmp_path / "werkbank")
    css, _, _ = farben.bauen(hc, WURZEL / "vendor/hausschrift", werkbank, "x")
    assert "html.nacht .bc-mode" in css
    assert "html.nacht,\n:root:has(html.nacht) {" in css


def test_schreibe_legt_beide_dateien_ab(tmp_path):
    farben.schreibe(tmp_path, "A", "B")
    assert (tmp_path / "static/bc/werkbank.css").read_text(encoding="utf-8") == "A"
    assert (tmp_path / "static/bc/farben.css").read_text(encoding="utf-8") == "B"


def test_vorschlag_behaelt_vorhandene_eintraege(tmp_path):
    hc = mini_healthchecks(tmp_path / "hc")
    alt = tmp_path / "alt.json"
    alt.write_text('{"selektoren": {".x": {"text": {"#fff": "var(--bc-ink)"}}},'
                   ' "farben": {"#22bc66": {"text": "var(--bc-text)"}}}', encoding="utf-8")
    daten = farben.vorschlag(hc, alt)
    assert daten["selektoren"] == {".x": {"text": {"#fff": "var(--bc-ink)"}}}
    assert daten["farben"]["#22bc66"]["text"] == "var(--bc-text)"
    assert daten["farben"]["#22bc66"]["background"] == "var(--bc-lime)"
    assert daten["farben"]["#ffffff"]["text"] == "var(--bc-white)"


def test_echte_ableitung_ohne_automatik():
    quellen = sorted(p.parents[2] for p in (WURZEL / ".upstream").glob("v*/static/css/variables.css"))
    if not quellen:
        pytest.skip("Keine Quelle von Healthchecks unter .upstream/.")
    css, _, bericht = farben.bauen(quellen[-1], WURZEL / "vendor/hausschrift", WURZEL / "werkbank", "test")
    assert bericht["automatisch"] == [], bericht["automatisch"][:5]
    assert bericht["deklarationen"] > 500
    assert "var(--bc-lime)" in css


def test_kommandozeile_bauen_meldet_fehlende_wurzel(tmp_path, capsys):
    rc = farben.main(["bauen", "--wurzel", str(tmp_path / "fehlt"), "--hausschrift",
                      str(WURZEL / "vendor/hausschrift"), "--werkbank", str(WURZEL / "werkbank"), "--fassung", "x"])
    assert rc == 1
    assert "Abbruch:" in capsys.readouterr().err

import sys
from pathlib import Path

import pytest

WURZEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WURZEL / "werkbank"))
import einbau  # noqa: E402

PLATZ = "@@WERKBANK_FASSUNG@@"
BASIS = """<!DOCTYPE html>{% load compress static hc_extras %}
<html><head>
{% compress css %}<link rel="stylesheet" href="x.css">{% endcompress %}
</head>
<body>
    <nav class="navbar navbar-default">menu</nav>
</body></html>
"""
LEISTE = '<nav class="bc-rail">Werkbank ' + PLATZ + "</nav>\n"


def plan(**anders):
    daten = {
        "vorlage": "templates/base.html",
        "einfuegungen": (
            einbau.Einfuegung("</head>", f'<link rel="stylesheet" href="w.css?v={PLATZ}">'),
            einbau.Einfuegung('<nav class="navbar navbar-default">', '{% include "bc/leiste.html" %}'),
        ),
        "platzhalter": PLATZ,
        "fassung_in": ("templates/base.html", "templates/bc/leiste.html"),
    }
    daten.update(anders)
    return einbau.Plan(**daten)


@pytest.fixture
def wurzel(tmp_path):
    (tmp_path / "templates" / "bc").mkdir(parents=True)
    (tmp_path / "templates" / "base.html").write_text(BASIS, encoding="utf-8")
    (tmp_path / "templates" / "bc" / "leiste.html").write_text(LEISTE, encoding="utf-8")
    return tmp_path


def test_setzt_zeilen_direkt_vor_die_anker(wurzel):
    einbau.einbauen(wurzel, plan(), "4.4-wb1.0.0")
    text = (wurzel / "templates/base.html").read_text(encoding="utf-8")
    assert '<link rel="stylesheet" href="w.css?v=4.4-wb1.0.0">\n</head>' in text
    assert '{% include "bc/leiste.html" %}\n<nav class="navbar navbar-default">' in text


def test_setzt_fassung_in_alle_genannten_dateien(wurzel):
    geaendert = einbau.einbauen(wurzel, plan(), "4.4-wb1.0.0")
    assert geaendert == ["templates/base.html", "templates/bc/leiste.html"]
    assert "Werkbank 4.4-wb1.0.0" in (wurzel / "templates/bc/leiste.html").read_text(encoding="utf-8")


def test_fehlender_anker_bricht_ab_und_nennt_ihn(wurzel):
    p = plan(einfuegungen=(einbau.Einfuegung("<footer>", "x"),))
    with pytest.raises(einbau.EinbauFehler, match=r"'<footer>' steht 0-mal in templates/base.html"):
        einbau.einbauen(wurzel, p, "4.4-wb1.0.0")


def test_doppelter_anker_bricht_ab(wurzel):
    (wurzel / "templates/base.html").write_text(BASIS + "</head>", encoding="utf-8")
    with pytest.raises(einbau.EinbauFehler, match="steht 2-mal"):
        einbau.einbauen(wurzel, plan(), "4.4-wb1.0.0")


def test_zweiter_lauf_bricht_ab(wurzel):
    einbau.einbauen(wurzel, plan(), "4.4-wb1.0.0")
    (wurzel / "templates/bc/leiste.html").write_text(LEISTE, encoding="utf-8")
    with pytest.raises(einbau.EinbauFehler, match="bereits"):
        einbau.einbauen(wurzel, plan(), "4.4-wb1.0.1")


def test_bei_fehler_bleibt_jede_datei_unveraendert(wurzel):
    (wurzel / "templates/bc/leiste.html").write_text("ohne Platzhalter", encoding="utf-8")
    with pytest.raises(einbau.EinbauFehler, match="fehlt der Platzhalter"):
        einbau.einbauen(wurzel, plan(), "4.4-wb1.0.0")
    assert (wurzel / "templates/base.html").read_text(encoding="utf-8") == BASIS


@pytest.mark.parametrize("fassung", ["", "4.4 wb1", "-4.4", "ä1", "x" * 65])
def test_ungueltige_fassung(wurzel, fassung):
    with pytest.raises(einbau.EinbauFehler, match="taugt nicht als Image-Tag"):
        einbau.einbauen(wurzel, plan(), fassung)


def test_anderer_plan_mit_anderen_ankern(wurzel):
    p = plan(
        einfuegungen=(einbau.Einfuegung("<body>", "<!-- vorn -->"),),
        platzhalter="%%F%%",
        fassung_in=("templates/bc/leiste.html",),
    )
    (wurzel / "templates/bc/leiste.html").write_text("F=%%F%%", encoding="utf-8")
    einbau.einbauen(wurzel, p, "9.9-wb2.0.0")
    assert "<!-- vorn -->\n<body>" in (wurzel / "templates/base.html").read_text(encoding="utf-8")
    assert (wurzel / "templates/bc/leiste.html").read_text(encoding="utf-8") == "F=9.9-wb2.0.0"


def test_lade_plan_meldet_kaputtes_json(tmp_path):
    datei = tmp_path / "plan.json"
    datei.write_text("{", encoding="utf-8")
    with pytest.raises(einbau.EinbauFehler, match="kein gültiges JSON"):
        einbau.lade_plan(datei)


def test_lade_plan_meldet_fehlende_felder(tmp_path):
    datei = tmp_path / "plan.json"
    datei.write_text('{"vorlage": "x"}', encoding="utf-8")
    with pytest.raises(einbau.EinbauFehler, match="braucht die Felder"):
        einbau.lade_plan(datei)


def test_mitgelieferter_plan_passt_auf_die_echte_vorlage(tmp_path):
    vorlagen = sorted((WURZEL / ".upstream").glob("v*/templates/base.html"))
    if not vorlagen:
        pytest.skip("Keine Vorlage von Healthchecks unter .upstream/; tools/dev.py vorbereiten legt sie an.")
    (tmp_path / "templates" / "bc").mkdir(parents=True)
    (tmp_path / "templates" / "base.html").write_text(vorlagen[-1].read_text(encoding="utf-8"), encoding="utf-8")
    (tmp_path / "templates" / "bc" / "leiste.html").write_text(PLATZ, encoding="utf-8")
    einbau.einbauen(tmp_path, einbau.lade_plan(einbau.PLAN_VORGABE), "4.4-wb1.0.0")
    text = (tmp_path / "templates" / "base.html").read_text(encoding="utf-8")
    assert "{% static 'bc/werkbank.css' %}?v=4.4-wb1.0.0" in text
    assert text.index('{% include "bc/leiste.html" %}') < text.index('<nav class="navbar navbar-default">')


def test_mitgelieferte_leiste_traegt_den_platzhalter():
    text = (WURZEL / "werkbank/templates/bc/leiste.html").read_text(encoding="utf-8")
    assert PLATZ in text


def test_kommandozeile_meldet_fehler_mit_exit_1(wurzel, capsys):
    rc = einbau.main(["--wurzel", str(wurzel), "--fassung", "kaputte fassung"])
    assert rc == 1
    assert "Abbruch:" in capsys.readouterr().err

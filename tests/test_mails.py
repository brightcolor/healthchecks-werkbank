import hashlib
import json
import sys
import tomllib
from pathlib import Path

import pytest

WURZEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WURZEL / "werkbank"))
import mails  # noqa: E402

ORIGINAL = "{% block title %}{% endblock %}{% block content %}{% endblock %}{% if button_text %}{{ button_url }}{% endif %}"
EIGENES = ('{% block title %}{% endblock %}{% block content %}{% endblock %}{% block grund %}x{% endblock %}'
           '{% if button_text %}<a href="{{ button_url }}">{{ button_text }}</a>{% endif %}')


def summe(text):
    return hashlib.sha256(text.replace("\r\n", "\n").encode("utf-8")).hexdigest()


def aufbau(tmp_path, original=ORIGINAL, eigenes=EIGENES, pruefsumme=None, layout="templates/emails/base.html"):
    wurzel, werkbank, hausschrift = tmp_path / "hc", tmp_path / "werkbank", tmp_path / "hausschrift"
    (wurzel / layout).parent.mkdir(parents=True)
    (wurzel / layout).write_bytes(original.encode("utf-8"))
    (werkbank / "mails").mkdir(parents=True)
    (werkbank / "mails" / "base.html").write_bytes(eigenes.encode("utf-8"))
    (werkbank / "mails" / "original.sha256").write_bytes(f"{pruefsumme or summe(original)}  base.html\n".encode())
    logo = hausschrift / "assets" / "logo" / "png" / "bc-logo-light-noclaim.png"
    logo.parent.mkdir(parents=True)
    logo.write_bytes(b"PNG")
    return wurzel, werkbank, hausschrift


def test_layout_und_logo_werden_eingesetzt(tmp_path):
    wurzel, werkbank, hausschrift = aufbau(tmp_path)
    assert mails.einsetzen(wurzel, werkbank, hausschrift) == []
    assert (wurzel / "templates/emails/base.html").read_bytes().decode() == EIGENES
    assert (wurzel / "static/bc/logo/bc-logo-light-noclaim.png").read_bytes() == b"PNG"


@pytest.mark.parametrize("zusatz, meldung", [
    ("{% block unsub %}{% endblock %}", "die Blöcke unsub"),
    ("{{ unsub_link }}", "die Variablen unsub_link"),
    ("{% if not footer_text %}{% endif %}", "die Variablen footer_text"),
])
def test_fehlendes_bricht_ab(tmp_path, zusatz, meldung):
    wurzel, werkbank, hausschrift = aufbau(tmp_path, original=ORIGINAL + zusatz)
    with pytest.raises(mails.MailFehler, match=meldung):
        mails.einsetzen(wurzel, werkbank, hausschrift)
    assert (wurzel / "templates/emails/base.html").read_bytes().decode() == ORIGINAL + zusatz


def test_abweichende_pruefsumme_ergibt_hinweis(tmp_path):
    wurzel, werkbank, hausschrift = aufbau(tmp_path, pruefsumme="0" * 64)
    hinweise = mails.einsetzen(wurzel, werkbank, hausschrift)
    assert len(hinweise) == 1
    assert "Healthchecks hat sein Mail-Layout geändert" in hinweise[0]


def test_pruefsumme_gilt_fuer_lf(tmp_path):
    wurzel, werkbank, hausschrift = aufbau(tmp_path, original=ORIGINAL.replace("}{", "}\r\n{"),
                                           pruefsumme=summe(ORIGINAL.replace("}{", "}\n{")))
    assert mails.einsetzen(wurzel, werkbank, hausschrift) == []


def test_andere_ziele(tmp_path, monkeypatch):
    monkeypatch.setenv("WB_MAIL_LAYOUT", "templates/mail/layout.html")
    monkeypatch.setenv("WB_MAIL_LOGO_ZIEL", "static/eigen/logo.png")
    wurzel, werkbank, hausschrift = aufbau(tmp_path, layout="templates/mail/layout.html")
    mails.einsetzen(wurzel, werkbank, hausschrift)
    assert (wurzel / "templates/mail/layout.html").read_bytes().decode() == EIGENES
    assert (wurzel / "static/eigen/logo.png").is_file()


def test_ungueltiger_pfad(tmp_path, monkeypatch):
    monkeypatch.setenv("WB_MAIL_LAYOUT", "../draussen.html")
    wurzel, werkbank, hausschrift = aufbau(tmp_path)
    with pytest.raises(mails.MailFehler, match="WB_MAIL_LAYOUT ist '../draussen.html'"):
        mails.einsetzen(wurzel, werkbank, hausschrift)


def test_bericht_ueber_die_kommandozeile(tmp_path):
    wurzel, werkbank, hausschrift = aufbau(tmp_path, pruefsumme="0" * 64)
    bericht = tmp_path / "bericht.json"
    bericht.write_bytes(b'{"fassung": "x"}')
    rc = mails.main(["einsetzen", "--wurzel", str(wurzel), "--werkbank", str(werkbank),
                     "--hausschrift", str(hausschrift), "--bericht", str(bericht)])
    daten = json.loads(bericht.read_text(encoding="utf-8"))
    assert rc == 0
    assert daten["fassung"] == "x"
    assert len(daten["mails"]["hinweise"]) == 1


def test_werkbank_layout_passt_zur_standversion():
    stand = tomllib.loads((WURZEL / "werkbank/deutsch/katalog.toml").read_text(encoding="utf-8"))["katalog"]["stand"]
    original_pfad = WURZEL / ".upstream" / stand / "templates" / "emails" / "base.html"
    if not original_pfad.is_file():
        pytest.skip(f"Keine Quelle von Healthchecks {stand} unter .upstream/.")
    original = mails.text(original_pfad)
    eigenes = mails.text(WURZEL / "werkbank" / "mails" / "base.html")
    assert mails.bloecke(original) <= mails.bloecke(eigenes)
    assert mails.variablen(original) <= mails.variablen(eigenes)
    assert summe(original) == (WURZEL / "werkbank/mails/original.sha256").read_text(encoding="utf-8").split()[0]

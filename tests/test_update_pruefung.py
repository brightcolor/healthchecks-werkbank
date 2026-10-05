"""Prüfung im Container aus deploy/hc-werkbank-update gegen einen lokalen Webserver.

Das Skript bettet das Prüfprogramm als Python-Heredoc ein; der Test zieht es heraus
und lässt es mit denselben Argumenten laufen, die das Skript übergibt.
"""
import os
import re
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

WURZEL = Path(__file__).resolve().parent.parent
SKRIPT = (WURZEL / "deploy" / "hc-werkbank-update").read_text(encoding="utf-8")
PRUEFUNG = re.search(r'python - "\$APP_PORT".*?<<\'PY\'\n(.*?)\nPY\n', SKRIPT, re.S).group(1)
MERKMAL = "bc/werkbank"

SEITEN = {
    # Django liefert auch die schlichte Statusantwort als text/html aus.
    "/api/v3/status/": (200, "text/html; charset=utf-8", "OK"),
    "/accounts/login/": (200, "text/html; charset=utf-8",
                         f'<!doctype html><html><head><link href="/static/{MERKMAL}.css"></head></html>'),
    "/ohne-werkbank/": (200, "text/html; charset=utf-8", "<!DOCTYPE html><HTML><body>Healthchecks</body></HTML>"),
    "/kaputt/": (500, "text/html; charset=utf-8", "<html><body>Server Error</body></html>"),
}


class Antwort(BaseHTTPRequestHandler):
    def do_GET(self):
        pfad = self.path.removeprefix(self.server.praefix)
        code, art, text = SEITEN.get(pfad, (404, "text/plain", "fehlt"))
        daten = text.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", art)
        self.send_header("Content-Length", str(len(daten)))
        self.end_headers()
        self.wfile.write(daten)

    def log_message(self, *args):
        pass


@pytest.fixture
def server():
    s = ThreadingHTTPServer(("127.0.0.1", 0), Antwort)
    s.praefix = ""
    faden = threading.Thread(target=s.serve_forever, daemon=True)
    faden.start()
    yield s
    s.shutdown()
    s.server_close()


def pruefe(server, *pfade, site_root=None):
    port = server.server_address[1]
    # PYTHONUTF8: Im Container schreibt Python UTF-8, unter Windows sonst cp1252.
    env = dict(os.environ, SITE_ROOT=site_root or f"http://127.0.0.1:{port}", PYTHONUTF8="1")
    # Das Skript fragt localhost; im Test steht der Server auf 127.0.0.1.
    programm = PRUEFUNG.replace('f"http://localhost:{port}', 'f"http://127.0.0.1:{port}')
    return subprocess.run([sys.executable, "-c", programm, str(port), "5", MERKMAL, *pfade],
                          capture_output=True, text=True, encoding="utf-8", env=env)


def test_statusantwort_ohne_html_braucht_kein_merkmal(server):
    erg = pruefe(server, "/api/v3/status/", "/accounts/login/")
    assert erg.returncode == 0, erg.stdout + erg.stderr
    assert "Prüfung bestanden" in erg.stdout


def test_html_seite_ohne_merkmal_scheitert(server):
    erg = pruefe(server, "/ohne-werkbank/")
    assert erg.returncode == 1
    assert f"/ohne-werkbank/ enthält {MERKMAL} nicht" in erg.stdout


def test_fehlerstatus_wird_gemeldet(server):
    erg = pruefe(server, "/api/v3/status/", "/kaputt/")
    assert erg.returncode == 1
    assert "/kaputt/ antwortet mit HTTP 500" in erg.stdout


def test_site_root_mit_unterpfad(server):
    server.praefix = "/hc"
    port = server.server_address[1]
    erg = pruefe(server, "/api/v3/status/", "/accounts/login/", site_root=f"http://127.0.0.1:{port}/hc/")
    assert erg.returncode == 0, erg.stdout + erg.stderr

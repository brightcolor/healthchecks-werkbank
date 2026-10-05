"""Musterdaten für die Browserprüfung. Aufruf: ./manage.py shell < tests/musterdaten.py

Legt zwei Konten an (hell: Superuser mit heller Darstellung, dunkel:
Teammitglied mit dunkler Darstellung), zwei Projekte, Checks in jedem Zustand,
zwei Integrationen und Pings. Am Ende steht eine Zeile "MUSTERDATEN: {json}"
mit Konten, Codes und Seitenadressen. Das Passwort kommt aus WB_TEST_PASSWORT.
Alle Namen und Adressen sind erfunden; das Skript lässt sich mehrfach ausführen.
"""

import json
import os
from datetime import timedelta

from django.contrib.auth.models import User
from django.urls import reverse
from django.utils.timezone import now

from hc.accounts.models import Member, Profile, Project
from hc.api.models import Channel, Check, Flip, Ping

passwort = os.environ.get("WB_TEST_PASSWORT", "")
if len(passwort) < 12:
    raise SystemExit("WB_TEST_PASSWORT fehlt oder ist kürzer als 12 Zeichen. "
                     "tools/dev.py oder tools/ci/testinstanz.sh setzen es.")
jetzt = now()


def konto(email, theme, admin):
    nutzer, _ = User.objects.get_or_create(username=email.split("@")[0], defaults={"email": email})
    nutzer.email = email
    nutzer.is_staff = nutzer.is_superuser = admin
    nutzer.set_password(passwort)
    nutzer.save()
    profil, _ = Profile.objects.get_or_create(user=nutzer)
    profil.theme = theme
    profil.save()
    return nutzer


hell = konto("hell@example.org", "", True)
dunkel = konto("dunkel@example.org", "dark", False)


def projekt(name, schluessel):
    p = Project.objects.filter(owner=hell, name=name).first()
    if p is None:
        p = Project(owner=hell, name=name, badge_key=schluessel)
        p.save()
    Member.objects.get_or_create(user=dunkel, project=p, defaults={"role": Member.Role.REGULAR})
    return p


nord = projekt("Projekt Nord", "wb-nord")
sued = projekt("Projekt Süd", "wb-sued")


def check(projekt_, name, **felder):
    c = Check.objects.filter(project=projekt_, name=name).first() or Check(project=projekt_, name=name)
    for schluessel, wert in felder.items():
        setattr(c, schluessel, wert)
    c.save()
    return c


stunde = timedelta(hours=1)
checks = {
    "up": check(nord, "backup-nacht", tags="sicherung nord", timeout=timedelta(days=1), grace=stunde,
                status="up", last_ping=jetzt - timedelta(minutes=20), n_pings=3),
    "grace": check(nord, "zertifikate-erneuern", tags="zertifikate", timeout=timedelta(days=1),
                   grace=timedelta(hours=6), status="up", last_ping=jetzt - timedelta(days=1, hours=2)),
    "down": check(nord, "statistik-archiv", tags="statistik", timeout=timedelta(minutes=15),
                  grace=timedelta(minutes=10), status="down", last_ping=jetzt - timedelta(hours=3)),
    "started": check(nord, "replikation", tags="replikation", timeout=stunde, grace=timedelta(minutes=30),
                     status="up", last_ping=jetzt - timedelta(minutes=50), last_start=jetzt - timedelta(minutes=2)),
    "paused": check(sued, "mailing-test", tags="mailing", status="paused"),
    "new": check(sued, "neuer-lauf", kind="cron", schedule="*/5 * * * *", tz="Europe/Berlin"),
}


def kanal(name, adresse):
    k = Channel.objects.filter(project=nord, name=name).first()
    if k is None:
        k = Channel(project=nord, name=name, kind="email", email_verified=True,
                    value=json.dumps({"value": adresse, "up": True, "down": True}))
        k.save()
    return k


alarm = kanal("Alarm-Mail", "alarm@example.org")
bericht = kanal("Bericht-Mail", "bericht@example.org")
for c in checks.values():
    if c.project_id == nord.id:
        c.channel_set.add(alarm)
checks["up"].channel_set.add(bericht)

if not Ping.objects.filter(owner=checks["up"]).exists():
    for n, (vor, art, text) in enumerate([
        (timedelta(days=2), None, b"backup fertig"),
        (timedelta(days=1), "fail", b"backup abgebrochen: kein Platz auf dem Ziel"),
        (timedelta(minutes=20), None, b"backup fertig"),
    ], start=1):
        Ping.objects.create(owner=checks["up"], n=n, created=jetzt - vor, kind=art, scheme="http",
                            method="POST", remote_addr="192.0.2.10", ua="curl/8.5.0", body_raw=text)
    for vor, alt, neu in ((timedelta(days=1), "up", "down"), (timedelta(hours=23), "down", "up")):
        Flip.objects.create(owner=checks["up"], created=jetzt - vor, processed=jetzt - vor,
                            old_status=alt, new_status=neu)

seiten = {
    "anmeldung": reverse("hc-login"),
    "projekte": reverse("hc-index"),
    "checks": reverse("hc-checks", args=[nord.code]),
    "details": reverse("hc-details", args=[checks["up"].code]),
    "log": reverse("hc-log", args=[checks["up"].code]),
    "integrations": reverse("hc-channels", args=[nord.code]),
    "badges": reverse("hc-badges", args=[nord.code]),
    "projekt": reverse("hc-project-settings", args=[nord.code]),
    "konto": reverse("hc-profile"),
    "darstellung": reverse("hc-appearance"),
    "docs": reverse("hc-docs"),
}
print("MUSTERDATEN: " + json.dumps({
    "nutzer": {"hell": hell.email, "dunkel": dunkel.email},
    "projekte": [{"name": p.name, "code": str(p.code)} for p in (nord, sued)],
    "checks": {name: str(c.code) for name, c in checks.items()},
    "seiten": seiten,
}, ensure_ascii=False))

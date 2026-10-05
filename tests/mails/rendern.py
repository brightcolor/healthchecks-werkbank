"""Rendert jede Mail von Healthchecks mit den Musterdaten, ohne sie zu verschicken.

Läuft über `manage.py shell -c` nach tests/musterdaten.py. WB_MAILS_ZIEL nennt den Ordner;
je Mail entstehen <name>.html, <name>.txt und <name>-betreff.txt. Das Skript ruft dieselben
Methoden auf wie Healthchecks im Betrieb und fängt nur den Versand in hc.lib.emails.send ab;
so stimmen die Kontexte mit denen echter Mails überein. Am Ende steht eine Zeile
"MAILS: [...]" mit den Namen.
"""

import json
import os
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.contrib.auth.models import User
from django.utils.timezone import now

from hc.accounts.models import Member, Profile, Project
from hc.api.models import Channel, Check, Flip, Notification
from hc.integrations.email.transport import Email
from hc.lib import emails

ziel = Path(os.environ.get("WB_MAILS_ZIEL", "/tmp/werkbank-mails"))
ziel.mkdir(parents=True, exist_ok=True)
gesammelt = []
emails.send = lambda message, block=False: gesammelt.append(message)
namen = []


def ablegen(name):
    if not gesammelt:
        raise SystemExit(f"Die Mail {name} wurde nicht erzeugt; die Musterdaten aus tests/musterdaten.py prüfen.")
    message = gesammelt.pop()
    html = next(inhalt for inhalt, art in message.alternatives if art == "text/html")
    (ziel / f"{name}.html").write_bytes(html.encode("utf-8"))
    (ziel / f"{name}.txt").write_bytes(message.body.encode("utf-8"))
    (ziel / f"{name}-betreff.txt").write_bytes(message.subject.encode("utf-8"))
    namen.append(name)


jetzt = now()
hell = User.objects.get(email="hell@example.org")
dunkel = User.objects.get(email="dunkel@example.org")
profil = Profile.objects.for_user(hell)
nord = Project.objects.get(owner=hell, name="Projekt Nord")
ausgefallen = Check.objects.get(project=nord, name="statistik-archiv")
alarm = Channel.objects.get(project=nord, name="Alarm-Mail")

profil.send_instant_login_link()
ablegen("login")

Profile.objects.for_user(dunkel).send_instant_login_link(membership=Member.objects.filter(user=dunkel, project=nord).first())
ablegen("login-einladung")

profil.send_transfer_request(nord)
ablegen("transfer-request")

profil.reports = "monthly"
profil.send_report()
ablegen("report")

profil.nag_period = timedelta(hours=1)
profil.send_report(nag=True)
ablegen("nag")

for name, alt, neu in (("alert-down", "up", "down"), ("alert-up", "down", "up")):
    flip = Flip(owner=ausgefallen, created=jetzt, old_status=alt, new_status=neu, reason="timeout" if neu == "down" else "")
    Email(alarm).notify(flip, Notification(owner=ausgefallen, channel=alarm))
    ablegen(name)

alarm.send_verify_link()
ablegen("verify-email")

telefon = json.dumps({"value": "+4930123456", "up": True, "down": True})
Channel(project=nord, kind="signal", value=telefon).send_signal_rate_limited_notice(
    "statistik-archiv ist ausgefallen", "statistik-archiv ist ausgefallen\nLetzter Ping vor 3 Stunden")
ablegen("signal-rate-limited")
Channel(project=nord, kind="call", value=telefon).send_call_limit_notice("statistik-archiv ist ausgefallen")
ablegen("phone-call-limit")
Channel(project=nord, kind="sms", value=telefon).send_sms_limit_notice("SMS", "statistik-archiv ist ausgefallen")
ablegen("sms-limit")

emails.sudo_code(hell.email, {"sudo_code": "482913"})
ablegen("sudo-code")

ausgefallen.num_flips = 14
emails.flapping_notice(hell.email, {"email": hell.email, "check": ausgefallen, "num_flips": 14,
                                    "support_email": settings.SUPPORT_EMAIL})
ablegen("flapping-notice")

emails.deletion_notice(hell.email, {"email": hell.email, "support_email": settings.SUPPORT_EMAIL})
ablegen("deletion-notice")

emails.deletion_scheduled([hell.email], {"owner_email": hell.email, "num_checks": profil.num_checks_used(),
                                         "support_email": settings.SUPPORT_EMAIL,
                                         "deletion_scheduled_date": jetzt + timedelta(days=30)})
ablegen("deletion-scheduled")

print("MAILS: " + json.dumps(namen))

"""Legt die Markierung der Update-Probe an: ein Check namens probe-markierung."""
from django.contrib.auth.models import User

from hc.accounts.models import Project
from hc.api.models import Check

nutzer, _ = User.objects.get_or_create(username="probe", defaults={"email": "probe@example.org"})
projekt = Project.objects.filter(owner=nutzer).first() or Project.objects.create(owner=nutzer, name="Probe", badge_key="probe")
Check.objects.get_or_create(project=projekt, name="probe-markierung")

#!/bin/sh
# Fassung für die Update-Probe: löscht die Markierung in der Datenbank und wird nie gesund.
./manage.py shell -c "from hc.api.models import Check; Check.objects.filter(name='probe-markierung').delete()" >/dev/null 2>&1
exec uwsgi /opt/healthchecks/docker/uwsgi.ini

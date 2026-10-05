#!/usr/bin/env bash
# Update-Probe für deploy/hc-werkbank-update; läuft in der CI auf Linux mit Docker und sudo.
# Aufruf: tests/update/probe.sh <gebautes Image, etwa wb-test:lokal>
#
# Baut aus dem Image drei Fassungen (probe-a, probe-b, probe-kaputt), legt sie in
# eine lokale Registry und prüft: Wechsel, gleiche Fassung, Rückweg mit
# zurückgespielter Datenbank, Auslassen der zurückgenommenen Fassung, --erneut,
# neuere Fassung trotz Vermerk, ungültige Einstellung, andere Einstellungen.
set -euo pipefail

BILD="${1:?Aufruf: tests/update/probe.sh <Image>}"
WURZEL="$(cd "$(dirname "$0")/../.." && pwd)"
SKRIPT="$WURZEL/deploy/hc-werkbank-update"
REGISTRY_PORT="${WB_PROBE_REGISTRY_PORT:-5000}"
REGISTRY_IMAGE="${WB_PROBE_REGISTRY_IMAGE:-registry:2}"
FRIST="${WB_PROBE_FRIST:-180}"
REG="localhost:${REGISTRY_PORT}"
ARBEIT="$(mktemp -d)"

# shellcheck disable=SC2317 # läuft über trap EXIT
aufraeumen() {
	local d
	for d in "$ARBEIT"/hc*; do
		if [ -f "$d/compose.yaml" ]; then docker compose --project-directory "$d" down -v >/dev/null 2>&1 || true; fi
	done
	docker rm -f wb-probe-registry >/dev/null 2>&1 || true
}
trap aufraeumen EXIT

pruefe() { # Beschreibung, Befehl
	local beschreibung="$1"
	shift
	if "$@"; then echo "ok: $beschreibung"; else echo "FEHLER: $beschreibung" >&2; exit 1; fi
}

fassung() { # Name, Zusatzzeilen für das Dockerfile
	local ordner="$ARBEIT/bau-$1"
	mkdir -p "$ordner"
	printf 'FROM %s\nLABEL org.opencontainers.image.version=%s\n%s\n' "$BILD" "$1" "$2" > "$ordner/Dockerfile"
	cp "$WURZEL/tests/update/kaputt.sh" "$ordner/"
	docker build -q -t "$REG/hcwb:$1" "$ordner" >/dev/null
	docker push -q "$REG/hcwb:$1" >/dev/null
}

als_latest() {
	docker tag "$REG/hcwb:$1" "$REG/hcwb:latest"
	docker push -q "$REG/hcwb:latest" >/dev/null
}

aufbau() { # Ordner, Dienst, Tag-Variable, Start-Fassung
	mkdir -p "$1"
	cat > "$1/compose.yaml" <<EOF
services:
  $2:
    image: $REG/hcwb:\${$3}
    env_file: .env
    volumes:
      - daten:/data
volumes:
  daten:
EOF
	cat > "$1/.env" <<EOF
$3=$4
SECRET_KEY=probe-$(openssl rand -hex 16)
DEBUG=False
SITE_ROOT=http://localhost:8000
DB_NAME=/data/hc.sqlite
REGISTRATION_OPEN=False
EOF
	docker compose --project-directory "$1" up -d --wait --wait-timeout "$FRIST" >/dev/null
	# shell -c: Über die Standardeingabe liest Django das Skript nur, wenn es beim Start schon bereitliegt.
	docker compose --project-directory "$1" exec -T "$2" ./manage.py shell -c "$(cat "$WURZEL/tests/update/markierung.py")" >/dev/null
}

einstellungen() { # Datei, Zeilen
	local datei="$1" entwurf
	shift
	entwurf="$(mktemp)"
	printf '%s\n' "$@" > "$entwurf"
	sudo install -o root -g root -m 600 "$entwurf" "$datei"
	rm -f "$entwurf"
}

update() { # Einstellungsdatei, weitere Optionen; Ausgabe auch nach $ARBEIT/ausgabe.txt
	local datei="$1" rc=0
	shift
	sudo bash "$SKRIPT" --einstellungen "$datei" "$@" 2>&1 | tee "$ARBEIT/ausgabe.txt" || rc=$?
	return "$rc"
}

env_wert() { grep -E "^$2=" "$1/.env" | cut -d= -f2-; }
gesund() { [ "$(docker inspect -f '{{.State.Health.Status}}' "$(docker compose --project-directory "$1" ps -q "$2")")" = healthy ]; }
markiert() {
	docker compose --project-directory "$1" exec -T "$2" ./manage.py shell -c \
		"from hc.api.models import Check; print('MARKIERUNG', Check.objects.filter(name='probe-markierung').count())" \
		| grep -qx 'MARKIERUNG 1'
}
sicherungen() { sudo find "$1" -maxdepth 1 -name 'healthchecks-*.sqlite' | wc -l; }

docker run -d --name wb-probe-registry -p "127.0.0.1:${REGISTRY_PORT}:5000" "$REGISTRY_IMAGE" >/dev/null
fassung probe-a ""
fassung probe-b ""
fassung probe-kaputt 'COPY kaputt.sh /opt/kaputt.sh
HEALTHCHECK --interval=2s --start-period=2s --retries=1 CMD false
CMD ["sh", "/opt/kaputt.sh"]'

HC="$ARBEIT/hc"
aufbau "$HC" healthchecks HC_IMAGE_TAG probe-a
E1="$ARBEIT/eins.conf"
VERMERK="$ARBEIT/vermerk/failed-version"
einstellungen "$E1" "IMAGE=$REG/hcwb" "COMPOSE_DIR=$HC" "BACKUP_DIR=$ARBEIT/sicherung" \
	"LOG_FILE=$ARBEIT/update.log" "LOCK_FILE=$ARBEIT/update.lock" "FAILED_FILE=$VERMERK" "WAIT_SECONDS=$FRIST"

echo "== 1. Neue Fassung wird übernommen"
als_latest probe-b
rc=0; update "$E1" || rc=$?
pruefe "Rückgabe 0" [ "$rc" -eq 0 ]
pruefe ".env trägt probe-b" [ "$(env_wert "$HC" HC_IMAGE_TAG)" = probe-b ]
pruefe "Container gesund" gesund "$HC" healthchecks
pruefe "eine Sicherung" [ "$(sicherungen "$ARBEIT/sicherung")" -eq 1 ]
pruefe "Markierung vorhanden" markiert "$HC" healthchecks

echo "== 2. Gleiche Fassung: nichts zu tun"
rc=0; update "$E1" || rc=$?
pruefe "Rückgabe 0" [ "$rc" -eq 0 ]
pruefe "Meldung aktuell" grep -q "Aktuell: probe-b" "$ARBEIT/ausgabe.txt"
pruefe "keine neue Sicherung" [ "$(sicherungen "$ARBEIT/sicherung")" -eq 1 ]

echo "== 3. Kaputte Fassung: Rückweg mit Datenbank"
als_latest probe-kaputt
rc=0; update "$E1" || rc=$?
pruefe "Rückgabe 1" [ "$rc" -eq 1 ]
pruefe ".env wieder probe-b" [ "$(env_wert "$HC" HC_IMAGE_TAG)" = probe-b ]
pruefe "Container gesund" gesund "$HC" healthchecks
pruefe "Markierung aus der Sicherung zurück" markiert "$HC" healthchecks
pruefe "Protokoll nennt den Rückweg" sudo grep -q "Rückweg erledigt" "$ARBEIT/update.log"
pruefe "Vermerk nennt probe-kaputt" [ "$(sudo head -n 1 "$VERMERK")" = probe-kaputt ]
pruefe "zwei Sicherungen" [ "$(sicherungen "$ARBEIT/sicherung")" -eq 2 ]

echo "== 4. Zurückgenommene Fassung: spätere Läufe lassen sie aus"
rc=0; update "$E1" || rc=$?
pruefe "Rückgabe 1" [ "$rc" -eq 1 ]
pruefe "Meldung nennt das Auslassen" grep -q "Dieser Lauf lässt sie aus" "$ARBEIT/ausgabe.txt"
pruefe "keine neue Sicherung" [ "$(sicherungen "$ARBEIT/sicherung")" -eq 2 ]
pruefe ".env weiter probe-b" [ "$(env_wert "$HC" HC_IMAGE_TAG)" = probe-b ]

echo "== 5. --erneut versucht die Fassung noch einmal"
rc=0; update "$E1" --erneut || rc=$?
pruefe "Rückgabe 1" [ "$rc" -eq 1 ]
pruefe "Meldung nennt den neuen Versuch" grep -q "Neuer Versuch mit probe-kaputt" "$ARBEIT/ausgabe.txt"
pruefe "dritte Sicherung" [ "$(sicherungen "$ARBEIT/sicherung")" -eq 3 ]
pruefe "Container gesund" gesund "$HC" healthchecks
pruefe "Markierung vorhanden" markiert "$HC" healthchecks

echo "== 6. Neuere Fassung läuft trotz Vermerk durch"
als_latest probe-a
rc=0; update "$E1" || rc=$?
pruefe "Rückgabe 0" [ "$rc" -eq 0 ]
pruefe ".env trägt probe-a" [ "$(env_wert "$HC" HC_IMAGE_TAG)" = probe-a ]
pruefe "Vermerk ist gelöscht" sudo test ! -e "$VERMERK"
pruefe "Markierung vorhanden" markiert "$HC" healthchecks

echo "== 7. Ungültige Einstellung"
E2="$ARBEIT/ungueltig.conf"
einstellungen "$E2" "COMPOSE_DIR=$HC" "BACKUP_KEEP=0"
rc=0; update "$E2" || rc=$?
pruefe "Rückgabe 2" [ "$rc" -eq 2 ]
pruefe "Meldung nennt BACKUP_KEEP" grep -q "BACKUP_KEEP ist 0" "$ARBEIT/ausgabe.txt"
pruefe ".env unverändert" [ "$(env_wert "$HC" HC_IMAGE_TAG)" = probe-a ]

echo "== 8. Andere Einstellungen: Dienst hc, Variable WB_TAG, eine Sicherung"
HC2="$ARBEIT/hc-anders"
aufbau "$HC2" hc WB_TAG probe-b
E3="$ARBEIT/anders.conf"
einstellungen "$E3" "IMAGE=$REG/hcwb" "COMPOSE_DIR=$HC2" "SERVICE=hc" "TAG_VARIABLE=WB_TAG" "BACKUP_KEEP=1" \
	"BACKUP_DIR=$ARBEIT/sicherung-anders" "LOG_FILE=$ARBEIT/anders.log" "LOCK_FILE=$ARBEIT/anders.lock" \
	"FAILED_FILE=$ARBEIT/vermerk-anders" "CHECK_PATHS=/api/v3/status/" "WAIT_SECONDS=$FRIST"
als_latest probe-a
rc=0; update "$E3" || rc=$?
pruefe "Rückgabe 0" [ "$rc" -eq 0 ]
pruefe "WB_TAG trägt probe-a" [ "$(env_wert "$HC2" WB_TAG)" = probe-a ]
als_latest probe-b
rc=0; update "$E3" || rc=$?
pruefe "zweiter Wechsel" [ "$(env_wert "$HC2" WB_TAG)" = probe-b ]
pruefe "nur eine Sicherung bleibt" [ "$(sicherungen "$ARBEIT/sicherung-anders")" -eq 1 ]

echo "Update-Probe bestanden."

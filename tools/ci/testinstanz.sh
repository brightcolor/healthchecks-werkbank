#!/usr/bin/env bash
# Startet eine Testinstanz des gebauten Images und legt die Musterdaten an.
# Aufruf: tools/ci/testinstanz.sh <Image>
# Schreibt tests/e2e/ergebnisse/musterdaten.json und WB_TEST_PASSWORT nach GITHUB_ENV.
set -euo pipefail

BILD="${1:?Aufruf: tools/ci/testinstanz.sh <Image>}"
NAME="${WB_TESTINSTANZ:-wb-test}"
PORT="${WB_TESTPORT:-8000}"
ERGEBNIS="${WB_MUSTERDATEN:-tests/e2e/ergebnisse/musterdaten.json}"
FRIST="${WB_START_FRIST:-180}"

passwort="$(openssl rand -hex 16)"
echo "::add-mask::${passwort}"
docker rm -f "$NAME" >/dev/null 2>&1 || true
docker run -d --name "$NAME" -p "127.0.0.1:${PORT}:8000" \
	-e SECRET_KEY="$(openssl rand -hex 32)" -e DEBUG=False -e SITE_ROOT="http://localhost:${PORT}" \
	-e DB_NAME=/data/hc.sqlite -e REGISTRATION_OPEN=False -e SITE_NAME=Healthchecks \
	"$BILD" >/dev/null

zustand=""
ende=$((SECONDS + FRIST))
while [ "$SECONDS" -lt "$ende" ]; do
	zustand="$(docker inspect -f '{{.State.Health.Status}}' "$NAME")"
	if [ "$zustand" = healthy ]; then break; fi
	sleep 2
done
if [ "$zustand" != healthy ]; then
	docker logs "$NAME" 2>&1 | tail -n 40
	echo "::error::Die Testinstanz wurde nicht gesund (Zustand: ${zustand:-unbekannt}). Das Log steht darüber."
	exit 1
fi

# shell -c: Über die Standardeingabe liest Django das Skript nur, wenn es beim Start
# schon bereitliegt; sonst landet es Zeile für Zeile in der Konsole.
mkdir -p "$(dirname "$ERGEBNIS")"
roh="$(mktemp)"
if ! docker exec -e WB_TEST_PASSWORT="$passwort" "$NAME" ./manage.py shell -c "$(cat tests/musterdaten.py)" > "$roh" 2>&1; then
	tail -n 40 "$roh"
	echo "::error::Die Musterdaten wurden nicht angelegt. Die Ausgabe von manage.py shell steht darüber."
	exit 1
fi
sed -n 's/^MUSTERDATEN: //p' "$roh" > "$ERGEBNIS"
if [ ! -s "$ERGEBNIS" ]; then
	tail -n 40 "$roh"
	echo "::error::manage.py shell lief durch, gab aber keine Zeile MUSTERDATEN aus. Die Ausgabe steht darüber."
	exit 1
fi
echo "WB_TEST_PASSWORT=${passwort}" >> "${GITHUB_ENV:-/dev/null}"
echo "Testinstanz ${NAME} läuft auf Port ${PORT}, Musterdaten in ${ERGEBNIS}."

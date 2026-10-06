#!/usr/bin/env bash
# Führt einen Befehl aus und wiederholt ihn, wenn er scheitert. Gedacht für Schreibzugriffe auf
# ghcr.io, die gelegentlich mit "unknown blob" abbrechen und beim nächsten Versuch durchgehen.
# Aufruf: tools/ci/wiederholen.sh -- <Befehl> [Argumente]
# Einstellungen: WB_VERSUCHE (Vorgabe 3, 1 bis 10), WB_VERSUCH_PAUSE in Sekunden (Vorgabe 20, 0 bis 300).
set -uo pipefail

VERSUCHE="${WB_VERSUCHE:-3}"
PAUSE="${WB_VERSUCH_PAUSE:-20}"

if [ "${1:-}" != "--" ] || [ $# -lt 2 ]; then
	echo "Aufruf: tools/ci/wiederholen.sh -- <Befehl> [Argumente]" >&2
	exit 2
fi
shift

zahl() {
	local name="$1" wert="$2" min="$3" max="$4"
	if ! [[ "$wert" =~ ^[0-9]+$ ]] || [ "$wert" -lt "$min" ] || [ "$wert" -gt "$max" ]; then
		echo "::error::$name ist '$wert'. Erlaubt ist eine ganze Zahl von $min bis $max; den Wert oben im Workflow korrigieren." >&2
		exit 2
	fi
}
zahl WB_VERSUCHE "$VERSUCHE" 1 10
zahl WB_VERSUCH_PAUSE "$PAUSE" 0 300

code=0
for versuch in $(seq 1 "$VERSUCHE"); do
	"$@" && exit 0
	code=$?
	if [ "$versuch" -lt "$VERSUCHE" ]; then
		echo "::warning::$1 ist gescheitert (Rückgabe $code, Versuch $versuch von $VERSUCHE). Neuer Versuch in $PAUSE Sekunden."
		sleep "$PAUSE"
	fi
done
echo "::error::$1 ist nach $VERSUCHE Versuchen gescheitert (zuletzt Rückgabe $code). Die Meldung darüber nennt den Grund; den Dienst prüfen und den Lauf danach neu starten."
exit "$code"

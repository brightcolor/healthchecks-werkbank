#!/usr/bin/env bash
# Führt einen Prüfschritt aus, hält die Ausgabe in artefakte/logs/<name>.log fest
# und schreibt bei Fehlschlag einen Auszug nach fehler/<arch>-<name>.md für das Issue.
# Aufruf: tools/ci/schritt.sh <name> -- <befehl ...>
set -uo pipefail

name="${1:?Aufruf: tools/ci/schritt.sh <name> -- <befehl>}"
shift
if [ "${1:-}" = "--" ]; then shift; fi
mkdir -p artefakte/logs fehler
"$@" 2>&1 | tee "artefakte/logs/${name}.log"
rc=${PIPESTATUS[0]}
if [ "$rc" -ne 0 ]; then
	{
		echo "### ${name} (${WB_ARCH:-unbekannt})"
		echo
		echo '```'
		tail -n "${WB_AUSZUG_ZEILEN:-40}" "artefakte/logs/${name}.log"
		echo '```'
		echo
	} > "fehler/${WB_ARCH:-unbekannt}-${name}.md"
fi
exit "$rc"

#!/usr/bin/env bash
# Hält den Zustand der Werkbank-Prüfung in einem Issue fest.
#   tools/ci/meldung.sh rot    legt das Issue der Healthchecks-Version an oder ergänzt es
#   tools/ci/meldung.sh gruen  schließt das offene Issue der Version
set -euo pipefail

ART="${1:?Aufruf: tools/ci/meldung.sh rot|gruen}"
HC_TAG="${HC_TAG:-unbekannt}"
LAUF_URL="${LAUF_URL:?LAUF_URL fehlt}"
LABEL="${WB_ISSUE_LABEL:-theme-rot}"
TITEL="Healthchecks ${HC_TAG}: Werkbank-Prüfung rot"

nummer="$(gh issue list --label "$LABEL" --state open --json number,title \
	--jq "map(select(.title == \"${TITEL}\")) | .[0].number // empty" 2>/dev/null || true)"

case "$ART" in
	rot)
		if [ -n "$nummer" ] && [ "${EREIGNIS:-}" = schedule ]; then
			echo "Issue #${nummer} ist schon offen; ein Lauf aus dem Zeitplan ergänzt es nicht erneut."
			exit 0
		fi
		koerper="$(mktemp)"
		{
			echo "Die Prüfung für Healthchecks ${HC_TAG} (Fassung ${FASSUNG:-unbekannt}) ist rot. Es wurde nichts veröffentlicht; docker-a1 behält die laufende Fassung."
			echo
			echo "Lauf: ${LAUF_URL}"
			echo
			if compgen -G "fehler/*.md" >/dev/null; then
				cat fehler/*.md
			else
				echo "Ein Auszug fehlt; die Ursache steht im Log des Laufs."
			fi
			echo
			echo "Nächster Schritt: das Theme in einer Sitzung anpassen und auf main pushen. Der nächste grüne Lauf veröffentlicht und schließt dieses Issue."
		} > "$koerper"
		gh label create "$LABEL" --color d61f7a --description "Werkbank-Prüfung rot" >/dev/null 2>&1 || true
		if [ -n "$nummer" ]; then
			gh issue comment "$nummer" --body-file "$koerper"
		else
			gh issue create --title "$TITEL" --label "$LABEL" --body-file "$koerper"
		fi
		;;
	gruen)
		if [ -n "$nummer" ]; then
			gh issue close "$nummer" --comment "Wieder grün und veröffentlicht als ${FASSUNG:-unbekannt}: ${LAUF_URL}"
		else
			echo "Kein offenes Issue für Healthchecks ${HC_TAG}."
		fi
		;;
	*)
		echo "Unbekannte Art '${ART}'. Erlaubt sind rot und gruen." >&2
		exit 2
		;;
esac

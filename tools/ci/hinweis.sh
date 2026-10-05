#!/usr/bin/env bash
# Hinweis-Issue zur Übersetzung. Nach einem Update von Healthchecks nennt es Textstücke, die noch
# englisch sind, Katalog-Einträge ohne Fundstelle und Hinweise zu den Mails. Die Fassung ist
# trotzdem veröffentlicht. Ohne Hinweise schließt das Skript offene Issues mit dem Label.
#   tools/ci/hinweis.sh <werkbank-bericht.json>
set -euo pipefail

BERICHT="${1:?Aufruf: tools/ci/hinweis.sh <werkbank-bericht.json>}"
HC_TAG="${HC_TAG:-unbekannt}"
FASSUNG="${FASSUNG:-unbekannt}"
LAUF_URL="${LAUF_URL:?LAUF_URL fehlt}"
LABEL="${WB_HINWEIS_LABEL:-uebersetzung}"
PYTHON="${WB_PYTHON:-python3}"
SKRIPTE="$(cd "$(dirname "$0")" && pwd)"

if [ ! -s "$BERICHT" ]; then
	echo "::warning::Der Bericht ${BERICHT} fehlt oder ist leer; das Hinweis-Issue bleibt unverändert."
	exit 0
fi

read -r englisch ohne mails < <("$PYTHON" -c '
import json, sys
b = json.load(open(sys.argv[1], encoding="utf-8"))
u = b.get("uebersetzung") or {}
print(len(u.get("englisch", [])), len(u.get("ohne_fundstelle", [])), len(b.get("mails", {}).get("hinweise", [])))
' "$BERICHT")

offen="$(gh issue list --label "$LABEL" --state open --json number --jq '.[].number' 2>/dev/null || true)"

if [ "$englisch" -eq 0 ] && [ "$ohne" -eq 0 ] && [ "$mails" -eq 0 ]; then
	while read -r nummer; do
		[ -n "$nummer" ] || continue
		gh issue close "$nummer" --comment "Healthchecks ${HC_TAG}: alle Texte deutsch, veröffentlicht als ${FASSUNG}. ${LAUF_URL}"
	done <<< "$(tr ' ' '\n' <<< "$offen")"
	echo "Keine Hinweise zur Übersetzung für Healthchecks ${HC_TAG}."
	exit 0
fi

if [ "$englisch" -gt 0 ]; then
	TITEL="Healthchecks ${HC_TAG}: ${englisch} Texte noch englisch"
elif [ "$ohne" -gt 0 ]; then
	TITEL="Healthchecks ${HC_TAG}: ${ohne} Katalog-Einträge ohne Fundstelle"
else
	TITEL="Healthchecks ${HC_TAG}: Hinweise zu den Mails"
fi

koerper="$(mktemp)"
{
	echo "Die Fassung ${FASSUNG} ist veröffentlicht. Stellen ohne Übersetzung erscheinen englisch, bis der Katalog sie abdeckt."
	echo
	echo "Lauf: ${LAUF_URL}"
	echo
	WB_HC_VERSION="$HC_TAG" "$PYTHON" "$SKRIPTE/bericht.py" "$BERICHT" --uebersetzung
	echo
	echo "Nächster Schritt: den Katalog in \`werkbank/deutsch/\` ergänzen (Inventur: \`python werkbank/sprache.py inventur --wurzel <Healthchecks> --werkbank werkbank\`), \`stand\` in \`katalog.toml\` auf ${HC_TAG} setzen und auf main pushen. Der nächste Lauf ohne Hinweise schließt dieses Issue."
} > "$koerper"

gh label create "$LABEL" --color fed329 --description "Übersetzung unvollständig" >/dev/null 2>&1 || true
nummer="$(gh issue list --label "$LABEL" --state open --json number,title \
	--jq "map(select(.title | startswith(\"Healthchecks ${HC_TAG}:\"))) | .[0].number // empty" 2>/dev/null || true)"
if [ -n "$nummer" ]; then
	gh issue edit "$nummer" --title "$TITEL" --body-file "$koerper"
	echo "Issue #${nummer} aktualisiert: ${TITEL}"
else
	gh issue create --title "$TITEL" --label "$LABEL" --body-file "$koerper"
fi

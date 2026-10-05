#!/usr/bin/env bash
# Entscheidet, welche Healthchecks-Version die CI baut und ob sie veröffentlicht.
# Umgebung: UPSTREAM, BASIS_IMAGE, ZIEL_IMAGE, EREIGNIS, REF, EINGABE, ERZWINGEN,
# GH_TOKEN, GITHUB_ACTOR, GITHUB_OUTPUT, GITHUB_STEP_SUMMARY.
set -euo pipefail

: "${UPSTREAM:?}" "${BASIS_IMAGE:?}" "${ZIEL_IMAGE:?}" "${EREIGNIS:?}" "${GITHUB_OUTPUT:?}"
ZUSAMMENFASSUNG="${GITHUB_STEP_SUMMARY:-/dev/null}"

ausgabe() { printf '%s=%s\n' "$1" "$2" >> "$GITHUB_OUTPUT"; }
notiz() { printf '%s\n' "$*" >> "$ZUSAMMENFASSUNG"; }

hc_tag="${EINGABE:-}"
if [ -z "$hc_tag" ]; then
	hc_tag="$(gh api "repos/${UPSTREAM}/releases/latest" --jq .tag_name)"
fi
if ! [[ "$hc_tag" =~ ^v[0-9]+(\.[0-9]+)*$ ]]; then
	echo "::error::Die Version '${hc_tag}' hat nicht die Form v4.4. Beim Handstart eine Version wie v4.4 eingeben oder das Feld leer lassen."
	exit 1
fi
theme="$(tr -d '[:space:]' < VERSION)"
if ! [[ "$theme" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
	echo "::error::VERSION enthält '${theme}', erwartet ist eine Fassung wie 1.0.0."
	exit 1
fi
fassung="${hc_tag#v}-wb${theme}"
ausgabe hc_tag "$hc_tag"
ausgabe fassung "$fassung"

hub="$(curl -s -o /dev/null -w '%{http_code}' "https://hub.docker.com/v2/repositories/${BASIS_IMAGE}/tags/${hc_tag}")"
if [ "$hub" != 200 ]; then
	notiz "Das Basis-Image ${BASIS_IMAGE}:${hc_tag} liegt noch nicht auf Docker Hub (HTTP ${hub}). Der nächste Lauf versucht es erneut."
	ausgabe bauen false
	ausgabe veroeffentlichen false
	exit 0
fi

pfad="${ZIEL_IMAGE#ghcr.io/}"
adresse="https://ghcr.io/token?scope=repository:${pfad}:pull&service=ghcr.io"
# Mit GH_TOKEN sieht die Abfrage auch ein Paket, das noch privat ist. Der Zugang geht
# über die Standardeingabe an curl und erscheint so in keiner Prozessliste.
if [ -n "${GH_TOKEN:-}" ]; then
	antwort="$(printf 'user = "%s:%s"\n' "${GITHUB_ACTOR:-token}" "$GH_TOKEN" | curl -fsSL -K - "$adresse" || true)"
else
	antwort="$(curl -fsSL "$adresse" || true)"
fi
token=""
if [[ "$antwort" =~ \"token\":\"([^\"]*)\" ]]; then token="${BASH_REMATCH[1]}"; fi
vorhanden=false
if [ -n "$token" ]; then
	code="$(curl -s -o /dev/null -w '%{http_code}' -H "Authorization: Bearer ${token}" \
		-H 'Accept: application/vnd.oci.image.index.v1+json' \
		-H 'Accept: application/vnd.docker.distribution.manifest.list.v2+json' \
		"https://ghcr.io/v2/${pfad}/manifests/${fassung}")"
	if [ "$code" = 200 ]; then vorhanden=true; fi
fi

case "$EREIGNIS" in
	schedule)
		if [ "$vorhanden" = true ]; then bauen=false; else bauen=true; fi
		veroeffentlichen="$bauen" ;;
	push)
		bauen=true
		if [ "${REF:-}" = refs/heads/main ] && [ "$vorhanden" = false ]; then veroeffentlichen=true; else veroeffentlichen=false; fi ;;
	pull_request)
		bauen=true
		veroeffentlichen=false ;;
	workflow_dispatch)
		if [ "${ERZWINGEN:-false}" = true ] || [ "$vorhanden" = false ]; then
			bauen=true
			veroeffentlichen=true
		else
			bauen=false
			veroeffentlichen=false
		fi ;;
	*)
		echo "::error::Unbekanntes Ereignis '${EREIGNIS}'. Die CI kennt schedule, push, pull_request und workflow_dispatch."
		exit 1 ;;
esac
ausgabe bauen "$bauen"
ausgabe veroeffentlichen "$veroeffentlichen"
notiz "Healthchecks ${hc_tag}, Fassung ${fassung}: schon veröffentlicht ${vorhanden}, bauen ${bauen}, veröffentlichen ${veroeffentlichen}."

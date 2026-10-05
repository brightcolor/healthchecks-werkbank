#!/usr/bin/env bash
# Holt Vorlagen und Stylesheets aus dem Basis-Image nach .upstream/<version> für die Einheitstests.
# Aufruf: tools/ci/upstream_aus_image.sh <Image> <Zielordner>
set -euo pipefail

BILD="${1:?Aufruf: tools/ci/upstream_aus_image.sh <Image> <Zielordner>}"
ZIEL="${2:?Zielordner fehlt}"
WURZEL_IM_IMAGE="${WB_HC_WURZEL:-/opt/healthchecks}"

docker pull -q "$BILD" >/dev/null
behaelter="$(docker create "$BILD")"
trap 'docker rm -f "$behaelter" >/dev/null' EXIT
mkdir -p "$ZIEL"
docker cp "$behaelter:$WURZEL_IM_IMAGE/templates" "$ZIEL/templates"
docker cp "$behaelter:$WURZEL_IM_IMAGE/static" "$ZIEL/static"
echo "Vorlagen und Stylesheets aus $BILD liegen in $ZIEL."

# syntax=docker/dockerfile:1
# healthchecks-werkbank: das offizielle Image von Healthchecks mit der Werkbank von bright color.
ARG HC_VERSION=v4.4
FROM healthchecks/healthchecks:${HC_VERSION}

ARG WERKBANK_FASSUNG=lokal
# Sprache des Images: de wendet den Katalog aus werkbank/deutsch/ an, en lässt die Texte stehen.
ARG WB_SPRACHE=de
USER root
# Die Quellen kommen als Bind-Mount in den Bauschritt; im Image bleibt nur das Ergebnis.
RUN --mount=type=bind,source=werkbank,target=/tmp/werkbank \
    --mount=type=bind,source=vendor/hausschrift,target=/tmp/hausschrift \
    set -eu; \
    cp -r /tmp/werkbank/templates/bc templates/bc; \
    mkdir -p static/bc/logo; \
    cp -r /tmp/hausschrift/assets/fonts static/bc/fonts; \
    cp /tmp/hausschrift/assets/logo/*.svg static/bc/logo/; \
    cp /tmp/werkbank/static/bc/leiste.js static/bc/; \
    python /tmp/werkbank/einbau.py --wurzel /opt/healthchecks --fassung "$WERKBANK_FASSUNG"; \
    python /tmp/werkbank/farben.py bauen --wurzel /opt/healthchecks --hausschrift /tmp/hausschrift \
        --werkbank /tmp/werkbank --fassung "$WERKBANK_FASSUNG" --bericht /opt/healthchecks/werkbank-bericht.json; \
    python /tmp/werkbank/mails.py einsetzen --wurzel /opt/healthchecks --werkbank /tmp/werkbank \
        --hausschrift /tmp/hausschrift --bericht /opt/healthchecks/werkbank-bericht.json; \
    WB_SPRACHE="$WB_SPRACHE" python /tmp/werkbank/sprache.py bauen --wurzel /opt/healthchecks \
        --werkbank /tmp/werkbank --bericht /opt/healthchecks/werkbank-bericht.json; \
    DEBUG=False SECRET_KEY=build-key ./manage.py collectstatic --noinput; \
    DEBUG=False SECRET_KEY=build-key ./manage.py compress --force
USER hc
LABEL org.opencontainers.image.version="${WERKBANK_FASSUNG}" \
      org.opencontainers.image.title="healthchecks-werkbank"

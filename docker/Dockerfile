ARG JELLYFIN_BASE=jellyfin/jellyfin:12.0@sha256:baba630419915985442f315f08b0cf46d9f4c8a0cc4bd38e94a6d35751dd5ef5
FROM ${JELLYFIN_BASE}

ARG JELLYFIN_BASE
ARG IMAGE_VERSION
ARG IMAGE_REVISION
LABEL org.opencontainers.image.title="Jellyfin with database fixes" \
      org.opencontainers.image.description="Jellyfin 12 with nintwentydo's upstream database fixes" \
      org.opencontainers.image.source="https://github.com/nintwentydo/jellyfin" \
      org.opencontainers.image.licenses="GPL-2.0-only" \
      org.opencontainers.image.version="${IMAGE_VERSION}" \
      org.opencontainers.image.revision="${IMAGE_REVISION}" \
      org.opencontainers.image.base.name="${JELLYFIN_BASE}"

# Keep the official web client, runtime, FFmpeg and container configuration.
RUN mv /jellyfin/jellyfin-web /tmp/jellyfin-web \
    && rm -rf /jellyfin
COPY server/ /jellyfin/
RUN mv /tmp/jellyfin-web /jellyfin/jellyfin-web

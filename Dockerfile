FROM python:3.12-slim

LABEL org.opencontainers.image.title="vibescore" \
      org.opencontainers.image.description="Grade your vibe-coded project with a letter grade" \
      org.opencontainers.image.source="https://github.com/stef41/vibescore" \
      org.opencontainers.image.licenses="Apache-2.0"

RUN pip install --no-cache-dir vibescore

WORKDIR /project

ENTRYPOINT ["vibescore"]

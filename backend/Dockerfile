FROM python:3.11-slim

# Install build deps so C extensions (e.g. blis via spacy/openai-guardrails) can compile when no wheel exists (e.g. aarch64).
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY . .

ENTRYPOINT ["./entrypoint.sh"]

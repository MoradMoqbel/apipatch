# ── ApiPatch Webhook Server — Dockerfile ──────────────────────────────────────
# Build:  docker build -t apipatch .
# Run:    docker run --env-file .env -p 8080:8080 apipatch
# ──────────────────────────────────────────────────────────────────────────────

FROM python:3.11-slim

# Metadata
LABEL maintainer="Morad Moqbel <moradyunes2@gmail.com>"
LABEL description="ApiPatch — Autonomous AI Agent Webhook Server"
LABEL version="0.8.1"

# Security: run as non-root user
RUN groupadd -r apipatch && useradd -r -g apipatch apipatch

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
        git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy project files
COPY pyproject.toml ./
COPY apipatch/ ./apipatch/

# Install package + all AI provider dependencies
RUN pip install --no-cache-dir ".[ai]"

# Switch to non-root user
USER apipatch

# Expose webhook port
EXPOSE 8080

# Health check — verifies the server is accepting connections
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health', timeout=4)" 
    || exit 1

# Default entrypoint: run webhook server
ENTRYPOINT ["apipatch", "webhook"]
CMD ["--host", "0.0.0.0", "--port", "8080"]

# ─────────────────────────────────────────────────────────────────────────────
# Dockerfile — Multi-Agent LangGraph WebSocket Server (ECS Fargate)
#
# Build:  docker build --platform linux/amd64 -t multi-agent-api .
# Run:    docker run --env-file .env -p 8000:8000 multi-agent-api
# ─────────────────────────────────────────────────────────────────────────────

FROM python:3.11-slim

WORKDIR /app

# ── System dependencies ───────────────────────────────────────────────────────
# lxml (BeautifulSoup parser) needs libxml2; psycopg[binary] needs libpq.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libxml2-dev \
    libxslt-dev \
    libpq-dev \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# ── Python dependencies (layer-cached) ────────────────────────────────────────
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Application code ──────────────────────────────────────────────────────────
COPY config/      ./config/
COPY agents/      ./agents/
COPY graph/       ./graph/
COPY guardrails/  ./guardrails/
COPY evaluation/  ./evaluation/
COPY tools/       ./tools/
COPY api/         ./api/

# ── Health check (used by ECS / ALB) ──────────────────────────────────────────
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# ── Security: non-root user ───────────────────────────────────────────────────
RUN useradd --create-home appuser
USER appuser

EXPOSE 8000

# ── Entry point ───────────────────────────────────────────────────────────────
# Single worker: the compiled LangGraph + WebSocket state live in-process.
# Scale by running more ECS tasks behind the ALB, not more workers per task.
CMD ["uvicorn", "api.websocket_server:app", "--host", "0.0.0.0", "--port", "8000"]

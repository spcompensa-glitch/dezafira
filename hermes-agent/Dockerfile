# ============================================================================
# Nous Hermes Agent — Dezafira Microservice
# ============================================================================
# Agent IA com memória persistente, shell, cron, subagents
# Roda como API server (gateway mode) na porta 9119
# ============================================================================

FROM python:3.11-slim AS base

# System deps: git, curl, ffmpeg, ripgrep (busca), build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    ffmpeg \
    ripgrep \
    build-essential \
    gcc \
    g++ \
    make \
    cmake \
    openssh-client \
    && rm -rf /var/lib/apt/lists/*

# Instalar uv (package manager rápido do Astral)
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:${PATH}"

# ============================================================================
# Stage 2: Nous Hermes Agent
# ============================================================================

FROM base AS hermes

WORKDIR /opt

# Clonar Nous Hermes Agent (última release estável)
RUN git clone --depth 1 --branch v0.18.2 \
    https://github.com/NousResearch/hermes-agent.git /opt/hermes || \
    git clone --depth 1 https://github.com/NousResearch/hermes-agent.git /opt/hermes

WORKDIR /opt/hermes

# Instalar dependências Python com uv
RUN uv sync --frozen --no-dev 2>/dev/null || uv sync --no-dev
# Instalar aiohttp (necessário para API server gateway)
RUN /opt/hermes/.venv/bin/pip install aiohttp

# ============================================================================
# Stage 3: Runtime
# ============================================================================

FROM hermes AS runtime

# Diretórios de trabalho
RUN mkdir -p /workspace/tools /workspace/outputs

# Copiar ferramentas Dezafira
COPY tools/ /workspace/tools/
COPY config.yaml /workspace/config.yaml
COPY setup_dezafira.py /workspace/setup_dezafira.py
COPY start.sh /workspace/start.sh
RUN chmod +x /workspace/start.sh

# Environment
ENV HERMES_HOME=/opt/data
ENV HERMES_DISABLE_LAZY_INSTALLS=1
ENV HERMES_ALLOW_ROOT_GATEWAY=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PATH="/opt/hermes/.venv/bin:/opt/hermes/bin:${PATH}"

WORKDIR /workspace
EXPOSE 9119

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:9119/v1/models || exit 1

# Start script (setup on first boot + gateway)
CMD ["/workspace/start.sh"]

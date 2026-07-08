#!/bin/bash
# ============================================================================
# Dezafira — Start script para Nous Hermes Agent
# ============================================================================

echo "[Dezafira] Iniciando Nous Hermes Agent..."

# Rodar setup na primeira vez
if [ ! -f "/opt/data/.setup_done" ]; then
    echo "[Dezafira] Primeira execução — rodando setup..."
    python /workspace/setup_dezafira.py
    touch /opt/data/.setup_done
    echo "[Dezafira] Setup concluído!"
fi

# Criar diretórios necessários
mkdir -p /workspace/outputs
mkdir -p /opt/data/skills

# Copiar config para HERMES_HOME (/opt/data)
cp /workspace/config.yaml /opt/data/config.yaml 2>/dev/null || true

echo "[Dezafira] Iniciando gateway (API server)..."
echo "[Dezafira] Porta: 9119"
echo "[Dezafira] Health check: /v1/models"

# Iniciar Nous Hermes Agent em modo gateway
echo "[Dezafira] Iniciando gateway via hermes CLI..."
exec /opt/hermes/.venv/bin/hermes gateway

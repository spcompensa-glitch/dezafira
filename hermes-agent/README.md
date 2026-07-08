# Hermes Agent — Dezafira Microservice

## O que é

O Nous Hermes Agent roda como microserviço separado no Railway, fornecendo:
- **Memória persistente** (SQLite) - lembra conversas entre sessões
- **Shell tools** - executa scripts Python do Dezafira
- **Cron** - agendamento automático de tarefas
- **Subagents** - workers paralelos
- **Skills** - cria ferramentas automaticamente

## Deploy no Railway

### 1. Criar novo serviço no Railway
- Nome: `hermes-agent`
- Source: GitHub repo `dezafira`
- Dockerfile path: `hermes-agent/Dockerfile`

### 2. Configurar variáveis de ambiente
```
NVIDIA_API_KEY=nvapi-your-key-here
DEEPSEEK_API_KEY=sk-your-key-here
HERMES_HOME=/opt/data
API_SERVER_HOST=0.0.0.0
API_SERVER_KEY=<gerar-secret>
```

### 3. Adicionar volume persistente
- Mount path: `/opt/data`
- Nome: `hermes-state`

### 4. Configurar deploy
- Start command: `/opt/hermes/.venv/bin/python -m hermes_cli gateway run`
- Health check: `/v1/models`

## Ferramentas Disponíveis

| Script | O que faz |
|--------|-----------|
| `tools/produce_video.py` | Produz vídeo via HermesOrchestrator |
| `tools/research.py` | Pesquisa tendências de nicho |
| `tools/upload.py` | Faz upload para YouTube |
| `tools/manage_channels.py` | Gerencia canais (list/create/delete) |
| `tools/analyze_performance.py` | Analisa métricas de performance |

## Uso via Shell

```bash
# Produzir vídeo
python /workspace/tools/produce_video.py "neurociência" "default" "vertical"

# Pesquisar nicho
python /workspace/tools/research.py "tech"

# Listar canais
python /workspace/tools/manage_channels.py list

# Analisar performance
python /workspace/tools/analyze_performance.py week
```

## Comunicação com Dezafira Backend

O Nous Hermes Agent comunica com o Dezafira Backend via:
- **Shell**: Executa scripts Python que importam nossos módulos
- **API**: Expõe endpoint HTTP na porta 9119
- **Memória**: Salva contexto entre sessões (SQLite)

## Cron Jobs Configurados

| Job | Schedule | O que faz |
|-----|----------|-----------|
| `produzir_videos_diarios` | Todo dia 9h | Pesquisa tendências e produz 3 vídeos |
| `analise_semanal` | Todo domingo 18h | Analisa performance da semana |

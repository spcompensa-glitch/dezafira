# DEZAFIRA — Arquitetura do Sistema

> **Fábrica de Canais Autônoma** — Geração de vídeos YouTube Shorts 100% automatizada.
> Motor de renderização: **OpenMontage** (via NVIDIA AI) com fallback **MoviePy + Pexels**.

---

## 🏗️ Visão Geral da Arquitetura

```
┌────────────────────────────────────────────────────────────────────┐
│                    FRONTEND (Next.js 15)                           │
│   Porta 3000                                                       │
│   • Factory Studio → Disparo de produção                           │
│   • Mission Control → Monitoramento em tempo real                 │
│   • Hermes Chat → Orquestrador conversacional                     │
└──────────────────────┬─────────────────────────────────────────────┘
                       │ HTTP REST + WebSocket (polling 3s)
┌──────────────────────▼─────────────────────────────────────────────┐
│                     BACKEND (FastAPI)                               │
│   Porta 8000                                                        │
│                                                                     │
│  ┌──────────────┐    ┌──────────────────┐    ┌─────────────────┐  │
│  │  Hermes Chat │    │  Mission Control │    │   Shared Memory │  │
│  │  (server.py) │    │  /factory/*      │    │  /channels/*/   │  │
│  └──────┬───────┘    └────────┬─────────┘    │  knowledge      │  │
│         │                     │              └────────┬────────┘  │
│         ▼                     ▼                       │           │
│  ┌────────────────────────────────────────────────────┘           │
│  │                   SWARM AGENTS                                  │
│  │  agent_triage → agent_writer → agent_seo → agent_producer      │
│  └─────────────────────────────────────────────────────────────────┘
│                                                                     │
│  ┌──────────────┐    ┌──────────────────┐    ┌─────────────────┐  │
│  │  Trend Hunter│    │  SniperBrain     │    │   Kokoro TTS    │  │
│  │  (Scrapling) │    │  (NVIDIA NIM)    │    │   (CPU-friendly)│  │
│  └──────────────┘    └──────────────────┘    └─────────────────┘  │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │              OPEN MONTAGE BRIDGE                               │  │
│  │  services/open_montage_bridge.py                                │  │
│  │  • Modo 1: OpenMontage + Remotion (primário)                   │  │
│  │  • Modo 2: MoviePy + Pexels (fallback)                         │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │              SHARED MEMORY SYSTEM                               │  │
│  │  services/memory_service.py                                     │  │
│  │  • Tabela channel_knowledge no SQLite                           │  │
│  │  • Agentes compartilham aprendizados                            │  │
│  │  • Feedbacks de aprovação/rejeição salvos                       │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  ┌──────────────┐    ┌──────────────────┐    ┌─────────────────┐  │
│  │  Database    │    │  Uploader        │    │  Telegram Bot   │  │
│  │  SQLAlchemy  │    │  Playwright      │    │  (pyTelegramBot)│  │
│  │  SQLite/PG   │    │  YouTube Studio  │    │  Notificações   │  │
│  └──────────────┘    └──────────────────┘    └─────────────────┘  │
└────────────────────────────────────────────────────────────────────┘
```

---

## 📦 Stack Tecnológica

| Camada | Tecnologia | Versão | Licença |
|--------|-----------|--------|---------|
| **Backend** | FastAPI | 0.110+ | MIT |
| **LLM Primário** | NVIDIA NIM (Llama 3.3 70B) | — | Free Tier |
| **LLM Fallback** | DeepSeek API | — | Pago |
| **TTS** | Kokoro | 0.9+ | Apache 2.0 |
| **Motor de Vídeo** | OpenMontage + Remotion | — | MIT |
| **Fallback Vídeo** | MoviePy + Pexels | 2.0+ | MIT |
| **Legendas** | Whisper (tiny/base) | — | MIT |
| **Upload** | Playwright Stealth | 1.42+ | Apache 2.0 |
| **Upload (API)** | YouTube Data API v3 | — | Google ToS |
| **Banco** | SQLite / PostgreSQL | — | — |
| **Frontend** | Next.js 15 + React 19 | — | MIT |
| **Bot** | pyTelegramBotAPI | 4.18+ | GPL |
| **Trends** | Scrapling | 1.0+ | Apache 2.0 |

---

## 🧠 Pipeline de Produção (Fluxo Completo)

```
1. DISPARO
   ├── POST /api/v1/predictions { prompt, brand, channel }
   ├── /produzir [tema] via Telegram
   └── Hermes Chat detecta "produzir/iniciar"

2. TRIAGEM (agent_triage)
   ├── Trend Hunter busca tendências no YouTube
   ├── Seed conhecimento padrão (Shared Memory)
   └── Define o melhor título/tópico

3. ROTEIRO (agent_writer + SniperBrain)
   ├── Consulta Shared Memory (tom de voz, growth hacks)
   ├── LLM (NVIDIA NIM) gera:
   │   • Título com gatilho de curiosidade
   │   • Script otimizado (hook nos primeiros 3s)
   │   • Visual keywords para busca de mídia
   └── Validação: rejeita roteiros que começam com saudações

4. SEO (agent_seo)
   ├── Gera tags, descrição
   ├── Consulta blacklist de SEO no Shared Memory
   └── Prepara metadados para o YouTube

5. LOCUÇÃO (Kokoro TTS)
   ├── Converte script em áudio WAV/MP3
   └── CPU-friendly (3-5x real-time)

6. PRODUÇÃO DE VÍDEO (agent_producer + OpenMontage Bridge)
   ├── MODO 1 (Primário): OpenMontage + Remotion
   │   → Gera props JSON para o Remotion
   │   → Executa npx remotion render
   │   → Retorna MP4 final
   ├── MODO 2 (Fallback): MoviePy + Pexels
   │   → Busca clipes no Pexels
   │   → Concatena + insere áudio + legendas
   │   → Exporta MP4
   └── Registra sucesso/falha no Shared Memory

7. CURADORIA HUMANA
   ├── Vídeo disponível no histórico
   ├── Botões Aprovar (✅) / Rejeitar (❌) na UI
   └── Feedback salvo no Shared Memory

8. UPLOAD
   ├── Se aprovado: Playwright faz upload no YouTube Studio
   └── Fallback: YouTube API OAuth
```

---

## 🧩 Shared Memory System (channel_knowledge)

### Tabela no Banco

```sql
CREATE TABLE channel_knowledge (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_id VARCHAR(50) NOT NULL,      -- FK para channels
    category VARCHAR(50) NOT NULL,        -- style_guide, growth_hack, pexels_fallback, etc.
    meta_key VARCHAR(100) NOT NULL,       -- tom_de_voz, failed_keyword_X, hook_rule
    meta_value TEXT NOT NULL,             -- Valor do conhecimento
    source VARCHAR(50),                   -- hermes, deepseek, user_feedback
    created_at DATETIME DEFAULT NOW(),
    updated_at DATETIME DEFAULT NOW()
);
```

### Categorias

| Categoria | Descrição | Exemplo |
|-----------|-----------|---------|
| `style_guide` | Tom de voz e regras de estilo | "tom_de_voz: Direto e objetivo" |
| `growth_hack` | Táticas de growth hacking | "hook_3_segundos: Começar com fato intrigante" |
| `pexels_fallback` | Keywords que falharam no Pexels | "failed_keyword_alien: Evitar buscar" |
| `seo_blacklist` | Palavras/padrões SEO a evitar | "palavra_proibida_X: Evitar no título" |
| `audience_insight` | Insights sobre o público | "faixa_etaria: 18-25 anos" |
| `success_pattern` | Padrões de vídeos de sucesso | "success_keyword_X: Gerou bom engajamento" |

### Benefícios

- **Economia de tokens**: Agentes não precisam repetir contexto
- **Aprendizado contínuo**: O sistema melhora com o tempo
- **Personalização por canal**: Cada canal tem seu próprio tom de voz
- **Feedback Loop**: Aprovações/rejeições na UI alimentam a memória

---

## 🤖 OpenMontage Integration

### Modos de Operação

| Modo | Descrição | Quando Usar |
|------|-----------|-------------|
| **FULL_PIPELINE** | OpenMontage + Remotion (via subprocess) | OpenMontage instalado e configurado |
| **FALLBACK** | MoviePy + Pexels + Whisper | OpenMontage não disponível ou falhou |

### Como o Bridge Funciona

```
agent_producer()
    │
    ▼
produce_video()  ← services/open_montage_bridge.py
    │
    ├─ is_open_montage_available()?
    │   ├─ Sim → run_open_montage_pipeline()
    │   │          ├─ Gera props JSON
    │   │          ├─ npx remotion render → MP4
    │   │          └─ Retorna resultado
    │   │
    │   └─ Não → run_fallback_pipeline()
    │              ├─ PexelsClient.search_and_download()
    │              ├─ assemble_video() (MoviePy)
    │              └─ Retorna resultado
    │
    ▼
Retorna video_path + status
```

---

## 🛸 Endpoints da API

### Produção

| Método | Rota | Descrição |
|--------|------|-----------|
| `POST` | `/api/v1/predictions` | Criar nova produção |
| `GET` | `/api/v1/predictions/history` | Histórico de vídeos |
| `GET` | `/api/v1/predictions/{id}/result` | Resultado de uma produção |
| `POST` | `/.../{id}/approve` | Aprovar vídeo para upload |
| `POST` | `/.../{id}/reject` | Rejeitar vídeo |
| `POST` | `/api/v1/factory/dispatch` | Disparar pipeline via Swarm |

### Monitoramento

| Método | Rota | Descrição |
|--------|------|-----------|
| `GET` | `/api/v1/factory/monitor-stats` | Métricas consolidadas da fábrica |
| `GET` | `/api/v1/factory/openmontage-status` | Status da integração OpenMontage |
| `GET` | `/api/v1/logs` | Logs de atividade em tempo real |

### Shared Memory

| Método | Rota | Descrição |
|--------|------|-----------|
| `GET` | `/api/v1/channels/{id}/knowledge` | Listar conhecimentos do canal |
| `POST` | `/api/v1/channels/{id}/knowledge` | Salvar conhecimento no canal |

### Hermes / Chat

| Método | Rota | Descrição |
|--------|------|-----------|
| `POST` | `/api/v1/hermes/chat` | Conversar com o Hermes |
| `GET` | `/api/v1/hermes/history` | Histórico do chat |
| `POST` | `/api/v1/hermes/clear` | Limpar histórico |
| `POST` | `/api/v1/hermes/analyze-video` | Análise reversa de concorrente |

### Canais

| Método | Rota | Descrição |
|--------|------|-----------|
| `GET` | `/api/v1/channels` | Listar canais |
| `POST` | `/api/v1/channels` | Criar canal |
| `DELETE` | `/api/v1/channels/{id}` | Remover canal |
| `POST` | `/.../login-stealth` | Login stealth no Google |
| `GET` | `/.../connection-status` | Status da conexão |
| `POST` | `/.../submit-2fa` | Enviar código 2FA |

---

## 📁 Estrutura de Diretórios

```
SniperVideoEngine/
├── server.py                          # API FastAPI (ponto de entrada)
├── manager.py                         # SniperDirector - orquestrador
├── orchestrator.py                    # MoviePy + Whisper (fallback)
├── start_local.py                     # Inicialização local
├── setup_dezafira.py                  # Script de setup automatizado
├── requirements.txt                   # Dependências Python
├── Dockerfile                         # Docker para Railway
├── .env.example                       # Template de variáveis de ambiente
├── ARCHITECTURE.md                    # Este arquivo
│
├── modules/
│   ├── brain.py                       # SniperBrain (LLM NVIDIA NIM)
│   ├── voice_gen.py                   # Kokoro TTS (Apache 2.0)
│   ├── pexels_client.py               # Pexels API client
│   ├── scrapling_agent.py             # Trend hunter (YouTube)
│   ├── swarm_agents.py                # Pipeline assíncrona (Triage→Writer→SEO→Producer)
│   ├── database.py                    # SQLAlchemy ORM (SQLite/PostgreSQL)
│   ├── uploader.py                    # Playwright YouTube upload
│   ├── youtube_api_uploader.py        # YouTube API OAuth upload
│   ├── agent_login.py                 # Login stealth Google
│   └── telegram_bot.py                # Telegram Bot (Hermes)
│
├── services/
│   ├── open_montage_bridge.py         # OpenMontage integration
│   ├── memory_service.py              # Shared Memory System
│   └── video_engine.py                # Legacy DeepSeek pipeline
│
├── brand_config/
│   ├── brand_bible.md                 # Identidade visual/tonal
│   ├── target_audience.md             # Definição de público
│   ├── voice_guide.md                 # Guia de voz e estilo
│   └── ctas.md                        # Calls to action
│
└── OpenMontage/                       # Motor de renderização (submódulo)
    ├── tools/                         # 48+ ferramentas Python
    ├── remotion-composer/             # Remotion (React/Node.js)
    ├── pipeline_defs/                 # Definições de pipeline YAML
    ├── skills/                        # Skills para agentes
    └── ...
```

---

## 🌐 Variáveis de Ambiente

```bash
# Obrigatório (pelo menos uma)
NVIDIA_API_KEY=           # Primário - Llama 3.3 70B via Nvidia NIM
DEEPSEEK_API_KEY=         # Fallback
PEXELS_API_KEY=           # Vídeos stock gratuitos

# Upload (obrigatório para Playwright)
# Cookies são salvos no banco via login stealth

# Opcional
TELEGRAM_BOT_TOKEN=       # Notificações Telegram
TELEGRAM_CHAT_ID=         # Seu chat ID
GOOGLE_CLIENT_ID=         # OAuth YouTube API
GOOGLE_CLIENT_SECRET=     # OAuth YouTube API
DATABASE_URL=             # PostgreSQL (padrão: SQLite)
```

---

## 💰 Orçamento (Custo por Vídeo)

| Item | Custo |
|------|-------|
| NVIDIA NIM (LLM) | $0 (free tier) |
| DeepSeek API | ~$0.001 (fallback) |
| Kokoro TTS | $0 (open-source, local) |
| OpenMontage / Remotion | $0 (open-source) |
| Pexels API | $0 (free tier generoso) |
| MoviePy + Whisper | $0 (open-source, local) |
| Playwright | $0 (open-source, local) |
| **TOTAL por vídeo** | **~$0.001** (centavos) |

---

## 🔄 Fluxo de Curadoria Humana

```
1. Pipeline produz vídeo automaticamente
2. Status muda para "ready"
3. UI mostra preview + botões:
   ┌─────────────┐  ┌─────────────┐
   │ ✅ APROVAR  │  │ ❌ REJEITAR │
   └─────────────┘  └─────────────┘
4. Se aprovado:
   → Upload via Playwright no YouTube Studio
   → Notificação no Telegram
5. Se rejeitado:
   → Feedback salvo no Shared Memory
   → Próximo vídeo incorpora o aprendizado
```

---

## 🧪 Growth Hacker — Especialização do Hermes

O Hermes foi especializado com as seguintes regras de crescimento:

### Regra 1: Hook Implacável (Primeiros 3 Segundos)
- **NUNCA** começar com saudações ("Olá pessoal", "Bem-vindos")
- Começar direto no ápice: fato intrigante, pergunta provocativa
- Validação pós-geração rejeita scripts que violam a regra

### Regra 2: Engenharia de CTR (Títulos)
- Usar fórmula [Gatilho de Curiosidade] + [Fato Inesperado]
- Ex: "A mentira que te contaram sobre..." ao invés de "História de..."
- Máximo 60 caracteres

### Regra 3: Ritmo Visual
- Nenhuma cena > 2.5 segundos
- Alternar keywords visuais para manter ritmo frenético
- Maximizar tempo de exibição (retention time)

---

## 📝 Licenças

- **Dezafira Core**: MIT
- **OpenMontage**: MIT
- **Kokoro TTS**: Apache 2.0
- **MoviePy**: MIT
- **Whisper**: MIT
- **Playwright**: Apache 2.0
- **Scrapling**: Apache 2.0

---

*Documentação gerada em 2026-07-01 — Versão 2.0*

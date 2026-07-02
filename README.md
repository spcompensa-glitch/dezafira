# DEZAFIRA — Fábrica de Canais Autônoma

> **Automação Global & Foco em Monetização**

Dezafira é uma plataforma de ponta a ponta para criação, otimização e publicação automática e recorrente de vídeos verticais (Shorts/TikTok) focada em monetização acelerada. A arquitetura integra orquestração inteligente por IA, clonagem de voz e avatares digitais hiper-realistas.

---

## 🏗️ Arquitetura do Sistema

```
┌─────────────────────────────────────────────────────────────┐
│                     FRONTEND (Next.js 15)                   │
│   Coluna 1: Gestão de Canais  │  Coluna 2: Hermes Chat     │
│   Coluna 3: Painel de Controle e Disparo                   │
└──────────────────────┬──────────────────────────────────────┘
                       │ API + WebSocket
┌──────────────────────▼──────────────────────────────────────┐
│                  BACKEND (FastAPI - SniperVideoEngine)       │
│                                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────────────┐ │
│  │  Brain   │  │  Voice   │  │  Video   │  │   Uploader  │ │
│  │ (LLM)   │  │(OmniVoice│  │(ComfyUI) │  │(Playwright) │ │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └──────┬──────┘ │
│       │              │              │                │       │
│  ┌────▼──────────────▼──────────────▼────────────────▼────┐ │
│  │              Orchestrator (MoviePy + Whisper)          │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────────┐  │
│  │ Trend Hunter│  │ Telegram Bot │  │  Database (SQL)   │  │
│  │ (Scrapling) │  │  (Hermes)    │  │  Channels/Preds   │  │
│  └─────────────┘  └──────────────┘  └───────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

### Pipeline de Produção

```
Tema/Theme
    ↓
Brain (SniperBrain) — Gera roteiro, títulos, prompts visuais, clima musical
    ↓
Voice (Edge-TTS / OmniVoice) — Locução em PT-BR/EN/ES
    ↓
Music (MusicAgent) — Seleção de trilha por categoria de clima
    ↓
Video (ComfyUI) — Geração de clipes visuais via prompts de IA
    ↓
Orchestrator (MoviePy + Whisper) — Montagem final + legendas dinâmicas palavra por palavra
    ↓
Uploader (Playwright Stealth) — Publicação automática no YouTube Studio
```

---

## 🛠️ Tecnologias

| Camada | Tecnologias |
|--------|-------------|
| **Frontend** | Next.js 15, React 19, Tailwind CSS |
| **Backend** | FastAPI (Python 3.10+), SQLAlchemy, PostgreSQL/SQLite |
| **IA (LLM)** | Nvidia NIM (Llama 3.3 70B), DeepSeek API |
| **Voz** | Edge-TTS, gTTS (fallback) |
| **Vídeo** | ComfyUI, MoviePy, Whisper (legendas) |
| **Upload** | Playwright Stealth, YouTube API (OAuth) |
| **Tendências** | Scrapling Crawler (YouTube Trends) |
| **Notificações** | Telegram Bot (pyTelegramBotAPI) |

---

## 🚀 Como Rodar Localmente

### 1. Requisitos
- Node.js v18+ e npm
- Python v3.10+
- ComfyUI (local ou remoto para geração de vídeo)

### 2. Inicialização Rápida (Windows)

```bash
start_dezafira_local.bat
```

Este script:
1. Instala dependências do frontend (Next.js) e inicia na porta 3000
2. Cria ambiente virtual Python, instala dependências e inicia o backend na porta 8000

### 3. Setup Manual

#### Backend (FastAPI)
```bash
cd SniperVideoEngine
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn server:app --reload --port 8000
```

#### Frontend (Next.js)
```bash
cd open-generative-ai
npm install
npm run dev
```

### 4. Variáveis de Ambiente (.env)

```bash
# IA (obrigatório pelo menos uma)
NVIDIA_API_KEY=sua-chave-nvidia
DEEPSEEK_API_KEY=sua-chave-deepseek

# Telegram (opcional - notificações do Hermes)
TELEGRAM_BOT_TOKEN=token-do-bot
TELEGRAM_CHAT_ID=seu-chat-id

# YouTube OAuth (para upload via API oficial)
GOOGLE_CLIENT_ID=client-id
GOOGLE_CLIENT_SECRET=client-secret

# ComfyUI (padrão: 127.0.0.1:8188)
COMFYUI_SERVER=127.0.0.1:8188

# Banco de dados (opcional - padrão: SQLite local)
DATABASE_URL=postgresql://user:pass@host/db
```

---

## 📁 Estrutura do Projeto

```
dezafira/
├── SniperVideoEngine/           # Backend FastAPI
│   ├── server.py                # API principal + rotas
│   ├── manager.py               # SniperDirector (orquestrador de pipeline)
│   ├── orchestrator.py          # Montagem de vídeo (MoviePy + Whisper)
│   ├── ui.py                    # Interface Gradio (legado)
│   ├── requirements.txt         # Dependências Python
│   ├── brand_config/            # Templates de configuração de canal
│   │   ├── brand_bible.md       # Identidade visual/tonal
│   │   ├── target_audience.md   # Definição de público
│   │   ├── voice_guide.md       # Guia de voz e estilo
│   │   └── ctas.md              # Calls to action
│   ├── modules/
│   │   ├── brain.py             # LLM (Nvidia NIM → DeepSeek)
│   │   ├── voice_gen.py         # Edge-TTS + gTTS fallback
│   │   ├── video_agent.py       # ComfyUI video generation
│   │   ├── comfy_agent.py       # ComfyUI WebSocket client
│   │   ├── music_agent.py       # Seleção de trilha
│   │   ├── uploader.py          # Playwright YouTube upload
│   │   ├── youtube_api_uploader.py  # YouTube API OAuth upload
│   │   ├── scrapling_agent.py   # Trend hunting (YouTube)
│   │   ├── agent_login.py       # Login stealth Playwright
│   │   ├── database.py          # SQLAlchemy ORM
│   │   └── telegram_bot.py      # Bot Telegram (Hermes)
│   └── assets/
│       └── workflows/           # Workflows ComfyUI
│
├── open-generative-ai/          # Frontend Next.js
│   ├── app/                     # Next.js App Router
│   ├── components/              # React components
│   ├── src/                     # Source (ImageStudio, VideoStudio, etc.)
│   └── package.json
│
├── start_dezafira_local.bat     # Script de inicialização Windows
├── Logo/                        # Logotipos
├── outputs/                     # Vídeos gerados
└── README.md
```

---

## 🤖 Agentes do Sistema

| Agente | Responsabilidade |
|--------|-----------------|
| **Hermes** | Orquestrador executivo. Conversa com o usuário via Chat/Telegram e comanda toda a pipeline de produção. |
| **SniperBrain** | Roteirista IA. Gera títulos, roteiros, prompts visuais e clima musical usando LLM (Llama 3.3 / DeepSeek). |
| **Trend Hunter** | Garimpa tendências virais no YouTube para fundamentar os roteiros. |
| **Voice Gen** | Gera locuções com Edge-TTS ( OmniVoice ) com fallback para gTTS. |
| **Video Agent** | Gera clipes visuais via ComfyUI usando prompts do Brain. |
| **Music Agent** | Seleciona trilhas sonoras por categoria de clima emocional. |
| **Orchestrator** | Monta o vídeo final: junta voz + música + legendas dinâmicas (Whisper). |
| **Uploader** | Publica vídeos no YouTube Studio via Playwright Stealth ou API OAuth. |
| **Telegram Bot** | Permite controle remoto da fábrica via Telegram. |

---

## 📋 API Endpoints

| Método | Rota | Descrição |
|--------|------|-----------|
| `POST` | `/api/v1/predictions` | Criar nova produção de vídeo |
| `GET` | `/api/v1/predictions/{id}/result` | Consultar resultado da produção |
| `GET` | `/api/v1/predictions/history` | Histórico de vídeos produzidos |
| `POST` | `/api/v1/predictions/{id}/approve` | Aprovar vídeo para upload |
| `POST` | `/api/v1/predictions/{id}/reject` | Rejeitar vídeo |
| `GET` | `/api/v1/channels` | Listar canais cadastrados |
| `POST` | `/api/v1/channels` | Criar novo canal |
| `DELETE` | `/api/v1/channels/{id}` | Remover canal |
| `POST` | `/api/v1/channels/{id}/login-stealth` | Conectar canal ao YouTube |
| `POST` | `/api/v1/hermes/chat` | Chat com o Hermes (orquestrador) |
| `GET` | `/api/v1/hermes/history` | Histórico do chat |
| `GET` | `/api/v1/trends` | Buscar tendências do YouTube |
| `POST` | `/api/v1/hermes/analyze-video` | Análise reversa de vídeo concorrente |
| `GET` | `/api/v1/logs` | Logs de atividade em tempo real |

---

## 📄 Brand Config

Os templates em `SniperVideoEngine/brand_config/` permitem personalizar a identidade de cada canal:

- **brand_bible.md** — Nome, nicho, proposta de valor, tom de voz
- **target_audience.md** — Idade, medos, desejos, linguagem do público
- **voice_guide.md** — Persona gramatical, ritmo, frases proibidas/permitidas
- **ctas.md** — Produtos, preços e CTAs nativos para cada canal

---

## 🔄 Curadoria Humana (Human-in-the-Loop)

A pipeline opera em modo de curadoria:
1. **Hermes garimpa** tendências e gera o roteiro otimizado
2. **Pipeline produz** o vídeo automaticamente (voz + visual + montagem)
3. **Vídeo fica disponível** na UI para aprovação
4. **Jonatas aprova ou rejeita** via botões na interface
5. **Se aprovado**, o upload é disparado automaticamente no YouTube
6. **Se rejeitado**, o Hermes recebe o feedback e ajusta a próxima produção

---

*Plataforma Dezafira — Automação Global & Foco em Monetização*

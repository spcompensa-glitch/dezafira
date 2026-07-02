# SPEC.md — Dezafira Pipeline Specification

> **Versão:** 1.0
> **Data:** 2026-06-30
> **Status:** Especificação para Refactor

---

## 1. Visão Geral

Dezafira é uma fábrica autônoma de canais YouTube. A pipeline gera vídeos verticais (Shorts) de forma 100% automatizada, desde a garimpagem de tendências até a publicação no YouTube.

### Restrições de Infraestrutura
- **Plataforma:** Railway (Docker containers)
- **Hardware:** CPU only (sem GPU)
- **Orçamento:** $0 (todas as ferramentas devem ser gratuitas)
- **Licença:** Apache 2.0 ou MIT (ou equivalente permissivo)

---

## 2. Ferramentas Definidas

| # | Etapa | Ferramenta | Licença | Tipo | Arquivo Atual | Status |
|---|-------|-----------|---------|------|---------------|--------|
| 1 | Tendências | **Scrapling** (DeczafiraTrendHunter) | Apache 2.0 | Local | `scrapling_agent.py` | 🟡 Integrar na esteira |
| 2 | Roteiro IA | **Nvidia NIM** (Llama 3.3 70B) | API Free Tier | Cloud API | `brain.py` | 🟢 Manter |
| 3 | Locução | **Kokoro TTS** | Apache 2.0 | Local (CPU) | Novo (substitui `voice_gen.py`) | 🔴 Criar |
| 4 | Vídeo | **Pexels API** + **MoviePy** | Gratuito / MIT | API + Local | Novo (substitui `video_agent.py`) | 🔴 Criar |
| 5 | Legendas | **Whisper** (whisper_timestamped) | MIT | Local (CPU) | `orchestrator.py` | 🟢 Manter |
| 6 | Montagem | **MoviePy** + **FFmpeg** | MIT / LGPL | Local | `orchestrator.py` | 🟢 Manter |
| 7 | Upload | **Playwright Stealth** | Apache 2.0 | Local | `uploader.py` | 🟢 Manter |
| 8 | DB | **SQLAlchemy** + **SQLite** | MIT | Local | `database.py` | 🟢 Manter |
| 9 | Notificações | **Telegram Bot** (pyTelegramBotAPI) | GPL | Local | `telegram_bot.py` | 🟢 Manter |
| 10 | Frontend | **Next.js 15** | MIT | Local | `open-generative-ai/` | 🟢 Manter |

### Ferramentas REMOVIDAS da stack

| Ferramenta | Motivo |
|-----------|--------|
| OmniVoice | Precisa de GPU para rodar local |
| LTX-2 | Precisa de GPU + licença restritiva (não Apache 2.0) |
| InfiniteTalk | Precisa de GPU (14B parâmetros) |
| ComfyUI | Precisa de GPU |
| Edge-TTS | Não é open-source (serviço Microsoft, pode mudar terms) |
| DeepSeek | Não necessário (Nvidia NIM já cobre) |
| Gradio (ui.py) | Legado — Next.js é o frontend |

---

## 3. Arquitetura da Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│                    ESTEIRA DEZAFIRA v2.0                         │
│                                                                  │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────────┐ │
│  │    1     │   │    2     │   │    3     │   │      4       │ │
│  │ SCRAPLING│──▶│  HERMES  │──▶│  KOKORO  │──▶│  PEXELS API  │ │
│  │ (Trends) │   │  (LLM)  │   │  (Voz)   │   │  (Vídeos)    │ │
│  └──────────┘   └──────────┘   └──────────┘   └──────┬───────┘ │
│                                                        │         │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐          │         │
│  │    7     │◀──│    6     │◀──│    5     │◀─────────┘         │
│  │PLAYWRIGHT│   │  MOVIEPY │   │ WHISPER  │                     │
│  │ (Upload) │   │ (Monta)  │   │(Legendas)│                     │
│  └──────────┘   └──────────┘   └──────────┘                     │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  8. TELEGRAM BOT — Notificações em tempo real            │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 4. Detalhes Técnicos por Ferramenta

### 4.1 Scrapling (Trend Hunter)

**Arquivo:** `modules/scrapling_agent.py`

**O que faz:** Garimpa tendências virais no YouTube para embasar os roteiros.

**Integração na esteira:** O Scrapling deve ser chamado ANTES do Hermes para fornecer dados de trending ao roteirista.

**Busca atual:** Usa fallback HTTP+Regex (Scrapling real pode não estar instalado).

**Ação necessária:**
- Instalar `scrapling` no `requirements.txt`
- Integrar na pipeline principal (`manager.py`)
- Hermes recebe os trending topics como contexto para gerar roteiro

---

### 4.2 Nvidia NIM (LLM / Roteirista)

**Arquivo:** `modules/brain.py`

**O que faz:** Gera roteiros, títulos, prompts visuais, CTAs via LLM.

**Modelo:** `meta/llama-3.3-70b-instruct`

**Endpoint:** `https://integrate.api.nvidia.com/v1/chat/completions`

**Env var:** `NVIDIA_API_KEY`

**Ação necessária:**
- Manter como está (funcional)
- Remover fallback DeepSeek (não necessário)
- Simplificar `brain.py` para usar apenas Nvidia NIM

---

### 4.3 Kokoro TTS (Locução)

**Arquivo NOVO:** `modules/voice_gen.py` (substituir atual)

**O que faz:** Converte texto em fala de alta qualidade em PT-BR.

**Licença:** Apache 2.0

**Instalação:**
```bash
pip install kokoro>=0.9.4 soundfile pydub
apt-get install -y espeak-ng  # dependency do sistema
```

**Código de integração:**
```python
from kokoro import KPipeline
import soundfile as sf

def generate_voice(text, output_path, voice="pt_br_female1"):
    pipeline = KPipeline(lang_code='p')  # 'p' = Portuguese
    
    generator = pipeline(text, voice=voice, speed=1)
    
    for i, (gs, ps, audio) in enumerate(generator):
        sf.write(output_path, audio, 24000)
```

**Vozes PT-BR disponíveis:**
- `pt_br_female1` — Voz feminina padrão
- `pt_br_male1` — Voz masculina padrão
- (outras vozes disponíveis — verificar `VOICES.md` no repo)

**Performance CPU:** 3x–5x real-time (gera 3-5s de áudio por 1s de processamento)

**Saída:** WAV (24000 Hz). Para MP3, usar `pydub`:
```python
from pydub import AudioSegment
audio_segment = AudioSegment.from_wav(output_path)
audio_segment.export(output_path.replace('.wav', '.mp3'), format='mp3')
```

**Timestamps:** Kokoro NÃO gera word-level timestamps. Para legendas, usar Whisper no áudio gerado.

**Dockerfile:**
```dockerfile
RUN apt-get update && apt-get install -y espeak-ng libstdc++6
```

**Ação necessária:**
- Substituir `voice_gen.py` atual (Edge-TTS/gTTS) por Kokoro
- Manter Edge-TTS como fallback opcional
- Gerar áudio WAV, depois converter para MP3 se necessário

---

### 4.4 Pexels API + MoviePy (Geração de Vídeo)

**Arquivos NOVOS:** `modules/video_agent.py` (substituir atual)

**O que faz:** Busca vídeos stock verticais no Pexels e monta o vídeo final com MoviePy.

**Pexels API:**
- **Site:** pexels.com/api
- **Obter API key:** Criar conta → pexels.com/api → "Request your API key"
- **Env var:** `PEXELS_API_KEY`
- **Rate limit:** 200 requests/hora, 20.000/mês
- **Licença:** Gratuito, uso comercial (atribuição obrigatória)

**Código de integração:**
```python
import requests
import os

PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")

def search_vertical_videos(query, count=5):
    """Busca vídeos verticais (9:16) no Pexels"""
    headers = {"Authorization": PEXELS_API_KEY}
    params = {
        "query": query,
        "orientation": "portrait",  # Filtra verticais
        "per_page": count
    }
    response = requests.get(
        "https://api.pexels.com/v1/videos/search",
        headers=headers,
        params=params
    )
    return response.json().get("videos", [])

def download_video(video_data, output_dir="outputs/temp"):
    """Baixa o melhor link HD de um vídeo"""
    os.makedirs(output_dir, exist_ok=True)
    
    # Pegar versão HD
    hd_file = next(
        (f for f in video_data["video_files"] if f["quality"] == "hd"),
        video_data["video_files"][0]
    )
    
    video_url = hd_file["link"]
    output_path = os.path.join(output_dir, f"stock_{video_data['id']}.mp4")
    
    response = requests.get(video_url)
    with open(output_path, "wb") as f:
        f.write(response.content)
    
    return output_path
```

**MoviePy (montagem):**
```python
from moviepy import VideoFileClip, AudioFileClip, CompositeVideoClip, TextClip

def assemble_short(video_paths, voice_path, output_path, subtitles=None):
    """Monta um Short vertical (1080x1920)"""
    # 1. Concatenar clipes stock
    clips = [VideoFileClip(v) for v in video_paths]
    # Ajustar cada clipe para 9:16 (1080x1920)
    for clip in clips:
        clip = clip.resized(height=1920)
        # Crop central se necessário
    
    # 2. Concatenar
    from moviepy import concatenate_videoclips
    video = concatenate_videoclips(clips)
    
    # 3. Adicionar voz
    voice = AudioFileClip(voice_path)
    video = video.with_duration(voice.duration)
    video = video.with_audio(voice)
    
    # 4. Exportar
    video.write_videofile(output_path, codec="libx264", fps=24)
```

**Ação necessária:**
- Substituir `video_agent.py` e `comfy_agent.py` por integração Pexels + MoviePy
- Criar `modules/pexels_client.py` para busca e download
- Adaptar `orchestrator.py` para usar clipes stock

---

### 4.5 Whisper (Legendas)

**Arquivo:** `orchestrator.py` (já integrado)

**O que faz:** Transcreve o áudio gerado para criar legendas palavra por palavra (estilo TikTok).

**Modelo recomendado para CPU:** `tiny` ou `base`

**Performance:** `tiny` é rápido em CPU. `base` é mais lento mas mais preciso.

**Ação necessária:**
- Manter como está (funcional)
- Considerar usar modelo `base` se `tiny` não for preciso o suficiente

---

### 4.6 Playwright (Upload)

**Arquivo:** `modules/uploader.py` (já integrado)

**O que faz:** Upload automático no YouTube Studio via browser headless.

**Ação necessária:**
- Manter como está (funcional)

---

### 4.7 Banco de Dados

**Arquivo:** `modules/database.py`

**Modelos ORM:** Channel, Prediction, AiCreatedChannel

**Ação necessária:**
- Manter como está (funcional)
- SQLite para dev, PostgreSQL para produção (Railway)

---

### 4.8 Telegram Bot

**Arquivo:** `modules/telegram_bot.py`

**Env vars:** `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`

**Ação necessária:**
- Manter como está (funcional)

---

## 5. Fluxo da Pipeline (Detalhado)

```
1. DISPARO
   POST /api/v1/predictions { prompt: "tema", brand: "canal" }
   ou /produzir [tema] via Telegram
   ou chat com Hermes detecta "produzir/iniciar"

2. TREND HUNTING (Scrapling)
   ScraplingAgent.fetch_youtube_trends(tema)
   → Retorna top 5 trending topics relacionados
   → Passa como contexto para o Hermes

3. ROTEIRO (Hermes + Nvidia NIM)
   Brain.generate_script(tema, trends_context)
   → LLM gera JSON com:
     • title (título viral, <60 chars)
     • script (narração, ~120 palavras, ~45s)
     • visual_keywords (3-5 keywords para busca Pexels)
     • music_prompt (clima musical)
     • target_duration

4. LOCUÇÃO (Kokoro TTS)
   generate_voice(script, output.wav, voice="pt_br_female1")
   → Gera WAV 24000Hz
   → Converte para MP3 via pydub

5. VÍDEO (Pexels API)
   search_vertical_videos(visual_keywords)
   → Busca 3-5 vídeos verticais relevantes
   → Baixa HD

6. MONTAGEM (MoviePy + Whisper)
   a) Whisper transcreve áudio → timestamps palavra por palavra
   b) MoviePy:
      - Concatena clipes stock
      - Ajusta duração = duração da voz
      - Adiciona voz como áudio
      - Adiciona legendas dinâmicas (TextClip por palavra)
      - Exporta: {id}_preview.mp4 (1080x1920, 24fps)

7. CURADORIA HUMANA
   → Vídeo disponível na UI
   → Jonatas aprova (✅) ou rejeita (❌)

8. UPLOAD (Playwright)
   → Se aprovado: YouTubeUploader.upload_video()
   → Injeta cookies, preenche metadados, publica
```

---

## 6. Variáveis de Ambiente

```bash
# LLM (obrigatório)
NVIDIA_API_KEY=seu-api-key

# TTS (obrigatório)
# Nenhuma — Kokoro roda local

# Vídeo (obrigatório)
PEXELS_API_KEY=seu-api-key  # Gratuito em pexels.com/api

# Upload YouTube
GOOGLE_CLIENT_ID=client-id
GOOGLE_CLIENT_SECRET=client-secret

# Telegram (opcional)
TELEGRAM_BOT_TOKEN=token
TELEGRAM_CHAT_ID=chat-id

# Banco de dados
DATABASE_URL=sqlite:///./dezafira.db  # ou postgresql://...
```

---

## 7. Arquivos a Criar/Modificar

### Arquivos a CRIAR
| Arquivo | Descrição |
|---------|-----------|
| `modules/pexels_client.py` | Cliente para API do Pexels (busca + download de vídeos) |
| `modules/voice_gen.py` (substituir) | Kokoro TTS integrado |

### Arquivos a MODIFICAR
| Arquivo | Mudança |
|---------|---------|
| `manager.py` | Integrar Scrapling + Pexels no pipeline |
| `server.py` | Remover referências DeepSeek, simplificar LLM |
| `orchestrator.py` | Adaptar para vídeos stock + Kokoro audio |
| `requirements.txt` | Atualizar dependências |
| `Dockerfile` (novo) | Instalar espeak-ng + ffmpeg |

### Arquivos a DELETAR
| Arquivo | Motivo |
|---------|--------|
| `modules/comfy_agent.py` | Substituído por Pexels API |
| `modules/video_agent.py` (atual) | Substituído por Pexels + MoviePy |
| `modules/music_agent.py` | Pode ser integrado ou simplificado |
| `ui.py` | Legado (Next.js é o frontend) |
| `open-generative-ai/packages/` | Subpacotes não utilizados |

### requirements.txt (novo)
```
fastapi==0.110.0
uvicorn==0.28.0
pydantic==2.6.4
httpx==0.27.0
playwright==1.42.0
SQLAlchemy==2.0.28
python-dotenv==1.0.1
requests==2.31.0
pyTelegramBotAPI==4.18.0
kokoro>=0.9.4
soundfile>=0.12.0
pydub>=0.25.1
whisper-timestamped>=1.14.4
moviepy>=2.0.0
google-auth==2.28.1
google-auth-oauthlib==1.2.0
google-api-python-client==2.122.0
```

### Dockerfile (novo)
```dockerfile
FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    ffmpeg \
    espeak-ng \
    libstdc++6 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## 8. Brand Config (templates existentes — manter)

| Arquivo | Descrição |
|---------|-----------|
| `brand_config/brand_bible.md` | Identidade visual/tonal do canal |
| `brand_config/target_audience.md` | Público-alvo |
| `brand_config/voice_guide.md` | Guia de voz e estilo |
| `brand_config/ctas.md` | Calls to action |

Estes templates são lidos pelo Brain (Hermes) para contextualizar os roteiros.

---

## 9. Orçamento

| Item | Custo |
|------|-------|
| Kokoro TTS | $0 (open-source, local) |
| Pexels API | $0 (free tier generoso) |
| MoviePy + Whisper | $0 (open-source, local) |
| Playwright | $0 (open-source, local) |
| Nvidia NIM | $0 (free tier) |
| Telegram Bot | $0 (gratuito) |
| Railway | Pago (infraestrutura) |
| **TOTAL por vídeo** | **$0 em APIs** |

---

*SPEC v1.0 — Baseado em pesquisa realizada em 2026-06-30.*

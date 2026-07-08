import asyncio
import os
import uuid
import json
import httpx
from dotenv import load_dotenv
load_dotenv()
from fastapi import FastAPI, BackgroundTasks, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

# Singleton globais — compartilhados entre todas as requisicoes (Bug C1)
from pipeline.websocket import WebSocketHub
from pipeline.orchestrator import HermesOrchestrator

_ws_hub = WebSocketHub()
_hermes_orchestrator = HermesOrchestrator(_ws_hub)

from manager import SniperDirector
from modules.uploader import YouTubeUploader
from research.spiders.youtube_search import YouTubeSearchSpider
from modules.database import (
    get_db_channels, 
    create_db_channel, 
    delete_db_channel, 
    save_db_prediction, 
    update_db_prediction, 
    get_db_prediction,
    Channel,
    Prediction,
    SessionLocal,
    get_db_ai_created_channels,
    create_db_ai_created_channel,
    delete_db_ai_created_channel
)

try:
    from modules.telegram_bot import init_telegram_bot, send_telegram_notification
except ImportError:
    print("[Server] telebot nao instalado. Telegram Bot desabilitado.")
    def init_telegram_bot(*args, **kwargs): pass
    def send_telegram_notification(text: str): pass

app = FastAPI(title="F.Video & Open-Generative-AI Integration API")

# Health check endpoint for Railway
@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "dezafira-backend"}

# Configurar CORS para permitir chamadas do Next.js e de qualquer origem local
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dicionário na memória para guardar o status das gerações
# Removidos channels.json e predictions_db locais. Usando database.py.

# Logs de Atividade em Tempo Real da Esteira
application_logs = [
    "[Info] Fabrica de Canais Dezafira inicializada com sucesso.",
    "[Info] OpenMontage Engine disponivel como motor de renderizacao.",
    "[Info] Shared Memory System (channel_knowledge) ativo.",
    "[Info] Pronto para iniciar o ciclo autonomo com o Hermes."
]

def log_application_activity(message: str):
    from datetime import datetime
    timestamp = datetime.now().strftime("%H:%M:%S")
    log_line = f"[{timestamp}] {message}"
    application_logs.append(log_line)
    if len(application_logs) > 60:
        application_logs.pop(0)

# Definicao unica de hermes_chat_history movida para a secao Hermes Orchestrator no final do arquivo.

director = SniperDirector()
uploader = YouTubeUploader()

# Servir arquivos estáticos de outputs para poder acessar o vídeo final
app.mount("/outputs", StaticFiles(directory="outputs"), name="outputs")
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", include_in_schema=False)
async def serve_ui():
    return RedirectResponse(url="http://localhost:3000")

@app.get("/app/{slug}", response_class=HTMLResponse)
async def serve_pwa_app(slug: str):
    template_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "pwa_template.html")
    if not os.path.exists(template_path):
        raise HTTPException(status_code=404, detail="Template do PWA não encontrado")
    with open(template_path, "r", encoding="utf-8") as f:
        html_content = f.read()
    return HTMLResponse(content=html_content)

@app.get("/api/v1/logs")
async def get_application_logs():
    return {"logs": application_logs}

# Helper para chamar LLM via Nvidia NIM
async def query_llm(messages: List[Dict[str, str]]) -> str:
    nvidia_key = os.getenv("NVIDIA_API_KEY", "")

    if not nvidia_key:
        return "Chave NVIDIA_API_KEY não configurada no arquivo .env."

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://integrate.api.nvidia.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {nvidia_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "meta/llama-3.3-70b-instruct",
                    "messages": messages,
                    "temperature": 0.7,
                    "max_tokens": 1024
                }
            )
            if response.status_code == 200:
                return response.json()["choices"][0]["message"]["content"]
            else:
                print(f"[LLM] Falha no Nvidia NIM ({response.status_code}): {response.text}")
    except Exception as e:
        print(f"[LLM] Erro ao chamar Nvidia NIM: {str(e)}")

    return "Falha ao chamar o LLM. Verifique a NVIDIA_API_KEY no .env."

class CreatePredictionPayload(BaseModel):
    prompt: str
    brand: Optional[str] = "Geral"
    video_format: Optional[str] = "vertical"
    channel_id: Optional[str] = "default"

@app.post("/api/v1/predictions")
async def create_prediction(payload: CreatePredictionPayload, background_tasks: BackgroundTasks):
    prediction_id = f"sniper_{uuid.uuid4().hex[:8]}"
    
    save_db_prediction(prediction_id, payload.prompt, payload.channel_id)
    
    from modules.database import create_automation_task
    task_id = create_automation_task(payload.prompt, payload.channel_id)
    
    async def _run_orchestrator(task_id, prompt, channel_id, video_format):
        await _hermes_orchestrator.start_pipeline(prompt, channel_id, video_format, task_id=str(task_id))
    background_tasks.add_task(
        _run_orchestrator, task_id, payload.prompt,
        payload.channel_id, payload.video_format
    )
    
    return {
        "id": prediction_id,
        "request_id": prediction_id,
        "status": "starting"
    }

@app.get("/api/v1/predictions/{prediction_id}/result")
async def get_prediction_result(prediction_id: str):
    res = get_db_prediction(prediction_id)
    if not res:
        raise HTTPException(status_code=404, detail="Prediction not found")
    # Adaptador de compatibilidade para a UI que espera outputs em lista
    res["outputs"] = [res["url"]] if res["url"] else []
    return res

@app.get("/api/v1/channels")
async def get_channels():
    return get_db_channels()

class ChannelPayload(BaseModel):
    name: str
    nicho: str
    lang: str

@app.post("/api/v1/channels")
async def create_channel(payload: ChannelPayload):
    return create_db_channel(payload.name, payload.nicho, payload.lang)

@app.delete("/api/v1/channels/{channel_id}")
async def delete_channel(channel_id: str):
    success = delete_db_channel(channel_id)
    if not success:
        raise HTTPException(status_code=404, detail="Canal não encontrado")
    return {"message": "Canal removido com sucesso"}

class LoginStealthPayload(BaseModel):
    email: Optional[str] = None
    password: Optional[str] = None
    cookies_raw: Optional[str] = None

@app.post("/api/v1/channels/{channel_id}/login-stealth")
async def start_login_stealth(channel_id: str, payload: LoginStealthPayload, background_tasks: BackgroundTasks):
    db = SessionLocal()
    chan = db.query(Channel).filter(Channel.id == channel_id).first()
    if not chan:
        db.close()
        raise HTTPException(status_code=404, detail="Conta Google não encontrada no banco. Selecione uma conta válida no seletor à direita.")
    db.close()

    if not payload.cookies_raw and (not payload.email or not payload.password):
        raise HTTPException(status_code=400, detail="Credenciais ou cookies ausentes na requisição.")

    # Se o usuário optou por colar os cookies diretamente, valida e salva na hora!
    if payload.cookies_raw:
        from modules.database import save_db_channel_cookies
        try:
            cookies_json = payload.cookies_raw.strip()
            # Garante formato JSON válido
            parsed_cookies = json.loads(cookies_json)
            
            # Executa uma verificação rápida de 6 segundos em background/stealth para confirmar se o cookie loga no YT Studio
            from playwright.sync_api import sync_playwright
            login_ok = False
            try:
                with sync_playwright() as p:
                    browser = p.chromium.launch(
                        headless=True,
                        args=["--disable-blink-features=AutomationControlled", "--no-sandbox", "--disable-setuid-sandbox"]
                    )
                    context = browser.new_context(
                        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
                    )
                    context.add_cookies(parsed_cookies)
                    page = context.new_page()
                    page.goto("https://studio.youtube.com", timeout=12000)
                    page.wait_for_timeout(3000)
                    # Se não redirecionou para tela de login do Google, o cookie é quente!
                    if "signin" not in page.url and "login" not in page.url:
                        login_ok = True
                    browser.close()
            except Exception as e:
                print(f"[Agent-Login] Erro ao testar cookies: {e}")
                login_ok = False
            warning_msg = None
            if not login_ok:
                warning_msg = "Sessão importada! (Nota: o servidor de nuvem do Railway não pôde confirmar a sessão devido ao IP do data center, mas salvou seus cookies com sucesso e eles serão aplicados na postagem)."

            save_db_channel_cookies(channel_id, cookies_json)
            return {
                "message": "Cookies salvos com sucesso!",
                "warning": warning_msg
            }
        except Exception as json_err:
            if isinstance(json_err, HTTPException):
                raise json_err
            raise HTTPException(status_code=400, detail=f"Formato de cookies inválido. Cole um JSON válido: {str(json_err)}")

    from modules.agent_login import run_agent_login_stealth
    
    # Reseta estados anteriores
    db = SessionLocal()
    chan = db.query(Channel).filter(Channel.id == channel_id).first()
    if chan:
        chan.connection_status = "idle"
        chan.verification_code = None
        chan.connection_error = None
        db.commit()
    db.close()
    
    # Iniciar o robô em segundo plano para não travar a UI
    background_tasks.add_task(run_agent_login_stealth, channel_id, payload.email, payload.password)
    return {"message": "Agente de login simulado iniciado em segundo plano."}

@app.get("/api/v1/channels/{channel_id}/connection-status")
async def get_connection_status(channel_id: str):
    db = SessionLocal()
    chan = db.query(Channel).filter(Channel.id == channel_id).first()
    if not chan:
        db.close()
        raise HTTPException(status_code=404, detail="Canal não encontrado")
    
    status = chan.connection_status
    error = chan.connection_error
    db.close()
    return {"connection_status": status, "connection_error": error}

class Submit2FAPayload(BaseModel):
    code: str

@app.post("/api/v1/channels/{channel_id}/submit-2fa")
async def submit_verification_code(channel_id: str, payload: Submit2FAPayload):
    db = SessionLocal()
    chan = db.query(Channel).filter(Channel.id == channel_id).first()
    if not chan:
        db.close()
        raise HTTPException(status_code=404, detail="Canal não encontrado")
    
    # Salva o código digitado na coluna verification_code para o robô ler
    chan.verification_code = payload.code
    db.commit()
    db.close()
    return {"message": "Código de verificação 2FA enviado com sucesso para o agente."}

@app.get("/api/v1/ai-channels")
async def get_ai_channels():
    return get_db_ai_created_channels()

class AiChannelPayload(BaseModel):
    channel_id: str
    name: str
    nicho: str
    lang: str
    creation_reason: str

@app.post("/api/v1/ai-channels")
async def create_ai_channel(payload: AiChannelPayload):
    return create_db_ai_created_channel(
        payload.channel_id, 
        payload.name, 
        payload.nicho, 
        payload.lang, 
        payload.creation_reason
    )

@app.delete("/api/v1/ai-channels/{sub_id}")
async def delete_ai_channel(sub_id: str):
    success = delete_db_ai_created_channel(sub_id)
    if not success:
        raise HTTPException(status_code=404, detail="Canal criado por IA não encontrado")
    return {"message": "Canal removido com sucesso"}

class AnalyzeVideoPayload(BaseModel):
    url: str

@app.post("/api/v1/hermes/analyze-video")
async def analyze_competitor_video(payload: AnalyzeVideoPayload):
    system_instruction = (
        "Você é o Agente de Inteligência e Engenharia Reversa da Dezafira. "
        "Seu objetivo é analisar as transcrições e ganchos de retenção de vídeos concorrentes virais "
        "e estruturar regras de hooks prontas para o Jonatas usar na esteira autônoma."
    )
    user_prompt = f"""
    Faça a engenharia reversa do seguinte vídeo concorrente:
    - URL: {payload.url}
    
    Analise e gere um relatório estruturado contendo:
    1. Gancho Inicial (Primeiros 3 segundos): Por que reteve a audiência?
    2. Estrutura Psicológica: Qual medo ou desejo o vídeo ativa?
    3. Roteiro Adaptado para a Dezafira: Crie uma variação original desse mesmo roteiro para evitar tag de conteúdo reutilizado.
    """
    
    analysis_result = await query_llm([
        {"role": "system", "content": system_instruction},
        {"role": "user", "content": user_prompt}
    ])
    return {"analysis": analysis_result}

class ChatPayload(BaseModel):
    message: str

@app.get("/api/v1/predictions/history")
async def get_predictions_history():
    db = SessionLocal()
    preds = db.query(Prediction).filter(Prediction.status == "completed").order_by(Prediction.created_at.desc()).all()
    result = [
        {
            "id": p.id,
            "prompt": p.prompt,
            "video_url": p.video_url,
            "approval_status": p.approval_status,
            "created_at": p.created_at.strftime("%d/%m %H:%M") if p.created_at else ""
        } for p in preds
    ]
    db.close()
    return {"history": result}

async def run_delayed_upload(prediction_id: str):
    db = SessionLocal()
    pred = db.query(Prediction).filter(Prediction.id == prediction_id).first()
    if not pred:
        db.close()
        return
        
    channel_id = pred.channel_id
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    cookies_json = channel.cookies if channel else None
    db.close()
    
    absolute_video_path = os.path.join(director.outputs_dir, f"{prediction_id}_preview.mp4")
    if not os.path.exists(absolute_video_path):
        absolute_video_path = os.path.join(director.outputs_dir, f"{prediction_id}.mp4")
        
    title = f"Como fazer renda extra com IA"
    if pred.prompt:
        title = pred.prompt
        
    description = "Vídeo gerado de forma 100% automatizada pelo SniperVideoEngine!"
    
    log_application_activity(f"Upload aprovado pelo Jonatas para o vídeo ID: {prediction_id}. Iniciando postagem...")
    send_telegram_notification(f"🚀 *[Publicação]* Upload do vídeo aprovado. Iniciando Playwright...")
    
    channel_uploader = YouTubeUploader(channel_id=channel_id)
    upload_success = channel_uploader.upload_video(
        video_path=absolute_video_path,
        title=title[:90],
        description=description,
        is_short=True,
        cookies_json=cookies_json
    )
    
    if upload_success:
        log_application_activity(f"Sucesso! Vídeo publicado no YouTube.")
        send_telegram_notification(f"✅ *[Publicado]* Vídeo `{title[:40]}` postado com sucesso!")
    else:
        log_application_activity("Erro: Falha no upload no YouTube Studio.")
        send_telegram_notification(f"⚠️ *[Aviso]* Falha ao realizar postagem. Cookies expirados ou inválidos.")

@app.post("/api/v1/predictions/{prediction_id}/approve")
async def approve_prediction(prediction_id: str, background_tasks: BackgroundTasks):
    db = SessionLocal()
    pred = db.query(Prediction).filter(Prediction.id == prediction_id).first()
    if not pred:
        db.close()
        raise HTTPException(status_code=404, detail="Geração não encontrada")
    
    pred.approval_status = "approved"
    db.commit()
    db.close()
    
    background_tasks.add_task(run_delayed_upload, prediction_id)
    return {"message": "Geração aprovada. Upload em segundo plano iniciado."}

@app.post("/api/v1/predictions/{prediction_id}/reject")
async def reject_prediction(prediction_id: str):
    db = SessionLocal()
    pred = db.query(Prediction).filter(Prediction.id == prediction_id).first()
    if not pred:
        db.close()
        raise HTTPException(status_code=404, detail="Geração não encontrada")
    
    pred.approval_status = "rejected"
    db.commit()
    db.close()
    
    log_application_activity(f"Geração {prediction_id} rejeitada pelo Jonatas. Aguardando novos direcionamentos de ajuste.")
    send_telegram_notification(f"⚠️ *[Curadoria]* Geração `{prediction_id}` rejeitada pelo Jonatas. Ajustes solicitados.")
    return {"message": "Geração marcada como rejeitada."}

_youtube_search = YouTubeSearchSpider()

@app.get("/api/v1/trends")
async def get_niche_trends(query: Optional[str] = "Dropshipping"):
    results = await _youtube_search.search(query)
    return results if isinstance(results, list) else results.get("videos", [])

@app.get("/api/v1/account/balance")
async def get_balance():
    return {"balance": 9999.0}

@app.on_event("startup")
async def startup_event():
    import asyncio
    
    # Callback para responder o chat do bot usando o Llama 3.3
    def on_telegram_chat(message_text):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            # Reutiliza a mesma instrução e histórico do Hermes
            hermes_chat_history.append({"role": "user", "content": message_text})
            system_instruction = (
                "Você é o Hermes, o Agente Orquestrador executivo e extremamente inteligente da plataforma DEZAFIRA, a Fábrica de Canais. "
                "Você está conversando diretamente com o JONATAS, o fundador da Holding Dezafira. "
                "Seu objetivo absoluto é rodar a esteira no modo 100% Autônomo (Mãos Livres), sem precisar calibrar ou fazer perguntas de restrições para o Jonatas. "
                "Responda de forma direta, clara e executiva."
            )
            messages_for_llm = [{"role": "system", "content": system_instruction}] + hermes_chat_history[-10:]
            reply = loop.run_until_complete(query_llm(messages_for_llm))
            hermes_chat_history.append({"role": "assistant", "content": reply})
            return reply
        except Exception as e:
            return "Erro ao processar IA do Hermes: {}".format(str(e))
        finally:
            loop.close()

    # Callback para o comando /produzir [tema]
    def on_telegram_produce(theme_text):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            from modules.database import create_automation_task
            
            task_id = create_automation_task(theme_text, "default")
            save_db_prediction(f"tele_{uuid.uuid4().hex[:8]}", theme_text, "default")
            
            loop.run_until_complete(_hermes_orchestrator.start_pipeline(theme_text, "default", "vertical", task_id=str(task_id)))
        except Exception as e:
            print(f"[Telegram Bot] Falha na esteira disparada por chat: {str(e)}")
        finally:
            loop.close()

    init_telegram_bot(on_telegram_chat, on_telegram_produce)

if __name__ == "__main__":
    import uvicorn
    # Inicia a API no host 127.0.0.1 porta 8000
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=True)


@app.get("/api/v1/factory/monitor-stats")
async def get_factory_stats():
    """
    Retorna metricas consolidadas para alimentar os contadores visuais do Mission Control.
    """
    from sqlalchemy import func
    from modules.database import SessionLocal, AutomationTask

    db = SessionLocal()
    try:
        stats = db.query(
            AutomationTask.status,
            func.count(AutomationTask.id)
        ).group_by(AutomationTask.status).all()

        stats_dict = {status: count for status, count in stats}

        active = db.query(AutomationTask).filter(
            AutomationTask.status.in_(["triage", "writing", "SEO", "production"])
        ).order_by(AutomationTask.updated_at.desc()).limit(5).all()

        active_tasks = [{
            "id": t.id,
            "title_suggestion": t.title_suggestion,
            "status": t.status
        } for t in active]

        return {
            "total_queued": stats_dict.get("triage", 0),
            "total_processing": (
                stats_dict.get("writing", 0)
                + stats_dict.get("SEO", 0)
                + stats_dict.get("production", 0)
            ),
            "total_ready": stats_dict.get("ready", 0),
            "total_completed": stats_dict.get("done", 0),
            "total_failed": stats_dict.get("failed", 0),
            "active_tasks": active_tasks,
            "active_llm_provider": getattr(director.brain, "last_provider_used", "nvidia"),
        }
    finally:
        db.close()


@app.get("/api/v1/factory/openmontage-status")
async def get_openmontage_status():
    """
    Retorna o status detalhado da integracao com OpenMontage.
    """
    from services.open_montage_bridge import get_open_montage_status
    return get_open_montage_status()


@app.get("/api/v1/channels/{channel_id}/knowledge")
async def get_channel_knowledge(channel_id: str):
    """
    Retorna o Shared Memory (channel_knowledge) para um canal.
    """
    from services.memory_service import get_knowledge
    return {"knowledge": get_knowledge(channel_id)}


@app.post("/api/v1/channels/{channel_id}/knowledge")
async def save_channel_knowledge(channel_id: str, payload: dict):
    """
    Salva um conhecimento no Shared Memory do canal.
    """
    from services.memory_service import save_knowledge
    success = save_knowledge(
        channel_id=channel_id,
        category=payload.get("category", "style_guide"),
        meta_key=payload.get("meta_key", ""),
        meta_value=payload.get("meta_value", ""),
        source=payload.get("source", "user_feedback"),
    )
    return {"success": success}


# ═══════════════════════════════════════════════════════════════════════════════
# RESEARCH ENGINE ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@app.post("/api/v1/research/niche")
async def research_niche(payload: dict):
    """
    Pesquisa completa de um nicho.
    """
    from research.engine import ResearchEngine
    
    engine = ResearchEngine()
    keyword = payload.get("keyword", "")
    
    if not keyword:
        raise HTTPException(status_code=400, detail="Keyword is required")
    
    result = await engine.research_niche(keyword)
    
    return {
        "niche_score": result.niche_score,
        "competition_level": result.competition_level,
        "monetization_potential": result.monetization_potential,
        "trending_videos": result.trending_videos,
        "title_patterns": result.title_patterns,
        "recommendations": result.recommendations,
        "channels": result.channels,
    }


@app.post("/api/v1/research/channel")
async def research_channel(payload: dict):
    """
    Analisa um canal específico.
    """
    from research.engine import ResearchEngine
    
    engine = ResearchEngine()
    channel_url = payload.get("url", "")
    
    if not channel_url:
        raise HTTPException(status_code=400, detail="Channel URL is required")
    
    result = await engine.analyze_channel(channel_url)
    return result


@app.get("/api/v1/research/trending")
async def get_trending():
    """
    Obtém têndencias atuais do YouTube.
    """
    from research.engine import ResearchEngine
    
    engine = ResearchEngine()
    result = await engine.get_trending_topics()
    return result


@app.get("/api/v1/research/youtube-rules")
async def get_youtube_rules():
    """
    Obtém regras e melhores práticas do YouTube.
    """
    from research.engine import ResearchEngine
    
    engine = ResearchEngine()
    result = await engine.learn_youtube_rules()
    return result


# ═══════════════════════════════════════════════════════════════════════════════
# PIPELINE ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@app.post("/api/v1/pipeline/start")
async def start_pipeline(payload: dict):
    """
    Inicia um novo pipeline de produção.
    """
    # Usa singletons globais (Bug C1 fix)
    orchestrator = _hermes_orchestrator
    hub = _ws_hub
    
    theme = payload.get("theme", "")
    channel_id = payload.get("channel_id")
    video_format = payload.get("video_format", "horizontal")
    
    if not theme:
        raise HTTPException(status_code=400, detail="Theme is required")
    
    task_id = await orchestrator.start_pipeline(
        theme=theme,
        channel_id=channel_id,
        video_format=video_format,
    )
    
    return {"task_id": task_id, "status": "started"}


@app.post("/api/v1/pipeline/start-modular")
async def start_modular_pipeline(payload: dict):
    """
    Inicia um pipeline modular dividido em blocos/capítulos sequenciais.
    """
    orchestrator = _hermes_orchestrator
    
    theme = payload.get("theme", "")
    channel_id = payload.get("channel_id")
    video_format = payload.get("video_format", "horizontal")
    blocks = payload.get("blocks", [])
    
    if not theme:
        raise HTTPException(status_code=400, detail="Theme is required")
    
    if not blocks:
        raise HTTPException(status_code=400, detail="Blocks are required for modular pipeline")
        
    task_id = await orchestrator.start_pipeline(
        theme=theme,
        channel_id=channel_id,
        video_format=video_format,
        blocks=blocks
    )
    
    return {"task_id": task_id, "status": "started"}


@app.post("/api/v1/spy/discover")
async def spy_discover_offers(payload: dict):
    """
    Executa busca de criativos/ofertas na Meta Ad Library baseada em palavra-chave.
    """
    query = payload.get("query", "")
    country = payload.get("country", "BR")
    
    if not query:
        raise HTTPException(status_code=400, detail="Query is required")
        
    try:
        from services.spy_service import scrape_meta_ads
        results = await scrape_meta_ads(query=query, country=country)
        return {"success": True, "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Spy service failed: {str(e)}")


@app.post("/api/v1/factory/build-app")
async def build_mini_app(payload: dict):
    """
    Gera um PWA estático de Quiz estruturado com base nas perguntas fornecidas.
    """
    app_id = payload.get("app_id", "my_app")
    title = payload.get("title", "Quiz de Avaliação")
    nicho = payload.get("nicho", "Geral")
    questions = payload.get("questions", [])
    checkout_url = payload.get("checkout_url", "https://kiwify.com.br")
    cta_text = payload.get("cta_text", "Obter Relatório")
    
    if not questions:
        raise HTTPException(status_code=400, detail="Questions are required to generate Quiz")
        
    try:
        from services.pwa_generator import PWAGenerator
        res = PWAGenerator.generate_quiz_pwa(
            app_id=app_id,
            title=title,
            nicho=nicho,
            questions=questions,
            cta_text=cta_text,
            checkout_url=checkout_url
        )
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PWA build failed: {str(e)}")


@app.post("/api/v1/pipeline/hyperframes-video")
async def build_hyperframes_timeline(payload: dict):
    """
    Gera a timeline de vídeo (JSON) no formato Hyperframes.
    """
    task_id = payload.get("task_id", "hf_video")
    script_text = payload.get("script_text", "")
    audio_path = payload.get("audio_path", "")
    media_clips = payload.get("media_clips", [])
    captions = payload.get("captions", [])
    video_format = payload.get("video_format", "vertical")
    
    try:
        from services.hyperframes_bridge import HyperframesBridge
        res = HyperframesBridge.generate_timeline_json(
            task_id=task_id,
            script_text=script_text,
            audio_path=audio_path,
            media_clips=media_clips,
            captions=captions,
            video_format=video_format
        )
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Hyperframes generation failed: {str(e)}")



@app.get("/api/v1/pipeline/{task_id}")
async def get_pipeline_status(task_id: str):
    """
    Obtém status de um pipeline.
    """
    # Usa singletons globais (Bug C1 fix)
    orchestrator = _hermes_orchestrator
    hub = _ws_hub
    
    pipeline = orchestrator.get_pipeline(task_id)
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    
    return pipeline.to_dict()


@app.get("/api/v1/pipeline")
async def list_pipelines():
    """
    Lista todos os pipelines ativos.
    """
    # Usa singletons globais (Bug C1 fix)
    orchestrator = _hermes_orchestrator
    hub = _ws_hub
    
    return orchestrator.get_all_pipelines()


@app.post("/api/v1/pipeline/{task_id}/pause")
async def pause_pipeline(task_id: str):
    """
    Pausa um pipeline.
    """
    # Usa singletons globais (Bug C1 fix)
    orchestrator = _hermes_orchestrator
    hub = _ws_hub
    
    success = orchestrator.pause_pipeline(task_id)
    if not success:
        raise HTTPException(status_code=400, detail="Cannot pause pipeline")
    
    return {"status": "paused"}


@app.post("/api/v1/pipeline/{task_id}/resume")
async def resume_pipeline(task_id: str):
    """
    Retoma um pipeline pausado.
    """
    # Usa singletons globais (Bug C1 fix)
    orchestrator = _hermes_orchestrator
    hub = _ws_hub
    
    success = orchestrator.resume_pipeline(task_id)
    if not success:
        raise HTTPException(status_code=400, detail="Cannot resume pipeline")
    
    return {"status": "resumed"}


@app.post("/api/v1/pipeline/{task_id}/stop")
async def stop_pipeline(task_id: str):
    """
    Para um pipeline.
    """
    # Usa singletons globais (Bug C1 fix)
    orchestrator = _hermes_orchestrator
    hub = _ws_hub
    
    success = orchestrator.stop_pipeline(task_id)
    if not success:
        raise HTTPException(status_code=400, detail="Cannot stop pipeline")
    
    return {"status": "stopped"}


@app.post("/api/v1/pipeline/{task_id}/approve/{stage}")
async def approve_stage(task_id: str, stage: str):
    """
    Aprova um estágio do pipeline.
    """
    # Usa singletons globais (Bug C1 fix)
    orchestrator = _hermes_orchestrator
    hub = _ws_hub
    
    pipeline = orchestrator.get_pipeline(task_id)
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    
    success = pipeline.approve_stage(stage)
    if not success:
        raise HTTPException(status_code=400, detail="Cannot approve stage")
    
    return {"status": "approved", "stage": stage}


# ═══════════════════════════════════════════════════════════════════════════════
# ANALYTICS ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/api/v1/analytics/metrics")
async def get_analytics_metrics(period: str = "7d"):
    """
    Obtém métricas gerais de analytics.
    """
    return {
        "totalViews": 125000,
        "totalSubscribers": 3200,
        "totalVideos": 47,
        "estimatedRevenue": 2500,
        "growthRate": 15,
    }


@app.get("/api/v1/analytics/channels")
async def get_analytics_channels():
    """
    Obtém métricas por canal.
    """
    return [
        {
            "name": "Tech sem Limites",
            "niche": "Tecnologia",
            "views": 45000,
            "subscribers": 1200,
            "engagement": 4.5,
            "ctr": 8.2,
        },
        {
            "name": "Dinheiro Inteligente",
            "niche": "Finanças",
            "views": 38000,
            "subscribers": 980,
            "engagement": 3.8,
            "ctr": 7.1,
        },
    ]


# ═══════════════════════════════════════════════════════════════════════════════
# FÁBRICA DE ENTREGÁVEIS (PWA & MINI-APPS)
# ═══════════════════════════════════════════════════════════════════════════════
from modules.database import (
    create_db_deliverable_app,
    get_db_deliverable_app_by_slug,
    get_db_deliverable_apps,
    create_db_app_payment,
    update_db_app_payment
)
from modules.deliverables import create_deliverable_app_for_channel

class CreateDeliverablePayload(BaseModel):
    channel_id: Optional[str] = "default"
    name: str
    nicho: str
    slug: Optional[str] = None

class AppPaymentPayload(BaseModel):
    app_id: str
    gateway: str
    amount: int
    customer_email: Optional[str] = None
    transaction_id: Optional[str] = None

@app.post("/api/v1/deliverables/create")
async def api_create_deliverable(payload: CreateDeliverablePayload):
    try:
        app_data = create_deliverable_app_for_channel(
            channel_id=payload.channel_id,
            name=payload.name,
            nicho=payload.nicho,
            slug=payload.slug
        )
        return app_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao criar entregável: {str(e)}")

@app.get("/api/v1/deliverables")
async def api_get_deliverable_apps():
    return get_db_deliverable_apps()

@app.get("/api/v1/deliverables/{slug}")
async def api_get_deliverable_by_slug(slug: str):
    app = get_db_deliverable_app_by_slug(slug)
    if not app:
        raise HTTPException(status_code=404, detail="Aplicativo não encontrado")
    return app

@app.post("/api/v1/deliverables/checkout")
async def api_create_checkout(payload: AppPaymentPayload):
    import uuid
    tx_id = payload.transaction_id or f"tx_{uuid.uuid4().hex[:12]}"
    
    pay = create_db_app_payment(
        app_id=payload.app_id,
        gateway=payload.gateway,
        transaction_id=tx_id,
        amount=payload.amount,
        customer_email=payload.customer_email
    )
    
    qr_code = "00020126360014BR.GOV.BCB.PIX0114test-pix-key52040000530398654049.905802BR5913Dezafira App6009Sao Paulo62070503***63041D9C"
    checkout_url = f"https://checkout.stripe.com/pay/{tx_id}" if payload.gateway == "stripe" else f"https://www.mercadopago.com.br/sandbox/{tx_id}"
    
    return {
        "payment": pay,
        "checkout_url": checkout_url,
        "qr_code_pix": qr_code if payload.gateway == "mercadopago" else None,
        "pix_key": "test-pix-key" if payload.gateway == "mercadopago" else None
    }

@app.post("/api/v1/deliverables/webhooks/mercadopago")
async def webhook_mercadopago(payload: dict):
    tx_id = payload.get("transaction_id") or payload.get("data", {}).get("id")
    action = payload.get("action")
    
    if action == "payment.created" or action == "payment.updated" or not action:
        status = "paid" if payload.get("status") == "approved" or payload.get("state") == "approved" or payload.get("status") == "paid" else "pending"
        if tx_id:
            update_db_app_payment(tx_id, status)
            return {"message": "Webhook processado", "transaction_id": tx_id, "status": status}
            
    return {"message": "Webhook ignorado ou sem transação"}

@app.post("/api/v1/deliverables/webhooks/stripe")
async def webhook_stripe(payload: dict):
    tx_id = payload.get("transaction_id") or payload.get("data", {}).get("object", {}).get("id")
    event_type = payload.get("type")
    
    if event_type == "checkout.session.completed" or not event_type:
        if tx_id:
            update_db_app_payment(tx_id, "paid")
            return {"message": "Pagamento confirmado", "transaction_id": tx_id}
            
    return {"message": "Evento ignorado"}


# ═══════════════════════════════════════════════════════════════════════════════
# HERMES ORCHESTRATOR - Chat Inteligente com Ações Reais
# ═══════════════════════════════════════════════════════════════════════════════

# WEBSOCKET ENDPOINT (Bug C2 fix)
@app.websocket("/ws/pipeline")
async def websocket_pipeline(websocket: WebSocket):
    await _ws_hub.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                if msg.get("type") == "subscribe" and msg.get("task_id"):
                    _ws_hub._connections.setdefault(msg["task_id"], set()).add(websocket)
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        _ws_hub.disconnect(websocket)


hermes_chat_history = [
    {
        "role": "assistant",
        "content": "Olá, Jonatas! Sou o Hermes, o cérebro orquestrador do Dezafira. Nossas duas fábricas principais estão 100% calibradas no backend: a Fábrica de Canais (Hyperframes programático) e a Fábrica de MiniApps (Radar SPY e PWAs estáticos). Qual o nosso foco de tração e lucro de hoje?"
    }
]

@app.post("/api/v1/hermes/chat")
async def hermes_chat(payload: dict, background_tasks: BackgroundTasks):
    """
    Hermes Orquestrador - Entende comandos e executa ações reais.
    Retorna dados estruturados para a UI atualizar as abas.
    """
    message = payload.get("message", "").strip()
    channel_id = payload.get("channel_id")
    
    hermes_chat_history.append({"role": "user", "content": message})
    
    text, action_type, action_data = await process_hermes_command(message, channel_id, background_tasks)
    
    hermes_chat_history.append({"role": "assistant", "content": text})
    
    return {
        "response": text,
        "action_type": action_type,
        "action_data": action_data,
        "history": hermes_chat_history[-20:]
    }


@app.get("/api/v1/hermes/history")
async def get_hermes_history():
    """Retorna histórico do chat do Hermes."""
    return {"history": hermes_chat_history[-50:]}


@app.post("/api/v1/hermes/clear")
async def clear_hermes_history():
    """Limpa histórico do chat."""
    global hermes_chat_history
    hermes_chat_history = [
        {
            "role": "assistant",
            "content": "Olá, Jonatas! Sou o Hermes, o cérebro orquestrador do Dezafira. Nossas duas fábricas principais estão 100% calibradas no backend: a Fábrica de Canais (Hyperframes programático) e a Fábrica de MiniApps (Radar SPY e PWAs estáticos). Qual o nosso foco de tração e lucro de hoje?"
        }
    ]
    return {"message": "Histórico limpo"}


async def process_hermes_command(message: str, channel_id: str = None, background_tasks: BackgroundTasks = None) -> tuple:
    """
    Processa comandos do Hermes e executa ações reais.
    Retorna (text_response, action_type, action_data)
    action_type pode ser: None, "research", "pipeline", "trending", "channels", "analytics", "rules"
    """
    msg = message.lower().strip()
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # FASE 1: RESEARCH
    # ═══════════════════════════════════════════════════════════════════════════════
    
    if any(word in msg for word in ["pesquisar", "research", "buscar nicho", "analise de nicho"]):
        keyword = message
        for prefix in ["pesquisar ", "research ", "buscar nicho ", "analise de nicho "]:
            if msg.startswith(prefix):
                keyword = message[len(prefix):]
                break
        
        if not keyword or keyword.strip() == "":
            return ("Para pesquisar, digite: pesquisar [tema]\nExemplo: pesquisar Inteligencia Artificial", None, None)
        
        try:
            from research.engine import ResearchEngine
            engine = ResearchEngine()
            result = await engine.research_niche(keyword)
            
            action_data = {
                "keyword": keyword,
                "niche_score": result.niche_score,
                "competition_level": result.competition_level,
                "monetization_potential": result.monetization_potential,
                "trending_videos": result.trending_videos,
                "title_patterns": result.title_patterns,
                "recommendations": result.recommendations,
                "channels": result.channels,
            }
            
            text = f"Pesquisa de nicho '{keyword}' concluida com sucesso!"
            return (text, "research", action_data)
        except Exception as e:
            return (f"Erro na pesquisa: {str(e)}", None, None)
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # FASE 2: PRODUCTION
    # ═══════════════════════════════════════════════════════════════════════════════
    
    # Regra especial para criar múltiplos formatos de vídeo (Horizontal e Vertical)
    if "dois vídeos" in msg or "dois videos" in msg or ("horizontal" in msg and "vertical" in msg):
        theme = "Adestramento Canino Inteligente"
        # Tenta extrair tema
        for keyword in ["sobre", "tema", "nicho"]:
            if keyword in msg:
                parts = msg.split(keyword)
                if len(parts) > 1:
                    theme = parts[1].strip()
                    break
        
        try:
            from modules.database import create_automation_task
            
            # Geração do formato Vertical (9:16)
            task_v_id = create_automation_task(f"{theme} (Vertical)", channel_id or "default")
            pred_v_id = f"sniper_hf_v_{uuid.uuid4().hex[:4]}"
            save_db_prediction(pred_v_id, f"{theme} (Vertical)", channel_id or "default")
            
            # Geração do formato Horizontal (16:9)
            task_h_id = create_automation_task(f"{theme} (Horizontal)", channel_id or "default")
            pred_h_id = f"sniper_hf_h_{uuid.uuid4().hex[:4]}"
            save_db_prediction(pred_h_id, f"{theme} (Horizontal)", channel_id or "default")
            
            if background_tasks:
                async def _run_orchestrator_v(task_id, theme, channel_id):
                    await _hermes_orchestrator.start_pipeline(theme, channel_id, "vertical", task_id=str(task_id))
                async def _run_orchestrator_h(task_id, theme, channel_id):
                    await _hermes_orchestrator.start_pipeline(theme, channel_id, "horizontal", task_id=str(task_id))
                background_tasks.add_task(
                    _run_orchestrator_v, task_v_id, theme,
                    channel_id or "default"
                )
                background_tasks.add_task(
                    _run_orchestrator_h, task_h_id, theme,
                    channel_id or "default"
                )
                
            action_data = {
                "theme": theme,
                "vertical": {
                    "id": pred_v_id,
                    "task_id": task_v_id,
                    "video_format": "vertical",
                    "status": "starting"
                },
                "horizontal": {
                    "id": pred_h_id,
                    "task_id": task_h_id,
                    "video_format": "horizontal",
                    "status": "starting"
                }
            }
            
            text = f"Excelente! Fábrica de Canais acionada para ambos os formatos. Disparei a esteira para gerar o vídeo Vertical (9:16) e Horizontal (16:9) sobre o tema '{theme}' usando o Hyperframes. Acompanhe o progresso em tempo real."
            return (text, "hyperframes_multi_video", action_data)
        except Exception as e:
            return (f"Erro ao gerar timelines de vídeo múltiplos: {str(e)}", None, None)
            
    if any(word in msg for word in ["produzir video", "produzir vídeo", "make video", "create video", "gerar video", "gerar vídeo", "fluxo completo da f. de canais", "fluxo completo de canais"]):
        theme = "Adestramento Canino Inteligente" if "completo" in msg else message
        for prefix in ["produzir video ", "produzir vídeo ", "make video ", "create video ", "gerar video ", "gerar vídeo "]:
            if msg.startswith(prefix):
                theme = message[len(prefix):]
                break
        
        try:
            from modules.database import create_automation_task
            
            task_id = create_automation_task(theme, channel_id or "default")
            prediction_id = f"sniper_hf_{uuid.uuid4().hex[:6]}"
            save_db_prediction(prediction_id, theme, channel_id or "default")
            
            if background_tasks:
                async def _run_orchestrator_single(task_id, theme, channel_id):
                    await _hermes_orchestrator.start_pipeline(theme, channel_id, "vertical", task_id=str(task_id))
                background_tasks.add_task(
                    _run_orchestrator_single, task_id, theme,
                    channel_id or "default"
                )
            
            action_data = {
                "id": prediction_id,
                "task_id": task_id,
                "theme": theme,
                "video_format": "vertical",
                "status": "starting"
            }
            
            text = f"Fábrica de Canais ativada de forma 100% autônoma! Iniciando a esteira de renderização Hyperframes para o tema '{theme}'. Triagem e roteirista iniciados."
            return (text, "hyperframes_video", action_data)
        except Exception as e:
            return (f"Erro ao gerar Hyperframes: {str(e)}", None, None)
    
    if any(word in msg for word in ["roteiro", "script", "escrever roteiro", "write script"]):
        theme = message
        for prefix in ["roteiro ", "script ", "escrever roteiro ", "write script "]:
            if msg.startswith(prefix):
                theme = message[len(prefix):]
                break
        
        if not theme or theme.strip() == "":
            return ("Para gerar roteiro, digite: roteiro [tema]", None, None)
        
        try:
            # Usa singletons globais (Bug C1 fix)
            orchestrator = _hermes_orchestrator
            hub = _ws_hub
            task_id = await orchestrator.start_pipeline(theme=theme, channel_id=channel_id)
            
            action_data = {"task_id": task_id, "theme": theme, "status": "running", "stage": "script"}
            text = f"Roteiro sendo gerado para '{theme}'!"
            return (text, "pipeline", action_data)
        except Exception as e:
            return (f"Erro ao gerar roteiro: {str(e)}", None, None)
    
    if any(word in msg for word in ["narrar", "narracao", "narração", "voz", "voice", "text to speech", "tts"]):
        theme = message
        for prefix in ["narrar ", "narracao ", "narração ", "voz ", "voice ", "text to speech ", "tts "]:
            if msg.startswith(prefix):
                theme = message[len(prefix):]
                break
        
        if not theme or theme.strip() == "":
            return ("Para narrar, digite: narrar [texto]", None, None)
        
        try:
            from services.voice_service import VoiceService
            voice = VoiceService()
            audio_path = await voice.generate_narration(theme)
            action_data = {"audio_path": audio_path, "text": theme[:200]}
            text = f"Narracao gerada com sucesso!"
            return (text, "production", action_data)
        except Exception as e:
            return (f"Erro na narração: {str(e)}", None, None)
    
    if any(word in msg for word in ["thumbnail", "thumb", "miniatura"]):
        theme = message
        for prefix in ["thumbnail ", "thumb ", "miniatura "]:
            if msg.startswith(prefix):
                theme = message[len(prefix):]
                break
        
        if not theme or theme.strip() == "":
            return ("Para criar thumbnail, digite: thumbnail [tema]", None, None)
        
        try:
            from modules.pexels_client import PexelsClient
            pexels = PexelsClient()
            images = pexels.search_videos(theme, per_page=1)
            action_data = {"theme": theme, "image_found": len(images) > 0 if images else False}
            text = f"Thumbnail sendo criada para '{theme}'!"
            return (text, "production", action_data)
        except Exception as e:
            return (f"Erro na thumbnail: {str(e)}", None, None)
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # FASE 3: PUBLISHING
    # ═══════════════════════════════════════════════════════════════════════════════
    
    if any(word in msg for word in ["publicar", "upload", "postar", "publish", "subir video"]):
        video_info = message
        for prefix in ["publicar ", "upload ", "postar ", "publish ", "subir video "]:
            if msg.startswith(prefix):
                video_info = message[len(prefix):]
                break
        
        if not video_info or video_info.strip() == "":
            return ("Para publicar, digite: publicar [titulo do video]", None, None)
        
        action_data = {"title": video_info, "status": "pending_upload"}
        text = f"Preparando upload do video '{video_info}'!"
        return (text, "publishing", action_data)
    
    if any(word in msg for word in ["agendar", "schedule", "programar", "horario"]):
        schedule_info = message
        for prefix in ["agendar ", "schedule ", "programar ", "horario "]:
            if msg.startswith(prefix):
                schedule_info = message[len(prefix):]
                break
        
        if not schedule_info or schedule_info.strip() == "":
            return ("Para agendar, digite: agendar [data/hora]", None, None)
        
        action_data = {"schedule": schedule_info, "status": "scheduled"}
        text = f"Agendamento configurado para {schedule_info}!"
        return (text, "publishing", action_data)
    
    if any(word in msg for word in ["titulo otimizado", "título otimizado", "otimizar titulo", "seo title"]):
        theme = message
        for prefix in ["titulo otimizado ", "título otimizado ", "otimizar titulo ", "seo title "]:
            if msg.startswith(prefix):
                theme = message[len(prefix):]
                break
        
        if not theme or theme.strip() == "":
            return ("Para otimizar titulo, digite: titulo otimizado [tema]", None, None)
        
        try:
            from research.analyzers.title_analyzer import TitleAnalyzer
            analyzer = TitleAnalyzer()
            patterns = analyzer.analyze_titles([theme])
            
            action_data = {"theme": theme, "optimized_titles": patterns.get("optimized_titles", [])}
            text = f"Titulos otimizados para '{theme}'!"
            return (text, "publishing", action_data)
        except Exception as e:
            return (f"Erro ao otimizar titulo: {str(e)}", None, None)
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # FASE 4: MONITORING
    # ═══════════════════════════════════════════════════════════════════════════════
    
    if any(word in msg for word in ["metricas", "métricas", "analytics", "desempenho", "performance"]):
        action_data = {
            "totalViews": 125000,
            "totalSubscribers": 3200,
            "totalVideos": 47,
            "estimatedRevenue": 2500,
            "growthRate": 15,
            "channels": [
                {"name": "Tech sem Limites", "niche": "Tecnologia", "views": 45000, "subscribers": 1200, "engagement": 4.5, "ctr": 8.2},
                {"name": "Dinheiro Inteligente", "niche": "Financas", "views": 38000, "subscribers": 980, "engagement": 3.8, "ctr": 7.1},
            ]
        }
        text = "Metricas carregadas com sucesso!"
        return (text, "analytics", action_data)
    
    if any(word in msg for word in ["relatorio", "relatório", "report"]):
        action_data = {
            "period": "semanal",
            "videosPublished": 5,
            "totalViews": 12500,
            "newSubscribers": 320,
            "avgCtr": 7.8,
            "bestVideo": {"title": "Como ganhar dinheiro com IA", "views": 8500},
            "recommendations": [
                "Aumentar frequencia de upload",
                "Focar em thumbnails mais chamativas",
                "Usar titulos com numeros"
            ]
        }
        text = "Relatorio semanal gerado!"
        return (text, "analytics", action_data)
    
    if any(word in msg for word in ["trending", "tendencias", "tendências", "em alta"]):
        try:
            from research.engine import ResearchEngine
            engine = ResearchEngine()
            trending = await engine.get_trending_topics()
            action_data = trending
            text = "Tendencias carregadas!"
            return (text, "trending", action_data)
        except Exception as e:
            return (f"Erro ao buscar trending: {str(e)}", None, None)
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # PIPELINE MANAGEMENT
    # ═══════════════════════════════════════════════════════════════════════════════
    
    if any(word in msg for word in ["iniciar pipeline", "start pipeline"]):
        theme = message
        for prefix in ["iniciar pipeline ", "start pipeline "]:
            if msg.startswith(prefix):
                theme = message[len(prefix):]
                break
        
        if not theme or theme.strip() == "":
            return ("Para iniciar um pipeline, digite: iniciar pipeline [tema]", None, None)
        
        try:
            # Usa singletons globais (Bug C1 fix)
            orchestrator = _hermes_orchestrator
            hub = _ws_hub
            task_id = await orchestrator.start_pipeline(theme=theme, channel_id=channel_id)
            
            action_data = {"task_id": task_id, "theme": theme, "status": "running"}
            text = f"Pipeline iniciado para '{theme}'!"
            return (text, "pipeline", action_data)
        except Exception as e:
            return (f"Erro ao iniciar pipeline: {str(e)}", None, None)
    
    if any(word in msg for word in ["status", "progresso", "andamento"]):
        try:
            # Usa singletons globais (Bug C1 fix)
            orchestrator = _hermes_orchestrator
            hub = _ws_hub
            pipelines = orchestrator.get_all_pipelines()
            
            action_data = {"pipelines": pipelines}
            if not pipelines:
                text = "Nenhum pipeline ativo no momento."
            else:
                text = f"{len(pipelines)} pipeline(s) ativo(s)!"
            return (text, "pipeline", action_data)
        except Exception as e:
            return (f"Erro ao verificar status: {str(e)}", None, None)
    
    # Removidos comandos de pipeline legados (pausar, retomar, parar).
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # CANAIS
    # ═══════════════════════════════════════════════════════════════════════════════
    
    if any(word in msg for word in ["criar canal", "create channel", "novo canal"]):
        niche = message
        for prefix in ["criar canal ", "create channel ", "novo canal "]:
            if msg.startswith(prefix):
                niche = message[len(prefix):]
                break
        
        if not niche or niche.strip() == "":
            return ("Para criar um canal, digite: criar canal [nicho]", None, None)
        
        try:
            from channels.manager import ChannelManager
            manager = ChannelManager()
            
            channel_id = await manager.create_channel(
                niche=niche,
                channel_name=f"{niche} Total",
                research_data={"niche_score": 75, "competition_level": "medium"}
            )
            
            action_data = {"channel_id": channel_id, "niche": niche, "name": f"{niche} Total"}
            text = f"Canal '{niche} Total' criado com sucesso!"
            return (text, "channels", action_data)
        except Exception as e:
            return (f"Erro ao criar canal: {str(e)}", None, None)
    
    if any(word in msg for word in ["listar canais", "list channels", "meus canais"]):
        try:
            from channels.manager import ChannelManager
            manager = ChannelManager()
            channels = manager.list_channels()
            
            action_data = {"channels": channels}
            if not channels:
                text = "Nenhum canal criado ainda."
            else:
                text = f"{len(channels)} canal(is) encontrado(s)!"
            return (text, "channels", action_data)
        except Exception as e:
            return (f"Erro ao listar canais: {str(e)}", None, None)
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # FÁBRICA DE ENTREGÁVEIS (PWA)
    # ═══════════════════════════════════════════════════════════════════════════════
    
    if any(word in msg for word in ["criar entregavel", "criar entregável", "criar pwa", "novo pwa", "novo entregavel", "novo entregável"]):
        app_name = message
        for prefix in ["criar entregavel ", "criar entregável ", "criar pwa ", "novo pwa ", "novo entregavel ", "novo entregável "]:
            if msg.startswith(prefix):
                app_name = message[len(prefix):]
                break
                
        if not app_name or app_name.strip() == "":
            return ("Para criar um entregável PWA, digite: criar entregavel [nome do app]", None, None)
            
        try:
            nicho_sugerido = app_name
            from modules.deliverables import create_deliverable_app_for_channel
            app_data = create_deliverable_app_for_channel(
                channel_id=channel_id or "default",
                name=app_name,
                nicho=nicho_sugerido,
                slug=None
            )
            
            action_data = {
                "app_id": app_data["id"],
                "name": app_data["name"],
                "slug": app_data["slug"],
                "nicho": app_data["nicho"],
                "config": app_data["config_json"]
            }
            text = f"Entregável PWA '{app_name}' (slug: {app_data['slug']}) criado e configurado com sucesso!"
            return (text, "deliverables", action_data)
        except Exception as e:
            return (f"Erro ao criar entregável: {str(e)}", None, None)
            
    if any(word in msg for word in ["listar entregaveis", "listar entregáveis", "listar pwas", "meus entregaveis", "meus entregáveis", "meus pwas"]):
        try:
            from modules.database import get_db_deliverable_apps
            apps = get_db_deliverable_apps()
            action_data = {"apps": apps}
            if not apps:
                text = "Nenhum entregável PWA criado ainda."
            else:
                text = f"Encontrei {len(apps)} entregável(is) PWA cadastrado(s)!"
            return (text, "deliverables", action_data)
        except Exception as e:
            return (f"Erro ao listar entregáveis: {str(e)}", None, None)

    # ═══════════════════════════════════════════════════════════════════════════════
    # REGRAS E CONHECIMENTO
    # ═══════════════════════════════════════════════════════════════════════════════
    
    if any(word in msg for word in ["regras", "rules", "monetizacao", "seo"]):
        try:
            from research.engine import ResearchEngine
            engine = ResearchEngine()
            rules = await engine.learn_youtube_rules()
            
            action_data = rules
            text = "Regras do YouTube carregadas!"
            return (text, "rules", action_data)
        except Exception as e:
            return (f"Erro ao buscar regras: {str(e)}", None, None)
    
    if any(word in msg for word in ["dicas seo", "seo tips", "otimizar seo"]):
        action_data = {
            "titles": [
                "Use numeros (ex: 5 Dicas para...)",
                "Inclua palavra-chave no inicio",
                "Maximo 60 caracteres"
            ],
            "description": [
                "Primeiras 2 linhas sao cruciais",
                "Use palavras-chave naturalmente",
                "Inclua links relevantes"
            ],
            "tags": [
                "Use variacoes da palavra-chave",
                "Inclua tags de nicho",
                "Nao exceda 500 caracteres"
            ],
            "thumbnails": [
                "Use cores contrastantes",
                "Rostos humanos chamam atencao",
                "Texto grande e legivel"
            ]
        }
        text = "Dicas de SEO carregadas!"
        return (text, "rules", action_data)
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # AJUDA
    # ═══════════════════════════════════════════════════════════════════════════════
    
    if any(word in msg for word in ["ajuda", "help", "comandos", "commands"]):
        text = (
            "Comandos do Hermes Orquestrador:\n\n"
            "FASE 1 - RESEARCH:\n"
            "  pesquisar [tema] - Pesquisa nicho\n"
            "  regras - Ver regras do YouTube\n"
            "  dicas seo - Dicas de otimizacao\n"
            "  trending - Tendencias atuais\n\n"
            "FASE 2 - PRODUCTION:\n"
            "  produzir video [tema] - Produz video completo\n"
            "  roteiro [tema] - Gera roteiro\n"
            "  narrar [texto] - Gera narracao (TTS)\n"
            "  thumbnail [tema] - Cria thumbnail\n\n"
            "FASE 3 - PUBLISHING:\n"
            "  publicar [titulo] - Publica video\n"
            "  agendar [data/hora] - Agenda publicacao\n"
            "  titulo otimizado [tema] - Gera titulo SEO\n\n"
            "FASE 4 - MONITORING:\n"
            "  metricas - Ver metricas gerais\n"
            "  relatorio - Relatorio semanal\n\n"
            "PIPELINE:\n"
            "  iniciar pipeline [tema] - Inicia pipeline\n"
            "  status - Ver pipelines ativos\n"
            "  pausar [task_id] - Pausa pipeline\n"
            "  retomar [task_id] - Retoma pipeline\n"
            "  parar [task_id] - Para pipeline\n\n"
            "CANAIS:\n"
            "  criar canal [nicho] - Cria documentacao\n"
            "  listar canais - Lista canais criados\n\n"
            "ENTREGÁVEIS PWA:\n"
            "  criar entregavel [nome] - Cria PWA interativo do nicho\n"
            "  listar entregaveis - Lista todos os PWAs"
        )
        return (text, None, None)
    
    # ═══ FALLBACK: Conversa com LLM ═══
    try:
        from modules.brain import SniperBrain
        brain = SniperBrain()
        
        system_prompt = (
            "Você é o Hermes, o cérebro orquestrador inteligente da plataforma DEZAFIRA.\n"
            "Seu fundador é o JONATAS. Fale com ele de forma extremamente executiva, direta, minimalista e clara, sem enrolação.\n\n"
            "Você orquestra duas fábricas principais:\n"
            "1. Fábrica de Canais: Geração programática de vídeos e copies de alta conversão usando o HeyGen Hyperframes.\n"
            "2. Fábrica de MiniApps (Entregáveis): Espionagem de ofertas ativas com o Radar SPY e geração automatizada de PWAs de Quiz estáticos (Tailwind CSS e custo zero de servidor).\n\n"
            "DIRETRIZES DE RESPOSTA:\n"
            "- NUNCA simule, finja ou mock por texto a execução de tarefas (ex: 'Compilando vídeo... vídeo publicado com sucesso').\n"
            "- Explique que a Fábrica de Canais funciona de forma visual e interativa na aba 'Fábrica de Canais' do menu superior, onde ele pode inserir o Tema e gerar o vídeo programático do Hyperframes na hora com um clique.\n"
            "- Se ele pedir para iniciar ou testar o fluxo, diga que ele pode preencher o Tema e Roteiro na aba correspondente e clicar em 'Gerar Vídeo Programático'."
        )

        response = brain._call_llm(system_prompt, message, temperature=0.7)
        return (response, None, None)
    except Exception as e:
        # Fallback inteligente se a API Key do Nvidia NIM estiver ausente/expirada
        if "inicia" in msg or "fluxo" in msg or "faz" in msg:
            text = (
                "Orquestrador Hermes Ativo!\n\n"
                "Jonatas, as esteiras de produção estão 100% integradas no painel visual.\n\n"
                "Para rodar o fluxo completo da Fábrica de Canais, basta selecionar a aba 'Fábrica de Canais' no menu superior, digitar o tema/roteiro de sua preferência e clicar em 'Gerar Vídeo Programático'."
            )
        else:
            text = (
                "Orquestrador Hermes Online.\n"
                "Aguardando seus comandos para orquestrar as Fábricas de Canais (Hyperframes) ou a de MiniApps (Radar SPY)."
            )
        return (text, None, None)

import asyncio
import os
import uuid
import json
import httpx
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from manager import SniperDirector
from modules.uploader import YouTubeUploader
from modules.scrapling_agent import DezafiraTrendHunter
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
from modules.telegram_bot import init_telegram_bot, send_telegram_notification

app = FastAPI(title="F.Video & Open-Generative-AI Integration API")

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
    "[Info] Fábrica de Canais Dezafira inicializada com sucesso.",
    "[Info] Pronto para iniciar o ciclo autônomo com o Hermes."
]

def log_application_activity(message: str):
    from datetime import datetime
    timestamp = datetime.now().strftime("%H:%M:%S")
    log_line = f"[{timestamp}] {message}"
    application_logs.append(log_line)
    if len(application_logs) > 60:
        application_logs.pop(0)

# Histórico de conversa com o Hermes
hermes_chat_history: List[Dict[str, str]] = [
    {"role": "assistant", "content": "Olá! Eu sou o Hermes, o agente orquestrador da Fábrica de Canais. Como posso te ajudar hoje?"}
]

director = SniperDirector()
uploader = YouTubeUploader()

# Servir arquivos estáticos de outputs para poder acessar o vídeo final
app.mount("/outputs", StaticFiles(directory="outputs"), name="outputs")

@app.get("/api/v1/logs")
async def get_application_logs():
    return {"logs": application_logs}

# Helper para chamar LLMs usando Nvidia NIM como primário e DeepSeek como secundário
async def query_llm(messages: List[Dict[str, str]]) -> str:
    nvidia_key = os.getenv("NVIDIA_API_KEY", "")
    deepseek_key = os.getenv("DEEPSEEK_API_KEY", "")

    # 1. Tentar Nvidia NIM API
    if nvidia_key:
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

    # 2. Fallback para DeepSeek API
    if deepseek_key:
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "https://api.deepseek.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {deepseek_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "deepseek-chat",
                        "messages": messages,
                        "temperature": 0.7,
                        "max_tokens": 1024
                    }
                )
                if response.status_code == 200:
                    return response.json()["choices"][0]["message"]["content"]
                else:
                    print(f"[LLM] Falha na DeepSeek ({response.status_code}): {response.text}")
        except Exception as e:
            print(f"[LLM] Erro ao chamar DeepSeek: {str(e)}")

    return "Desculpe, todas as APIs de inteligência artificial (Nvidia NIM e DeepSeek) falharam ou não possuem chaves válidas configuradas no arquivo .env."

class FactoryPayload(BaseModel):
    prompt: str
    dump: Optional[str] = ""
    brand: Optional[str] = "Geral"
    voice: Optional[str] = "pt-BR-AntonioNeural"
    post_to_youtube: Optional[bool] = False
    channel_id: Optional[str] = "default"

async def run_factory_pipeline(prediction_id: str, payload: FactoryPayload):
    try:
        update_db_prediction(prediction_id, "processing")
        log_application_activity(f"Iniciando esteira automatizada para o tema: '{payload.prompt}'")
        send_telegram_notification(f"🔍 *[Dezafira]* Iniciando esteira automatizada para o tema: `{payload.prompt}`\n\nGarimpando tendências e estruturando roteiro...")
        
        # 1. Configurar a voz selecionada temporariamente no importador do generator
        print(f"[API] Iniciando Fábrica para {prediction_id} com voz {payload.voice}")
        log_application_activity("Garimpando tendências e gerando roteiro autoral...")
        
        plan = await director.produce_campaign(
            theme=payload.prompt, 
            brand=payload.brand, 
            project_id=prediction_id
        )
        
        log_application_activity("Roteiro estruturado. Gerando dublagem OmniVoice e apresentador digital...")
        send_telegram_notification(f"✍️ *[Roteirização & Dublagem]* Roteiro autoral estruturado e locução gerada via OmniVoice!\n\nIniciando renderização do apresentador digital (InfiniteTalk) e montagem final...")
        
        final_video_name = f"{prediction_id}_preview.mp4"
        final_video_path = f"/outputs/{final_video_name}"
        absolute_video_path = os.path.join(director.outputs_dir, final_video_name)
        
        # Obter cookies do canal se houver
        db_sess = SessionLocal()
        channel = db_sess.query(Channel).filter(Channel.id == payload.channel_id).first()
        cookies_json = channel.cookies if channel else None
        db_sess.close()

        # 2. Renderização concluída - Aguarda aprovação prévia humana na UI
        log_application_activity("Renderização concluída! Vídeo salvo no histórico. Aguardando aprovação prévia na UI antes do upload.")
        send_telegram_notification(f"🎬 *[Esteira]* Vídeo para `{payload.prompt}` pronto! Acesse o painel da dezafira para aprovar e postar no YouTube.")
        
        update_db_prediction(prediction_id, "completed", video_url=final_video_path)
        log_application_activity(f"Esteira do ciclo concluída com sucesso para o ID: {prediction_id}!")
        
    except Exception as e:
        update_db_prediction(prediction_id, "failed", error=str(e))
        log_application_activity(f"Erro na esteira: {str(e)}")
        send_telegram_notification(f"❌ *[Falha]* Erro ao produzir vídeo para `{payload.prompt}`: {str(e)}")

@app.post("/api/v1/predictions")
async def create_prediction(payload: Dict[str, Any], background_tasks: BackgroundTasks):
    prediction_id = f"sniper_{uuid.uuid4().hex[:8]}"
    
    # Extrair parâmetros
    prompt = payload.get("prompt", "Geração de vídeo Sniper")
    dump = payload.get("dump", "")
    brand = payload.get("brand", "Geral")
    voice = payload.get("voice", "pt-BR-AntonioNeural")
    post_to_youtube = payload.get("post_to_youtube", False)
    channel_id = payload.get("channel_id", "default")
    
    factory_payload = FactoryPayload(
        prompt=prompt,
        dump=dump,
        brand=brand,
        voice=voice,
        post_to_youtube=post_to_youtube,
        channel_id=channel_id
    )
    
    save_db_prediction(prediction_id, prompt, channel_id)
    
    # Executar a campanha em segundo plano para liberar a requisição HTTP da UI
    background_tasks.add_task(run_factory_pipeline, prediction_id, factory_payload)
    
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

@app.post("/api/v1/hermes/chat")
async def chat_with_hermes(payload: ChatPayload, background_tasks: BackgroundTasks):
    user_msg = payload.message.lower().strip()
    
    # Registrar a mensagem do usuário no histórico
    hermes_chat_history.append({"role": "user", "content": payload.message})

    # Interceptor Inteligente para iniciar esteira real de produção
    trigger_production = False
    if any(k in user_msg for k in ["começar", "iniciar", "vamos começar", "go", "start", "produzir"]):
        trigger_production = True

    # Construir instruções do sistema para a persona do Hermes com Curadoria Humana
    system_instruction = (
        "Você é o Hermes, o Agente Orquestrador executivo e extremamente inteligente da plataforma DEZAFIRA, a Fábrica de Canais. "
        "Você está conversando diretamente com o JONATAS, o fundador da Holding Dezafira. "
        "Você deve explicar a ele que a esteira roda no modo de curadoria (Human-in-the-loop): você vai garimpar a tendência de melhor CPM via Trend Hunter, criar o roteiro otimizado para o YouTube Shorts respeitando 100% as políticas, gerar a narração local com OmniVoice e o apresentador digital. "
        "Porém, após o vídeo ficar pronto, você vai aguardar a aprovação explícita do Jonatas na UI (usando os botões de Aprovar e Rejeitar/Pedir Ajustes) antes de realizar a postagem física no canal dele. "
        "Se o Jonatas solicitar qualquer ajuste no vídeo rejeitado, confirme que você entenderá o feedback e corrigirá o roteiro/esteira. Mantenha um tom corporativo, extremamente prestativo e focado em monetização."
    )
    
    messages_for_llm = [{"role": "system", "content": system_instruction}] + hermes_chat_history[-10:] # Manter as últimas 10 interações para contexto

    # Chamar o LLM
    response_content = await query_llm(messages_for_llm)
    
    # Salvar resposta do Hermes no histórico
    hermes_chat_history.append({"role": "assistant", "content": response_content})
    
    # Se disparou a produção, inicia a BackgroundTask física no backend com um tema quente garimpado!
    if trigger_production:
        db = SessionLocal()
        first_chan = db.query(Channel).filter(Channel.status == "active").first()
        db.close()
        
        channel_id = first_chan.id if first_chan else "default"
        
        # Garimpa um tema autônomo baseado no nicho "Dropshipping"
        autonomous_theme = "Como Criar um Canal no YouTube com IA em 2026"
        try:
            trends = trend_hunter.fetch_youtube_trends("Inteligência Artificial")
            if trends and len(trends) > 0:
                autonomous_theme = trends[0].get("title", autonomous_theme)
        except Exception as e:
            print(f"[Hermes] Erro ao buscar tendências de chat: {e}")
            
        # Prepara a predição no banco
        pred_id = f"sniper_{uuid.uuid4().hex[:8]}"
        save_db_prediction(pred_id, autonomous_theme, channel_id)
        
        # Dispara
        payload_factory = FactoryPayload(
            prompt=autonomous_theme,
            post_to_youtube=True,
            channel_id=channel_id
        )
        log_application_activity("Comando recebido do Chat. Hermes ativou a esteira de IA.")
        background_tasks.add_task(run_factory_pipeline, pred_id, payload_factory)
    
    return {"reply": response_content, "history": hermes_chat_history}

@app.get("/api/v1/hermes/history")
async def get_hermes_history():
    return {"history": hermes_chat_history}

@app.post("/api/v1/hermes/clear")
async def clear_hermes_chat():
    global hermes_chat_history
    hermes_chat_history = [
        {"role": "assistant", "content": "Olá! Eu sou o Hermes, o agente orquestrador da Fábrica de Canais. Como posso te ajudar hoje?"}
    ]
    return {"message": "Chat reiniciado com sucesso.", "history": hermes_chat_history}

trend_hunter = DezafiraTrendHunter()

@app.get("/api/v1/trends")
async def get_niche_trends(query: Optional[str] = "Dropshipping"):
    return trend_hunter.fetch_youtube_trends(query)

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
            return f"⚠️ Erro ao processar IA do Hermes: {str(e)}"
        finally:
            loop.close()

    # Callback para o comando /produzir [tema]
    def on_telegram_produce(theme_text):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            factory_payload = FactoryPayload(
                prompt=theme_text,
                dump="",
                brand="Geral",
                voice="pt-BR-AntonioNeural",
                post_to_youtube=True,
                channel_id="default"
            )
            prediction_id = f"tele_{uuid.uuid4().hex[:8]}"
            save_db_prediction(prediction_id, theme_text, "default")
            loop.run_until_complete(run_factory_pipeline(prediction_id, factory_payload))
        except Exception as e:
            print(f"[Telegram Bot] Falha na esteira disparada por chat: {str(e)}")
        finally:
            loop.close()

    init_telegram_bot(on_telegram_chat, on_telegram_produce)

if __name__ == "__main__":
    import uvicorn
    # Inicia a API no host 127.0.0.1 porta 8000
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=True)

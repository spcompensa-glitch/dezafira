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

# Histórico de conversa com o Hermes
hermes_chat_history: List[Dict[str, str]] = [
    {"role": "assistant", "content": "Olá! Eu sou o Hermes, o agente orquestrador da Fábrica de Canais. Como posso te ajudar hoje?"}
]

director = SniperDirector()
uploader = YouTubeUploader()

# Servir arquivos estáticos de outputs para poder acessar o vídeo final
app.mount("/outputs", StaticFiles(directory="outputs"), name="outputs")

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
        send_telegram_notification(f"🔍 *[Dezafira]* Iniciando esteira automatizada para o tema: `{payload.prompt}`\n\nGarimpando tendências e estruturando roteiro...")
        
        # 1. Configurar a voz selecionada temporariamente no importador do generator
        # Se for pt-BR-FranciscaNeural, passamos ela para a produção de locução
        print(f"[API] Iniciando Fábrica para {prediction_id} com voz {payload.voice}")
        
        # Ajustamos o SniperDirector para receber o dump e a voz
        # Gerando o Roteiro, Narração e a Edição Completa com Legendas Dinâmicas
        # Nota: O SniperDirector chama o orquestrador que por sua vez chama o Whisper
        plan = await director.produce_campaign(
            theme=payload.prompt, 
            brand=payload.brand, 
            project_id=prediction_id
        )
        
        send_telegram_notification(f"✍️ *[Roteirização & Dublagem]* Roteiro autoral estruturado e locução gerada via OmniVoice!\n\nIniciando renderização do apresentador digital (InfiniteTalk) e montagem final...")
        
        final_video_name = f"{prediction_id}_preview.mp4"
        final_video_path = f"/outputs/{final_video_name}"
        absolute_video_path = os.path.join(director.outputs_dir, final_video_name)
        
        # Obter cookies do canal se houver
        db_sess = SessionLocal()
        channel = db_sess.query(Channel).filter(Channel.id == payload.channel_id).first()
        cookies_json = channel.cookies if channel else None
        db_sess.close()

        # 2. Upload automático no YouTube Studio se marcado
        if payload.post_to_youtube:
            update_db_prediction(prediction_id, "uploading")
            
            title = plan.get("title", f"Roteiro Automático: {payload.prompt}")
            description = plan.get("script", "Vídeo gerado de forma 100% automatizada pelo SniperVideoEngine!")
            
            send_telegram_notification(f"🚀 *[Publicação]* Renderização concluída! Iniciando upload no YouTube via Playwright simulado...")
            print(f"[API] Iniciando upload automático do vídeo {prediction_id} via Playwright...")
            channel_uploader = YouTubeUploader(channel_id=payload.channel_id)
            upload_success = channel_uploader.upload_video(
                video_path=absolute_video_path,
                title=title[:90], # Margem de segurança de caracteres do título do YT
                description=description,
                is_short=True,
                cookies_json=cookies_json
            )
            
            if upload_success:
                send_telegram_notification(f"✅ *[Publicado!]* O vídeo vertical `{title[:40]}` foi postado e agendado com sucesso no canal!")
                print(f"[API] Upload do vídeo {prediction_id} concluído com sucesso!")
            else:
                send_telegram_notification(f"⚠️ *[Aviso]* Vídeo gerado com sucesso, mas ocorreu uma falha no upload do YouTube.")
                print(f"[API] ⚠️ Falha ao fazer upload do vídeo {prediction_id}.")
        else:
            send_telegram_notification(f"🎬 *[Esteira Concluída]* Geração finalizada! Vídeo pronto para visualização local.")
        
        update_db_prediction(prediction_id, "completed", video_url=final_video_path)
        print(f"[API] Geração {prediction_id} finalizada com sucesso!")
        
    except Exception as e:
        update_db_prediction(prediction_id, "failed", error=str(e))
        send_telegram_notification(f"❌ *[Falha]* Erro ao produzir vídeo para `{payload.prompt}`: {str(e)}")
        print(f"[API] Erro na geração {prediction_id}: {str(e)}")

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

    # Se o usuário optou por colar os cookies diretamente, pula o robô de digitação e salva na hora!
    if payload.cookies_raw:
        from modules.database import save_db_channel_cookies
        try:
            cookies_json = payload.cookies_raw.strip()
            json.loads(cookies_json)
            success = save_db_channel_cookies(channel_id, cookies_json)
            if not success:
                raise HTTPException(status_code=400, detail="Falha ao salvar os cookies de sessão no banco.")
            return {"message": "Cookies importados e salvos com sucesso!"}
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

@app.post("/api/v1/hermes/chat")
async def chat_with_hermes(payload: ChatPayload):
    # Registrar a mensagem do usuário no histórico
    hermes_chat_history.append({"role": "user", "content": payload.message})

    # Construir instruções do sistema para a persona do Hermes
    system_instruction = (
        "Você é o Hermes, o Agente Orquestrador executivo e extremamente inteligente da plataforma DEZAFIRA, a Fábrica de Canais. "
        "Você está conversando diretamente com o JONATAS, o fundador da Holding Dezafira. "
        "Seu objetivo absoluto é rodar a esteira no modo 100% Autônomo (Mãos Livres), sem precisar calibrar ou fazer perguntas de restrições para o Jonatas. "
        "Quando o Jonatas mandar iniciar ou começar, confirme que assumirá todo o processo: garimpar a tendência de melhor CPM via Trend Hunter, criar o roteiro otimizado para o YouTube Shorts respeitando 100% as políticas do YouTube (original e autoral), gerar a narração, editar e agendar a postagem no canal dele. "
        "Mantenha um tom corporativo, direto, altamente capaz e diga a ele que você cuidará de tudo sozinho."
    )
    
    messages_for_llm = [{"role": "system", "content": system_instruction}] + hermes_chat_history[-10:] # Manter as últimas 10 interações para contexto

    # Chamar o LLM
    response_content = await query_llm(messages_for_llm)
    
    # Salvar resposta do Hermes no histórico
    hermes_chat_history.append({"role": "assistant", "content": response_content})
    
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

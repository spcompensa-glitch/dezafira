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
    SessionLocal
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
        
        # Obter refresh token do canal se houver
        db_sess = SessionLocal()
        channel = db_sess.query(Channel).filter(Channel.id == payload.channel_id).first()
        refresh_token = channel.youtube_refresh_token if channel else None
        db_sess.close()

        # 2. Upload automático no YouTube Studio se marcado
        if payload.post_to_youtube:
            update_db_prediction(prediction_id, "uploading")
            
            title = plan.get("title", f"Roteiro Automático: {payload.prompt}")
            description = plan.get("script", "Vídeo gerado de forma 100% automatizada pelo SniperVideoEngine!")
            
            if refresh_token:
                send_telegram_notification(f"🚀 *[Publicação]* Renderização concluída! Iniciando upload via API oficial do YouTube...")
                print(f"[API] Iniciando upload automático do vídeo {prediction_id} via YouTube API...")
                from modules.youtube_api_uploader import YouTubeApiUploader
                api_uploader = YouTubeApiUploader(refresh_token)
                upload_success = api_uploader.upload_video(
                    video_path=absolute_video_path,
                    title=title,
                    description=description
                )
            else:
                send_telegram_notification(f"🚀 *[Publicação]* Renderização concluída! Iniciando upload via Playwright (navegador virtual)...")
                print(f"[API] Iniciando upload automático do vídeo {prediction_id} via Playwright...")
                channel_uploader = YouTubeUploader(channel_id=payload.channel_id)
                upload_success = channel_uploader.upload_video(
                    video_path=absolute_video_path,
                    title=title[:90], # Margem de segurança de caracteres do título do YT
                    description=description,
                    is_short=True
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

@app.post("/api/v1/channels/{channel_id}/connect")
async def connect_channel_session(channel_id: str):
    # Retorna o link de login do OAuth dezafira
    # O frontend Next.js lerá esse link e abrirá em uma nova aba
    google_client_id = os.getenv("GOOGLE_CLIENT_ID", "")
    if not google_client_id:
        # Se as credenciais do Google OAuth não existirem nas variáveis, cai para o aviso de uploader local
        return {
            "message": "Navegador de Login aberto localmente.", 
            "auth_url": None
        }
        
    auth_url = f"https://backend-production-fc8b.up.railway.app/api/v1/auth/google/login?channel_id={channel_id}"
    return {
        "message": "Link de login OAuth gerado com sucesso.",
        "auth_url": auth_url
    }

@app.get("/api/v1/auth/google/login")
async def google_login(channel_id: str):
    google_client_id = os.getenv("GOOGLE_CLIENT_ID", "")
    if not google_client_id:
        raise HTTPException(status_code=400, detail="Google OAuth não configurado no servidor (GOOGLE_CLIENT_ID ausente)")
        
    actual_redirect = "https://backend-production-fc8b.up.railway.app/api/v1/auth/google/callback"
    auth_url = (
        "https://accounts.google.com/o/oauth2/v2/auth?"
        "response_type=code&"
        f"client_id={google_client_id}&"
        f"redirect_uri={actual_redirect}&"
        "scope=https://www.googleapis.com/auth/youtube.upload&"
        "access_type=offline&"
        "prompt=consent&"
        f"state={channel_id}"
    )
    return RedirectResponse(auth_url)

@app.get("/api/v1/auth/google/callback")
async def google_callback(code: str, state: str):
    channel_id = state
    google_client_id = os.getenv("GOOGLE_CLIENT_ID", "")
    google_client_secret = os.getenv("GOOGLE_CLIENT_SECRET", "")
    actual_redirect = "https://backend-production-fc8b.up.railway.app/api/v1/auth/google/callback"
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": google_client_id,
                "client_secret": google_client_secret,
                "redirect_uri": actual_redirect,
                "grant_type": "authorization_code"
            }
        )
        
        token_data = response.json()
        refresh_token = token_data.get("refresh_token")
        
        if refresh_token:
            from modules.database import save_db_channel_token
            save_db_channel_token(channel_id, refresh_token)
            
            html_content = """
            <html>
                <head>
                    <title>Dezafira — Canal Vinculado</title>
                    <style>
                        body {
                            background-color: #050505;
                            color: #ffffff;
                            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                            display: flex;
                            align-items: center;
                            justify-content: center;
                            height: 100vh;
                            margin: 0;
                        }
                        .container {
                            text-align: center;
                            border: 1px solid rgba(255,255,255,0.05);
                            background: rgba(255,255,255,0.02);
                            backdrop-filter: blur(10px);
                            padding: 40px;
                            border-radius: 24px;
                            box-shadow: 0 0 40px rgba(139, 92, 246, 0.1);
                        }
                        h1 {
                            font-size: 2.5em;
                            margin-bottom: 10px;
                            background: linear-gradient(to right, #00f2fe, #4facfe);
                            -webkit-background-clip: text;
                            -webkit-text-fill-color: transparent;
                        }
                        p { color: rgba(255,255,255,0.7); font-size: 1.1em; }
                    </style>
                </head>
                <body>
                    <div class="container">
                        <h1>✓ Canal Vinculado!</h1>
                        <p>A Dezafira já possui permissão segura de publicação.</p>
                        <p>Você pode fechar esta aba agora.</p>
                    </div>
                </body>
            </html>
            """
            return HTMLResponse(content=html_content)
        else:
            return {"error": "Falha ao obter token. Certifique-se de que removeu o acesso anterior do app e tente novamente."}

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

import asyncio
import os
import uuid
import json
import httpx
from fastapi import FastAPI, BackgroundTasks, HTTPException
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
    get_db_prediction
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
        
        # 2. Upload automático no YouTube Studio se marcado
        if payload.post_to_youtube:
            update_db_prediction(prediction_id, "uploading")
            send_telegram_notification(f"🚀 *[Publicação]* Renderização concluída! Iniciando upload seguro do vídeo no YouTube Studio...")
            print(f"[API] Iniciando upload automático do vídeo {prediction_id} no YouTube...")
            
            # Instancia o uploader dinamicamente com o ID do canal para isolar a sessão
            title = plan.get("title", f"Roteiro Automático: {payload.prompt}")
            description = plan.get("script", "Vídeo gerado de forma 100% automatizada pelo SniperVideoEngine!")
            
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
                send_telegram_notification(f"⚠️ *[Aviso]* Vídeo gerado com sucesso, mas ocorreu uma falha no upload automático do YouTube Studio.")
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
async def connect_channel_session(channel_id: str, background_tasks: BackgroundTasks):
    import time
    def open_login_window():
        from playwright.sync_api import sync_playwright
        import os
        project_dir = os.path.dirname(os.path.abspath(__file__))
        user_data_dir = os.path.join(project_dir, "temp", f"session_{channel_id}")
        os.makedirs(user_data_dir, exist_ok=True)
        
        with sync_playwright() as p:
            print(f"[Dezafira-Login] Abrindo painel de autenticação do YouTube Studio para o canal: {channel_id}")
            browser = p.chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                headless=False,
                args=["--disable-blink-features=AutomationControlled", "--start-maximized"],
                no_viewport=True
            )
            page = browser.pages[0] if browser.pages else browser.new_page()
            page.goto("https://studio.youtube.com")
            
            # Aguarda o usuário fazer login. Mantém o navegador aberto por até 5 minutos (300 segundos).
            # Se o usuário fechar o navegador antes, a execução termina de forma limpa.
            for _ in range(60):
                if browser.is_connected() == False:
                    break
                # Se detectar o seletor de painel do YouTube Studio, o login foi um sucesso
                try:
                    if page.locator("a#logo").is_visible():
                        print("[Dezafira-Login] Login de canal detectado com sucesso!")
                        break
                except:
                    pass
                time.sleep(5)
            
            # Garantir fechamento de navegador e persistência
            browser.close()
            print(f"[Dezafira-Login] Sessão de login do canal {channel_id} fechada e salva.")

    # Dispara a abertura do navegador em background para liberar o HTTP imediatamente
    background_tasks.add_task(open_login_window)
    return {"message": "Navegador de Login iniciado em background. Faça login na janela aberta."}

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

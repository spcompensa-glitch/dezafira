"""
Dezafira Backend - Railway Deployment
Health check + Hermes Chat + Video Production
"""
import os
import uuid
import asyncio
from datetime import datetime
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

app = FastAPI(title="Dezafira Backend")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ═══════════════════════════════════════════════════════════════════════════════
# LLM LOGS
# ═══════════════════════════════════════════════════════════════════════════════

llm_logs = []
active_provider = "none"

def log_llm(provider: str, message: str, tokens: int = 0):
    global active_provider
    active_provider = provider
    llm_logs.append({
        "provider": provider,
        "message": message,
        "tokens": tokens,
        "time": datetime.now().strftime("%H:%M:%S")
    })
    if len(llm_logs) > 50:
        llm_logs.pop(0)

@app.get("/api/v1/llm/logs")
async def get_llm_logs():
    return {"logs": llm_logs[-20:], "active_provider": active_provider}

# ═══════════════════════════════════════════════════════════════════════════════
# HEALTH CHECK
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "dezafira-backend"}

@app.get("/")
async def root():
    return {"message": "Dezafira Backend API", "version": "2.0"}

# ═══════════════════════════════════════════════════════════════════════════════
# HERMES CHAT
# ═══════════════════════════════════════════════════════════════════════════════

hermes_chat_history = [
    {
        "role": "assistant",
        "content": "Olá! Sou o Hermes, o orquestrador da DEZAFIRA. Controlo a fábrica de vídeos, canais YouTube e miniapps. O que deseja produzir?"
    }
]

async def query_llm(messages: List[Dict[str, str]]) -> str:
    import httpx
    
    nvidia_key = os.getenv("NVIDIA_API_KEY", "")
    deepseek_key = os.getenv("DEEPSEEK_API_KEY", "")
    
    # 1. NVIDIA (Primary)
    if nvidia_key:
        try:
            log_llm("nvidia", "Tentando NVIDIA NIM...")
            async with httpx.AsyncClient(timeout=90.0) as client:
                response = await client.post(
                    "https://integrate.api.nvidia.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {nvidia_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "meta/llama-3.1-8b-instruct",
                        "messages": messages,
                        "temperature": 0.7,
                        "max_tokens": 1024
                    }
                )
                if response.status_code == 200:
                    data = response.json()
                    tokens = data.get("usage", {}).get("total_tokens", 0)
                    log_llm("nvidia", "NVIDIA respondeu com sucesso!", tokens)
                    return data["choices"][0]["message"]["content"]
                else:
                    log_llm("nvidia", f"NVIDIA falhou: {response.status_code}")
        except Exception as e:
            log_llm("nvidia", f"Erro NVIDIA: {str(e)[:50]}")
    
    # 2. DeepSeek (Fallback)
    if deepseek_key:
        try:
            log_llm("deepseek", "Tentando DeepSeek...")
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    "https://api.deepseek.com/chat/completions",
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
                    data = response.json()
                    tokens = data.get("usage", {}).get("total_tokens", 0)
                    log_llm("deepseek", "DeepSeek respondeu com sucesso!", tokens)
                    return data["choices"][0]["message"]["content"]
                else:
                    log_llm("deepseek", f"DeepSeek falhou: {response.status_code}")
        except Exception as e:
            log_llm("deepseek", f"Erro DeepSeek: {str(e)[:50]}")
    
    log_llm("error", "Todos os provedores falharam")
    return "Erro: Todos os provedores LLM falharam."

@app.post("/api/v1/hermes/chat")
async def hermes_chat(payload: dict, background_tasks: BackgroundTasks):
    global hermes_chat_history
    message = payload.get("message", "").strip()
    channel_id = payload.get("channel_id")
    
    hermes_chat_history.append({"role": "user", "content": message})
    text, action_type, action_data = await process_hermes_command(message, channel_id, background_tasks)
    hermes_chat_history.append({"role": "assistant", "content": text})
    
    return {
        "response": text,
        "action_type": action_type,
        "action_data": action_data,
        "history": hermes_chat_history[-20:],
        "active_provider": active_provider
    }

@app.get("/api/v1/hermes/history")
async def get_hermes_history():
    return {"history": hermes_chat_history[-50:]}

@app.post("/api/v1/hermes/clear")
async def clear_hermes_history():
    global hermes_chat_history
    hermes_chat_history = [{"role": "assistant", "content": "Olá! Sou o Hermes, o orquestrador da DEZAFIRA. Controlo a fábrica de vídeos, canais YouTube e miniapps. O que deseja produzir?"}]
    return {"message": "Histórico limpo"}

async def process_hermes_command(message: str, channel_id: str = None, background_tasks: BackgroundTasks = None) -> tuple:
    msg = message.lower().strip()
    
    # VIDEO PRODUCTION
    if any(word in msg for word in ["dois vídeos", "dois videos"]):
        theme = "O Reino de Deus"
        for keyword in ["sobre", "tema"]:
            if keyword in msg:
                parts = msg.split(keyword)
                if len(parts) > 1:
                    theme = parts[1].strip()
                    break
        try:
            from modules.database import create_automation_task
            from modules.swarm_agents import agent_triage
            
            task_v_id = create_automation_task(f"{theme} (Vertical)", channel_id or "default")
            task_h_id = create_automation_task(f"{theme} (Horizontal)", channel_id or "default")
            
            if background_tasks:
                background_tasks.add_task(agent_triage, task_v_id, theme, channel_id or "default", "vertical")
                background_tasks.add_task(agent_triage, task_h_id, theme, channel_id or "default", "horizontal")
            
            return (
                f"Gerando vídeos sobre '{theme}' em formatos vertical e horizontal!",
                "multi_video",
                {"theme": theme, "vertical": {"status": "starting"}, "horizontal": {"status": "starting"}}
            )
        except Exception as e:
            return (f"Erro ao gerar vídeos: {str(e)}", None, None)
    
    if any(word in msg for word in ["produzir video", "produzir vídeo", "gerar video", "gerar vídeo", "make video"]):
        theme = message
        for prefix in ["produzir video ", "produzir vídeo ", "gerar video ", "gerar vídeo ", "make video "]:
            if msg.startswith(prefix):
                theme = message[len(prefix):]
                break
        try:
            from modules.database import create_automation_task
            from modules.swarm_agents import agent_triage
            
            task_id = create_automation_task(theme, channel_id or "default")
            if background_tasks:
                background_tasks.add_task(agent_triage, task_id, theme, channel_id or "default", "vertical")
            
            return (
                f"Iniciando produção do vídeo sobre '{theme}'!",
                "video",
                {"theme": theme, "status": "starting"}
            )
        except Exception as e:
            return (f"Erro ao produzir vídeo: {str(e)}", None, None)
    
    # RESEARCH
    if any(word in msg for word in ["pesquisar", "research"]):
        keyword = message
        for prefix in ["pesquisar ", "research "]:
            if msg.startswith(prefix):
                keyword = message[len(prefix):]
                break
        try:
            from research.engine import ResearchEngine
            engine = ResearchEngine()
            result = await engine.research_niche(keyword)
            return (f"Pesquisa de nicho '{keyword}' concluída!", "research", {"keyword": keyword})
        except Exception as e:
            return (f"Erro na pesquisa: {str(e)}", None, None)
    
    # HELP
    if any(word in msg for word in ["ajuda", "help", "comandos"]):
        return (
            "Comandos do Hermes:\n\n"
            "• produzir video [tema] - Gera vídeo vertical\n"
            "• dois vídeos sobre [tema] - Gera vertical + horizontal\n"
            "• pesquisar [tema] - Pesquisa nicho\n"
            "• help - Esta ajuda",
            None, None
        )
    
    # FALLBACK - LLM
    system_prompt = """Você é o Hermes, o cérebro orquestrador da plataforma DEZAFIRA - uma fábrica automatizada de canais YouTube.

Suas capacidades REAIS no sistema:
1. PRODUÇÃO DE VÍDEOS: Gerar vídeos completos via Hyperframes (roteiro + narração + edição automática)
2. GESTÃO DE CANAIS: Criar e gerenciar canais YouTube automatizados
3. PESQUISA DE NICHO: Analisar tendências e oportunidades de mercado
4. SEO & THUMBNAILS: Otimizar títulos, descrições e miniaturas para engajamento
5. UPLOAD AUTOMÁTICO: Postar vídeos diretamente no YouTube via Playwright
6. FÁBRICA DE MINIAPPS: Criar PWAs interativos (quizzes, landing pages) para monetização

COMANDOS DISPONÍVEIS:
• "produzir video [tema]" - Gera um vídeo vertical
• "dois vídeos sobre [tema]" - Gera vertical + horizontal
• "pesquisar [tema]" - Pesquisa o nicho
• "criar canal [nicho]" - Cria documentação do canal

Responda de forma DIRETA e EXECUTIVA. Foque no que o sistema DEZAFIRA pode fazer de REAL, não em conceitos genéricos de IA."""
    
    response = await query_llm([{"role": "system", "content": system_prompt}, {"role": "user", "content": message}])
    return (response, None, None)

# ═══════════════════════════════════════════════════════════════════════════════
# PREDICTIONS (VÍDEOS)
# ═══════════════════════════════════════════════════════════════════════════════

# In-memory store for predictions (simpler than DB for now)
predictions_store = {}

class PredictionCreate(BaseModel):
    prompt: str
    brand: Optional[str] = "Geral"
    video_format: Optional[str] = "vertical"
    channel_id: Optional[str] = "default"

@app.post("/api/v1/predictions")
async def create_prediction(payload: PredictionCreate, background_tasks: BackgroundTasks):
    prediction_id = f"sniper_{uuid.uuid4().hex[:8]}"
    predictions_store[prediction_id] = {
        "id": prediction_id,
        "prompt": payload.prompt,
        "brand": payload.brand,
        "video_format": payload.video_format,
        "channel_id": payload.channel_id,
        "status": "pending",
        "video_url": None
    }
    
    try:
        from modules.database import create_automation_task, save_db_prediction
        from modules.swarm_agents import agent_triage
        
        task_id = create_automation_task(payload.prompt, payload.channel_id or "default")
        save_db_prediction(prediction_id, payload.prompt, payload.channel_id or "default")
        
        if background_tasks:
            background_tasks.add_task(agent_triage, task_id, payload.prompt, payload.channel_id or "default", payload.video_format)
        
        return {"id": prediction_id, "status": "starting", "message": "Geração iniciada!"}
    except Exception as e:
        return {"id": prediction_id, "status": "error", "message": str(e)}

@app.get("/api/v1/predictions/history")
async def get_predictions_history():
    return {"history": list(predictions_store.values())}

@app.get("/api/v1/predictions/{prediction_id}")
async def get_prediction(prediction_id: str):
    if prediction_id not in predictions_store:
        raise HTTPException(status_code=404, detail="Predição não encontrada")
    return predictions_store[prediction_id]

@app.post("/api/v1/predictions/{prediction_id}/approve")
async def approve_prediction(prediction_id: str):
    if prediction_id not in predictions_store:
        raise HTTPException(status_code=404, detail="Predição não encontrada")
    predictions_store[prediction_id]["status"] = "approved"
    return {"message": "Aprovado!"}

@app.post("/api/v1/predictions/{prediction_id}/reject")
async def reject_prediction(prediction_id: str):
    if prediction_id not in predictions_store:
        raise HTTPException(status_code=404, detail="Predição não encontrada")
    predictions_store[prediction_id]["status"] = "rejected"
    return {"message": "Rejeitado!"}

# ═══════════════════════════════════════════════════════════════════════════════
# ANALYTICS
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/api/v1/factory/monitor-stats")
async def get_factory_stats():
    return {
        "total_queued": 0,
        "total_processing": 0,
        "total_ready": 0,
        "total_completed": len([p for p in predictions_store.values() if p["status"] == "completed"]),
        "total_failed": len([p for p in predictions_store.values() if p["status"] == "failed"]),
        "active_tasks": []
    }

# ═══════════════════════════════════════════════════════════════════════════════
# STATIC FILES
# ═══════════════════════════════════════════════════════════════════════════════

if os.path.exists("outputs"):
    app.mount("/outputs", StaticFiles(directory="outputs"), name="outputs")

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))

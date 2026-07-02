import asyncio
import os
from .database import update_automation_task, get_automation_task
from manager import SniperDirector
from services.memory_service import (
    get_channel_context_prompt,
    log_failed_keyword,
    log_success_pattern,
    seed_default_knowledge,
)
from services.open_montage_bridge import produce_video, is_open_montage_available

director = SniperDirector()


async def agent_triage(task_id: int, theme: str, channel_id: str, video_format: str = "vertical"):
    """
    Agente de Triagem: Busca tendências e escolhe o melhor tópico.
    """
    print(f"[Swarm - Triage] Iniciando triagem para a task {task_id} (tema: {theme})")

    # Seed conhecimento padrão se for um canal novo
    if channel_id:
        seed_default_knowledge(channel_id)

    # Busca tendências
    trends = []
    try:
        trends = director.trend_hunter.fetch_youtube_trends(theme)
    except Exception as e:
        print(f"[Swarm - Triage] Erro no trend hunting: {e}")

    best_title = theme
    if trends:
        best_title = trends[0].get('title', theme)
        print(f"[Swarm - Triage] Melhor tendência garimpada: {best_title}")
    else:
        print("[Swarm - Triage] Sem tendências. Usando tema direto.")

    # Atualiza banco
    update_automation_task(task_id, title_suggestion=best_title, status="writing")

    # Chama o próximo agente no Swarm
    asyncio.create_task(agent_writer(task_id, best_title, theme, trends, channel_id, video_format))


async def agent_writer(task_id: int, best_title: str, theme: str, trends: list, channel_id: str = "default", video_format: str = "vertical"):
    """
    Agente Roteirista: Escreve o roteiro e gera visual prompts usando o SniperBrain.
    Inclui contexto do Shared Memory (channel_knowledge) para personalizar o tom.
    """
    print(f"[Swarm - Writer] Escrevendo roteiro para a task {task_id} ({best_title})")

    trends_context = "\n".join(
        [f"- {t['title']} ({t['metric']})" for t in trends[:5]]
    ) if trends else ""

    # ─── Shared Memory: Injetar contexto do canal ────────────────────
    channel_context = ""
    if channel_id:
        channel_context = get_channel_context_prompt(channel_id)
        if channel_context:
            print(f"[Swarm - Writer] Shared Memory encontrado para canal {channel_id}")

    # Passar contexto da memória para o Brain
    plan = director.brain.generate_script(
        theme,
        "Dezafira",
        trends_context=trends_context,
        channel_context=channel_context,
    )

    script_text = plan.get('script', '')

    # Atualiza banco
    update_automation_task(task_id, script_content=script_text, status="SEO")

    # Chama próximo agente
    asyncio.create_task(agent_seo(task_id, best_title, plan, channel_id, video_format))


async def agent_seo(task_id: int, best_title: str, plan: dict, channel_id: str = "default", video_format: str = "vertical"):
    """
    Agente SEO: Gera tags e descrição para o vídeo.
    Consulta o Shared Memory para blacklist de SEO.
    """
    print(f"[Swarm - SEO] Otimizando SEO para a task {task_id}")

    # Consultar Shared Memory para blacklist de SEO
    from services.memory_service import get_knowledge, CATEGORY_SEO_BLACKLIST
    seo_blacklist = []
    if channel_id:
        blacklist_records = get_knowledge(channel_id, category=CATEGORY_SEO_BLACKLIST)
        seo_blacklist = [r["meta_key"] for r in blacklist_records]

    tags = f"#Shorts, {best_title.replace(' ', '')}, #Viral, #IA"
    description = (
        f"Vídeo 100% autônomo sobre {best_title}!\n\n"
        f"Roteiro gerado pela Dezafira Factory — sua fábrica de canais YouTube.\n\n"
        f"🎬 Produzido com OpenMontage + NVIDIA AI + Pexels"
    )

    if seo_blacklist:
        blacklist_str = ", ".join(seo_blacklist)
        print(f"[Swarm - SEO] Evitando blacklist: {blacklist_str}")

    metadata = f"Title: {best_title}\nDescription: {description}\nTags: {tags}"
    update_automation_task(task_id, metadata_tags=metadata, status="production")

    # Chama próximo agente
    asyncio.create_task(agent_producer(task_id, plan, best_title, channel_id, video_format))


async def agent_producer(task_id: int, plan: dict, best_title: str, channel_id: str = "default", video_format: str = "vertical"):
    """
    Agente Produtor: Gera áudio via Kokoro TTS e produz o vídeo
    usando o OpenMontage como motor principal (com fallback MoviePy).

    Args:
        task_id: ID da task
        plan: Dicionário com título, script, visual_prompts
        best_title: Título do vídeo
        channel_id: ID do canal
        video_format: 'vertical' (9:16) para Shorts ou 'horizontal' (16:9) para YouTube normal
    """
    print(f"[Swarm - Producer] Produzindo mídia para a task {task_id} (formato: {video_format})")

    project_id = f"task_{task_id}"

    from modules.voice_gen import generate_voice
    import os

    # Garantir diretórios
    os.makedirs(director.outputs_dir, exist_ok=True)
    os.makedirs(director.temp_dir, exist_ok=True)

    voice_file = os.path.join(director.outputs_dir, f"{project_id}_voice.mp3")

    print(f"[Swarm - Producer] Gerando TTS via Kokoro...")
    try:
        await generate_voice(plan.get("script", best_title), voice_file)
    except Exception as e:
        print(f"[Swarm - Producer] Erro no TTS: {e}")
        update_automation_task(task_id, status="failed")
        return

    # ─── Produzir vídeo via OpenMontage Bridge ──────────────────────
    print(f"[Swarm - Producer] Iniciando produção de vídeo...")
    print(f"[Swarm - Producer] OpenMontage disponível: {is_open_montage_available()}")

    search_query = director._build_search_query(plan)
    visual_keywords = plan.get("visual_prompts", [search_query])

    result = await produce_video(
        task_id=task_id,
        prompt=best_title,
        script_text=plan.get("script", ""),
        visual_keywords=visual_keywords,
        voice_path=voice_file,
        channel_id=channel_id,
        provider="nvidia",
        video_format=video_format,
    )

    if result.get("success"):
        video_url = f"/outputs/{project_id}_preview.mp4"
        print(f"[Swarm - Producer] Vídeo produzido com sucesso! Modo: {result.get('mode', 'unknown')}")
        print(f"[Swarm - Producer] Tamanho: {result.get('size_mb', '?')}MB")

        # Registrar sucesso no Shared Memory
        if channel_id:
            for kw in visual_keywords[:2]:
                log_success_pattern(channel_id, kw)

        update_automation_task(task_id, status="ready", video_url=video_url)
    else:
        print(f"[Swarm - Producer] Falha na produção: {result.get('error')}")

        # Registrar falha no Shared Memory
        if channel_id:
            for kw in visual_keywords[:2]:
                log_failed_keyword(channel_id, kw)

        update_automation_task(task_id, status="failed")

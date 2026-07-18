"""
Hermes Orchestrator
Orquestrador principal do pipeline de produção.
"""
import asyncio
import sys
import os
from typing import Dict, Any, Optional
from .engine import PipelineEngine, StageStatus
from .websocket import WebSocketHub

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from research.engine import ResearchEngine


class HermesOrchestrator:
    """
    Orquestrador Hermes - Controla todo o fluxo de produção.
    
    Responsabilidades:
    1. Iniciar e gerenciar pipelines
    2. Coordenar estágios de produção
    3. Reportar status via WebSocket
    4. Integrar Research Engine com Production
    """

    def __init__(self, websocket_hub: WebSocketHub):
        self.ws_hub = websocket_hub
        self.research_engine = ResearchEngine()
        self.pipelines: Dict[str, PipelineEngine] = {}
        self._running_tasks: Dict[str, asyncio.Task] = {}

    async def start_pipeline(
        self,
        theme: str,
        channel_id: str = None,
        video_format: str = "vertical",
        blocks: list = None,
        task_id: str = None,
    ) -> str:
        """
        Inicia um novo pipeline de produção.
        
        Args:
            theme: Tema do vídeo
            channel_id: ID do canal (opcional)
            video_format: Formato do vídeo (horizontal/vertical)
            blocks: Lista de blocos modulares para o vídeo (opcional)
            task_id: ID externo da tarefa (opcional, gera UUID se None)
            
        Returns:
            ID da tarefa criada
        """
        if not task_id:
            import uuid
            task_id = str(uuid.uuid4())[:8]
        
        print(f"[Hermes] Iniciando pipeline: {task_id} - {theme} (Modular: {blocks is not None})")
        
        pipeline = PipelineEngine(
            task_id=task_id,
            theme=theme,
            channel_id=channel_id,
            video_format=video_format,
        )
        pipeline.modular_blocks = blocks
        
        pipeline.add_listener(self._on_pipeline_event)
        
        self.pipelines[task_id] = pipeline
        
        await self.ws_hub.broadcast("pipeline_created", {
            "task_id": task_id,
            "theme": theme,
            "status": "running",
        })
        
        self._running_tasks[task_id] = asyncio.create_task(
            self._run_pipeline(task_id)
        )
        
        return task_id

    async def _run_pipeline(self, task_id: str):
        """
        Executa o pipeline completo.
        
        Args:
            task_id: ID da tarefa
        """
        pipeline = self.pipelines.get(task_id)
        if not pipeline:
            return
        
        try:
            await self._run_research_stage(pipeline)
            
            if pipeline.state.status != "running":
                return
            
            await self._run_script_stage(pipeline)
            
            if pipeline.state.status != "running":
                return
            
            await self._run_seo_stage(pipeline)
            
            if pipeline.state.status != "running":
                return
            
            await self._run_produce_stage(pipeline)
            
        except Exception as e:
            print(f"[Hermes] Erro no pipeline {task_id}: {e}")
            pipeline.fail_stage(pipeline.state.current_stage, str(e))

    async def _run_research_stage(self, pipeline: PipelineEngine):
        """Executa estágio de pesquisa."""
        stage_name = "research"
        pipeline.start_stage(stage_name)
        
        await self.ws_hub.send_to_task(
            pipeline.state.task_id,
            "stage_log",
            {"stage": stage_name, "message": "Iniciando pesquisa de tendências..."}
        )
        
        research_result = await self.research_engine.research_niche(pipeline.state.theme)
        
        pipeline.complete_stage(stage_name, {
            "niche_score": research_result.niche_score,
            "competition": research_result.competition_level,
            "trending_videos": len(research_result.trending_videos),
            "title_patterns": research_result.title_patterns[:5],
        })

    async def _run_script_stage(self, pipeline: PipelineEngine):
        """Executa estágio de roteiro com ScriptWriter (DeepSeek 6-pass)."""
        stage_name = "script"
        pipeline.start_stage(stage_name)

        await self.ws_hub.send_to_task(
            pipeline.state.task_id,
            "stage_log",
            {"stage": stage_name, "message": "Gerando roteiro com ScriptWriter (DeepSeek 6-pass)..."}
        )

        pipeline.update_progress(stage_name, 25, "Chamando ScriptWriter...")

        try:
            from modules.scriptwriter import ScriptWriter
            writer = ScriptWriter(channel_id=pipeline.state.channel_id or "default")

            script_data = await writer.write(
                theme=pipeline.state.theme,
                target_seconds=60,
                video_format=pipeline.state.video_format or "vertical",
                language="pt",
            )

            word_count = script_data.get("word_count", 0)
            title = script_data.get("title", pipeline.state.theme)

            pipeline.update_progress(stage_name, 90, f"Roteiro gerado: {word_count} palavras")

            pipeline.complete_stage(stage_name, {
                "title": title,
                "script_length": word_count,
                "word_count": f"{word_count} palavras",
                "duration_estimate": f"{script_data.get('duration_estimate', 60)}s",
                "script_data": script_data,
            })
        except Exception as e:
            print(f"[Hermes] Erro no estagio script: {e}")
            pipeline.fail_stage(stage_name, str(e))

    async def _run_seo_stage(self, pipeline: PipelineEngine):
        """Executa estágio de SEO com ResearchEngine SEOAnalyzer REAL (Bug C3 fix)."""
        stage_name = "seo"
        pipeline.start_stage(stage_name)

        await self.ws_hub.send_to_task(
            pipeline.state.task_id,
            "stage_log",
            {"stage": stage_name, "message": "Otimizando SEO com SEOAnalyzer..."}
        )

        pipeline.update_progress(stage_name, 30, "Analisando padroes SEO...")

        try:
            from research.analyzers.seo_analyzer import SEOAnalyzer
            seo_analyzer = SEOAnalyzer()

            # Recuperar roteiro do estagio anterior
            script_stage = pipeline.state.stages.get("script")
            script_data = script_stage.data.get("script_data", {}) if script_stage else {}
            title = script_data.get("title", pipeline.state.theme)

            # Analise SEO real: gera tags, description, otimizacoes
            seo_result = await seo_analyzer.analyze([
                {"title": title, "views": "1000", "channel": ""},
            ])

            tags = seo_result.get("keywords", []) if isinstance(seo_result, dict) else []
            tags_count = len(tags) if isinstance(tags, list) else 0

            pipeline.update_progress(stage_name, 90, f"SEO otimizado: {tags_count} tags")

            pipeline.complete_stage(stage_name, {
                "tags_count": tags_count,
                "tags": tags[:25] if isinstance(tags, list) else [],
                "title_optimized": True,
                "description_optimized": True,
                "seo_analysis": seo_result,
            })
        except Exception as e:
            print(f"[Hermes] Erro no estagio SEO: {e}")
            pipeline.fail_stage(stage_name, str(e))

    async def _run_produce_stage(self, pipeline: PipelineEngine):
        """Executa estágio de produção via HyperFrames (motor único)."""
        stage_name = "produce"
        pipeline.start_stage(stage_name)
        await self.ws_hub.send_to_task(
            pipeline.state.task_id,
            "stage_log",
            {"stage": stage_name, "message": "Produzindo video via HyperFrames..."}
        )

        pipeline.update_progress(stage_name, 10, "Preparando producao...")

        try:
            import os
            script_stage = pipeline.state.stages.get("script")
            script_data = script_stage.data if script_stage else {}
            title = script_data.get("title", pipeline.state.theme)
            script_text = script_data.get("script_data", {}).get("script", "") if script_data else ""

            # 1. Gerar narracao (Kokoro TTS)
            pipeline.update_progress(stage_name, 20, "Gerando narracao Kokoro TTS...")
            audio_path = None
            try:
                from modules.voice_gen import generate_voice
                project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                audio_path = os.path.join(project_dir, "outputs", "temp", f"{pipeline.state.task_id}_voice.wav")
                os.makedirs(os.path.dirname(audio_path), exist_ok=True)

                voice_text = script_text or f"Video sobre {pipeline.state.theme}"
                audio_path = await generate_voice(voice_text, audio_path, voice="pf_dora")
                print(f"[Hermes] Audio gerado: {audio_path}")
            except Exception as voice_err:
                print(f"[Hermes] Erro TTS: {voice_err}")
                audio_path = None

            if not audio_path or not os.path.exists(audio_path):
                pipeline.fail_stage(stage_name, "Falha ao gerar audio - pipeline abortada")
                return

            # 2. Produzir video via HyperFrames (motor único)
            pipeline.update_progress(stage_name, 40, "Produzindo video via OpenMontage Bridge...")
            video_path = None
            try:
                from services.open_montage_bridge import produce_video
                project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                video_path = os.path.join(project_dir, "outputs", f"{pipeline.state.task_id}_preview.mp4")

                visual_keywords = script_data.get("visual_prompts", [pipeline.state.theme]) if script_data else [pipeline.state.theme]
                if isinstance(visual_keywords, str):
                    visual_keywords = [visual_keywords]

                result = await produce_video(
                    task_id=hash(pipeline.state.task_id) % 100000,
                    prompt=title or pipeline.state.theme,
                    script_text=script_text,
                    visual_keywords=visual_keywords,
                    voice_path=audio_path,
                    channel_id=pipeline.state.channel_id or "default",
                    provider="nvidia",
                    video_format=pipeline.state.video_format,
                )

                if result.get("success"):
                    video_path = result.get("output_path")
                    mode = result.get("mode", "unknown")
                    size_mb = result.get("size_mb", 0)
                    print(f"[Hermes] Video produzido ({mode}): {video_path} ({size_mb}MB)")
                else:
                    print(f"[Hermes] Producao falhou: {result.get('error')}")
                    video_path = None
            except Exception as prod_err:
                print(f"[Hermes] Erro na producao: {prod_err}")
                video_path = None

            pipeline.update_progress(stage_name, 95, "Finalizando video...")

            if video_path and os.path.exists(video_path):
                size_mb = os.path.getsize(video_path) / (1024 * 1024)
                pipeline.complete_stage(stage_name, {
                    "video_ready": True,
                    "output_path": video_path,
                    "audio_path": audio_path,
                    "title": title,
                    "size_mb": round(size_mb, 1),
                })
            else:
                pipeline.fail_stage(stage_name, "Video nao foi gerado. Verifique logs de producao.")

            # 3. (Aditivo, não-bloqueante) Pipeline ELTON FLOW — imagens originais
            #    via Google Flow + draft editável do CapCut, como entrega extra.
            #    Não sobrescreve o vídeo principal; apenas anexa às entregas.
            try:
                pipeline.update_progress(
                    stage_name, 97,
                    "Gerando entrega adicional ELTON FLOW (imagens Google Flow + draft CapCut)...")
                from modules.video_pipeline import produce_with_elton
                elton = await produce_with_elton(
                    theme=pipeline.state.theme,
                    video_format=pipeline.state.video_format,
                    language="pt",
                    target_seconds=60,
                    make_draft=True,
                    nome_projeto=f"Dezafira_{pipeline.state.task_id}",
                    on_progress=lambda s, p, l: print(f"[Hermes/ELTON] {s} {p}% — {l}"),
                )
                produce_stage = pipeline.state.stages.get(stage_name)
                if produce_stage is not None:
                    produce_stage.data.setdefault("extras", {})["elton_flow"] = {
                        "ok": elton.get("ok"),
                        "images": len([i for i in elton.get("images", []) if i.get("path")]),
                        "video": elton.get("video"),
                        "capcut_draft": (elton.get("capcut_draft") or {}).get("draft_path"),
                    }
                print(f"[Hermes] ELTON FLOW aditivo concluído: ok={elton.get('ok')}")
            except Exception as elton_err:
                print(f"[Hermes] ELTON FLOW aditivo falhou (não-bloqueante): {elton_err}")
        except Exception as e:
            print(f"[Hermes] Erro no estagio produce: {e}")
            pipeline.fail_stage(stage_name, str(e))

    def _on_pipeline_event(self, event_type: str, data: Dict[str, Any]):
        """Callback para eventos do pipeline (Bug L11 fix)."""
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.ws_hub.broadcast(event_type, data))
        except RuntimeError:
            # Sem event loop rodando - schedulesafe
            asyncio.ensure_future(self.ws_hub.broadcast(event_type, data))

    def get_pipeline(self, task_id: str) -> Optional[PipelineEngine]:
        """Retorna pipeline pelo ID."""
        return self.pipelines.get(task_id)

    def get_all_pipelines(self) -> Dict[str, Dict[str, Any]]:
        """Retorna todos os pipelines."""
        return {
            task_id: pipeline.to_dict()
            for task_id, pipeline in self.pipelines.items()
        }

    def pause_pipeline(self, task_id: str) -> bool:
        """Pausa um pipeline."""
        pipeline = self.pipelines.get(task_id)
        if pipeline:
            return pipeline.pause()
        return False

    def resume_pipeline(self, task_id: str) -> bool:
        """Retoma um pipeline."""
        pipeline = self.pipelines.get(task_id)
        if pipeline:
            return pipeline.resume()
        return False

    def stop_pipeline(self, task_id: str) -> bool:
        """Para um pipeline."""
        pipeline = self.pipelines.get(task_id)
        if pipeline:
            if task_id in self._running_tasks:
                self._running_tasks[task_id].cancel()
                del self._running_tasks[task_id]
            return pipeline.stop()
        return False

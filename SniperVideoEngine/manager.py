import asyncio
import os
import json
from modules.brain import SniperBrain
from modules.voice_gen import generate_voice
from modules.pexels_client import PexelsClient
from modules.scrapling_agent import DezafiraTrendHunter
from orchestrator import assemble_video
from dotenv import load_dotenv

load_dotenv()


class SniperDirector:
    def __init__(self):
        self.brain = SniperBrain()
        self.trend_hunter = DezafiraTrendHunter()
        self.pexels = PexelsClient()

        self.project_dir = os.path.dirname(os.path.abspath(__file__))
        self.outputs_dir = os.path.join(self.project_dir, "outputs")
        self.temp_dir = os.path.join(self.project_dir, "outputs", "temp")
        self.assets_dir = os.path.join(self.project_dir, "assets")

        os.makedirs(self.outputs_dir, exist_ok=True)
        os.makedirs(self.temp_dir, exist_ok=True)

        # Seed conhecimento padrão para canal default
        try:
            from services.memory_service import seed_default_knowledge
            seed_default_knowledge("default")
        except Exception:
            pass

    async def produce_campaign(self, theme, brand="Geral", project_id="campanha_01", video_format="vertical"):
        print(f"\n{'='*60}")
        print(f" DEZAFIRA - PRODUCAO AUTOMATIZADA")
        print(f" Campanha: {project_id} | Marca: {brand}")
        print(f"{'='*60}\n")

        # ── STEP 1: TREND HUNTING ─────────────────────────────────
        print("[1/6] Garimpando tendencias no YouTube...")
        trends = []
        try:
            trends = self.trend_hunter.fetch_youtube_trends(theme)
            if trends:
                print(f"   [OK] {len(trends)} tendencias encontradas:")
                for t in trends[:3]:
                    print(f"      - {t['title']}")
            else:
                print("   [AVISO] Nenhuma tendencia encontrada. Usando tema direto.")
        except Exception as e:
            print(f"   [AVISO] Erro no trend hunting: {e}")

        # ── STEP 2: ROTEIRO (BRAIN + LLM) ─────────────────────────
        print("\n[2/6] Gerando roteiro via LLM...")
        trends_context = "\n".join(
            [f"- {t['title']} ({t['metric']})" for t in trends[:5]]
        ) if trends else ""
        plan = self.brain.generate_script(theme, brand, trends_context=trends_context)
        print(f"   [OK] Roteiro pronto: \"{plan['title']}\"")
        print(f"   {len(plan['script'].split())} palavras | ~{plan.get('target_duration', 45)}s")

        # ── STEP 3: LOCUCACAO (KOKORO TTS) ──────────────────────────
        voice_file = os.path.join(self.outputs_dir, f"{project_id}_voice.mp3")
        print("\n[3/6] Gerando locucao via Kokoro TTS...")
        await generate_voice(plan["script"], voice_file)
        print(f"   [OK] Locucao salva: {os.path.basename(voice_file)}")

        # ── STEP 4: PRODUCAO DE VIDEO (OpenMontage + Fallback) ────
        print("\n[4/6] Produzindo video via OpenMontage Bridge...")
        search_query = self._build_search_query(plan)
        print(f"   Busca visual: \"{search_query}\"")

        from services.open_montage_bridge import produce_video, is_open_montage_available

        om_available = is_open_montage_available()
        print(f"   OpenMontage disponivel: {om_available}")

        final_output = os.path.join(self.outputs_dir, f"{project_id}_preview.mp4")

        visual_keywords = plan.get("visual_prompts", [search_query])

        result = await produce_video(
            task_id=0,  # Task ID 0 = chamada direta do manager
            prompt=plan.get("title", theme),
            script_text=plan.get("script", ""),
            visual_keywords=visual_keywords,
            voice_path=voice_file,
            channel_id="default",
            provider="nvidia",
            video_format=video_format,
        )

        if result.get("success"):
            print(f"   [OK] Video produzido! Modo: {result.get('mode', 'unknown')}")
            print(f"   Tamanho: {result.get('size_mb', '?')}MB")
        else:
            print(f"   [ERRO] Falha na producao: {result.get('error')}")

        # ── STEP 5: RESUMO ────────────────────────────────────────
        print(f"\n{'='*60}")
        if os.path.exists(final_output):
            size_mb = os.path.getsize(final_output) / (1024 * 1024)
            print(f" [OK] PRODUCAO CONCLUIDA!")
            print(f" Video: {final_output}")
            print(f" Tamanho: {size_mb:.1f}MB")
        else:
            print(f" [AVISO] PRODUCAO PARCIAL - Sem video final")
            print(f" Roteiro e audio disponiveis em: {self.outputs_dir}")

        print(f" Roteiro: {plan['title']}")
        print(f"{'='*60}\n")

        # Registrar no Shared Memory
        try:
            from services.memory_service import log_success_pattern
            log_success_pattern("default", search_query, "Pipeline classica concluida")
        except Exception:
            pass

        return plan

    def _build_search_query(self, plan):
        """Construi query de busca para o Pexels extraindo palavras-chave dos visual_prompts."""
        visual_prompts = plan.get("visual_prompts", [])
        if visual_prompts:
            prompt = visual_prompts[0]
            stopwords = {'a', 'o', 'e', 'de', 'do', 'da', 'em', 'um', 'uma', 'com', 'para', 'por',
                         'the', 'of', 'in', 'to', 'and', 'is', 'with', 'for', 'on', 'at', 'high',
                         'quality', 'cinematic', 'shot', 'of', 'person', 'thinking', 'about'}
            words = prompt.split()
            keywords = [w.strip('.,!?;:"') for w in words
                        if w.lower().strip('.,!?;:"') not in stopwords and len(w) > 3]
            return ' '.join(keywords[:5]) if keywords else prompt[:80]

        # Fallback: usar o titulo como query
        return plan.get("title", "abstract technology")[:80]


if __name__ == "__main__":
    director = SniperDirector()
    tema = "Como a Inteligência Artificial está transformando o mundo em 2026"
    asyncio.run(director.produce_campaign(tema, "Dezafira", "test_pipeline_01"))

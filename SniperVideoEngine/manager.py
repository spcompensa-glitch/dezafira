import asyncio
import os
import json
from modules.brain import SniperBrain
from modules.voice_gen import generate_voice
from modules.video_agent import VideoAgent
from modules.music_agent import MusicAgent
from orchestrator import assemble_video
from dotenv import load_dotenv

load_dotenv()

class SniperDirector:
    def __init__(self):
        self.brain = SniperBrain()
        self.video_agent = VideoAgent()
        self.music_agent = MusicAgent()
        
        self.project_dir = os.path.dirname(os.path.abspath(__file__))
        self.outputs_dir = os.path.join(self.project_dir, "outputs")
        self.assets_dir = os.path.join(self.project_dir, "assets")
        
        os.makedirs(self.outputs_dir, exist_ok=True)

    async def produce_campaign(self, theme, brand="Geral", project_id="campanha_01"):
        print(f"\n{'='*50}")
        print(f" SNIPER VIDEO ENGINE - INICIANDO PRODUÇÃO")
        print(f" Campanha: {project_id} | Marca: {brand}")
        print(f"{'='*50}\n")
        
        # 1. BRAIN: Roteirização e Planejamento
        print("[Brain] Gerando roteiro estratégico e prompts visuais...")
        plan = self.brain.generate_script(theme, brand)
        print(f"[Brain] Roteiro finalizado. Estimativa: {plan['target_duration']}s")
        
        # 2. VOICE: Produção da Locução
        voice_file = os.path.join(self.outputs_dir, f"{project_id}_voice.mp3")
        print(f"[Voice] Gravando locução em PT-BR...")
        await generate_voice(plan['script'], voice_file)
        
        # 3. MUSIC: Seleção de Trilha Sonora
        print(f"[Music] Selecionando trilha para o clima: {plan['music_prompt']}")
        music_file = self.music_agent.select_track(plan['music_prompt'])
        if music_file:
            print(f"[Music] Trilha selecionada: {os.path.basename(music_file)}")
        else:
            print("[Music] Nenhuma trilha compatível encontrada. Usando modo sem música.")
        
        # 4. VIDEO: Geração Real via ComfyUI
        print("[Video] Iniciando geração de clipes reais...")
        generated_clips = await self.video_agent.generate_clips(plan['visual_prompts'], project_id)
        
        # 5. EDITOR: Montagem Final
        final_output = os.path.join(self.outputs_dir, f"{project_id}_preview.mp4")
        
        if generated_clips and len(generated_clips) > 0:
            video_source = generated_clips[0] # Usa o primeiro clipe gerado
            print(f"[Editor] Usando clipe gerado: {os.path.basename(video_source)}")
        else:
            print("[Editor] ⚠️ Nenhum clipe gerado. Usando placeholder de emergência.")
            video_source = os.path.join(self.assets_dir, "placeholder_video.mp4")
        
        print("[Editor] Realizando montagem do vídeo final...")
        assemble_video(video_source, voice_file, final_output, music_path=music_file)
        
        print(f"\n{'='*50}")
        print(f" CAMPANHA PRONTA PARA REVISÃO!")
        print(f" Arquivo Preview: {final_output}")
        print(f"{'='*50}\n")
        
        return plan

if __name__ == "__main__":
    director = SniperDirector()
    
    # Exemplo de uso:
    tema = "Como a Otto Pinturas transforma fachadas de prédios com segurança e rapidez"
    asyncio.run(director.produce_campaign(tema, "Otto Pinturas", "otto_predios_01"))

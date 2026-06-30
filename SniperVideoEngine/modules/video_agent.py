import os
import json
import asyncio
from .comfy_agent import ComfyAgent

class VideoAgent:
    def __init__(self):
        self.project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.temp_dir = os.path.join(self.project_dir, "temp")
        self.outputs_dir = os.path.join(self.project_dir, "outputs")
        self.comfy = ComfyAgent()
        os.makedirs(self.temp_dir, exist_ok=True)
        os.makedirs(self.outputs_dir, exist_ok=True)

    async def generate_clips(self, visual_prompts, project_name):
        """
        Gera vídeos reais utilizando o ComfyUI.
        """
        print(f"[VideoAgent] Iniciando geração real para: {project_name}")
        
        # 1. Tentar carregar um workflow base (assets/workflows/video_gen.json)
        workflow_path = os.path.join(self.project_dir, "assets", "workflows", "video_gen.json")
        
        if not os.path.exists(workflow_path):
            print("[VideoAgent] ⚠️ Workflow 'video_gen.json' não encontrado. Abortando geração real.")
            return None

        with open(workflow_path, 'r', encoding='utf-8') as f:
            workflow_json = f.read()

        generated_files = []
        for i, prompt in enumerate(visual_prompts):
            print(f"[VideoAgent] Gerando Cena {i+1}/{len(visual_prompts)}...")
            
            # Mapeamento genérico de nodes (ajustar conforme o workflow real)
            # Geralmente node "6" ou "7" é o CLIP Text Encode no workflow da HKUDS
            mapping = {"6": prompt, "7": f"{prompt}, high quality, cinematic"}
            
            try:
                # Executa a geração no ComfyUI
                files = self.comfy.generate_video(workflow_json, mapping)
                if files:
                    generated_files.extend(files)
            except Exception as e:
                print(f"[VideoAgent] ❌ Erro ao gerar cena {i+1}: {e}")

        return generated_files

    def prepare_generation_job(self, visual_prompts, project_name):
        # Mantido para compatibilidade/backup
        job_file = os.path.join(self.temp_dir, f"job_{project_name}.json")
        job_data = {"project": project_name, "prompts": visual_prompts}
        with open(job_file, 'w', encoding='utf-8') as f:
            json.dump(job_data, f, indent=4, ensure_ascii=False)
        return job_file

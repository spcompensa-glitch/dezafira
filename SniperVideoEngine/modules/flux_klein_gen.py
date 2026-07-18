"""
FLUX.2 Klein 4B — Gerador de Imagens Oficial da Dezafira
=========================================================
Engine: OpenRouter API (black-forest-labs/flux.2-klein-4b)
Custo: ~$0.015/img (1920x1080)
Upscale: Pillow LANCZOS quando necessário
"""
import os, json, base64, time
from pathlib import Path
from typing import Optional, List, Dict
from dotenv import load_dotenv
import requests
from PIL import Image

load_dotenv()

API_KEY = os.getenv("OPENROUTER_API_KEY")
API_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "black-forest-labs/flux.2-klein-4b"


class FluxKleinClient:
    """Cliente para gerar imagens via FLUX.2 Klein 4B (OpenRouter)."""

    def __init__(self):
        if not API_KEY:
            raise RuntimeError("OPENROUTER_API_KEY não configurada no .env")
        print(f"[FluxKlein] Cliente inicializado (modelo: {MODEL})")

    def generate(self, prompt: str, output_path: str,
                 width: int = 1920, height: int = 1080,
                 seed: Optional[int] = None) -> Optional[str]:
        """Gera uma imagem com FLUX.2 Klein 4B.

        Args:
            prompt: Descrição da imagem
            output_path: Caminho para salvar
            width, height: Resolução alvo (FLUX gera 1024x768, faz upscale)
            seed: Seed para reprodutibilidade

        Returns:
            Caminho da imagem ou None
        """
        try:
            os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

            body = {
                "model": MODEL,
                "messages": [
                    {"role": "user", "content": [
                        {"type": "text", "text": f"Generate a high quality image: {prompt}"}
                    ]}
                ],
                "modalities": ["image"],
            }
            if seed is not None:
                body["seed"] = seed

            headers = {
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json",
            }

            print(f"[FluxKlein] Gerando: {prompt[:80]}...")
            resp = requests.post(API_URL, headers=headers, json=body, timeout=120)

            if resp.status_code != 200:
                print(f"[FluxKlein] Erro HTTP {resp.status_code}: {resp.text[:200]}")
                return None

            data = resp.json()
            images = (data.get("choices", [{}])[0]
                      .get("message", {})
                      .get("images", []))

            if not images:
                print(f"[FluxKlein] Resposta sem imagens: {json.dumps(data, indent=2)[:300]}")
                return None

            url = images[0].get("image_url", {}).get("url", "")
            if not url or not url.startswith("data:image"):
                print(f"[FluxKlein] Formato inesperado: {str(images[0])[:200]}")
                return None

            b64 = url.split(",", 1)[1]
            img_data = base64.b64decode(b64)

            # Salvar imagem original
            with open(output_path, "wb") as f:
                f.write(img_data)

            # Upscale se necessário
            actual = Image.open(output_path)
            if actual.width < width or actual.height < height:
                actual = actual.resize((width, height), Image.LANCZOS)
                actual.save(output_path, quality=95)
                print(f"[FluxKlein] Upscale: {actual.size[0]}x{actual.size[1]}")

            size_kb = os.path.getsize(output_path) / 1024
            print(f"[FluxKlein] OK: {output_path} ({size_kb:.0f}KB)")
            return output_path

        except Exception as e:
            print(f"[FluxKlein] Erro: {e}")
            return None

    def generate_scene_images(self, scenes: List[Dict], output_dir: str,
                               width: int = 1920, height: int = 1080,
                               channel_seed: int = 42) -> List[str]:
        """Gera imagens para múltiplas cenas.

        Args:
            scenes: Lista de cenas com 'full_prompt' ou 'pollinations_prompt'
            output_dir: Diretório de saída
            width, height: Resolução
            channel_seed: Seed base para consistência visual

        Returns:
            Lista de caminhos das imagens geradas
        """
        paths = []
        os.makedirs(output_dir, exist_ok=True)

        for i, scene in enumerate(scenes):
            prompt = (scene.get("pollinations_prompt")
                      or scene.get("full_prompt")
                      or scene.get("visual_prompt", ""))
            if not prompt:
                continue

            sid = scene.get("scene_id", i + 1)
            output_path = os.path.join(output_dir, f"scene_{sid}.png")
            seed = channel_seed + i

            result = self.generate(prompt, output_path,
                                    width=width, height=height,
                                    seed=seed)
            if result:
                paths.append(result)

        return paths


if __name__ == "__main__":
    client = FluxKleinClient()
    img = client.generate(
        prompt="Linda paisagem natural com um cavalo galopando, montanhas ao fundo, luz do amanhecer",
        output_path="../outputs/test_flux/test.jpg",
        width=1920, height=1080,
    )
    if img:
        print(f"Teste OK: {img}")
    else:
        print("Teste FALHOU")

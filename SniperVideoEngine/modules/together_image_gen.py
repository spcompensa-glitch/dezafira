"""
Dezafira Image Generator v2 — Together AI (Juggernaut Lightning Flux)
Custo: ~$0.0017/imagem (23x mais barato que Gemini)
"""
import base64
import hashlib
import json
import os
import time
import httpx

TOGETHER_API_URL = "https://api.together.xyz/v1/images/generations"
DEFAULT_MODEL = "black-forest-labs/FLUX.1-schnell"

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "outputs", "ai_images")


class TogetherImageGen:
    """Gera imagens via Together AI (FLUX Schnell — mais barato do mercado)."""

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("TOGETHER_API_KEY", "").strip()
        self.generated: list = []
        self.total_cost = 0.0
        os.makedirs(OUTPUT_DIR, exist_ok=True)

    async def generate(self, prompt: str, scene_id: int = None,
                       width: int = 1080, height: int = 1920,
                       steps: int = 4) -> dict:
        """
        Gera uma imagem via Together AI FLUX Schnell.

        Args:
            prompt: Prompt completo da imagem
            scene_id: ID da cena
            width, height: Dimensões (9:16 vertical = 1080x1920)
            steps: Passos de inferência (1-4, menos = mais rápido)

        Returns:
            dict com {path, scene_id, prompt, size_bytes}
        """
        if not self.api_key:
            raise ValueError("TOGETHER_API_KEY não configurada")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": DEFAULT_MODEL,
            "prompt": prompt,
            "width": width,
            "height": height,
            "steps": steps,
            "n": 1,
            "response_format": "b64_json",
        }

        async with httpx.AsyncClient(timeout=90.0) as client:
            for attempt in range(3):
                try:
                    resp = await client.post(TOGETHER_API_URL, headers=headers, json=payload)

                    if resp.status_code == 200:
                        data = resp.json()
                        return self._save_image(data, prompt, scene_id)

                    if resp.status_code == 429:
                        wait = min((attempt + 1) * 5, 20)
                        time.sleep(wait)
                        continue

                    error = resp.text[:300]
                    print(f"[Together] Erro {resp.status_code} cena {scene_id}: {error}")
                    if attempt < 2:
                        time.sleep(3)

                except httpx.RequestError as e:
                    print(f"[Together] Conexão falhou cena {scene_id}: {e}")
                    if attempt < 2:
                        time.sleep(3)

        raise RuntimeError(f"Falha ao gerar imagem para cena {scene_id}")

    def _save_image(self, data: dict, prompt: str, scene_id: int) -> dict:
        """Decodifica base64 e salva PNG."""
        images = data.get("data", [])
        if not images:
            raise RuntimeError(f"Sem imagens na resposta para cena {scene_id}")

        b64_data = images[0].get("b64_json", "")
        if not b64_data:
            raise RuntimeError(f"Sem b64_json na resposta para cena {scene_id}")

        scene_tag = f"scene_{scene_id:03d}" if scene_id is not None else "image"
        prompt_hash = hashlib.md5(prompt.encode()).hexdigest()[:8]
        filename = f"{scene_tag}_{prompt_hash}.png"
        filepath = os.path.join(OUTPUT_DIR, filename)

        raw = base64.b64decode(b64_data)
        with open(filepath, "wb") as f:
            f.write(raw)

        size_bytes = os.path.getsize(filepath)
        # Custo estimado Together FLUX schnell: ~$0.0017/img
        cost = 0.0017
        self.total_cost += cost

        result = {
            "scene_id": scene_id,
            "path": filepath,
            "filename": filename,
            "prompt": prompt,
            "model": DEFAULT_MODEL,
            "cost": cost,
            "size_bytes": size_bytes,
            "size_kb": round(size_bytes / 1024, 1),
        }
        self.generated.append(result)
        return result

    async def generate_scene_images(self, scenes: list, width: int = 1080,
                                    height: int = 1920, on_progress=None) -> list:
        """Gera imagens para todas as cenas."""
        total = len(scenes)
        results = []
        cost_estimate = total * 0.0017

        print(f"[Together] Gerando {total} imagens via {DEFAULT_MODEL}...")
        print(f"[Together] Custo estimado: ~${cost_estimate:.4f}")

        for i, scene in enumerate(scenes):
            scene_id = scene.get("scene_id", i + 1)
            prompt = scene.get("full_prompt", "")

            if on_progress:
                on_progress(scene_id, total, "generating")

            try:
                result = await self.generate(prompt, scene_id, width, height)
                result.update({
                    "narration": scene.get("narration", ""),
                    "duration_seconds": scene.get("duration_seconds", 5.0),
                    "motion_hint": scene.get("motion_hint", ""),
                })
                results.append(result)

                if on_progress:
                    on_progress(scene_id, total, "done")

                print(f"[Together] Cena {scene_id}/{total} OK | "
                      f"{result['size_kb']}KB | ${result['cost']:.4f}")

                if i < total - 1:
                    time.sleep(0.3)

            except Exception as e:
                print(f"[Together] FALHA cena {scene_id}: {e}")
                results.append({
                    "scene_id": scene_id,
                    "path": None,
                    "error": str(e),
                    "narration": scene.get("narration", ""),
                    "duration_seconds": scene.get("duration_seconds", 5.0),
                })

        ok = sum(1 for r in results if r.get("path"))
        print(f"[Together] {ok}/{total} | Custo: ${self.total_cost:.4f}")
        return results

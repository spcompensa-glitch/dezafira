"""
Dezafira Image Generator — Gera imagens via OpenRouter (Gemini) a partir de prompts estruturados.

Provider chain: OpenRouter/Gemini → arquivo PNG local
"""
import base64
import hashlib
import json
import os
import re
import time
import httpx

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURAÇÃO
# ═══════════════════════════════════════════════════════════════════════════════

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
IMAGE_MODEL = "google/gemini-2.5-flash-image"      # ~$0.04/img
FALLBACK_MODEL = "google/gemini-3.1-flash-image"     # fallback (~$0.04/img)

DEFAULT_OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "outputs", "ai_images")


class ImageGenerator:
    """
    Gera imagens via OpenRouter/Gemini a partir de prompts cinematográficos.
    """

    def __init__(self, api_key: str = None, output_dir: str = None):
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY", "").strip()
        self.output_dir = output_dir or DEFAULT_OUTPUT_DIR
        self.generated_images: list = []
        self.total_cost: float = 0.0
        os.makedirs(self.output_dir, exist_ok=True)

    # ─── Geração de uma única imagem ────────────────────────────────────

    async def generate_image(self, prompt: str, scene_id: int = None,
                             model: str = IMAGE_MODEL,
                             aspect_ratio: str = "16:9") -> dict:
        """
        Gera uma imagem a partir de um prompt cinematográfico.

        Args:
            prompt: Prompt completo da imagem (inglês)
            scene_id: ID da cena (para nome do arquivo)
            model: Modelo OpenRouter a usar
            aspect_ratio: "16:9" | "9:16" | "1:1"

        Returns:
            dict: {path, scene_id, prompt, model, cost, size_bytes}
        """
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY não configurada. Adicione créditos em openrouter.ai")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": (
                        f"Generate a high-quality image based on this detailed description. "
                        f"The image must be {aspect_ratio} aspect ratio. "
                        f"Do NOT add any text, letters, watermarks, or typography to the image. "
                        f"Here is the detailed prompt:\n\n{prompt}"
                    )
                }
            ],
            "modalities": ["image", "text"],
            "max_tokens": 4096,
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            for attempt in range(3):
                try:
                    response = await client.post(OPENROUTER_URL, headers=headers, json=payload)
                    if response.status_code == 200:
                        return self._process_response(response.json(), prompt, scene_id, model)
                    elif response.status_code == 402:
                        raise ValueError(
                            "Sem créditos no OpenRouter. Adicione em: https://openrouter.ai/settings/credits"
                        )
                    elif response.status_code == 429:
                        wait = min((attempt + 1) * 5, 30)
                        print(f"[ImageGen] Rate limit cena {scene_id}, aguardando {wait}s...")
                        time.sleep(wait)
                    else:
                        error_body = response.text[:300]
                        print(f"[ImageGen] Erro {response.status_code} cena {scene_id}: {error_body}")
                        if attempt < 2:
                            time.sleep(3)
                except httpx.RequestError as e:
                    print(f"[ImageGen] Erro conexão cena {scene_id}: {e}")
                    if attempt < 2:
                        time.sleep(3)

        # Fallback: tenta o modelo alternativo
        if model == IMAGE_MODEL:
            print(f"[ImageGen] Fallback para {FALLBACK_MODEL} na cena {scene_id}")
            return await self.generate_image(prompt, scene_id, FALLBACK_MODEL, aspect_ratio)

        raise RuntimeError(f"Falha ao gerar imagem para cena {scene_id} após 3 tentativas")

    # ─── Processamento da resposta ──────────────────────────────────────

    def _process_response(self, data: dict, prompt: str, scene_id: int, model: str) -> dict:
        """Extrai imagem base64 da resposta e salva em disco."""
        # Calcula custo
        usage = data.get("usage", {})
        cost = usage.get("cost", 0.0)
        self.total_cost += cost

        # Extrai imagem
        choices = data.get("choices", [])
        if not choices:
            raise RuntimeError(f"Resposta sem choices para cena {scene_id}")

        message = choices[0].get("message", {})
        images = message.get("images", [])

        if not images:
            # Pode ser uma resposta de texto (modelo não gerou imagem)
            text_response = message.get("content", "")
            print(f"[ImageGen] Cena {scene_id}: modelo retornou texto, não imagem: {text_response[:200]}")
            raise RuntimeError(f"Modelo não gerou imagem para cena {scene_id}")

        # Pega a primeira imagem
        image_data = images[0]
        image_url = image_data.get("image_url", {}).get("url", "")
        image_b64 = image_data.get("image", "")

        # Salva em disco
        scene_tag = f"scene_{scene_id:03d}" if scene_id is not None else "image"
        prompt_hash = hashlib.md5(prompt.encode()).hexdigest()[:8]
        filename = f"{scene_tag}_{prompt_hash}.png"
        filepath = os.path.join(self.output_dir, filename)

        if image_b64:
            # Decodifica base64 direto
            raw = base64.b64decode(image_b64)
            with open(filepath, "wb") as f:
                f.write(raw)
        elif image_url:
            if image_url.startswith("data:"):
                # Data URL: data:image/png;base64,XXXX
                b64_part = image_url.split(",", 1)[1] if "," in image_url else image_url
                raw = base64.b64decode(b64_part)
                with open(filepath, "wb") as f:
                    f.write(raw)
            else:
                # URL de imagem (Google Cloud Storage signed URL)
                import requests as sync_requests
                r = sync_requests.get(image_url, timeout=60)
                r.raise_for_status()
                with open(filepath, "wb") as f:
                    f.write(r.content)
        else:
            raise RuntimeError(f"Sem dados de imagem na resposta para cena {scene_id}")

        size_bytes = os.path.getsize(filepath)

        result = {
            "scene_id": scene_id,
            "path": filepath,
            "filename": filename,
            "prompt": prompt,
            "model": model,
            "cost": cost,
            "size_bytes": size_bytes,
            "size_kb": round(size_bytes / 1024, 1),
        }
        self.generated_images.append(result)
        return result

    # ─── Geração em lote ────────────────────────────────────────────────

    async def generate_scene_images(self, scenes: list, aspect_ratio: str = "16:9",
                                    on_progress=None) -> list:
        """
        Gera imagens para todas as cenas de um plano de vídeo.

        Args:
            scenes: Lista de dicts com scene_id, full_prompt, etc.
            aspect_ratio: "16:9" | "9:16"
            on_progress: Callback(scene_id, total, status) para progresso

        Returns:
            List[dict]: Imagens geradas com metadados
        """
        total = len(scenes)
        results = []

        print(f"[ImageGen] Gerando {total} imagens via {IMAGE_MODEL}...")
        print(f"[ImageGen] Custo estimado: ~${total * 0.0000003:.8f}")

        for i, scene in enumerate(scenes):
            scene_id = scene.get("scene_id", i + 1)
            prompt = scene.get("full_prompt", "")

            if on_progress:
                on_progress(scene_id, total, "generating")

            try:
                result = await self.generate_image(prompt, scene_id, IMAGE_MODEL, aspect_ratio)
                result["narration"] = scene.get("narration", "")
                result["duration_seconds"] = scene.get("duration_seconds", 5.0)
                result["motion_hint"] = scene.get("motion_hint", "")
                results.append(result)

                if on_progress:
                    on_progress(scene_id, total, "done")

                print(f"[ImageGen] Cena {scene_id}/{total} OK | {result['size_kb']}KB | "
                      f"${result['cost']:.8f}")

                # Pequeno delay entre chamadas pra evitar rate limit
                if i < total - 1:
                    await httpx.AsyncClient().aclose()
                    time.sleep(0.5)

            except Exception as e:
                print(f"[ImageGen] FALHA cena {scene_id}/{total}: {e}")
                results.append({
                    "scene_id": scene_id,
                    "path": None,
                    "error": str(e),
                    "narration": scene.get("narration", ""),
                    "duration_seconds": scene.get("duration_seconds", 5.0),
                })

        success = sum(1 for r in results if r.get("path"))
        print(f"[ImageGen] Concluído: {success}/{total} imagens | Custo total: ${self.total_cost:.8f}")
        return results

    # ─── Utilitários ────────────────────────────────────────────────────

    @staticmethod
    def get_prompt_preview(prompt: str, max_len: int = 120) -> str:
        """Retorna preview curto do prompt."""
        return prompt[:max_len] + "..." if len(prompt) > max_len else prompt

    def clear_output_dir(self):
        """Remove todas as imagens geradas anteriormente."""
        for f in os.listdir(self.output_dir):
            fp = os.path.join(self.output_dir, f)
            if os.path.isfile(fp) and f.endswith(('.png', '.jpg', '.webp')):
                os.remove(fp)
        self.generated_images = []
        self.total_cost = 0.0

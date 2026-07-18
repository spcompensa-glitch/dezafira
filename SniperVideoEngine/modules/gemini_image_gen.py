"""
GeminiImageGen — Geração de imagens via Google Gemini API (Nano Banana).

Substitui o Google Flow (que esgota com 10 imagens).
Gemini 2.5 Flash Image: ~$0.039/img, free tier generoso, alta qualidade.

Cadeia: Gemini API → Pollinations (backup grátis)
"""
import asyncio
import base64
import hashlib
import json
import os
import time
import httpx
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
IMAGES_DIR = BASE_DIR / "outputs" / "ai_images"
IMAGES_DIR.mkdir(parents=True, exist_ok=True)

# Gemini 2.5 Flash Image via Google AI Studio
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-image-generation:generateContent"
GEMINI_MODEL = "gemini-2.5-flash-preview-image-generation"


class GeminiImageGen:
    """Gera imagens via Gemini API direto (Nano Banana)."""

    def __init__(self, api_key: str = None, output_dir: str = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "").strip()
        self.output_dir = str(output_dir or IMAGES_DIR)
        self.total_cost = 0.0
        os.makedirs(self.output_dir, exist_ok=True)

    async def generate_image(self, prompt: str, scene_id: int = None,
                              width: int = 1080, height: int = 1920) -> dict:
        """Gera uma imagem via Gemini API."""
        if not self.api_key:
            raise RuntimeError("GEMINI_API_KEY não configurada")

        url = f"{GEMINI_API_URL}?key={self.api_key}"
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [{
                "parts": [{
                    "text": (
                        f"Generate a high-quality {width}x{height} image. "
                        f"Do NOT add any text, letters, watermarks, or typography. "
                        f"Prompt: {prompt}"
                    )
                }]
            }],
            "generationConfig": {
                "responseModalities": ["TEXT", "IMAGE"],
                "responseMimeType": "text/plain",
            }
        }

        async with httpx.AsyncClient(timeout=120) as client:
            for attempt in range(3):
                try:
                    r = await client.post(url, json=payload, headers=headers)
                    if r.status_code == 200:
                        return self._process_response(r.json(), prompt, scene_id)
                    elif r.status_code == 429:
                        wait = min((attempt + 1) * 10, 60)
                        print(f"[Gemini] Rate limit, aguardando {wait}s...")
                        time.sleep(wait)
                    else:
                        print(f"[Gemini] Erro {r.status_code}: {r.text[:200]}")
                        if attempt < 2:
                            time.sleep(3)
                except Exception as e:
                    print(f"[Gemini] Erro conexao: {e}")
                    if attempt < 2:
                        time.sleep(3)

        raise RuntimeError(f"Gemini falhou para cena {scene_id} apos 3 tentativas")

    def _process_response(self, data: dict, prompt: str, scene_id: int) -> dict:
        """Extrai imagem da resposta Gemini."""
        candidates = data.get("candidates", [])
        if not candidates:
            raise RuntimeError(f"Resposta sem candidates para cena {scene_id}")

        parts = candidates[0].get("content", {}).get("parts", [])
        image_b64 = None
        for part in parts:
            if "inlineData" in part:
                image_b64 = part["inlineData"].get("data", "")
                break

        if not image_b64:
            raise RuntimeError(f"Sem imagem na resposta para cena {scene_id}")

        # Salva
        scene_tag = f"scene_{scene_id:03d}" if scene_id else "image"
        prompt_hash = hashlib.md5(prompt.encode()).hexdigest()[:8]
        filename = f"{scene_tag}_{prompt_hash}.png"
        filepath = os.path.join(self.output_dir, filename)

        raw = base64.b64decode(image_b64)
        with open(filepath, "wb") as f:
            f.write(raw)

        size_bytes = len(raw)
        cost = 0.039  # custo estimado por imagem
        self.total_cost += cost

        return {
            "scene_id": scene_id,
            "path": filepath,
            "filename": filename,
            "prompt": prompt,
            "model": "gemini-2.5-flash",
            "cost": cost,
            "size_bytes": size_bytes,
            "size_kb": round(size_bytes / 1024, 1),
        }

    async def generate_scene_images(self, scenes: list,
                                     on_progress=None) -> list:
        """Gera imagens para todas as cenas."""
        total = len(scenes)
        results = []

        print(f"[Gemini] Gerando {total} imagens via Gemini 2.5 Flash Image...")
        print(f"[Gemini] Custo estimado: ~${total * 0.039:.2f}")

        for i, scene in enumerate(scenes):
            scene_id = scene.get("scene_id", i + 1)
            prompt = scene.get("full_prompt", "")

            if on_progress:
                on_progress(scene_id, total, "generating-gemini")

            try:
                result = await self.generate_image(prompt, scene_id)
                result["narration"] = scene.get("narration", "")
                result["duration_seconds"] = scene.get("duration_seconds", 5.0)
                results.append(result)

                if on_progress:
                    on_progress(scene_id, total, "done")

                print(f"[Gemini] Cena {scene_id}/{total} OK | "
                      f"{result['size_kb']}KB | ${result['cost']:.3f}")

                if i < total - 1:
                    time.sleep(0.5)

            except Exception as e:
                print(f"[Gemini] FALHA cena {scene_id}: {e}")
                results.append({
                    "scene_id": scene_id, "path": None,
                    "error": str(e),
                    "narration": scene.get("narration", ""),
                    "duration_seconds": scene.get("duration_seconds", 5.0),
                })

        ok = sum(1 for r in results if r.get("path"))
        print(f"[Gemini] {ok}/{total} imagens | Custo: ${self.total_cost:.2f}")
        return results

"""
Pollinations.ai Client — Geração de Imagens IA 100% Gratuita (v2)
=================================================================
Sem chave de API, sem cadastro.
Endpoint: GET https://image.pollinations.ai/prompt/{descricao}

v2.0 — Qualidade Cinema:
- Prompts brand-aware por nicho
- Seed fixa por canal (consistência visual)
- Quality boosters automáticos
- Geração multi-variante + seleção
- Upscale via Real-ESRGAN (CPU)
"""

import os
import hashlib
import requests
from typing import Optional, List, Dict


class PollinationsClient:
    """Cliente para gerar imagens via Pollinations.ai (SDXL gratuito) v2."""

    def __init__(self):
        self.base_url = "https://image.pollinations.ai/prompt"
        print("[Pollinations] Cliente v2 inicializado (100% gratuito)")

    # ─── Prompts por nicho ──────────────────────────────────────────────────

    NICHE_STYLES = {
        "tech": {
            "prefix": "futuristic tech aesthetic, holographic interface, neon cyan/magenta rim lighting",
            "suffix": "volumetric fog, 8k, sharp focus, cinematic composition, digital art",
            "colors": ["#00e5ff", "#ff00ff", "#0d0d0d"],
        },
        "finance": {
            "prefix": "clean corporate luxury, gold and white palette, subtle particle effects",
            "suffix": "professional lighting, high-end photography, 8k, wealth visualization",
            "colors": ["#FFD700", "#ffffff", "#1a1a1a"],
        },
        "curiosity": {
            "prefix": "mysterious cinematic atmosphere, dramatic chiaroscuro lighting",
            "suffix": "film grain, depth of field, 8k, storytelling composition, intrigue",
            "colors": ["#ff6b35", "#004e89", "#0a0a0a"],
        },
        "health": {
            "prefix": "clean medical aesthetic, soft natural lighting, wellness vibe",
            "suffix": "fresh colors, 8k, professional health photography, calm atmosphere",
            "colors": ["#00c9a7", "#ffffff", "#f0f0f0"],
        },
        "education": {
            "prefix": "modern educational aesthetic, clean design, information visualization",
            "suffix": "bright engaging colors, 8k, professional, knowledge presentation",
            "colors": ["#4361ee", "#ffffff", "#f8f9fa"],
        },
        "entertainment": {
            "prefix": "vibrant entertainment aesthetic, bold colors, dynamic composition",
            "suffix": "dramatic lighting, 8k, high energy, cinematic color grading",
            "colors": ["#e63946", "#f1faee", "#1d3557"],
        },
    }

    QUALITY_BOOSTERS = (
        "masterpiece, best quality, highly detailed, "
        "cinematic lighting, sharp focus, 8k resolution, "
        "professional photography, dramatic composition"
    )

    NEGATIVE_PROMPTS = (
        "blurry, low quality, distorted, deformed, "
        "watermark, text, logo, signature, "
        "ugly, bad anatomy, bad proportions, "
        "oversaturated, underexposed, overexposed"
    )

    def generate(
        self,
        prompt: str,
        output_path: str,
        width: int = 1080,
        height: int = 1920,
        seed: Optional[int] = None,
        niche: str = "curiosity",
        channel_seed: Optional[int] = None,
        num_variants: int = 1,
    ) -> Optional[str]:
        """
        Gera imagem com qualidade cinematográfica.

        Args:
            prompt: Descrição da cena
            output_path: Caminho para salvar
            width: Largura (default 1080 vertical)
            height: Altura (default 1920 vertical)
            seed: Seed específica (override)
            niche: Nicho do canal (para estilo)
            channel_seed: Seed fixa do canal (consistência)
            num_variants: Número de variantes para gerar (pick best)

        Returns:
            Caminho da melhor imagem ou None
        """
        try:
            # Seed: prioridade channel_seed > seed > auto
            final_seed = channel_seed if channel_seed is not None else seed

            # Montar prompt estilizado
            styled_prompt = self._style_prompt(prompt, niche)

            params = {"width": width, "height": height}
            if final_seed is not None:
                params["seed"] = final_seed

            url = f"{self.base_url}/{styled_prompt}"
            print(f"[Pollinations] Gerando: {styled_prompt[:80]}...")

            best_path = None
            best_size = 0

            for variant in range(num_variants):
                # Variação de seed para variantes
                variant_params = params.copy()
                if final_seed is not None:
                    variant_params["seed"] = final_seed + variant

                resp = requests.get(url, params=variant_params, timeout=90)

                if resp.status_code != 200:
                    print(f"[Pollinations] Erro HTTP {resp.status_code} (variante {variant})")
                    continue

                # Verificar qualidade mínima (>50KB = imagem real, não placeholder)
                size_kb = len(resp.content) / 1024
                if size_kb < 50:
                    print(f"[Pollinations] Imagem muito pequena ({size_kb:.0f}KB), retry...")
                    continue

                # Salvar variante
                if num_variants > 1:
                    variant_path = output_path.replace(".", f"_v{variant}.")
                else:
                    variant_path = output_path

                os.makedirs(os.path.dirname(variant_path) or ".", exist_ok=True)
                with open(variant_path, "wb") as f:
                    f.write(resp.content)

                # Escolher melhor por tamanho (heurística simples)
                if size_kb > best_size:
                    best_size = size_kb
                    best_path = variant_path

                print(f"[Pollinations] Variante {variant}: {size_kb:.0f}KB")

            if best_path:
                print(f"[Pollinations] Melhor: {best_path} ({best_size:.0f}KB)")

                # Upscale se < 1080px
                if width > 0 and height > 0:
                    upscaled = self._upscale_if_needed(best_path, width, height)
                    if upscaled:
                        best_path = upscaled

            return best_path

        except Exception as e:
            print(f"[Pollinations] Erro: {e}")
            return None

    def _style_prompt(self, prompt: str, niche: str) -> str:
        """Aplica estilo do nicho + quality boosters ao prompt."""
        style = self.NICHE_STYLES.get(niche, self.NICHE_STYLES["curiosity"])
        prefix = style["prefix"]
        suffix = style["suffix"]

        # Limpar prompt original de termos de qualidade genéricos
        clean = prompt
        for term in ["cinematic", "high quality", "4k", "8k", "masterpiece"]:
            clean = clean.replace(term, "").replace(", ,", ",").strip(",")

        # Compor prompt final
        parts = [prefix, clean.strip(), suffix, self.QUALITY_BOOSTERS]
        final = ", ".join(p for p in parts if p)
        return final

    def generate_scene_images(
        self,
        scenes: List[Dict],
        output_dir: str,
        width: int = 1080,
        height: int = 1920,
        niche: str = "curiosity",
        channel_seed: int = 42,
    ) -> List[str]:
        """
        Gera imagens para múltiplas cenas com qualidade cinematográfica.

        Args:
            scenes: Lista de cenas do ScenePlanner
            output_dir: Diretório de saída
            width, height: Resolução
            niche: Nicho do canal
            channel_seed: Seed fixa do canal

        Returns:
            Lista de caminhos das imagens geradas
        """
        paths = []
        os.makedirs(output_dir, exist_ok=True)

        for i, scene in enumerate(scenes):
            prompt = scene.get("pollinations_prompt") or scene.get("visual_prompt", "")
            if not prompt:
                continue

            scene_seed = scene.get("seed", channel_seed + i)
            output_path = os.path.join(output_dir, f"scene_{scene.get('scene_id', i)}.jpg")

            result = self.generate(
                prompt=prompt,
                output_path=output_path,
                width=width,
                height=height,
                seed=scene_seed,
                niche=niche,
                channel_seed=scene_seed,
                num_variants=1,
            )
            if result:
                paths.append(result)

        return paths

    def _upscale_if_needed(self, image_path: str, target_w: int, target_h: int) -> Optional[str]:
        """Upscale via Real-ESRGAN se imagem for menor que target."""
        try:
            from PIL import Image
            img = Image.open(image_path)
            w, h = img.size

            # Se já >= target, não fazer nada
            if w >= target_w and h >= target_h:
                return None

            # Tentar Real-ESRGAN
            try:
                from realesrgan import RealESRGANer
                # Configuração CPU
                upsampler = RealESRGANer(
                    scale=4,
                    model_path="https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth",
                    tile=256,
                    tile_pad=10,
                    pre_pad=0,
                    half=False,  # CPU não suporta half
                )
                output, _ = upsampler.enhance(image_path, outscale=4)
                upscaled_path = image_path.replace(".", "_upscaled.")
                from PIL import Image as PILImage
                PILImage.fromarray(output).save(upscaled_path, quality=95)
                print(f"[Pollinations] Upscale: {image_path} → {upscaled_path}")
                return upscaled_path
            except ImportError:
                pass

            # Fallback: Pillow resize com LANCZOS
            resized = img.resize((target_w, target_h), Image.LANCZOS)
            resized_path = image_path.replace(".", "_resized.")
            resized.save(resized_path, quality=95)
            print(f"[Pollinations] Resize: {image_path} → {resized_path}")
            return resized_path

        except Exception as e:
            print(f"[Pollinations] Upscale falhou: {e}")
            return None


if __name__ == "__main__":
    client = PollinationsClient()
    img = client.generate(
        prompt="futuristic AI robot analyzing data streams",
        output_path="../outputs/temp/test_pollinations_v2.jpg",
        width=1080,
        height=1920,
        niche="tech",
        channel_seed=42,
        num_variants=2,
    )
    if img:
        print(f"Teste OK: {img}")
    else:
        print("Teste FALHOU")

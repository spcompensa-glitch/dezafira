import os
import json
import time
import asyncio
from typing import List, Dict, Any, Optional


class BatchGenerator:
    """
    Gera N variacoes do mesmo tema.
    Cada variacao: script diferente -> TTS -> stock footage -> video render.
    """

    def __init__(self, brain=None, planner=None):
        self.brain = brain
        self.planner = planner

    async def generate_variants(
        self,
        theme: str,
        count: int = 3,
        video_format: str = "vertical",
        voice: str = "pf_dora",
        output_dir: str = "outputs",
    ) -> List[Dict[str, Any]]:
        """
        Gera N variacoes de video para o mesmo tema.

        Args:
            theme: Tema base
            count: Numero de variacoes
            video_format: 'vertical' ou 'horizontal'
            voice: Voz TTS
            output_dir: Diretorio de saida

        Returns:
            Lista de resultados: [{"variant": N, "path": "...", "success": bool, ...}]
        """
        results = []
        print(f"\n{'='*60}")
        print(f"BATCH GENERATOR: {count} variacoes para '{theme}'")
        print(f"{'='*60}")

        for i in range(count):
            variant_label = f"{theme} (Variant {i+1})"
            print(f"\n--- Variante {i+1}/{count} ---")

            try:
                result = await self._generate_single(
                    theme=variant_label,
                    variant_id=i + 1,
                    video_format=video_format,
                    voice=voice,
                    output_dir=output_dir,
                )
                results.append(result)
            except Exception as e:
                print(f"[Batch] Erro na variante {i+1}: {e}")
                results.append({"variant": i + 1, "success": False, "error": str(e)})

        return results

    async def _generate_single(
        self,
        theme: str,
        variant_id: int,
        video_format: str,
        voice: str,
        output_dir: str,
    ) -> Dict[str, Any]:
        from services.open_montage_bridge import produce_video

        task_id = int(time.time() * 1000) % 100000 + variant_id

        result = await produce_video(
            task_id=task_id,
            prompt=theme,
            script_text="",
            visual_keywords=[],
            voice_path="",
            channel_id="batch",
            provider="nvidia",
            video_format=video_format,
        )

        return {
            "variant": variant_id,
            "theme": theme,
            "success": result.get("success", False),
            "output_path": result.get("output_path"),
            "error": result.get("error"),
        }

    @staticmethod
    def print_summary(results: List[Dict[str, Any]]):
        print(f"\n{'='*60}")
        print(f"BATCH SUMMARY")
        print(f"{'='*60}")
        success = [r for r in results if r.get("success")]
        failed = [r for r in results if not r.get("success")]
        print(f"Total: {len(results)} | Sucesso: {len(success)} | Falha: {len(failed)}")
        for r in success:
            print(f"  [OK] Variante {r['variant']}: {r.get('output_path')}")
        for r in failed:
            print(f"  [X] Variante {r['variant']}: {r.get('error', 'Erro desconhecido')}")

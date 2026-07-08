"""
Hybrid Media Assembler — Combina clips PEXELS + imagens AI_IMAGE
===============================================================
Mantém a ordem cronológica correta das cenas no timeline.
"""

from typing import List, Dict, Any


class HybridMediaAssembler:
    """Monta a lista de mídia combinando Pexels + Pollinations na ordem das cenas."""

    @staticmethod
    def assemble(
        scenes: List[Dict[str, Any]],
        pexels_clips: List[str],
        ai_images: List[str],
        video_format: str = "vertical",
    ) -> List[Dict[str, Any]]:
        """
        Combina clips Pexels e imagens AI na ordem cronológica das cenas.

        Args:
            scenes: Lista de cenas do ScenePlanner (com type, visual_prompt, etc.)
            pexels_clips: Lista de caminhos de vídeos do Pexels
            ai_images: Lista de caminhos de imagens geradas por IA

        Returns:
            Lista de media_payload ordenada: [{"path": "...", "duration": N}, ...]
        """
        media_payload = []
        pexels_idx = 0
        ai_idx = 0

        for scene in scenes:
            scene_type = scene.get("type", "PEXELS")
            duration = scene.get("duration", 5.0)

            if scene_type == "PEXELS" and pexels_idx < len(pexels_clips):
                # Usar clip do Pexels
                media_payload.append({
                    "path": pexels_clips[pexels_idx],
                    "duration": duration,
                    "type": "video",
                })
                pexels_idx += 1
            elif scene_type == "AI_IMAGE" and ai_idx < len(ai_images):
                # Usar imagem gerada por IA
                media_payload.append({
                    "path": ai_images[ai_idx],
                    "duration": duration,
                    "type": "image",
                })
                ai_idx += 1
            else:
                # Fallback: usar o que tiver disponível
                if pexels_idx < len(pexels_clips):
                    media_payload.append({
                        "path": pexels_clips[pexels_idx],
                        "duration": duration,
                        "type": "video",
                    })
                    pexels_idx += 1
                elif ai_idx < len(ai_images):
                    media_payload.append({
                        "path": ai_images[ai_idx],
                        "duration": duration,
                        "type": "image",
                    })
                    ai_idx += 1
                else:
                    # Sem mídia disponível para esta cena
                    media_payload.append({
                        "path": "",
                        "duration": duration,
                        "type": "empty",
                    })

        return media_payload

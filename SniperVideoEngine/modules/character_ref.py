"""
Character Reference Frame — Gera imagem de referência do personagem.

A imagem de referência é usada como base/seed para manter consistência
visual do personagem em todas as cenas do vídeo.
"""
import os
from pathlib import Path
from modules.prompt_engine import get_character_reference_prompt


def generate_character_reference(style_id: str = None,
                                  style_custom: str = "",
                                  character: str = "",
                                  video_format: str = "vertical",
                                  output_dir: str = None) -> str:
    """
    Gera o prompt para o character reference frame.

    Args:
        style_id: Preset visual (ver modules/styles)
        style_custom: Descrição customizada do estilo
        character: Descrição do personagem
        video_format: 'vertical' ou 'horizontal'
        output_dir: Diretório para salvar (não salva aqui, só gera prompt)

    Returns:
        Prompt string para gerar a imagem de referência
    """
    prompt = get_character_reference_prompt(
        style_id=style_id,
        style_custom=style_custom,
        character=character,
        video_format=video_format,
    )

    print(f"[CharRef] Prompt gerado para character reference:")
    print(f"  {prompt[:120]}...")

    return prompt


def get_reference_seed(channel_seed: int = 42) -> int:
    """
    Retorna um seed determinístico para o character reference frame.
    O mesmo seed + mesmo prompt = mesma aparência do personagem.
    """
    return channel_seed


# Mapeamento de prompts de personagem por estilo
CHARACTER_PRESETS = {
    "boneco_palito": (
        "single stick figure character standing in neutral pose, "
        "large circular head, dot eyes, expressive thick brow lines, "
        "simple body with thick black outlines, facing forward, "
        "flat white background"
    ),
    "minimalista": (
        "minimalist geometric character, simple shapes, "
        "clean lines, limited color palette, centered, "
        "flat white background"
    ),
    "anime": (
        "anime-style character, clean line art, expressive eyes, "
        "centered pose, cel shading, flat white background"
    ),
    "storybook_cinematografico": (
        "storybook illustration character, painterly style, "
        "warm lighting, soft colors, centered, "
        "textured paper background"
    ),
    "3d_pixar": (
        "3D rendered character, Pixar style, rounded features, "
        "soft lighting, centered pose, "
        "clean studio background"
    ),
    "realista_cinematografico": (
        "photorealistic person, cinematic lighting, "
        "centered portrait, shallow depth of field, "
        "neutral background"
    ),
    "aquarela": (
        "watercolor painted character, bleeding edges, "
        "soft organic colors, centered, "
        "textured paper background"
    ),
}


def get_character_description(style_id: str = "boneco_palito",
                              custom_description: str = "") -> str:
    """
    Retorna a descrição do personagem para um estilo específico.
    Usada pelo PromptEngine para manter consistência entre cenas.
    """
    if custom_description:
        return custom_description
    return CHARACTER_PRESETS.get(style_id, CHARACTER_PRESETS["boneco_palito"])

"""
Dezafira Visual Styles — Presets visuais do ELTON VIDEO MAKER + sistema de
consistency locks para manter um canal COERENTE e MONETIZÁVEL.

Cada estilo define um MASTER (descritores aplicados a TODAS as cenas) e se
permite texto na tela. O builder de locks injeta STYLE_LOCK / CHARACTER_LOCK /
WORLD_LOCK / COMPOSITION_LOCK / NEGATIVE_LOCK no prompt de cada cena, garantindo
o mesmo personagem, universo e enquadramento do início ao fim.
"""

VISUAL_STYLES = {
    "boneco_palito": {
        "nome": "Boneco palito (doodle)",
        "permite_texto": True,
        "master": (
            "Hand-drawn 2D doodle cartoon animation, flat colors, bold black "
            "marker outlines, slightly imperfect sketchy lines, simple stick "
            "figures with large round heads and dot eyes, flat solid-color "
            "background, no gradients, no shadows, no 3D, no photorealism, "
            "9:16 aspect ratio, educational YouTube explainer doodle style"
        ),
    },
    "storybook_cinematografico": {
        "nome": "Storybook cinematográfico",
        "permite_texto": False,
        "master": (
            "Premium cinematic storybook illustration, painterly cel-shading, "
            "soft warm lighting, dramatic depth, rich cohesive color palette, "
            "subtle paper texture, emotional atmosphere, 9:16 aspect ratio"
        ),
    },
    "3d_pixar": {
        "nome": "3D estilo Pixar",
        "permite_texto": False,
        "master": (
            "Polished 3D animated movie style, soft global illumination, rounded "
            "appealing character design, subsurface skin, cinematic depth of "
            "field, vibrant coherent palette, 9:16 aspect ratio"
        ),
    },
    "realista_cinematografico": {
        "nome": "Realista cinematográfico",
        "permite_texto": False,
        "master": (
            "Photorealistic cinematic still, natural lighting, shallow depth of "
            "field, filmic color grading, realistic textures and materials, "
            "consistent lens and mood, 9:16 aspect ratio"
        ),
    },
    "anime": {
        "nome": "Anime / mangá",
        "permite_texto": False,
        "master": (
            "Modern anime style, clean line art, cel shading, expressive eyes, "
            "vibrant cohesive palette, soft cinematic lighting, detailed "
            "backgrounds, 9:16 aspect ratio"
        ),
    },
    "aquarela": {
        "nome": "Aquarela / pintura",
        "permite_texto": False,
        "master": (
            "Hand-painted watercolor illustration, soft bleeding edges, textured "
            "paper, gentle organic color palette, delicate brush strokes, calm "
            "artistic atmosphere, 9:16 aspect ratio"
        ),
    },
    "minimalista": {
        "nome": "Minimalista (flat)",
        "permite_texto": True,
        "master": (
            "Clean modern flat vector illustration, simple geometric shapes, "
            "limited harmonious color palette, generous negative space, crisp "
            "edges, corporate explainer style, no gradients, 9:16 aspect ratio"
        ),
    },
    "personalizado": {
        "nome": "Personalizado (descreva)",
        "permite_texto": True,
        "master": "",
    },
}

DEFAULT_STYLE = "boneco_palito"


def resolve_style(style_id: str = None, style_custom: str = None,
                  style_hint: str = None) -> tuple:
    """
    Devolve (master_prompt, permite_texto, style_id_resolvido).

    Prioridade: style_id (ou 'personalizado' + style_custom) > style_hint
    (legado, tratado como custom) > default 'boneco_palito'.
    """
    if not style_id or style_id not in VISUAL_STYLES:
        if style_hint and style_hint.strip():
            return style_hint.strip(), True, "personalizado"
        style_id = DEFAULT_STYLE

    st = VISUAL_STYLES[style_id]
    if style_id == "personalizado" and (style_custom or "").strip():
        return style_custom.strip(), True, style_id
    return st["master"], st["permite_texto"], style_id


def negative_lock(permite_texto: bool) -> str:
    """NEGATIVE_LOCK: o que NUNCA deve aparecer na imagem."""
    if permite_texto:
        return ("no logos, no watermark, no gibberish text, no inconsistent "
                "style, no duplicate character, no extra random people, "
                "no split-screen")
    return ("no text, no subtitles, no captions, no logos, no watermark, "
            "no inconsistent style, no duplicate character, no extra random "
            "people, no split-screen")


def build_consistency_locks(master: str, permite_texto: bool,
                            character: str = "", world: str = "") -> dict:
    """
    Monta o bloco de consistency locks usado no system prompt do roteirista.

    Returns: dict com as 5 chaves de lock (texto) para o PromptEngine injetar.
    """
    text_rule = (
        "On-screen text (if any) must be in Brazilian PORTUGUESE, bold ALL CAPS, "
        "short, top of frame."
        if permite_texto else
        "No text inside the image (clean cinematic style)."
    )
    char_lock = character.strip() or (
        "same character OR same central subject/environment from start to end "
        "(same appearance, clothing, proportions, palette)"
    )
    world_lock = world.strip() or (
        "same visual universe (era, place, atmosphere) — never mix styles"
    )
    return {
        "STYLE_LOCK": f"exactly the same visual style in every scene: {master}",
        "CHARACTER_LOCK": char_lock,
        "WORLD_LOCK": world_lock,
        "COMPOSITION_LOCK": ("one coherent scene per prompt, no split-screen, "
                             "no panels, no duplicated character, clear framing"),
        "NEGATIVE_LOCK": negative_lock(permite_texto),
        "TEXT_RULE": text_rule,
    }


def style_list() -> list:
    """Lista de presets para a UI (endpoint /ai-video/styles)."""
    return [
        {
            "id": sid,
            "nome": st["nome"],
            "permite_texto": st["permite_texto"],
            "master": st["master"],
        }
        for sid, st in VISUAL_STYLES.items()
    ]

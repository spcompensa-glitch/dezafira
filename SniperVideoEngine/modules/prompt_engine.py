"""
PromptEngine v3 — Gera prompts visuais por timestamp com consistência visual.

Diferenças do v2:
- Descrições CONCRETAS de cena (não só palavras da narração)
- Anatomia explícita do boneco (2 braços, 2 pernas, 1 cabeça)
- Negative lock forte (sem membros extras, sem olhos extras)
- Continuidade de cena (mantém mesma cena em timestamps consecutivos)
- Frame types mais inteligentes com mapeamento concreto
"""
import json
import os
import re
from modules.styles import (
    resolve_style,
    build_consistency_locks,
    DEFAULT_STYLE,
)


# ─── Mapeamento de cor por tom narrativo ─────────────────────────────────────

TONE_COLORS = {
    "ancient": "tan background",
    "prehistoric": "tan background",
    "danger": "stark white background with red accents",
    "threat": "stark white background with red accents",
    "happy": "bright white background",
    "triumph": "bright yellow background",
    "discovery": "bright white background",
    "science": "solid blue background",
    "underwater": "solid blue background",
    "nature": "flat green ground with blue sky",
    "evolution": "flat green ground with blue sky",
    "outdoor": "flat green ground with blue sky",
    "fire": "solid orange background",
    "night": "solid orange background",
    "ritual": "solid orange background",
    "mystery": "dark tan background",
    "contemplative": "soft white background",
    "tension": "white background with dark shadows",
    "reveal": "bright golden yellow background",
    "impact": "stark white background",
    "love": "soft pink background",
    "sadness": "light gray background",
    "neutral": "white background",
}

# ─── Anatomia do boneco de palito (SEMPRE incluir) ──────────────────────────

STICK_FIGURE_ANATOMY = (
    "single stick figure character with exactly 2 arms, 2 legs, "
    "1 large circular head, 2 dot eyes, 1 mouth, expressive thick brow lines, "
    "thick black outlines, simple body proportions"
)

STICK_FIGURE_NEGATIVE = (
    "no extra arms, no extra legs, no extra eyes, no extra heads, "
    "no deformed body, no floating limbs, no duplicate character, "
    "no split-screen, no panels"
)

# ─── Mapeamento de narração → descrição concreta de cena ────────────────────

SCENE_ACTION_MAP = {
    # Ações do boneco
    "abraçar": "stick figure hugging another stick figure warmly",
    "abraço": "two stick figures hugging each other",
    "chorar": "stick figure crying with teardrops falling",
    "rir": "stick figure laughing with wide open mouth",
    "pensar": "stick figure with hand on chin, thinking deeply",
    "correr": "stick figure running fast with motion lines",
    "cair": "stick figure falling down with surprised expression",
    "lutar": "stick figure in fighting pose with fists up",
    "abraçar": "stick figure giving a warm hug to another figure",
    "olhar": "stick figure looking at something with curiosity",
    "apontar": "stick figure pointing at an object with finger",
    "perguntar": "stick figure with question mark above head",
    "responder": "stick figure with exclamation mark above head",
    "descobrir": "stick figure with lightbulb moment above head",
    "ensinar": "stick figure pointing at a blackboard",
    "aprender": "stick figure reading a book carefully",
    "trabalhar": "stick figure working at a desk",
    "descansar": "stick figure lying down relaxing",
    "comer": "stick figure eating food",
    "beber": "stick figure drinking from a glass",
    # Objetos comuns
    "coração": "large red heart shape centered in frame",
    "mundo": "Earth globe centered in frame",
    "tempo": "large hourglass or clock centered in frame",
    "cérebro": "large brain illustration centered in frame",
    "olho": "large eye illustration centered in frame",
    "estrela": "large yellow star centered in frame",
    "livro": "large open book centered in frame",
    "casa": "simple house drawing centered in frame",
    "árvore": "simple tree drawing centered in frame",
    "sol": "large yellow sun centered in frame",
    "lua": "large crescent moon centered in frame",
    "nuvem": "large cloud shape centered in frame",
    "seta": "large arrow pointing right",
    "pergunta": "large question mark centered in frame",
    "exclamação": "large exclamation mark centered in frame",
}

# ─── Frame types ──────────────────────────────────────────────────────────────

FRAME_TYPES = {
    "concept_text": (
        "large centered object (hourglass, clock, skull, scroll, heart, brain) "
        "with bold ALL CAPS text at top of frame, flat single-color background"
    ),
    "evolution_sequence": (
        "left-to-right progression of 2-3 stick figures showing transformation "
        "with a right-pointing arrow between them, flat background"
    ),
    "labeled_diagram": (
        "central object with yellow diagonal arrow pointing at it and short "
        "ALL CAPS label word beside the arrowhead, white background"
    ),
    "stick_reaction": (
        "stick figure with thought bubble above head containing '?', 'HMMMM', '!', "
        "or 'WAIT...', expressive thick brow lines, white background"
    ),
    "villain_personified": (
        "abstract concept given an angry cartoon face (clock with fangs, "
        "storm cloud with angry eyes), bold outlines, flat background"
    ),
    "globe_creatures": (
        "Earth globe centered in frame, surrounded by floating cartoon objects "
        "or symbols related to the theme, flat colorful background"
    ),
    "duo_scene": (
        "two stick figures together in the same scene, interacting with each other, "
        "clear composition, flat background"
    ),
    "scene_normal": (
        "single stick figure performing an action, clear composition, flat background"
    ),
}


class PromptEngine:
    """
    Gera e refina prompts visuais por timestamp.
    Recebe timestamps do ScriptWriter v2 e aplica consistência visual.
    """

    def __init__(self):
        self._prev_scene = None  # Para manter continuidade

    def refine_timestamps(self, timestamps: list, theme: str = "",
                          video_format: str = "vertical",
                          style_id: str = None, style_custom: str = "",
                          character: str = "", world: str = "") -> list:
        """
        Refina os prompts visuais de cada timestamp com style anchor + lock.

        Args:
            timestamps: Lista de {time, narration, image_prompt} do ScriptWriter
            theme: Tema do vídeo
            video_format: 'vertical' ou 'horizontal'
            style_id: Preset visual (ver modules/styles)
            style_custom: Descrição customizada
            character: Descrição do personagem
            world: Descrição do universo visual

        Returns:
            Lista refinada de timestamps com prompts prontos para geração
        """
        aspect = "16:9" if video_format == "horizontal" else "9:16"

        # Resolve estilo
        master, permite_texto, resolved_style = resolve_style(
            style_id, style_custom, ""
        )

        # Monta style anchor e style lock
        style_anchor = self._build_style_anchor(resolved_style)
        style_lock = self._build_style_lock(aspect)

        # Character description com anatomia explícita
        char_desc = character if character else STICK_FIGURE_ANATOMY

        refined = []
        self._prev_scene = None

        for i, ts in enumerate(timestamps):
            narration = ts.get("narration", "")
            old_prompt = ts.get("image_prompt", "")

            # Detecta tom da narração
            tone = self._detect_tone(narration, i, len(timestamps))
            bg_color = TONE_COLORS.get(tone, TONE_COLORS["neutral"])

            # Detecta frame type apropriado
            frame_type = self._select_frame_type(narration, i, len(timestamps))

            # Constrói descrição CONCRETA da cena
            scene_desc = self._build_scene_description(
                narration, old_prompt, theme, frame_type, i, len(timestamps)
            )

            # Monta prompt final: anchor + scene + anatomy + bg + lock
            parts = [
                style_anchor,
                scene_desc,
                f"character: {char_desc}",
                bg_color,
            ]

            # Adiciona frame type hint se relevante
            if frame_type in FRAME_TYPES:
                parts.append(f"frame style: {FRAME_TYPES[frame_type]}")

            # Negative lock forte
            parts.append(STICK_FIGURE_NEGATIVE)
            parts.append(style_lock)

            refined_prompt = ", ".join(p for p in parts if p)

            refined.append({
                "time": ts.get("time", f"{i * 5 // 60:02d}:{i * 5 % 60:02d}"),
                "narration": narration,
                "image_prompt": refined_prompt,
                "tone": tone,
                "frame_type": frame_type,
                "scene_index": i,
            })

            self._prev_scene = scene_desc

        return refined

    def _build_style_anchor(self, style_id: str) -> str:
        """Constrói o style anchor baseado no estilo resolvido."""
        anchors = {
            "boneco_palito": (
                "Hand-drawn 2D doodle cartoon animation, flat colors, "
                "bold black outlines, slightly imperfect sketchy marker lines"
            ),
            "storybook_cinematografico": (
                "Premium cinematic storybook illustration, painterly cel-shading, "
                "soft warm lighting, paper texture feel"
            ),
            "3d_pixar": (
                "Polished 3D render, Pixar style, soft global illumination, "
                "rounded characters, subsurface scattering"
            ),
            "realista_cinematografico": (
                "Photorealistic cinematic still, natural lighting, "
                "shallow depth of field, filmic color grading"
            ),
            "anime": (
                "Modern anime style, clean line art, cel shading, "
                "expressive eyes, vibrant color palette"
            ),
            "aquarela": (
                "Hand-painted watercolor illustration, bleeding edges, "
                "textured paper, organic color palette"
            ),
            "minimalista": (
                "Clean modern flat vector illustration, geometric shapes, "
                "limited color palette, negative space"
            ),
        }
        return anchors.get(style_id, anchors["boneco_palito"])

    def _build_style_lock(self, aspect: str) -> str:
        """Constrói o style lock (fixo no final de todo prompt)."""
        return (
            f"no gradients, no shadows, no textures, no photorealism, "
            f"no 3D, {aspect} aspect ratio, educational YouTube explainer style"
        )

    def _detect_tone(self, narration: str, index: int, total: int) -> str:
        """Detecta o tom narrativo de uma linha."""
        lower = narration.lower()

        # Palavras-chave por tom (expandido)
        tone_keywords = {
            "danger": ["morte", "destruição", "perigo", "ameaça", "sangue",
                       "guerra", "fome", "peste", "castigo", "pecado", "medo",
                       "terror", "pânico", "assustado", "correr"],
            "ancient": ["antigo", "séculos", "milênios", "milhares de anos",
                        "ancestrais", "primitivo", "bíblia", "passado"],
            "mystery": ["mistério", "segredo", "escondido", "oculto",
                        "desconhecido", "enigma", "paradoxo", "por que"],
            "discovery": ["descoberta", "revelação", "revelou", "incrível",
                         "surpreendente", "novo", "nunca visto", "imagina"],
            "science": ["ciência", "estudo", "pesquisa", "cientistas",
                       "neurociência", "biologia", "evolução", "cérebro"],
            "triumph": ["vitória", "conquista", "superou", "triunfou",
                       "sucesso", "milagre", "ganhou", "venceu"],
            "contemplative": ["reflexão", "pensar", "significado", "propósito",
                             "eternidade", "infinito", "sentir", "alma"],
            "love": ["amor", "amar", "carinho", "afeto", "abraço",
                    "coração", "querer", "juntos", "união", "irmão",
                    "família", "pai", "mãe", "filho"],
            "sadness": ["triste", "chorar", "lágrima", "perda", "saudade",
                       "solidão", "sozinho", "dor", "sofrer"],
        }

        # Verifica palavras-chave
        for tone, keywords in tone_keywords.items():
            if any(kw in lower for kw in keywords):
                return tone

        # Padrão baseado posição no vídeo
        ratio = index / max(1, total - 1)
        if ratio < 0.15:
            return "tension"
        elif ratio < 0.4:
            return "mystery"
        elif ratio < 0.7:
            return "discovery"
        elif ratio < 0.85:
            return "reveal"
        else:
            return "contemplative"

    def _select_frame_type(self, narration: str, index: int, total: int) -> str:
        """Seleciona o frame type mais apropriado para a cena."""
        lower = narration.lower()

        # Conceitos abstratos → concept_text
        abstract = ["conceito", "ideia", "teoria", "significado", "verdade",
                    "razão", "propósito", "mistério", "tempo", "eternidade",
                    "infinito", "universo", "vida", "morte"]
        if any(w in lower for w in abstract):
            return "concept_text"

        # Progressão/evolução → evolution_sequence
        progression = ["evolução", "desenvolvimento", "cresceu", "mudou",
                      "transformou", "antes", "depois", "progressão",
                      "crescimento", "amadureceu"]
        if any(w in lower for w in progression):
            return "evolution_sequence"

        # Pergunta/confusão → stick_reaction
        questions = ["?", "como", "por que", "o que", "será que", "imagina",
                    "pergunta", "dúvida", "confuso"]
        if any(q in lower for q in questions):
            return "stick_reaction"

        # Números/dados → labeled_diagram
        has_numbers = bool(re.search(r'\d+', narration))
        data_words = ["número", "estatística", "dados", "pesquisa", "estudo",
                     "porcento", "milhões", "bilhões"]
        if has_numbers or any(w in lower for w in data_words):
            return "labeled_diagram"

        # Vilão/conceito negativo → villain_personified
        villains = ["destruição", "castigo", "pecado", "morte",
                   "guerra", "fome", "praga", "medo", "pânico"]
        if any(v in lower for v in villains):
            return "villain_personified"

        # Cena com 2+ pessoas → duo_scene
        duo_words = ["irmão", "irmã", "pai", "mãe", "filho", "amigo",
                    "juntos", "abraçar", "abraço", "dois", "dupla",
                    "família", "par", "casal"]
        if any(w in lower for w in duo_words):
            return "duo_scene"

        # Início/fim → globe_creatures
        if index == 0 or index >= total - 1:
            return "globe_creatures"

        return "scene_normal"

    def _build_scene_description(self, narration: str, old_prompt: str,
                                  theme: str, frame_type: str,
                                  index: int, total: int) -> str:
        """
        Constrói descrição CONCRETA da cena baseada na narração.
        Não repete palavras da narração — traduz em ação visual.
        """
        if not narration:
            return f"single stick figure standing next to a large object related to {theme}"

        lower = narration.lower()

        # 1. Se tem prompt antigo válido, usa como base
        if old_prompt and len(old_prompt) > 30:
            cleaned = old_prompt
            for prefix in ["Hand-drawn 2D", "no gradients", "no shadows"]:
                idx = cleaned.find(prefix)
                if idx > 0:
                    cleaned = cleaned[:idx]
            cleaned = cleaned.strip().rstrip(',').strip()
            if len(cleaned) > 20:
                return cleaned

        # 2. Mapeia palavras-chave da narração para ações concretas
        scene_parts = []

        # Detecta ações do boneco
        for keyword, action in SCENE_ACTION_MAP.items():
            if keyword in lower:
                scene_parts.append(action)
                break

        # Detecta objetos mencionados
        objects_found = []
        for keyword, obj in SCENE_ACTION_MAP.items():
            if keyword in lower and keyword not in ["abraçar", "abraço", "chorar",
                                                      "rir", "pensar", "correr",
                                                      "cair", "lutar", "olhar",
                                                      "apontar", "perguntar",
                                                      "responder", "descobrir",
                                                      "ensinar", "aprender",
                                                      "trabalhar", "descansar",
                                                      "comer", "beber"]:
                objects_found.append(obj)

        # 3. Se não encontrou mapeamento, descreve cena baseada no frame type
        if not scene_parts:
            if frame_type == "duo_scene":
                scene_parts.append("two stick figures together, interacting")
            elif frame_type == "concept_text":
                scene_parts.append("single stick figure standing next to a large symbolic object")
            elif frame_type == "stick_reaction":
                scene_parts.append("single stick figure with thought bubble above head")
            elif frame_type == "evolution_sequence":
                scene_parts.append("left-to-right progression of stick figures showing change")
            elif frame_type == "labeled_diagram":
                scene_parts.append("object with yellow arrow pointing at it and ALL CAPS label")
            elif frame_type == "villain_personified":
                scene_parts.append("angry cartoon face on an abstract concept")
            elif frame_type == "globe_creatures":
                scene_parts.append("Earth globe with floating objects around it")
            else:
                # Cena genérica — descreve o que o boneco está fazendo
                scene_parts.append("single stick figure in the center of the frame")

        # 4. Adiciona contexto do tema
        if theme:
            # Extrai palavras-chave do tema
            theme_words = theme.lower().split()
            theme_stop = {"o", "a", "e", "de", "do", "da", "em", "um", "uma",
                         "para", "por", "com", "não", "se", "mas", "que"}
            theme_keywords = [w for w in theme_words if w not in theme_stop][:3]
            if theme_keywords:
                scene_parts.append(f"related to {', '.join(theme_keywords)}")

        # 5. Adiciona objetos encontrados
        if objects_found:
            scene_parts.append(objects_found[0])

        # 6. Se ainda está vazio, usa descrição genérica
        if not scene_parts:
            scene_parts.append(f"single stick figure in a scene about {theme}")

        return ", ".join(scene_parts)

    def generate_character_reference(self, style_id: str = None,
                                      style_custom: str = "",
                                      character: str = "",
                                      video_format: str = "vertical") -> str:
        """
        Gera o prompt para o character reference frame.
        Esta imagem é usada como seed/base para manter consistência.

        Returns:
            Prompt string para gerar a imagem de referência do personagem
        """
        aspect = "16:9" if video_format == "horizontal" else "9:16"

        master, _, resolved_style = resolve_style(style_id, style_custom, "")
        anchor = self._build_style_anchor(resolved_style)

        char_desc = character if character else (
            "single stick figure character standing in neutral pose, "
            "exactly 2 arms, 2 legs, 1 large circular head, 2 dot eyes, "
            "1 mouth, expressive thick brow lines, simple body with thick "
            "black outlines, facing forward, full body visible"
        )

        prompt = (
            f"{anchor}, {char_desc}, "
            f"plain white background, centered in frame, full body visible, "
            f"character reference sheet style, "
            f"no extra arms, no extra legs, no extra eyes, no extra heads, "
            f"no deformed body, no floating limbs, "
            f"no gradients, no shadows, no textures, no photorealism, no 3D, "
            f"{aspect} aspect ratio"
        )

        return prompt

    def build_final_prompts(self, timestamps: list) -> list:
        """
        Monta os prompts finais prontos para geração de imagem.
        Cada prompt já está no formato correto para FLUX.2 Klein.

        Returns:
            Lista de {time, narration, image_prompt, scene_index}
        """
        return timestamps  # timestamps já vêm refinados de refine_timestamps()


# ─── Função de conveniência ──────────────────────────────────────────────────

def refine_video_prompts(timestamps: list, theme: str = "",
                         video_format: str = "vertical",
                         style_id: str = None, style_custom: str = "",
                         character: str = "", world: str = "") -> list:
    """Refina prompts de todos os timestamps. Função de conveniência."""
    engine = PromptEngine()
    return engine.refine_timestamps(
        timestamps, theme, video_format,
        style_id, style_custom, character, world
    )


def get_character_reference_prompt(style_id: str = None,
                                    style_custom: str = "",
                                    character: str = "",
                                    video_format: str = "vertical") -> str:
    """Gera prompt do character reference frame. Função de conveniência."""
    engine = PromptEngine()
    return engine.generate_character_reference(
        style_id, style_custom, character, video_format
    )

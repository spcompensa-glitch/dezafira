"""
Scene Planner Semântico — Planejador de Cenas com IA
====================================================
Divide o roteiro em "beats narrativos" (gancho, problema, solução, prova, CTA)
e gera visual prompts específicos para cada cena. Usa CLIP embeddings para
match semântico com stock footage e fallback para geração IA.

Versão: 2.0 — Qualidade Cinema
"""

import json
import re
import math
import hashlib
from typing import List, Dict, Any, Optional, Tuple

# CLIP embeddings para match semântico (lazy load)
_clip_model = None
_clip_tokenizer = None


def _load_clip():
    """Lazy load do modelo CLIP para matching semântico."""
    global _clip_model, _clip_tokenizer
    if _clip_model is None:
        try:
            from sentence_transformers import SentenceTransformer
            _clip_model = SentenceTransformer("clip-ViT-B-32")
            _clip_tokenizer = True
            print("[ScenePlanner] CLIP embeddings carregados (clip-ViT-B-32)")
        except Exception as e:
            print(f"[ScenePlanner] CLIP não disponível: {e}. Usando keyword fallback.")
            _clip_model = False
    return _clip_model


# ─── Constantes ─────────────────────────────────────────────────────────────

# Duração máxima de cena em segundos
MAX_SCENE_DURATION = 8.0
MIN_SCENE_DURATION = 3.0

# Palavras que indicam cena genérica → PEXELS
GENERIC_KEYWORDS = {
    "nature", "city", "landscape", "ocean", "beach", "mountain", "forest",
    "people", "crowd", "office", "street", "building", "sky", "sunset",
    "sunrise", "clouds", "rain", "snow", "traffic", "night", "cityscape",
    "field", "garden", "park", "river", "lake", "water", "sea", "wave",
    "desert", "island", "village", "town", "market", "store", "shop",
    "restaurant", "cafe", "kitchen", "bedroom", "living room", "house",
    "road", "highway", "bridge", "train", "airport", "station", "bus",
    "car", "bicycle", "walk", "run", "exercise", "gym", "sport",
    "computer", "laptop", "phone", "tablet", "screen", "keyboard",
    "writing", "reading", "book", "paper", "document", "meeting",
    "presentation", "conference", "classroom", "school", "university",
    "hospital", "doctor", "nurse", "laboratory", "factory", "warehouse",
    "construction", "worker", "business", "money", "cash", "bank",
    "shopping", "travel", "tourism", "food", "cooking", "eating",
    "drink", "coffee", "tea", "fruit", "vegetable", "garden",
    "sun", "moon", "star", "space", "earth", "globe", "map",
    "family", "friends", "couple", "child", "baby", "pet", "dog", "cat",
    "music", "guitar", "piano", "dance", "concert", "stage",
    "art", "paint", "draw", "sculpture", "museum", "gallery",
    "fitness", "yoga", "meditation", "health", "wellness",
}

# Tipos de transição por posição no arco narrativo
TRANSITIONS_BY_BEAT = {
    "hook": "zoom_in_fast",       # 0.3s zoom rápido (curiosidade)
    "problem": "crossfade_slow",  # 0.6s crossfade (contemplação)
    "solution": "slide_left",     # 0.4s slide (progresso)
    "proof": "cut",               # 0.0s corte direto (impacto)
    "climax": "zoom_out",         # 0.5s zoom out (revelação)
    "cta": "fade_black",          # 0.8s fade out (encerramento)
}


# ─── Classe Principal ────────────────────────────────────────────────────────

class ScenePlanner:
    """
    Planejador de cenas semântico — gera cenas com:
    - Beat narrativo (hook/problem/solution/proof/cta)
    - Visual prompt descritivo (não só keywords)
    - Tipo (PEXELS/AI_IMAGE) com score de confiança
    - Transição apropriada para o momento narrativo
    - Duração baseada em palavras + pausas naturais
    """

    def __init__(self, use_llm: bool = True, brain=None):
        self.use_llm = use_llm
        self.brain = brain

    def plan_scenes(
        self,
        script_text: str,
        title: str = "",
        target_duration: float = 45.0,
        channel_niche: str = "general",
        channel_seed: int = 42,
    ) -> List[Dict[str, Any]]:
        """
        Planeja cenas com qualidade cinematográfica.

        Args:
            script_text: Texto do roteiro
            title: Título do vídeo
            target_duration: Duração alvo em segundos
            channel_niche: Nicho do canal (para estilo visual)
            channel_seed: Seed fixa por canal (consistência)

        Returns:
            Lista de cenas enriquecidas com metadados completos
        """
        # 1. Dividir script em beats narrativos
        beats = self._extract_narrative_beats(script_text)

        # 2. Para cada beat, gerar visual prompt + classificação
        scenes = []
        current_time = 0.0

        for i, beat in enumerate(beats):
            # Calcular duração baseada em palavras
            word_count = len(beat["text"].split())
            words_per_second = 2.8  # ritmo natural: ~2.8 palavras/seg
            duration = max(MIN_SCENE_DURATION,
                          min(MAX_SCENE_DURATION, word_count / words_per_second))

            # Gerar visual prompt descritivo
            visual_prompt = self._generate_visual_prompt(
                beat, title, channel_niche, i, len(beats)
            )

            # Classificar tipo (PEXELS ou AI_IMAGE) com score
            scene_type, confidence = self._classify_scene(visual_prompt)

            # Escolher transição baseada no beat
            transition = TRANSITIONS_BY_BEAT.get(beat["type"], "crossfade_slow")

            # Seed para consistência visual
            scene_seed = channel_seed + i

            scenes.append({
                "scene_id": i + 1,
                "beat_type": beat["type"],
                "beat_label": beat["label"],
                "start_time": round(current_time, 2),
                "end_time": round(current_time + duration, 2),
                "duration": round(duration, 2),
                "narration": beat["text"],
                "type": scene_type,
                "confidence": round(confidence, 2),
                "visual_prompt": visual_prompt,
                "transition": transition,
                "seed": scene_seed,
                "word_count": word_count,
                "emphasis_words": beat.get("emphasis", []),
            })

            current_time += duration

        return scenes

    def _extract_narrative_beats(self, script_text: str) -> List[Dict[str, Any]]:
        """
        Extrai beats narrativos do roteiro.
        Usa LLM se disponível, senão usa heurísticas de estrutura narrativa.
        """
        if self.use_llm and self.brain:
            return self._extract_beats_with_llm(script_text)
        else:
            return self._extract_beats_heuristic(script_text)

    def _extract_beats_with_llm(self, script_text: str) -> List[Dict[str, Any]]:
        """Usa LLM para identificar beats narrativos com precisão."""
        try:
            system_prompt = """You are a video narrative analyst.
Break down scripts into "narrative beats" — each beat represents one visual scene.

For each beat, identify:
- type: hook | problem | solution | proof | climax | cta
- label: short label (e.g. "Opening hook", "Main problem", "Solution reveal")
- text: the narration text for this beat (1-3 sentences, max 25 words)
- emphasis: 1-2 words that should be visually emphasized (bold/highlighted)
- visual_intent: what the viewer should SEE during this beat (cinematic description)

RULES:
- Maximum 8 beats per script
- Hook beat MUST be first and max 10 words
- Each beat = one visual scene
- Alternate visual intensity (high/low) to maintain engagement
- CTA beat is always last

Return JSON:
{
  "beats": [
    {
      "type": "hook",
      "label": "Opening hook",
      "text": "text here",
      "emphasis": ["keyword"],
      "visual_intent": "what to show visually"
    }
  ]
}"""
            user_prompt = f"Break this script into narrative beats:\n\n{script_text}"
            result = self.brain._call_llm(system_prompt, user_prompt, temperature=0.3)

            if "```json" in result:
                result = result.split("```json")[1].split("```")[0].strip()
            elif "```" in result:
                result = result.split("```")[1].split("```")[0].strip()

            data = json.loads(result.strip())
            beats = data.get("beats", [])

            if beats:
                print(f"[ScenePlanner] LLM identificou {len(beats)} beats narrativos")
                return beats

        except Exception as e:
            print(f"[ScenePlanner] LLM falhou: {e}. Usando heurística.")

        return self._extract_beats_heuristic(script_text)

    def _extract_beats_heuristic(self, script_text: str) -> List[Dict[str, Any]]:
        """Fallback heurístico — identifica beats por padrões de escrita."""
        sentences = [s.strip() for s in re.split(r'[.!?]+', script_text) if s.strip()]
        if not sentences:
            sentences = [script_text]

        beats = []
        total = len(sentences)

        # Mapear sentenças para beats
        for i, sent in enumerate(sentences):
            progress = (i + 1) / total

            if progress < 0.15:
                beat_type = "hook"
                label = "Opening hook"
            elif progress < 0.35:
                beat_type = "problem"
                label = "Problem statement"
            elif progress < 0.60:
                beat_type = "solution"
                label = "Solution reveal"
            elif progress < 0.80:
                beat_type = "proof"
                label = "Proof/evidence"
            elif progress < 0.92:
                beat_type = "climax"
                label = "Key insight"
            else:
                beat_type = "cta"
                label = "Call to action"

            # Extrair ênfase (palavras maiúsculas ou que começam com *)
            emphasis = re.findall(r'\*{1,2}(\w+)\*{1,2}', sent)
            if not emphasis:
                words = sent.split()
                emphasis = [max(words, key=len)] if words else []

            beats.append({
                "type": beat_type,
                "label": label,
                "text": sent,
                "emphasis": emphasis[:2],
                "visual_intent": f"cinematic: {sent[:50]}",
            })

        return beats

    def _generate_visual_prompt(
        self, beat: Dict, title: str, niche: str, index: int, total: int
    ) -> str:
        """
        Gera visual prompt descritivo para o beat.
        Combina intent visual do LLM com estilo do nicho.
        """
        visual_intent = beat.get("visual_intent", beat.get("text", ""))
        beat_type = beat.get("type", "problem")

        # Prompts estilo por nicho e beat type
        NICHE_STYLE = {
            "tech": {
                "hook": "futuristic tech interface, holographic data visualization, neon cyan glow, volumetric fog, 8k cinematic",
                "problem": "dark glitching screen, error messages, broken technology, red warning lights, dramatic shadows",
                "solution": "clean tech dashboard, glowing UI elements, smooth animations, blue ambient light, professional",
                "proof": "data charts rising, success metrics, green checkmarks, modern office with screens, clean aesthetic",
                "climax": "mind-blowing tech reveal, light rays, particle effects, epic scale, cinematic composition",
                "cta": "subscribe button glow, channel logo, warm invitation light, clean modern end screen",
            },
            "finance": {
                "hook": "stacks of money, gold coins falling, luxury aesthetic, dramatic lighting, wealth visualization",
                "problem": "empty wallet, bills piling up, stress expression, dark moody lighting, financial anxiety",
                "solution": "growing investment chart, money multiplying, bright optimistic lighting, success imagery",
                "proof": "real financial data, stock charts green, bank account growing, clean professional setting",
                "climax": "financial freedom moment, beach sunset with laptop, passive income visualization, dream lifestyle",
                "cta": "link in description highlight, free resource mockup, warm call to action, professional end screen",
            },
            "curiosity": {
                "hook": "mysterious object reveal, dramatic close-up, suspenseful lighting, intrigue, question mark visual",
                "problem": "mind-blown reaction, confusion visualization, puzzle pieces scattered, chaotic composition",
                "solution": "light bulb moment, revelation, clarity, organized solution, bright clean aesthetic",
                "proof": "evidence presentation, facts overlay, before-after comparison, documentary style, credible",
                "climax": "epic reveal moment, dramatic zoom out, truth unveiled, cinematic wide shot, impactful",
                "cta": "follow for more mystery, next video teaser, curiosity loop, engaging end screen",
            },
        }

        # Estilo base do nicho
        niche_styles = NICHE_STYLE.get(niche, NICHE_STYLE.get("curiosity", {}))
        base_style = niche_styles.get(beat_type, "cinematic, high quality, professional lighting")

        # Compor prompt final
        prompt = f"{visual_intent}, {base_style}"

        # Adicionar Variação visual por posição (evitar repetição)
        if index == 0:
            prompt += ", opening shot, dramatic"
        elif index == total - 1:
            prompt += ", closing shot, resolution"
        elif index % 3 == 0:
            prompt += ", wide establishing shot"
        elif index % 3 == 1:
            prompt += ", medium shot, detail focus"
        else:
            prompt += ", close-up, emotional impact"

        return prompt

    def _classify_scene(self, prompt: str) -> Tuple[str, float]:
        """
        Classifica cena como PEXELS ou AI_IMAGE com score de confiança.
        Usa CLIP embeddings quando disponível.
        """
        # Tentar CLIP matching
        clip_model = _load_clip()
        if clip_model and clip_model is not False:
            return self._classify_with_clip(prompt, clip_model)

        # Fallback: keyword matching
        return self._classify_with_keywords(prompt)

    def _classify_with_clip(self, prompt: str, model) -> Tuple[str, float]:
        """Classifica usando embeddings CLIP para match semântico."""
        try:
            # Embedding do prompt
            prompt_embedding = model.encode([prompt])

            # Embedding de exemplos genéricos (PEXELS)
            generic_examples = [
                "person walking in city street",
                "nature landscape with mountains",
                "office workers at computers",
                "ocean waves on beach",
                "traffic on highway at night",
                "people cooking in kitchen",
                "sunset over city skyline",
                "forest with sunlight",
            ]
            generic_embedding = model.encode(generic_examples)

            # Similaridade cosine
            import numpy as np
            similarities = np.dot(generic_embedding, prompt_embedding[0]) / (
                np.linalg.norm(generic_embedding, axis=1) * np.linalg.norm(prompt_embedding[0])
            )
            max_sim = float(np.max(similarities))

            if max_sim > 0.28:
                return "PEXELS", min(max_sim * 1.2, 1.0)
            else:
                return "AI_IMAGE", min((1 - max_sim) * 1.1, 1.0)

        except Exception as e:
            print(f"[ScenePlanner] CLIP falhou: {e}. Usando keywords.")
            return self._classify_with_keywords(prompt)

    def _classify_with_keywords(self, prompt: str) -> Tuple[str, float]:
        """Classifica usando keyword matching (fallback)."""
        prompt_lower = prompt.lower()
        matches = sum(1 for kw in GENERIC_KEYWORDS if kw in prompt_lower)
        total_words = len(prompt_lower.split())

        if matches > 0 and matches / max(total_words, 1) > 0.1:
            return "PEXELS", min(0.5 + matches * 0.1, 0.9)
        return "AI_IMAGE", min(0.5 + (total_words - matches) * 0.05, 0.9)

    def get_pexels_keywords(self, scenes: List[Dict]) -> List[str]:
        """Extrai keywords PEXELS curtas e limpas de todas as cenas."""
        keywords = []
        for s in scenes:
            if s.get("type") == "PEXELS":
                raw = s["visual_prompt"]
                # Extrair sujeito principal e simplificar
                keyword = self._simplify_for_search(raw)
                if keyword:
                    keywords.append(keyword)
        return keywords

    def _simplify_for_search(self, description: str) -> str:
        """Simplifica descrição visual para keyword de busca curta — máximo 3 palavras."""
        # Mapeamento de termos complexos para simples
        term_map = {
            "ethereal": "nature",
            "dreamy": "nature",
            "gritty": "city",
            "cityscape": "city",
            "cosmic": "space",
            "starry": "night",
            "splitscreen": "people",
            "montage": "people",
            "glowing": "light",
            "mystical": "ancient",
            "artifacts": "history",
            "serene": "peace",
            "peaceful": "calm",
            "contemplation": "person",
            "dramatic": "nature",
            "intense": "action",
        }
        
        # Pegar primeiras palavras significativas
        words = description.lower().replace(",", " ").replace(".", " ").split()
        stop_words = {"a", "an", "the", "of", "in", "on", "at", "to", "for",
                       "with", "by", "from", "and", "or", "but", "is", "are",
                       "shot", "sequence", "close-up", "wide", "high-angle", "aerial"}
        
        meaningful = []
        for w in words:
            if w in stop_words or len(w) < 3:
                continue
            # Usar mapeamento se disponível
            mapped = term_map.get(w, w)
            meaningful.append(mapped)
            if len(meaningful) >= 2:
                break
        
        return " ".join(meaningful) if meaningful else "nature"

    def get_ai_scenes(self, scenes: List[Dict]) -> List[Dict]:
        """Retorna cenas AI_IMAGE com prompts otimizados para Pollinations."""
        ai_scenes = []
        for s in scenes:
            if s.get("type") == "AI_IMAGE":
                # Otimizar prompt para Pollinations (SDXL)
                optimized = self._optimize_for_pollinations(s["visual_prompt"])
                ai_scenes.append({**s, "pollinations_prompt": optimized})
        return ai_scenes

    def _optimize_for_pollinations(self, prompt: str) -> str:
        """Otimiza prompt para Pollinations SDXL (qualidade máxima)."""
        # Remover keywords genéricas, manter descritivo
        parts = [p.strip() for p in prompt.split(",")]
        # Adicionar quality boosters
        quality_tags = [
            "masterpiece", "best quality", "highly detailed",
            "cinematic lighting", "sharp focus", "8k resolution",
        ]
        # Filtrar partes muito curtas
        filtered = [p for p in parts if len(p) > 3]
        # Compor prompt final
        final = ", ".join(filtered[:8])  # Max 8 partes
        return f"{final}, {', '.join(quality_tags[:3])}"


# ─── Teste ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    planner = ScenePlanner(use_llm=False)
    script = (
        "Did you know that 97 percent of people fail at making money online? "
        "The reason is simpler than you think. "
        "They keep chasing shiny objects instead of building one system. "
        "Here is the exact method that changed everything for me. "
        "Start with this one simple step today."
    )
    scenes = planner.plan_scenes(
        script, "The #1 Reason You're Still Broke Online", 30.0, "finance", 42
    )
    for s in scenes:
        print(f"[{s['beat_type']}] {s['visual_prompt'][:60]}... → {s['type']} ({s['confidence']})")

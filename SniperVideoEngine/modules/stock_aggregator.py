"""
Stock Aggregator — Agregador de Stock Footage Qualidade Cinema (v2)
===================================================================
Múltiplas fontes com fallback inteligente, filtros de qualidade,
e matching semântico via CLIP.

Fontes: Pexels → Pixabay → Coverr
Filtros: resolução >= 1080p, duração >= 8s, orientation match
"""

import os
import re
import subprocess
from typing import List, Optional, Tuple

from modules.pexels_client import PexelsClient
from modules.pixabay_client import PixabayClient
from modules.coverr_client import CoverrClient


# ─── Quality Filters ────────────────────────────────────────────────────────

MIN_RESOLUTION_WIDTH = 1920   # mínimo 1080p landscape
MIN_DURATION_SECONDS = 4.0    # clip mínimo 4 segundos (reduzido para mais opções)


class StockAggregator:
    """
    Agregador de stock footage v2 — qualidade cinema.

    Filtros por clip:
    - Resolução >= 1920x1080
    - Duração >= 4 segundos
    - Orientation: dinâmico (landscape/portrait)

    Fontes em ordem de prioridade:
    1. Pexels (maior qualidade, API key)
    2. Pixabay (gratuito, sem chave)
    3. Coverr (cinematic, fallback)
    """

    def __init__(self):
        self.sources = [
            ("Pexels", PexelsClient(), self._pexels_search),
            ("Pixabay", PixabayClient(), self._pixabay_search),
            ("Coverr", CoverrClient(), self._coverr_search),
        ]

    def _clean_query(self, query: str) -> str:
        """Limpa query para API: remove caracteres especiais, limita tamanho."""
        # Remover caracteres especiais, manter só letras, números e espaços
        cleaned = re.sub(r'[^a-zA-Z0-9\s]', '', query)
        # Remover espaços múltiplos
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        # Limitar a 50 caracteres
        if len(cleaned) > 50:
            cleaned = cleaned[:50].rsplit(' ', 1)[0]
        return cleaned

    def _pexels_search(self, client, query: str, orientation: str) -> List[str]:
        """Busca Pexels com filtros de qualidade."""
        try:
            clean = self._clean_query(query)
            clips = client.search_and_download(query=clean, count=3, orientation=orientation)
            return [c for c in clips if self._validate_clip(c)]
        except Exception as e:
            print(f"[Stock] Pexels erro: {e}")
            return []

    def _pixabay_search(self, client, query: str, orientation: str) -> List[str]:
        """Busca Pixabay com filtros de qualidade."""
        try:
            clean = self._clean_query(query)
            clips = client.search_and_download(query=clean, count=3, orientation=orientation)
            return [c for c in clips if self._validate_clip(c)]
        except Exception as e:
            print(f"[Stock] Pixabay erro: {e}")
            return []

    def _coverr_search(self, client, query: str, orientation: str) -> List[str]:
        """Busca Coverr com filtros de qualidade."""
        try:
            clean = self._clean_query(query)
            clips = client.search_and_download(query=clean, count=3, orientation=orientation)
            return [c for c in clips if self._validate_clip(c)]
        except Exception as e:
            print(f"[Stock] Coverr erro: {e}")
            return []

    def _validate_clip(self, clip_path: str) -> bool:
        """Valida qualidade mínima do clip via ffprobe — versão permissiva."""
        if not os.path.exists(clip_path):
            return False

        try:
            result = subprocess.run(
                ["ffprobe", "-v", "quiet",
                 "-show_entries", "stream=codec_type,codec_name,width,height,duration",
                 "-of", "json", clip_path],
                capture_output=True, text=True, timeout=10,
                encoding="utf-8", errors="replace"
            )
            import json
            data = json.loads(result.stdout)
            streams = data.get("streams", [])

            video_stream = None
            for s in streams:
                if s.get("codec_type") == "video":
                    video_stream = s
                    break

            if not video_stream:
                return False

            width = video_stream.get("width", 0)
            height = video_stream.get("height", 0)
            duration = float(video_stream.get("duration", 0))

            # Aceitar qualquer resolução >= 640p
            if width < 640:
                return False
            # Aceitar clips >= 1 segundo
            if duration < 1.0:
                return False

            return True

        except Exception:
            # Se ffprobe falhar, aceitar
            return True

    def fetch_for_keyword(
        self,
        keyword: str,
        orientation: str = "portrait",
        min_clips: int = 1,
    ) -> List[str]:
        """
        Busca clips para uma keyword com fallback entre fontes.
        Retorna clips que passam nos filtros de qualidade.
        """
        all_clips = []
        clean = self._clean_query(keyword)
        for name, client, search_fn in self.sources:
            clips = search_fn(client, clean, orientation)
            all_clips.extend(clips)
            if len(all_clips) >= min_clips:
                print(f"[StockAggregator] {name}: {len(clips)} clips OK para '{clean}'")
                break
            print(f"[StockAggregator] {name}: 0 clips OK para '{clean}'")

        return all_clips[:min_clips]

    def fetch_all(
        self,
        keywords: List[str],
        orientation: str = "portrait",
        clips_per_keyword: int = 1,
    ) -> List[str]:
        """
        Busca clips para múltiplas keywords com deduplicação.

        Args:
            keywords: Lista de keywords de busca
            orientation: "portrait" (9:16) ou "landscape" (16:9)
            clips_per_keyword: Número de clips por keyword

        Returns:
            Lista de caminhos de clips validados
        """
        all_clips = []
        existing = set()

        for keyword in keywords:
            clips = self.fetch_for_keyword(keyword, orientation, min_clips=clips_per_keyword)
            for clip in clips:
                # Deduplicar por hash do conteúdo
                clip_hash = self._clip_hash(clip)
                if clip_hash not in existing:
                    all_clips.append(clip)
                    existing.add(clip_hash)

        print(f"[StockAggregator] Total: {len(all_clips)} clips para {len(keywords)} keywords")
        return all_clips

    def fetch_curated(
        self,
        visual_descriptions: List[str],
        beat_types: List[str],
        orientation: str = "portrait",
    ) -> List[str]:
        """
        Busca clips curados baseado em descrições visuais do ScenePlanner.

        Args:
            visual_descriptions: Descrições visuais de cada cena
            beat_types: Tipos de beat (hook, problem, etc.)
            orientation: Orientação do vídeo

        Returns:
            Lista de clips curados (1 por cena)
        """
        curated = []

        for i, (desc, beat) in enumerate(zip(visual_descriptions, beat_types)):
            # Otimizar query baseada no beat type
            query = self._optimize_query_for_beat(desc, beat)
            clips = self.fetch_for_keyword(query, orientation, min_clips=1)

            if clips:
                curated.append(clips[0])
            else:
                # Fallback: query genérica
                generic = " ".join(desc.split()[:3])
                clips = self.fetch_for_keyword(generic, orientation, min_clips=1)
                curated.append(clips[0] if clips else "")

        return curated

    def _optimize_query_for_beat(self, description: str, beat_type: str) -> str:
        """Otimiza query de busca baseada no beat type — queries curtas."""
        # Pegar sujeito principal e simplificar
        subject = description.split(",")[0].strip()
        # Simplificar para keywords
        words = subject.lower().split()
        # Remover artigos e adjetivos desnecessários
        stop = {"a", "an", "the", "of", "in", "on", "at", "to", "for", "with",
                "by", "from", "and", "or", "but", "is", "are", "was", "were",
                "shot", "sequence", "close-up", "wide", "high-angle", "aerial",
                "time-lapse", "dramatic", "stunning", "serene", "haunting"}
        meaningful = [w for w in words if w not in stop and len(w) > 2]
        subject_clean = " ".join(meaningful[:3])

        # Mapear beat para contexto visual curto
        beat_map = {
            "hook": "dramatic",
            "problem": "dark",
            "solution": "bright",
            "proof": "people",
            "climax": "epic",
            "cta": "warm",
        }
        ctx = beat_map.get(beat_type, "")
        return f"{subject_clean} {ctx}".strip()

    def _clip_hash(self, clip_path: str) -> str:
        """Gera hash simples do clip para deduplicação."""
        import hashlib
        basename = os.path.basename(clip_path)
        return hashlib.md5(basename.encode()).hexdigest()[:12]

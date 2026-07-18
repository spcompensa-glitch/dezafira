"""
Video Analyzer Spider
Analisa vídeos específicos do YouTube.
"""
import re
from typing import Dict, Any
from services.obscura_client import obscura_client


class VideoAnalyzerSpider:
    """Spider para análise detalhada de vídeos YouTube."""

    async def analyze(self, video_url: str) -> Dict[str, Any]:
        """
        Analisa um vídeo específico.

        Args:
            video_url: URL do vídeo

        Returns:
            Dict com análise completa do vídeo
        """
        print(f"[VideoAnalyzer] Analisando: {video_url}")

        try:
            html = await asyncio.to_thread(obscura_client.fetch_html, video_url)
            if not html:
                return {"url": video_url, "error": "Falha ao buscar página"}

            analysis = {
                "url": video_url,
                "title": self._extract_meta(html, "title"),
                "description": self._extract_meta(html, "description"),
                "views": self._extract_views(html),
                "likes": "",
                "channel": self._extract_channel(html),
                "upload_date": self._extract_date(html),
                "duration": "",
                "tags": self._extract_tags(html),
                "category": "",
                "comments_count": "",
            }

            print(f"[VideoAnalyzer] Vídeo analisado: {analysis['title'][:50]}...")
            return analysis

        except Exception as e:
            print(f"[VideoAnalyzer] Erro: {e}")
            return {"url": video_url, "error": str(e)}

    def _extract_meta(self, html: str, name: str) -> str:
        """Extrai meta tags."""
        patterns = [
            rf'<meta name="{name}" content="([^"]*)"',
            rf'<meta property="og:{name}" content="([^"]*)"',
        ]
        for pattern in patterns:
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return ""

    def _extract_views(self, html: str) -> str:
        """Extrai visualizações."""
        patterns = [
            r'"viewCount":\{"simpleText":"([^"]+)"\}',
            r'"viewCountText":\{"simpleText":"([^"]+)"\}',
        ]
        for pattern in patterns:
            match = re.search(pattern, html)
            if match:
                return match.group(1).strip()
        return ""

    def _extract_channel(self, html: str) -> str:
        """Extrai nome do canal."""
        patterns = [
            r'"ownerChannelName":"([^"]+)"',
            r'"author":"([^"]+)"',
        ]
        for pattern in patterns:
            match = re.search(pattern, html)
            if match:
                return match.group(1).strip()
        return ""

    def _extract_date(self, html: str) -> str:
        """Extrai data de upload."""
        match = re.search(r'"publishDate":"([^"]+)"', html)
        if match:
            return match.group(1).strip()
        match = re.search(r'"uploadDate":"([^"]+)"', html)
        if match:
            return match.group(1).strip()
        return ""

    def _extract_tags(self, html: str) -> list:
        """Extrai tags do vídeo."""
        match = re.search(r'"keywords":\[([^\]]+)\]', html)
        if match:
            tags_str = match.group(1)
            return [tag.strip().strip('"') for tag in tags_str.split(",")]
        return []

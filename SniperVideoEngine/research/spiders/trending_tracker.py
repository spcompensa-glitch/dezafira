"""
Trending Tracker Spider - Otimizado com Async
Rastreia tendências atuais no YouTube.
"""
import re
from typing import List, Dict, Any


class TrendingTrackerSpider:
    """Spider para rastrear tendências do YouTube."""

    TRENDING_URLS = {
        "general": "https://www.youtube.com/feed/trending",
        "music": "https://www.youtube.com/feed/trending?bp=6gQJRkVleHBsb3Jl",
        "gaming": "https://www.youtube.com/feed/trending?bp=6gQJRCVek1ZBSaLo_ZLbJA",
    }

    async def track(self, keyword: str) -> List[Dict[str, Any]]:
        """
        Rastreia tendências para uma palavra-chave.
        
        Args:
            keyword: Palavra-chave para rastrear
            
        Returns:
            Lista de vídeos em tendência
        """
        print(f"[TrendingTracker] Rastreando: {keyword}")
        
        url = f"https://www.youtube.com/results?search_query={keyword}&sp=CAMSAhAB"
        
        videos = await self._fetch_with_fallback(url)
        
        print(f"[TrendingTracker] {len(videos)} vídeos em tendência")
        return videos

    async def get_trending(self, category: str = "general") -> List[Dict[str, Any]]:
        """
        Obtém vídeos em tendência por categoria.
        
        Args:
            category: Categoria (general, music, gaming)
            
        Returns:
            Lista de vídeos em tendência
        """
        url = self.TRENDING_URLS.get(category, self.TRENDING_URLS["general"])
        
        videos = await self._fetch_with_fallback(url)
        
        print(f"[TrendingTracker] {len(videos)} vídeos em tendência ({category})")
        return videos

    async def _fetch_with_fallback(self, url: str) -> List[Dict[str, Any]]:
        """Busca trending via Obscura (renderiza JS real)."""
        try:
            import asyncio
            from services.obscura_client import obscura_client
            print("[TrendingTracker] Buscando via Obscura...")
            html = await asyncio.to_thread(obscura_client.fetch_html, url, "networkidle0", 30, True)

            if not html:
                print("[TrendingTracker] Obscura vazio, fallback urllib...")
                import urllib.request
                req = urllib.request.Request(url, headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                })
                with urllib.request.urlopen(req, timeout=15) as resp:
                    html = resp.read().decode("utf-8", errors="ignore")

            return self._parse_trending(html)

        except Exception as e:
            print(f"[TrendingTracker] Erro: {e}")
            return []

    def _parse_trending(self, html: str) -> List[Dict[str, Any]]:
        """Extrai vídeos de tendência do HTML."""
        videos = []
        
        # Extrair IDs e títulos do JSON embutido
        video_ids = re.findall(r'"videoId":"([^"]+)"', html)
        titles = re.findall(r'"title":\{"runs":\[\{"text":"([^"]+)"\}', html)
        channels = re.findall(r'"ownerChannelName":"([^"]+)"', html)
        views = re.findall(r'"viewCountText":\{"simpleText":"([^"]+)"\}', html)
        
        for i, title in enumerate(titles[:20]):
            if not title.strip():
                continue
                
            vid_id = video_ids[i] if i < len(video_ids) else ""
            
            videos.append({
                "title": title.strip(),
                "link": f"https://www.youtube.com/watch?v={vid_id}" if vid_id else "",
                "channel": channels[i].strip() if i < len(channels) else "",
                "views": views[i].strip() if i < len(views) else "",
                "is_trending": True,
            })
        
        return videos

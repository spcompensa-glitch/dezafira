"""
YouTube Search Spider - Otimizado com Async
Busca vídeos e canais no YouTube com bypass de Cloudflare.
"""
import re
import urllib.parse
from typing import List, Dict, Any


class YouTubeSearchSpider:
    """Spider para busca de vídeos no YouTube com bypass de Cloudflare."""

    def __init__(self):
        self.base_url = "https://www.youtube.com/results"

    async def search(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Busca vídeos no YouTube.
        
        Args:
            query: Termo de busca
            limit: Limite de resultados
            
        Returns:
            Lista de vídeos encontrados
        """
        print(f"[YouTubeSearch] Buscando: {query}")
        
        url = f"{self.base_url}?search_query={urllib.parse.quote(query)}"
        
        videos = await self._search_with_fetcher(url, limit)
        return videos

    async def _search_with_fetcher(self, url: str, limit: int) -> List[Dict[str, Any]]:
        """Busca usando Obscura (renderiza JS real do YouTube)."""
        try:
            import asyncio
            from services.obscura_client import obscura_client
            print("[YouTubeSearch] Buscando via Obscura (renderiza JS)...")
            html = await asyncio.to_thread(obscura_client.fetch_html, url, "networkidle0", 30, True)

            if not html:
                print("[YouTubeSearch] Obscura retornou vazio, fallback urllib...")
                import urllib.request
                req = urllib.request.Request(url, headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                })
                with urllib.request.urlopen(req, timeout=15) as resp:
                    html = resp.read().decode("utf-8", errors="ignore")

            class MockResponse:
                def __init__(self, html):
                    self.text = html

            response = MockResponse(html)
            videos = self._parse_videos(response)

            print(f"[YouTubeSearch] {len(videos)} vídeos encontrados")
            return videos[:limit]

        except Exception as e:
            print(f"[YouTubeSearch] Erro: {e}")
            return []

    def _parse_videos(self, response) -> List[Dict[str, Any]]:
        """Extrai vídeos da página de resultados."""
        videos = []
        
        html = getattr(response, 'text', '') or str(response)
        
        # Extrair IDs e títulos do JSON embutido do YouTube
        video_ids = re.findall(r'"videoId":"([^"]+)"', html)
        titles = re.findall(r'"title":\{"runs":\[\{"text":"([^"]+)"\}', html)
        channels = re.findall(r'"ownerChannelName":"([^"]+)"', html)
        views = re.findall(r'"viewCountText":\{"simpleText":"([^"]+)"\}', html)
        
        for i, title in enumerate(titles[:20]):
            if not title.strip():
                continue
                
            vid_id = video_ids[i] if i < len(video_ids) else ""
            
            video = {
                "title": title.strip(),
                "link": f"https://www.youtube.com/watch?v={vid_id}" if vid_id else "",
                "channel": channels[i].strip() if i < len(channels) else "",
                "views": views[i].strip() if i < len(views) else "",
                "channel_url": "",
            }
            videos.append(video)
        
        return videos
